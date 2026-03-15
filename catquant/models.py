"""Data models for CatQuant data engine."""

import re

__all__ = ["SecurityData", "LatestData", "PriceData", "normalize_symbol"]


class SecurityData:
    """Historical K-line bar."""

    __slots__ = [
        "amount", "close", "date", "high", "low", "open", "volume",
        "openInterest",
    ]

    def __init__(self):
        self.amount = 0        # turnover in CNY
        self.close = 0.0       # close price
        self.date = 0          # epoch seconds (UTC)
        self.high = 0.0        # high price
        self.low = 0.0         # low price
        self.open = 0.0        # open price
        self.volume = 0        # volume in shares
        self.openInterest = 0  # open interest (futures)

    def copy(self, other):
        """Copy all fields from another SecurityData."""
        for attr in self.__slots__:
            setattr(self, attr, getattr(other, attr))

    def to_dict(self) -> dict:
        return {attr: getattr(self, attr) for attr in self.__slots__}

    @staticmethod
    def from_dict(d) -> "SecurityData":
        sd = SecurityData()
        for k, v in d.items():
            if k in SecurityData.__slots__:
                setattr(sd, k, v)
        return sd

    def __repr__(self):
        return (f"SecurityData(date={self.date}, open={self.open}, "
                f"high={self.high}, low={self.low}, close={self.close}, "
                f"volume={self.volume}, amount={self.amount})")


class LatestData:
    """Real-time snapshot for a single security (getnewdata)."""

    __slots__ = [
        "code", "name", "close", "high", "low", "open", "volume", "amount",
        "lastClose", "buyPrices", "buyVolumes", "sellPrices", "sellVolumes",
        "datetime",
    ]

    def __init__(self):
        self.code = ""
        self.name = ""
        self.close = 0.0
        self.high = 0.0
        self.low = 0.0
        self.open = 0.0
        self.volume = 0
        self.amount = 0.0
        self.lastClose = 0.0
        self.buyPrices = []    # bid prices 1-5
        self.buyVolumes = []   # bid volumes 1-5
        self.sellPrices = []   # ask prices 1-5
        self.sellVolumes = []  # ask volumes 1-5
        self.datetime = ""

    def __repr__(self):
        return f"LatestData(code={self.code}, name={self.name}, close={self.close})"


class PriceData:
    """Batch price overview for a single security (price)."""

    __slots__ = [
        "code", "name", "close", "high", "low", "open", "volume", "amount",
        "lastClose", "totalShares", "flowShares", "pe",
        "upperLimit", "lowerLimit", "date",
    ]

    def __init__(self):
        self.code = ""
        self.name = ""
        self.close = 0.0
        self.high = 0.0
        self.low = 0.0
        self.open = 0.0
        self.volume = 0
        self.amount = 0.0
        self.lastClose = 0.0
        self.totalShares = 0
        self.flowShares = 0
        self.pe = 0.0
        self.upperLimit = 0.0
        self.lowerLimit = 0.0
        self.date = ""

    def __repr__(self):
        return f"PriceData(code={self.code}, name={self.name}, close={self.close})"


_PREFIX_RE = re.compile(r"^(SH|SZ|BJ)(\d+)$", re.IGNORECASE)
_DOTTED_RE = re.compile(r"^(\d+)\.(SH|SZ|BJ)$", re.IGNORECASE)


def normalize_symbol(symbol: str, fmt: str = "dotted") -> str:
    """Convert between symbol formats.

    Accepts: 'SH600000', '600000.SH', 'sh600000', etc.
    fmt='dotted' -> '600000.SH'  (FaceCat API)
    fmt='prefix' -> 'SH600000'   (TDX reader)
    """
    symbol = symbol.strip()

    m = _PREFIX_RE.match(symbol)
    if m:
        market = m.group(1).upper()
        code = m.group(2)
    else:
        m = _DOTTED_RE.match(symbol)
        if m:
            code = m.group(1)
            market = m.group(2).upper()
        else:
            raise ValueError(
                f"Unrecognized symbol format: '{symbol}'. "
                "Expected 'SH600000' or '600000.SH'."
            )

    if fmt == "dotted":
        return f"{code}.{market}"
    elif fmt == "prefix":
        return f"{market}{code}"
    else:
        raise ValueError(f"Unknown fmt: '{fmt}'. Use 'dotted' or 'prefix'.")
