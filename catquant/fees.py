"""A-share fee model for CatQuant backtesting."""

__all__ = ["calculate_cost"]

# A-share fee constants
COMMISSION_RATE = 0.00025       # 万2.5 per side
COMMISSION_MIN = 5.0            # Min 5 CNY per trade
STAMP_TAX_RATE = 0.001          # 千1, sell only
TRANSFER_FEE_RATE = 0.00001     # 十万分之一, Shanghai only

# VectorBT approximation (averaged per side)
VBT_FEES = 0.00125              # (buy_commission + sell_commission + stamp_tax) / 2
VBT_FIXED_FEES = 5              # Min commission

# ETF (no stamp tax)
VBT_FEES_ETF = 0.00025
VBT_FIXED_FEES_ETF = 5


def calculate_cost(amount: float, side: str = "buy", market: str = "sh") -> float:
    """Calculate exact transaction cost for a single trade.

    Args:
        amount: Trade amount in CNY.
        side: 'buy' or 'sell'.
        market: 'sh' (Shanghai) or 'sz' (Shenzhen).

    Returns:
        Total fee in CNY.
    """
    commission = max(amount * COMMISSION_RATE, COMMISSION_MIN)
    stamp_tax = amount * STAMP_TAX_RATE if side == "sell" else 0.0
    transfer_fee = amount * TRANSFER_FEE_RATE if market == "sh" else 0.0
    return commission + stamp_tax + transfer_fee
