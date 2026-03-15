"""Technical indicators for CatQuant.

Vectorized numpy implementations. Production-tested from FaceCat trading platform.

Usage in scanner filter_fn:

    from catquant.indicators import bars_to_arrays, MA, getKDJData, getRSIData

    def filter_fn(code, name, bars):
        close, high, low, vol = bars_to_arrays(bars)
        # ... use indicator functions ...
"""

from typing import List, Tuple, Union

import numpy as np

ArrayLike = Union[List[float], np.ndarray]

__all__ = [
    "bars_to_arrays", "getEMA", "ema_series", "MA", "REF", "HHV", "LLV",
    "getDIF", "getMACD", "getMACDData", "getKDJData", "getRSIData",
    "getBollData", "getRocData", "getBIASData", "getDMAData", "getBBIData",
    "getWRData", "getCCIData", "getTRIXData",
]


# ---------------------------------------------------------------------------
# Helper: extract arrays from SecurityData bars
# ---------------------------------------------------------------------------

def bars_to_arrays(bars: list) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract close, high, low, volume arrays from List[SecurityData].

    Returns:
        (close, high, low, volume) as numpy arrays.
    """
    close = np.array([b.close for b in bars], dtype=np.float64)
    high = np.array([b.high for b in bars], dtype=np.float64)
    low = np.array([b.low for b in bars], dtype=np.float64)
    volume = np.array([b.volume for b in bars], dtype=np.float64)
    return close, high, low, volume


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def getEMA(n: int, value: float, lastEMA: float) -> float:
    """Calculate single-point EMA (backward compatible).
    n: period
    value: current value
    lastEMA: previous EMA value"""
    return (value * 2 + lastEMA * (n - 1)) / (n + 1)


def ema_series(ticks: ArrayLike, n: int) -> np.ndarray:
    """Calculate full EMA series over an array.

    Args:
        ticks: price array (list or numpy array).
        n: EMA period.

    Returns:
        numpy array of EMA values (same length as ticks).
    """
    ticks = np.asarray(ticks, dtype=np.float64)
    out = np.empty_like(ticks)
    alpha = 2.0 / (n + 1)
    out[0] = ticks[0]
    for i in range(1, len(ticks)):
        out[i] = alpha * ticks[i] + (1.0 - alpha) * out[i - 1]
    return out


def MA(ticks: ArrayLike, days: int) -> np.ndarray:
    """Moving average using numpy cumsum.
    ticks: price array
    days: period"""
    ticks = np.asarray(ticks, dtype=np.float64)
    n = len(ticks)
    cs = np.cumsum(ticks)
    mas = np.empty(n, dtype=np.float64)
    # Before full window: expanding average
    for i in range(min(days, n)):
        mas[i] = cs[i] / (i + 1)
    # Full window: rolling average
    if days < n:
        mas[days:] = (cs[days:] - cs[:n - days]) / days
    return mas


def REF(ticks: ArrayLike, days: int) -> np.ndarray:
    """REF: reference previous value using np.roll.
    ticks: data array
    days: offset"""
    ticks = np.asarray(ticks, dtype=np.float64)
    out = np.roll(ticks, days)
    out[:days] = ticks[0]
    return out


def HHV(ticks: ArrayLike, days: int) -> np.ndarray:
    """Highest value over N periods.
    ticks: high price array
    days: period"""
    ticks = np.asarray(ticks, dtype=np.float64)
    n = len(ticks)
    hhv = np.empty(n, dtype=np.float64)
    # Use sliding window approach
    for i in range(n):
        start = max(0, i - days + 1) if i >= days else 0
        hhv[i] = np.max(ticks[start:i + 1])
    return hhv


def LLV(ticks: ArrayLike, days: int) -> np.ndarray:
    """Lowest value over N periods.
    ticks: low price array
    days: period"""
    ticks = np.asarray(ticks, dtype=np.float64)
    n = len(ticks)
    llv = np.empty(n, dtype=np.float64)
    for i in range(n):
        start = max(0, i - days + 1) if i >= days else 0
        llv[i] = np.min(ticks[start:i + 1])
    return llv


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------

def getDIF(close12: ArrayLike, close26: ArrayLike) -> np.ndarray:
    """DIF = EMA12 - EMA26."""
    return np.asarray(close12, dtype=np.float64) - np.asarray(close26, dtype=np.float64)


def getMACD(dif: ArrayLike, dea: ArrayLike) -> np.ndarray:
    """MACD = (DIF - DEA) * 2."""
    return (np.asarray(dif, dtype=np.float64) - np.asarray(dea, dtype=np.float64)) * 2


def getMACDData(ticks: ArrayLike, short: int = 12, long: int = 26, mid: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate complete MACD (DIF, DEA, MACD).

    Args:
        ticks: close price array
        short: short EMA period (default 12)
        long: long EMA period (default 26)
        mid: signal line period (default 9)

    Returns:
        (dif, dea, macd) as three numpy arrays.
    """
    es = ema_series(ticks, short)
    el = ema_series(ticks, long)
    dif = es - el
    dea = ema_series(dif, mid)
    macd = (dif - dea) * 2
    return dif, dea, macd


