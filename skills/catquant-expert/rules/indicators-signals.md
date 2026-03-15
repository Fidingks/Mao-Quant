---
name: indicators-signals
description: catquant.indicators reference and signal generation patterns for A-share backtesting
metadata:
  tags: indicators, ema, rsi, macd, kdj, bollinger, signals
  last_verified: "2026-03-15"
---

# catquant Indicators & Signal Generation

**Rule: Use `catquant.indicators` for all technical indicators.**

## Available Indicators

```python
from catquant.indicators import (
    bars_to_arrays,   # (bars) -> (close, high, low, volume) lists
    MA,               # MA(ticks, days) -> list
    getEMA,           # getEMA(n, value, lastEMA) -> float
    getMACDData,      # getMACDData(close, 12, 26, 9) -> (dif, dea, macd)
    getKDJData,       # getKDJData(high, low, close, 9, 3, 3) -> (k, d, j)
    getRSIData,       # getRSIData(close, 6, 12, 24) -> (rsi1, rsi2, rsi3)
    getBollData,      # getBollData(close, 20) -> (upper, mid, lower)
    getRocData,       # getRocData(close, 12, 6) -> (roc, maroc)
    getBIASData,      # getBIASData(close, 6, 12, 24) -> (bias1, bias2, bias3)
    getDMAData,       # getDMAData(close, 10, 50) -> (dif, difma)
    getBBIData,       # getBBIData(close, 3, 6, 12, 24) -> bbi
    getWRData,        # getWRData(close, high, low, 10, 6) -> (wr1, wr2)
    getCCIData,       # getCCIData(close, high, low, 14) -> cci
    getTRIXData,      # getTRIXData(close, 12, 20) -> (trix, matrix)
    HHV, LLV, REF,   # HHV(ticks, n), LLV(ticks, n), REF(ticks, n)
)
```

## Common Signal Patterns

### EMA Crossover
```python
close, high, low, vol = bars_to_arrays(bars)
close_arr = np.array(close)

# Compute EMA series
ema_fast = np.zeros(len(close))
ema_slow = np.zeros(len(close))
for i in range(len(close)):
    ema_fast[i] = getEMA(10, close[i], ema_fast[i-1] if i > 0 else close[i])
    ema_slow[i] = getEMA(20, close[i], ema_slow[i-1] if i > 0 else close[i])

buy_signal = (ema_fast[1:] > ema_slow[1:]) & (ema_fast[:-1] <= ema_slow[:-1])
sell_signal = (ema_fast[1:] < ema_slow[1:]) & (ema_fast[:-1] >= ema_slow[:-1])
```

### MACD
```python
dif, dea, macd_hist = getMACDData(close)
dif = np.array(dif)
dea = np.array(dea)
buy_signal = (dif[1:] > dea[1:]) & (dif[:-1] <= dea[:-1])
sell_signal = (dif[1:] < dea[1:]) & (dif[:-1] >= dea[:-1])
```

### KDJ
```python
ks, ds, js = getKDJData(high, low, close)
js = np.array(js)
buy_signal = (js[1:] < 20) & (js[:-1] >= 20)
sell_signal = (js[1:] > 80) & (js[:-1] <= 80)
```

### RSI
```python
rsi1, rsi2, rsi3 = getRSIData(close)
rsi = np.array(rsi1)
buy_signal = (rsi[1:] < 30) & (rsi[:-1] >= 30)
sell_signal = (rsi[1:] > 70) & (rsi[:-1] <= 70)
```

### Bollinger Bands
```python
upper, mid, lower = getBollData(close)
upper = np.array(upper)
lower = np.array(lower)
close_arr = np.array(close)
buy_signal = (close_arr[1:] < lower[1:]) & (close_arr[:-1] >= lower[:-1])
sell_signal = (close_arr[1:] > upper[1:]) & (close_arr[:-1] <= upper[:-1])
```

## Signal Cleaning (exrem)

Always clean signals to remove duplicate consecutive entries/exits:

```python
from catquant.signals import exrem

buy_clean, sell_clean = exrem(buy_signal, sell_signal)
```
