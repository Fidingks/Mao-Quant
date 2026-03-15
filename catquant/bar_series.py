"""BarSeries container for CatQuant.

Wraps List[SecurityData] with a summary repr that never exposes raw data.
Implements the sequence protocol for backward compatibility.
"""

from datetime import datetime, timezone, timedelta
from typing import Iterator, List, Union

from catquant.models import SecurityData

__all__ = ["BarSeries"]

_TZ_BJ = timezone(timedelta(hours=8))


def _epoch_to_date(epoch: int) -> str:
    if epoch <= 0:
        return "?"
    return datetime.fromtimestamp(epoch, tz=_TZ_BJ).strftime("%Y-%m-%d")


class BarSeries:
    """Sequence container for SecurityData bars.

    Provides summary repr (no raw data leak), sequence protocol for
    backward compatibility, and metadata (code, cycle).
    """

    __slots__ = ("_bars", "_code", "_cycle")

    def __init__(self, bars: List[SecurityData], code: str = "", cycle: int = 0):
        self._bars = list(bars)
        self._code = code
        self._cycle = cycle

    def __repr__(self) -> str:
        n = len(self._bars)
        if n == 0:
            return f"BarSeries({self._code}, 0 bars)"
        first = _epoch_to_date(self._bars[0].date)
        last = _epoch_to_date(self._bars[-1].date)
        close = self._bars[-1].close
        return f"BarSeries({self._code}, {n} bars, {first} ~ {last}, last={close})"

    def __len__(self) -> int:
        return len(self._bars)

    def __getitem__(self, index: Union[int, slice]) -> Union[SecurityData, "BarSeries"]:
        if isinstance(index, slice):
            return BarSeries(self._bars[index], self._code, self._cycle)
        return self._bars[index]

    def __iter__(self) -> Iterator[SecurityData]:
        return iter(self._bars)

    def __bool__(self) -> bool:
        return len(self._bars) > 0

    def __contains__(self, item: object) -> bool:
        return item in self._bars

    @property
    def code(self) -> str:
        return self._code

    @property
    def cycle(self) -> int:
        return self._cycle
