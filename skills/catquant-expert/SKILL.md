---
name: catquant-expert
spec: "skill-manifest/0.1"
description: CatQuant A-share backtesting API reference and knowledge base. The single source of truth for workflow, API signatures, metrics, indicators, and strategy patterns.
user-invocable: false
---

# CatQuant Reference

## Workflow

```python
import numpy as np
from catquant.data_engine import get_history
from catquant.backtest import run, export, get_limit_pct
from catquant.indicators import bars_to_arrays, ema_series, getMACDData
from catquant.signals import exrem, cross_above, cross_below
from catquant.chart import render

# 1. Data
bars = get_history("600000.SH", cycle=1440, count=1000)
close, high, low, vol = bars_to_arrays(bars)

# 2. Signals
ema_f = ema_series(close, 10)
ema_s = ema_series(close, 30)
buy_raw = cross_above(ema_f, ema_s)
sell_raw = cross_below(ema_f, ema_s)
buy, sell = exrem(buy_raw, sell_raw)

# 3. Backtest
result = run(bars, buy, sell, initial_capital=100000,
             limit_pct=get_limit_pct("600000.SH"),
             price_field="open", market="sh")

# 4. Output
outdir = "backtesting/ema_cross/output"
export(result, bars, outdir, code="600000.SH", strategy="EMA(10,30)")
render(result, bars, outdir)            # kline.png
render(result, bars, outdir, "equity")  # equity.png
```

## API Quick Reference

### backtest.run()

```python
run(bars, buy_signal, sell_signal,
    initial_capital=100000, size=0, size_pct=0.95,
    market="sh", limit_pct=0.10, slippage=0.0,
    price_field="close", stop_loss=0.0, take_profit=0.0)
-> BacktestResult
```

- `price_field="open"`: T+1 compliant (signal on bar[i], execute on bar[i+1] open)
- `limit_pct`: auto-detect via `get_limit_pct(code)` (0.10 main, 0.20 ChiNext/STAR, 0.30 BSE)

### backtest.export()

```python
export(result, bars, outdir, code="", strategy="") -> str
```

Outputs `{outdir}/result.json` with metrics, klines, trades.

### chart.render()

```python
render(result, bars, outdir=".", chart_type="kline", out=None,
       size=(19.2, 10.8), dpi=100, theme="dark",
       overlays=None, panels=None) -> str
```

- `"kline"`: candlestick + volume + equity (3+ subplots)
- `"equity"`: equity curve + drawdown fill (2 subplots)
- `theme`: `"dark"` or `"light"`

#### overlays (lines on price chart)

```python
overlays=[
    {"data": ema5,  "label": "EMA5",  "color": "#ff9800"},
    {"data": ema20, "label": "EMA20", "color": "#2196f3"},
]
```

#### panels (indicator subplots below volume)

```python
panels=[
    {
        "title": "MACD",
        "lines": [
            {"data": dif, "label": "DIF", "color": "#2962ff"},
            {"data": dea, "label": "DEA", "color": "#ff6d00"},
        ],
        "bars": [{"data": macd, "label": "MACD"}],  # auto red/green
        "zero_line": True,
    },
]
```

Panel fields: `title`, `lines` (list), `bars` (list, auto red/green by sign), `fill` (list with `upper`/`lower`/`color`/`alpha`), `zero_line` (bool).

### signals

| Function | Description |
|----------|-------------|
| `exrem(buy, sell)` | Remove duplicate consecutive signals, keep first of each alternation |
| `cross_above(a, b)` | True where `a` crosses above `b` (vectorized) |
| `cross_below(a, b)` | True where `a` crosses below `b` (vectorized) |

### data_engine.get_history()

```python
get_history(code, cycle=1440, count=1000, source="facecat",
            tdx_dir="", refresh=False, verify_ssl=True)
-> List[SecurityData]
```

## Metrics

`result.metrics` keys:

| Key | Description |
|-----|-------------|
| total_return | Total return ratio |
| annual_return | Annualized return |
| max_drawdown | Maximum drawdown ratio |
| max_drawdown_duration | Duration in bars |
| total_trades | Closed trades count |
| winning_trades / losing_trades | Win / loss count |
| win_rate | Win rate ratio |
| profit_factor | Gross profit / gross loss |
| avg_pnl / avg_win / avg_loss | Per-trade P&L |
| avg_holding_bars | Average holding duration |
| max_consecutive_wins / losses | Streak counts |
| sharpe_ratio / sortino_ratio / calmar_ratio | Risk-adjusted ratios |
| initial_capital / final_equity | Capital bookends |

## Indicators (`catquant.indicators`)

Pure Python, zero deps. **Always prefer these over hand-rolling.**

```python
from catquant.indicators import (
    bars_to_arrays,   # (bars) -> (close, high, low, vol) as lists
    MA, getEMA, ema_series,
    getMACDData,      # (close, 12, 26, 9) -> (dif, dea, macd)
    getKDJData,       # (high, low, close, 9, 3, 3) -> (k, d, j)
    getRSIData,       # (close, 6, 12, 24) -> (rsi1, rsi2, rsi3)
    getBollData,      # (close, 20) -> (upper, mid, lower)
    getRocData, getBIASData, getDMAData, getBBIData,
    getWRData, getCCIData, getTRIXData,
    HHV, LLV, REF,
)
```

## Rule Files

| File | Topic |
|------|-------|
| [china-market-rules](rules/china-market-rules.md) | T+1, price limits, lot sizing |
| [china-market-costs](rules/china-market-costs.md) | Fee model details |
| [data-tdx](rules/data-tdx.md) | TDX binary format parsing |
| [indicators-signals](rules/indicators-signals.md) | Indicator usage patterns |
| [parameter-optimization](rules/parameter-optimization.md) | Grid search methods |
| [pitfalls](rules/pitfalls.md) | Common backtesting mistakes |

## Strategy Patterns

| Strategy | Buy Signal | Sell Signal |
|----------|-----------|-------------|
| EMA Cross | `cross_above(ema_fast, ema_slow)` | `cross_below(ema_fast, ema_slow)` |
| MACD | `cross_above(dif, dea)` | `cross_below(dif, dea)` |
| RSI | `cross_below(rsi, oversold)` | `cross_above(rsi, overbought)` |
| KDJ | `cross_above(k, d)` when K < 20 | `cross_below(k, d)` when K > 80 |
| BOLL | `close < lower` | `close > upper` |
