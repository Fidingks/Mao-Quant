"""CatQuant A-share backtest engine.

Single-position, event-driven backtester with full A-share rule support:
T+1, limit up/down, round-lot (100 shares), commission/stamp tax/transfer fee.
"""

import json
import os
from dataclasses import dataclass, field
from typing import List

import numpy as np

from catquant import fees

__all__ = ["Trade", "BacktestResult", "run", "export", "get_limit_pct"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    """Record of a single round-trip (or open) trade."""
    entry_date: int = 0           # epoch seconds
    entry_price: float = 0.0
    exit_date: int = 0            # 0 = still open
    exit_price: float = 0.0       # 0.0 = still open
    shares: int = 0
    pnl: float = 0.0              # net P&L after fees
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    holding_bars: int = 0
    entry_bar: int = 0            # index into bars array
    exit_bar: int = -1            # -1 = still open


@dataclass
class BacktestResult:
    """Complete backtest output."""
    dates: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    equity: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    cash: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    positions: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.int64))
    drawdown: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    returns: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    trades: List[Trade] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_limit_pct(code: str) -> float:
    """Return limit-up/down percentage based on stock code prefix.

    60/00 -> 10% (main board)
    30/688 -> 20% (ChiNext / STAR)
    8/4 -> 30% (BSE)
    """
    # Strip market prefix like SH/SZ/BJ
    pure = code.upper().lstrip("SHSZBJ.")
    if pure.startswith("30") or pure.startswith("688"):
        return 0.20
    if pure.startswith("8") or pure.startswith("4"):
        return 0.30
    return 0.10


def _is_limit_up(close: float, prev_close: float, limit_pct: float) -> bool:
    limit_price = round(prev_close * (1 + limit_pct), 2)
    return close >= limit_price - 0.01


def _is_limit_down(close: float, prev_close: float, limit_pct: float) -> bool:
    limit_price = round(prev_close * (1 - limit_pct), 2)
    return close <= limit_price + 0.01


