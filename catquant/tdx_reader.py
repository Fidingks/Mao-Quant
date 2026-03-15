"""TDX (通达信) data reader for CatQuant."""

import os
import struct

import pandas as pd

__all__ = ["load", "symbol_to_path"]


def load_txt(filepath: str) -> pd.DataFrame:
    """Load TDX text export file (.txt).

    Handles GBK encoding and trailing comment lines.
    """
    df = pd.read_csv(
        filepath, skiprows=2, header=None, encoding="gbk",
        names=["date", "open", "high", "low", "close", "volume", "amount"],
        comment="#",
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df


def load_day(filepath: str) -> pd.DataFrame:
    """Load TDX binary day line file (.day).

    Each record is 32 bytes: date(i4), open(i4), high(i4), low(i4),
    close(i4), amount(f4), volume(i4), reserved(i4).
    Prices are stored as int * 100.
    """
    records = []
    with open(filepath, "rb") as f:
        while True:
            data = f.read(32)
            if len(data) < 32:
                break
            fields = struct.unpack("<IIIIIfII", data)
            date_str = str(fields[0])
            records.append({
                "date": f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}",
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


def load_minute(filepath: str) -> pd.DataFrame:
    """Load TDX binary minute line file (.lc1 / .lc5).

    Each record is 32 bytes: date(u2), time(u2), open(f4), high(f4),
    low(f4), close(f4), amount(f4), volume(i4).
    """
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


def symbol_to_path(tdx_dir: str, symbol: str, interval: str = "D") -> str:
    """Map symbol code to TDX file path.

    Args:
        tdx_dir: TDX installation directory (e.g., 'C:\\new_tdx').
        symbol: Stock code like 'SH600000', 'SZ000001'.
        interval: 'D' for daily, '1m' for 1-minute, '5m' for 5-minute.

    Returns:
        Full path to the TDX data file.
    """
    market = symbol[:2].lower()
    code = symbol[2:]

    if interval == "D":
        return os.path.join(tdx_dir, "vipdoc", market, "lday", f"{market}{code}.day")
    elif interval == "1m":
        return os.path.join(tdx_dir, "vipdoc", market, "minline", f"{market}{code}.lc1")
    elif interval == "5m":
        return os.path.join(tdx_dir, "vipdoc", market, "fzline", f"{market}{code}.lc5")
    else:
        raise ValueError(f"Unsupported interval: {interval}. Use 'D', '1m', or '5m'.")


def load(source: str, symbol: str = "", interval: str = "D", tdx_dir: str = "") -> pd.DataFrame:
    """Universal loader: auto-detect file type and load.

    Args:
        source: File path (.txt, .day, .lc1, .lc5) or 'tdx' to use tdx_dir + symbol.
        symbol: Stock code (required if source='tdx').
        interval: 'D', '1m', '5m' (required if source='tdx').
        tdx_dir: TDX installation directory (required if source='tdx').

    Returns:
        DataFrame with OHLCV data indexed by datetime.
    """
    if source == "tdx":
        if not tdx_dir or not symbol:
            raise ValueError("tdx_dir and symbol required when source='tdx'")
        filepath = symbol_to_path(tdx_dir, symbol, interval)
    else:
        filepath = source

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        return load_txt(filepath)
    elif ext == ".day":
        return load_day(filepath)
    elif ext in (".lc1", ".lc5"):
        return load_minute(filepath)
    else:
        raise ValueError(f"Unknown file extension: {ext}. Supported: .txt, .day, .lc1, .lc5")
