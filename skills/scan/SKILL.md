---
name: scan
spec: "skill-manifest/0.1"
description: Full-market A-share stock screening.
argument-hint: "[screening criteria]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
input:
  criteria: { type: string }
output:
  scan_results: { type: list }
  csv: { type: file, path: "scanning/{name}_scan.csv" }
---

Scan A-share market for stocks matching user criteria.

## Arguments

`$ARGUMENTS` = screening criteria in natural language. If empty, ask the user.

## Instructions

1. Parse criteria into pre_filter (PriceData) and filter_fn (K-line) layers
2. Create script at `scanning/{name}_scan.py`
3. Run and show results

## Choosing scan type

- **Price/volume/PE only** (no K-line needed): `quick_scan(pre_filter)` -- instant
- **Needs history** (MA, MACD, patterns): `scan(filter_fn, pre_filter)` -- two-layer

## pre_filter (Layer 1)

Receives `PriceData`. Key fields:
`p.code`, `p.name`, `p.close`, `p.open`, `p.high`, `p.low`, `p.volume`, `p.amount`,
`p.lastClose`, `p.pe`, `p.totalShares`, `p.flowShares`, `p.upperLimit`, `p.lowerLimit`

```python
p.volume > 0 and p.close > 3 and "ST" not in p.name  # typical
```

## filter_fn (Layer 2)

Receives `(code, name, bars)`. Return `{"score": float, "reason": str, ...}` or `None`.

```python
def filter_fn(code, name, bars):
    if len(bars) < 30:
        return None
    close, high, low, vol = bars_to_arrays(bars)
    # ... compute indicators (use catquant.indicators) ...
    if condition:
        return {"score": value, "reason": "description"}
    return None
```

## scan() / quick_scan()

```python
scan(filter_fn, pre_filter=None, universe=None, count=250,
     cycle=1440, source="facecat", max_results=20,
     sort_key="score", ascending=False, verbose=True, refresh=False)

quick_scan(pre_filter=None, max_results=50, sort_key="close", ascending=False)
```
