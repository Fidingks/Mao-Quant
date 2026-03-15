---
name: data-tdx
description: Loading market data from TDX (通达信) local files - binary .day/.lc1/.lc5 and text export .txt
metadata:
  tags: data, tdx, 通达信, ohlcv, binary, csv
  last_verified: "2026-03-15"
---

# TDX (通达信) Data Loading

## Data Source Overview

TDX stores historical data locally in binary format. Users can also export to text (.txt).

| Format | Extension | Resolution | Location |
|--------|-----------|-----------|----------|
| Day line | `.day` | Daily | `{TDX_DIR}/vipdoc/{sh,sz}/lday/` |
| 1-min | `.lc1` | 1 minute | `{TDX_DIR}/vipdoc/{sh,sz}/minline/` |
| 5-min | `.lc5` | 5 minutes | `{TDX_DIR}/vipdoc/{sh,sz}/fzline/` |
| Text export | `.txt` | Any | User-specified |

## 1. Text Export (.txt) — Simplest

```python
import pandas as pd

def load_tdx_txt(filepath):
    """Load TDX text export file."""
    df = pd.read_csv(filepath, skiprows=2, header=None, encoding="gbk",
                     names=["date", "open", "high", "low", "close", "volume", "amount"],
                     comment="#")
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df
```

## 2. Binary Day Line (.day)

```python
import struct
import pandas as pd
from pathlib import Path

def load_tdx_day(filepath):
    """Load TDX binary .day file. Each record = 32 bytes."""
    records = []
    with open(filepath, "rb") as f:
        while True:
            data = f.read(32)
            if len(data) < 32:
                break
            fields = struct.unpack("<IIIIIfII", data)
            date = str(fields[0])
            records.append({
                "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                "open": fields[1] / 100.0,
                "high": fields[2] / 100.0,
                "low": fields[3] / 100.0,
                "close": fields[4] / 100.0,
                "amount": fields[5],
                "volume": fields[6],
            })
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df
```

## 3. Binary Minute Line (.lc1 / .lc5)

```python
import struct
import pandas as pd

def load_tdx_minute(filepath):
    """Load TDX binary .lc1 or .lc5 file. Each record = 32 bytes."""
    records = []
    with open(filepath, "rb") as f:
        while True:
            data = f.read(32)
            if len(data) < 32:
                break
            fields = struct.unpack("<HHfffffi", data)
            date_raw = fields[0]
            time_raw = fields[1]
            year = (date_raw >> 11) + 2004
            month = (date_raw >> 7) & 0x0F
            day = date_raw & 0x1F
            hour = time_raw // 60
            minute = time_raw % 60
            records.append({
                "datetime": f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}",
                "open": fields[2],
                "high": fields[3],
                "low": fields[4],
                "close": fields[5],
                "amount": fields[6],
                "volume": fields[7],
            })
    df = pd.DataFrame(records)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    return df
```

## Symbol to File Path Mapping

```python
import os

def symbol_to_path(tdx_dir, symbol, interval="D"):
    """Map symbol code to TDX file path.

    symbol: 'SH600000', 'SZ000001', 'SZ300750'
    interval: 'D', '1m', '5m'
    """
    market = symbol[:2].lower()  # sh or sz
    code = symbol[2:]

    if interval == "D":
        return os.path.join(tdx_dir, "vipdoc", market, "lday", f"{market}{code}.day")
    elif interval == "1m":
        return os.path.join(tdx_dir, "vipdoc", market, "minline", f"{market}{code}.lc1")
    elif interval == "5m":
        return os.path.join(tdx_dir, "vipdoc", market, "fzline", f"{market}{code}.lc5")
    else:
        raise ValueError(f"Unsupported interval: {interval}")
```

## Best Practices

- Always use `encoding="gbk"` for TDX text files
- Always use `comment="#"` to skip trailing comment lines
- Binary files are little-endian
- TDX minute data may have gaps (no records during non-trading hours)
- Volume unit: shares (not lots)
- Amount unit: CNY
