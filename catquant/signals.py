"""Signal utilities for CatQuant backtesting."""

from typing import List, Tuple, Union

import numpy as np

ArrayLike = Union[List[float], np.ndarray]

__all__ = ["exrem", "cross_above", "cross_below"]


def exrem(buy: ArrayLike, sell: ArrayLike) -> Tuple[np.ndarray, np.ndarray]:
    """Remove duplicate consecutive signals for both buy and sell.

    Keep only the first buy=True before a sell=True alternation, and vice versa.

    Args:
        buy: Buy signal array (numpy array, list, or any sequence of booleans).
        sell: Sell signal array (numpy array, list, or any sequence of booleans).

    Returns:
        (cleaned_buy, cleaned_sell) as numpy boolean arrays.
    """
    buy = np.asarray(buy, dtype=bool)
    sell = np.asarray(sell, dtype=bool)
    n = len(buy)
    cb = np.zeros(n, dtype=bool)
    cs = np.zeros(n, dtype=bool)

    # Clean buy: keep first buy before a sell
    active = False
    for i in range(n):
        if not active and buy[i]:
            cb[i] = True
            active = True
        if sell[i]:
            active = False

    # Clean sell: keep first sell after a buy
    active = False
    for i in range(n):
        if not active and sell[i]:
            cs[i] = True
            active = True
        if buy[i]:
            active = False

    return cb, cs


def cross_above(a: ArrayLike, b: Union[ArrayLike, float]) -> np.ndarray:
    """True where a crosses above b. Vectorized, no loops.

    Args:
        a: Array-like, first series.
        b: Array-like, second series (or scalar).

    Returns:
        numpy boolean array, True at crossover points.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    above = a > b
    crossed = above & np.r_[True, ~above[:-1]]
    crossed[0] = False
    return crossed


def cross_below(a: ArrayLike, b: Union[ArrayLike, float]) -> np.ndarray:
    """True where a crosses below b. Vectorized, no loops.

    Args:
        a: Array-like, first series.
        b: Array-like, second series (or scalar).

    Returns:
        numpy boolean array, True at crossover points.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    below = a < b
    crossed = below & np.r_[True, ~below[:-1]]
    crossed[0] = False
    return crossed