# ---------------------------------------------------------------------------
# KDJ
# ---------------------------------------------------------------------------

def getKDJData(highArr: ArrayLike, lowArr: ArrayLike, closeArr: ArrayLike, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate KDJ indicator.

    Args:
        highArr: high price array
        lowArr: low price array
        closeArr: close price array
        n: RSV period (default 9)
        m1: K smooth factor (default 3)
        m2: D smooth factor (default 3)

    Returns:
        (ks, ds, js) as three numpy arrays.
    """
    highArr = np.asarray(highArr, dtype=np.float64)
    lowArr = np.asarray(lowArr, dtype=np.float64)
    closeArr = np.asarray(closeArr, dtype=np.float64)
    length = len(highArr)

    hhv = HHV(highArr, n)
    llv = LLV(lowArr, n)

    diff = hhv - llv
    rsv = np.where(diff != 0, (closeArr - llv) / diff * 100, 0.0)

    ks = np.empty(length, dtype=np.float64)
    ds = np.empty(length, dtype=np.float64)
    js = np.empty(length, dtype=np.float64)

    ks[0] = rsv[0]
    ds[0] = rsv[0]
    alpha_k = 1.0 / m1
    alpha_d = 1.0 / m2
    for i in range(1, length):
        ks[i] = (1 - alpha_k) * ks[i - 1] + alpha_k * rsv[i]
        ds[i] = (1 - alpha_d) * ds[i - 1] + alpha_d * ks[i]
    js = 3.0 * ks - 2.0 * ds
    return ks, ds, js


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------

def getRSIData(ticks: ArrayLike, n1: int = 6, n2: int = 12, n3: int = 24) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate RSI indicator (3 periods).

    Args:
        ticks: close price array
        n1: short period (default 6)
        n2: mid period (default 12)
        n3: long period (default 24)

    Returns:
        (rsi1, rsi2, rsi3) as three numpy arrays.
    """
    ticks = np.asarray(ticks, dtype=np.float64)
    length = len(ticks)

    def _rsi(period):
        rsi = np.zeros(length, dtype=np.float64)
        sm = 0.0
        sa = 0.0
        for i in range(1, length):
            diff = ticks[i] - ticks[i - 1]
            m = max(diff, 0.0)
            a = abs(diff)
            sm = (m + (period - 1) * sm) / period
            sa = (a + (period - 1) * sa) / period
            if sa != 0:
                rsi[i] = sm / sa * 100
        return rsi

    return _rsi(n1), _rsi(n2), _rsi(n3)


# ---------------------------------------------------------------------------
# BOLL
# ---------------------------------------------------------------------------

def getBollData(ticks: ArrayLike, maDays: int = 20) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Bollinger Bands.

    Args:
        ticks: close price array
        maDays: MA period (default 20)

    Returns:
        (ups, mas, lows) as three numpy arrays -- upper, middle, lower bands.
    """
    ticks = np.asarray(ticks, dtype=np.float64)
    n = len(ticks)
    ups = np.empty(n, dtype=np.float64)
    mas_arr = np.empty(n, dtype=np.float64)
    lows = np.empty(n, dtype=np.float64)

    for i in range(n):
        start = max(0, i - maDays + 1) if i >= maDays else 0
        window = ticks[start:i + 1]
        ma = np.mean(window)
        md = np.sqrt(np.mean((window - ma) ** 2))
        mas_arr[i] = ma
        ups[i] = ma + 2 * md
        lows[i] = ma - 2 * md

    return ups, mas_arr, lows


# ---------------------------------------------------------------------------
# ROC
# ---------------------------------------------------------------------------

def getRocData(ticks: ArrayLike, n: int = 12, m: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate ROC (Rate of Change).

    Args:
        ticks: close price array
        n: ROC period (default 12)
        m: MAROC MA period (default 6)

    Returns:
        (roc, maroc) as two numpy arrays.
    """
    ticks = np.asarray(ticks, dtype=np.float64)
    length = len(ticks)
    roc = np.zeros(length, dtype=np.float64)
    for i in range(length):
        ref = ticks[i - n] if i >= n else ticks[0]
        if ref != 0:
            roc[i] = 100 * (ticks[i] - ref) / ref
    maroc = MA(roc, m)
    return roc, maroc


# ---------------------------------------------------------------------------
# BIAS
# ---------------------------------------------------------------------------

def getBIASData(ticks: ArrayLike, n1: int = 6, n2: int = 12, n3: int = 24) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate BIAS (deviation from MA).

    Args:
        ticks: close price array
        n1, n2, n3: MA periods

    Returns:
        (bias1, bias2, bias3) as three numpy arrays.
    """
    ticks = np.asarray(ticks, dtype=np.float64)
    ma1 = MA(ticks, n1)
    ma2 = MA(ticks, n2)
    ma3 = MA(ticks, n3)
    bias1 = (ticks - ma1) / ma1 * 100
    bias2 = (ticks - ma2) / ma2 * 100
    bias3 = (ticks - ma3) / ma3 * 100
    return bias1, bias2, bias3


# ---------------------------------------------------------------------------
# DMA
# ---------------------------------------------------------------------------

def getDMAData(ticks: ArrayLike, n1: int = 10, n2: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate DMA (Difference of Moving Averages).

    Args:
        ticks: close price array
        n1: short MA period (default 10)
        n2: long MA period (default 50)

    Returns:
        (dif, difma) as two numpy arrays.
    """
    ma_short = MA(ticks, n1)
    ma_long = MA(ticks, n2)
    dif = ma_short - ma_long
    difma = MA(dif, n1)
    return dif, difma


# ---------------------------------------------------------------------------
# BBI
# ---------------------------------------------------------------------------

def getBBIData(ticks: ArrayLike, n1: int = 3, n2: int = 6, n3: int = 12, n4: int = 24) -> np.ndarray:
    """Calculate BBI (Bull and Bear Index).

    Args:
        ticks: close price array
        n1-n4: four MA periods

    Returns:
        bbi as a numpy array.
    """
    ma1 = MA(ticks, n1)
    ma2 = MA(ticks, n2)
    ma3 = MA(ticks, n3)
    ma4 = MA(ticks, n4)
    return (ma1 + ma2 + ma3 + ma4) / 4


# ---------------------------------------------------------------------------
# WR (Williams %R)
# ---------------------------------------------------------------------------

def getWRData(closeArr: ArrayLike, highArr: ArrayLike, lowArr: ArrayLike, n1: int = 10, n2: int = 6) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate WR (Williams %R).

    Args:
        closeArr: close price array
        highArr: high price array
        lowArr: low price array
        n1: first period (default 10)
        n2: second period (default 6)

    Returns:
        (wr1, wr2) as two numpy arrays.
    """
    closeArr = np.asarray(closeArr, dtype=np.float64)
    h1 = HHV(highArr, n1)
    h2 = HHV(highArr, n2)
    l1 = LLV(lowArr, n1)
    l2 = LLV(lowArr, n2)
    diff1 = h1 - l1
    diff2 = h2 - l2
    wr1 = np.where(diff1 != 0, 100 * (h1 - closeArr) / diff1, 0.0)
    wr2 = np.where(diff2 != 0, 100 * (h2 - closeArr) / diff2, 0.0)
    return wr1, wr2


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------

def getCCIData(closeArr: ArrayLike, highArr: ArrayLike, lowArr: ArrayLike, n: int = 14) -> np.ndarray:
    """Calculate CCI (Commodity Channel Index).
    CCI = (TP - MA) / MD / 0.015

    Args:
        closeArr: close price array
        highArr: high price array
        lowArr: low price array
        n: period (default 14)

    Returns:
        cci as a numpy array.
    """
    closeArr = np.asarray(closeArr, dtype=np.float64)
    highArr = np.asarray(highArr, dtype=np.float64)
    lowArr = np.asarray(lowArr, dtype=np.float64)
    tp = (closeArr + highArr + lowArr) / 3
    maClose = MA(closeArr, n)
    md = MA(maClose - closeArr, n)
    cci = np.where(md != 0, (tp - maClose) / (md * 0.015), 0.0)
    return cci


# ---------------------------------------------------------------------------
# TRIX
# ---------------------------------------------------------------------------

def getTRIXData(ticks: ArrayLike, n: int = 12, m: int = 20) -> Tuple[np.ndarray, np.ndarray]:
    """Calculate TRIX (Triple Exponential Moving Average).

    Args:
        ticks: close price array
        n: EMA period (default 12)
        m: signal MA period (default 20)

    Returns:
        (trix, matrix) as two numpy arrays.
    """
    ema1 = ema_series(ticks, n)
    ema2 = ema_series(ema1, n)
    mtr = ema_series(ema2, n)
    ref = REF(mtr, 1)
    trix_arr = np.where(ref != 0, 100 * (mtr - ref) / ref, 0.0)
    matrix_arr = MA(trix_arr, m)
    return trix_arr, matrix_arr