def _calc_shares(
    cash: float,
    price: float,
    fixed_size: int,
    size_pct: float,
    ref_equity: float,
) -> int:
    """Calculate shares to buy, rounded down to nearest 100 (1 lot)."""
    if fixed_size > 0:
        raw = fixed_size
    else:
        raw = int(size_pct * ref_equity / price)
    lots = raw // 100
    max_affordable = int(cash / price) // 100
    return min(lots, max_affordable) * 100


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _compute_metrics(
    equity: np.ndarray,
    returns: np.ndarray,
    drawdown: np.ndarray,
    trades: List[Trade],
    initial_capital: float,
) -> dict:
    n = len(equity)
    final_eq = equity[-1] if n > 0 else initial_capital
    total_return = (final_eq / initial_capital) - 1.0

    # Approximate trading days per year
    annual_factor = 244.0
    years = n / annual_factor if n > 0 else 1.0
    annual_return = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else 0.0

    # Max drawdown
    max_dd = float(np.min(drawdown)) if n > 0 else 0.0

    # Max drawdown duration (in bars)
    max_dd_duration = 0
    if n > 0:
        running_max = np.maximum.accumulate(equity)
        in_dd = equity < running_max
        current_dur = 0
        for flag in in_dd:
            if flag:
                current_dur += 1
                max_dd_duration = max(max_dd_duration, current_dur)
            else:
                current_dur = 0

    # Trade stats
    closed_trades = [t for t in trades if t.exit_bar >= 0]
    total_trades = len(closed_trades)
    wins = [t for t in closed_trades if t.pnl > 0]
    losses = [t for t in closed_trades if t.pnl <= 0]
    win_rate = len(wins) / total_trades if total_trades > 0 else 0.0

    gross_profit = sum(t.pnl for t in wins) if wins else 0.0
    gross_loss = abs(sum(t.pnl for t in losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    avg_pnl = sum(t.pnl for t in closed_trades) / total_trades if total_trades > 0 else 0.0
    avg_holding = (
        sum(t.holding_bars for t in closed_trades) / total_trades
        if total_trades > 0 else 0.0
    )

    # Sharpe ratio (annualized, risk-free = 0)
    if n > 1 and np.std(returns[1:]) > 0:
        sharpe_ratio = float(np.mean(returns[1:]) / np.std(returns[1:]) * np.sqrt(annual_factor))
    else:
        sharpe_ratio = 0.0

    # Sortino ratio (downside deviation)
    if n > 1:
        downside = returns[1:].copy()
        downside[downside > 0] = 0.0
        down_std = float(np.std(downside))
        sortino_ratio = float(np.mean(returns[1:]) / down_std * np.sqrt(annual_factor)) if down_std > 0 else 0.0
    else:
        sortino_ratio = 0.0

    # Calmar ratio
    calmar_ratio = annual_return / abs(max_dd) if max_dd != 0 else float("inf")

    # Per-trade stats
    avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0

    # Max consecutive wins / losses
    max_consecutive_wins = 0
    max_consecutive_losses = 0
    if closed_trades:
        cw = 0
        cl = 0
        for t in closed_trades:
            if t.pnl > 0:
                cw += 1
                cl = 0
                max_consecutive_wins = max(max_consecutive_wins, cw)
            else:
                cl += 1
                cw = 0
                max_consecutive_losses = max(max_consecutive_losses, cl)

    return {
        "total_return": round(total_return, 6),
        "annual_return": round(annual_return, 6),
        "max_drawdown": round(max_dd, 6),
        "max_drawdown_duration": max_dd_duration,
        "total_trades": total_trades,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "avg_pnl": round(avg_pnl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_holding_bars": round(avg_holding, 2),
        "max_consecutive_wins": max_consecutive_wins,
        "max_consecutive_losses": max_consecutive_losses,
        "sharpe_ratio": round(sharpe_ratio, 4),
        "sortino_ratio": round(sortino_ratio, 4),
        "calmar_ratio": round(calmar_ratio, 4),
        "initial_capital": initial_capital,
        "final_equity": round(final_eq, 2),
    }


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def run(
    bars,
    buy_signal: np.ndarray,
    sell_signal: np.ndarray,
    initial_capital: float = 100_000.0,
    size: int = 0,
    size_pct: float = 0.95,
    market: str = "sh",
    limit_pct: float = 0.10,
    slippage: float = 0.0,
    price_field: str = "close",
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
) -> BacktestResult:
    """Run a single-position backtest on A-share bars.

    Args:
        bars: List[SecurityData] with OHLCV fields.
        buy_signal: boolean array (N,), True = buy signal on that bar.
        sell_signal: boolean array (N,), True = sell signal on that bar.
        initial_capital: Starting cash in CNY.
        size: Fixed share count per trade. 0 = use size_pct instead.
        size_pct: Fraction of equity to allocate (default 0.95).
        market: 'sh' or 'sz' for fee calculation.
        limit_pct: Limit up/down threshold (0.10, 0.20, or 0.30).
        slippage: Per-share slippage in CNY.
        price_field: 'close' = execute on current bar close,
                     'open' = execute on next bar open.
        stop_loss: Stop-loss threshold (0.0=disabled, 0.05=5% loss).
        take_profit: Take-profit threshold (0.0=disabled, 0.10=10% gain).

    Returns:
        BacktestResult with equity curve, trades, and metrics.
    """
    N = len(bars)
    if N == 0:
        return BacktestResult()

    buy_signal = np.asarray(buy_signal, dtype=bool)
    sell_signal = np.asarray(sell_signal, dtype=bool)
    if len(buy_signal) != N or len(sell_signal) != N:
        raise ValueError(
            f"Signal length mismatch: bars={N}, "
            f"buy_signal={len(buy_signal)}, sell_signal={len(sell_signal)}"
        )

    # Extract OHLCV into numpy arrays
    dates_arr = np.array([b.date for b in bars], dtype=np.int64)
    open_arr = np.array([b.open for b in bars], dtype=np.float64)
    high_arr = np.array([b.high for b in bars], dtype=np.float64)
    low_arr = np.array([b.low for b in bars], dtype=np.float64)
    close_arr = np.array([b.close for b in bars], dtype=np.float64)
    volume_arr = np.array([b.volume for b in bars], dtype=np.int64)

    # Previous close for limit detection
    prev_close = np.empty(N, dtype=np.float64)
    prev_close[0] = open_arr[0]
    prev_close[1:] = close_arr[:-1]

    use_sl = stop_loss > 0.0
    use_tp = take_profit > 0.0

    # Output arrays
    cash_arr = np.zeros(N, dtype=np.float64)
    pos_arr = np.zeros(N, dtype=np.int64)
    equity_arr = np.zeros(N, dtype=np.float64)

    # State
    cash = initial_capital
    shares_held = 0
    buy_bar = -1
    entry_price = 0.0
    entry_fee = 0.0
    entry_date = 0
    trades: List[Trade] = []

    def _close_position(i, sell_price):
        """Helper to close current position at sell_price on bar i."""
        nonlocal cash, shares_held
        sell_amount = shares_held * sell_price
        s_fee = fees.calculate_cost(sell_amount, side="sell", market=market)
        pnl = (sell_price - entry_price) * shares_held - entry_fee - s_fee
        trades.append(Trade(
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=int(dates_arr[i]),
            exit_price=sell_price,
            shares=shares_held,
            pnl=pnl,
            entry_fee=entry_fee,
            exit_fee=s_fee,
            holding_bars=i - buy_bar,
            entry_bar=buy_bar,
            exit_bar=i,
        ))
        cash += sell_amount - s_fee
        shares_held = 0

    if price_field == "open":
        # Signal on bar[i] -> execute on bar[i+1] open
        pending_buy = False
        pending_sell = False

        for i in range(N):
            ep = open_arr[i]  # execution price base
            halted = volume_arr[i] == 0
            lu = _is_limit_up(close_arr[i], prev_close[i], limit_pct)
            ld = _is_limit_down(close_arr[i], prev_close[i], limit_pct)

            # Execute pending sell
            if pending_sell and shares_held > 0 and not halted and not ld:
                sell_price = ep - slippage
                _close_position(i, sell_price)
                pending_sell = False

            # Execute pending buy
            if pending_buy and shares_held == 0 and not halted and not lu:
                buy_price = ep + slippage
                ref_equity = cash  # all in cash before buy
                n_shares = _calc_shares(cash, buy_price, size, size_pct, ref_equity)
                if n_shares >= 100:
                    buy_amount = n_shares * buy_price
                    b_fee = fees.calculate_cost(buy_amount, side="buy", market=market)
                    if cash >= buy_amount + b_fee:
                        cash -= buy_amount + b_fee
                        shares_held = n_shares
                        buy_bar = i
                        entry_price = buy_price
                        entry_fee = b_fee
                        entry_date = int(dates_arr[i])
                pending_buy = False

            # Stop-loss / take-profit check (intrabar, price_field="open")
            # In open mode, after buy executes on this bar, SL/TP can trigger
            # immediately on the same bar since price has already moved.
            if shares_held > 0 and i > buy_bar and not halted:
                sl_triggered = use_sl and low_arr[i] <= entry_price * (1 - stop_loss)
                tp_triggered = use_tp and high_arr[i] >= entry_price * (1 + take_profit)
                if sl_triggered or tp_triggered:
                    if sl_triggered:
                        exit_price = round(entry_price * (1 - stop_loss), 2)
                    else:
                        exit_price = round(entry_price * (1 + take_profit), 2)
                    _close_position(i, exit_price)
                    pending_sell = False
                    # Skip signal reading since we just exited
                    cash_arr[i] = cash
                    pos_arr[i] = shares_held
                    equity_arr[i] = cash + shares_held * close_arr[i]
                    continue

            # Read today's signals for next-bar execution
            if sell_signal[i] and shares_held > 0 and i > buy_bar:
                pending_sell = True
            if buy_signal[i] and shares_held == 0:
                pending_buy = True

            # Record state
            cash_arr[i] = cash
            pos_arr[i] = shares_held
            equity_arr[i] = cash + shares_held * close_arr[i]

    else:
        # price_field == "close": execute on current bar close
        for i in range(N):
            ep = close_arr[i]
            halted = volume_arr[i] == 0
            lu = _is_limit_up(close_arr[i], prev_close[i], limit_pct)
            ld = _is_limit_down(close_arr[i], prev_close[i], limit_pct)

            # Stop-loss / take-profit (checked before sell signal, higher priority)
            if shares_held > 0 and i > buy_bar and not halted:
                sl_triggered = use_sl and low_arr[i] <= entry_price * (1 - stop_loss)
                tp_triggered = use_tp and high_arr[i] >= entry_price * (1 + take_profit)
                if sl_triggered or tp_triggered:
                    if sl_triggered:
                        exit_price = round(entry_price * (1 - stop_loss), 2)
                    else:
                        exit_price = round(entry_price * (1 + take_profit), 2)
                    _close_position(i, exit_price)
                    # Record and continue (skip normal sell/buy)
                    cash_arr[i] = cash
                    pos_arr[i] = shares_held
                    equity_arr[i] = cash + shares_held * close_arr[i]
                    continue

            # Sell check
            if sell_signal[i] and shares_held > 0 and i > buy_bar and not halted and not ld:
                sell_price = ep - slippage
                _close_position(i, sell_price)

            # Buy check
            if buy_signal[i] and shares_held == 0 and not halted and not lu:
                buy_price = ep + slippage
                ref_equity = cash
                n_shares = _calc_shares(cash, buy_price, size, size_pct, ref_equity)
                if n_shares >= 100:
                    buy_amount = n_shares * buy_price
                    b_fee = fees.calculate_cost(buy_amount, side="buy", market=market)
                    if cash >= buy_amount + b_fee:
                        cash -= buy_amount + b_fee
                        shares_held = n_shares
                        buy_bar = i
                        entry_price = buy_price
                        entry_fee = b_fee
                        entry_date = int(dates_arr[i])

            # Record state
            cash_arr[i] = cash
            pos_arr[i] = shares_held
            equity_arr[i] = cash + shares_held * close_arr[i]

    # Mark open position as unclosed trade
    if shares_held > 0:
        trades.append(Trade(
            entry_date=entry_date,
            entry_price=entry_price,
            exit_date=0,
            exit_price=0.0,
            shares=shares_held,
            pnl=0.0,
            entry_fee=entry_fee,
            exit_fee=0.0,
            holding_bars=N - 1 - buy_bar,
            entry_bar=buy_bar,
            exit_bar=-1,
        ))

    # Returns
    returns_arr = np.zeros(N, dtype=np.float64)
    if N > 1:
        returns_arr[1:] = np.diff(equity_arr) / equity_arr[:-1]

    # Drawdown
    running_max = np.maximum.accumulate(equity_arr)
    drawdown_arr = (equity_arr - running_max) / running_max
    drawdown_arr = np.where(running_max > 0, drawdown_arr, 0.0)

    # Metrics
    m = _compute_metrics(equity_arr, returns_arr, drawdown_arr, trades, initial_capital)

    return BacktestResult(
        dates=dates_arr,
        equity=equity_arr,
        cash=cash_arr,
        positions=pos_arr,
        drawdown=drawdown_arr,
        returns=returns_arr,
        trades=trades,
        metrics=m,
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export(result: "BacktestResult", bars, outdir: str,
           code: str = "", strategy: str = "") -> str:
    """Export backtest result to a single JSON file.

    Generates: {outdir}/result.json

    Args:
        result: BacktestResult from run().
        bars: List[SecurityData] used in backtest.
        outdir: Output directory.
        code: Stock symbol (for metadata).
        strategy: Strategy name (for metadata).

    Returns:
        Path to result.json.
    """
    from datetime import datetime, timezone, timedelta
    tz_bj = timezone(timedelta(hours=8))

    os.makedirs(outdir, exist_ok=True)

    def epoch_to_str(epoch):
        if epoch <= 0:
            return ""
        return datetime.fromtimestamp(epoch, tz=tz_bj).strftime("%Y-%m-%d")

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    klines = []
    for i, b in enumerate(bars):
        klines.append({
            "date": epoch_to_str(b.date),
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": int(b.volume),
            "amount": b.amount,
            "equity": round(float(result.equity[i]), 2),
            "cash": round(float(result.cash[i]), 2),
            "position": int(result.positions[i]),
            "drawdown": round(float(result.drawdown[i]), 6),
            "return": round(float(result.returns[i]), 6),
        })

    trades = []
    for t in result.trades:
        trades.append({
            "entry_date": epoch_to_str(t.entry_date),
            "entry_price": t.entry_price,
            "exit_date": epoch_to_str(t.exit_date),
            "exit_price": t.exit_price if t.exit_price > 0 else None,
            "shares": int(t.shares),
            "pnl": round(t.pnl, 2),
            "entry_fee": round(t.entry_fee, 2),
            "exit_fee": round(t.exit_fee, 2),
            "holding_bars": int(t.holding_bars),
        })

    data = {
        "code": code,
        "strategy": strategy,
        "metrics": result.metrics,
        "klines": klines,
        "trades": trades,
    }

    out_path = os.path.join(outdir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)

    print(f"Exported to {out_path} ({len(bars)} bars, {len(result.trades)} trades)")
    return out_path
