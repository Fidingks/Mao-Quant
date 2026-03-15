---
name: data
spec: "skill-manifest/0.1"
description: Data engine reference. Unified SecurityData from FaceCat API, TDX binary, and user CSV.
user-invocable: false
allowed-tools: Read, Glob, Grep, Bash
---

# Data Engine Reference

Internal package `catquant.data_engine`. All sources return `List[SecurityData]`.

## SecurityData (K-line bar)

| Field | Type | Description |
|-------|------|-------------|
| date | int | Epoch seconds (UTC), Beijing midnight for daily |
| open / high / low / close | float | OHLC prices |
| volume | int | Volume in shares |
| amount | float | Turnover in CNY |

Methods: `to_dict()`, `SecurityData.from_dict(d)`, `copy(other)`

## LatestData (real-time snapshot, FaceCat)

| Field | Type | Description |
|-------|------|-------------|
| code / name | str | Symbol and name |
| close / high / low / open | float | Prices |
| volume / amount | int/float | Volume and turnover |
| lastClose | float | Previous close |
| buyPrices / buyVolumes | list | Bid 1-5 |
| sellPrices / sellVolumes | list | Ask 1-5 |

## PriceData (batch overview, FaceCat)

| Field | Type | Description |
|-------|------|-------------|
| code / name | str | Symbol and name |
| close / high / low / open | float | Prices |
| volume / amount | int/float | Volume and turnover |
| lastClose | float | Previous close |
| totalShares / flowShares | int | Total and float shares |
| pe | float | P/E ratio |
| upperLimit / lowerLimit | float | Price limits |

## Symbol Format

`normalize_symbol()` auto-converts between `600000.SH` (FaceCat) and `SH600000` (TDX).

## API

```python
get_history(code, cycle=1440, count=1000, source="facecat",
            tdx_dir="", refresh=False, verify_ssl=True) -> List[SecurityData]

get_latest(code) -> LatestData

get_prices(codes="all", count=200) -> Dict[str, PriceData]
```

## Cache

FaceCat data cached as `{CACHE_DIR}/{code}_{cycle}.csv`. `refresh=True` bypasses cache.

## User CSV

No built-in loader. Agent writes a converter to `List[SecurityData]` in the backtest script when users provide custom data files.

## FaceCat API Response Formats (debug)

Base URL: env `FaceCat_URL`, endpoint `/quote`.

- **getkline**: Line 0 header, lines 1+ CSV: `date,open,high,low,close,volume,amount`
- **getnewdata**: Single CSV line. `[0]code [1]name [2]close [3]high [4]low [5]open [6]volume [7]amount [8]lastClose [9-13]bid_prices [14-18]bid_volumes [19-23]ask_prices [24-28]ask_volumes [29]datetime`
- **price**: Multi-line CSV. `[0]code [1]name [2]close [3]high [4]low [5]open [6]volume [7]amount [8]lastClose [9]totalShares [10]flowShares [11]pe [12]? [13]? [14]upperLimit [15]lowerLimit [16]datetime`

## Environment

- `FaceCat_URL`: API base (default `https://www.jjmfc.com:9969`)
- `TDX_DIR`: TongDaXin path
- `CACHE_DIR`: Cache directory (default `./cache`)
