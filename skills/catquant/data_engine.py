"""Unified data engine for CatQuant.

Provides a single API for fetching historical K-line data from multiple sources
(FaceCat HTTP API, TDX local binary files) and real-time market data.

Includes a transparent CSV cache layer for FaceCat data: first fetch hits the
server and writes a local CSV; subsequent calls read from disk.
"""

import csv
import os
from datetime import datetime, timezone, timedelta

from catquant.models import SecurityData, LatestData, PriceData, normalize_symbol
from catquant.bar_series import BarSeries
from catquant import facecat

__all__ = ["get_history", "get_latest", "get_prices"]

_TZ_BEIJING = timezone(timedelta(hours=8))

_CYCLE_TO_TDX = {
    1440: "D",
    1: "1m",
    5: "5m",
}

_CYCLE_TO_DIR = {
    1440: "day",
    1: "1min",
    5: "5min",
    15: "15min",
    30: "30min",
    60: "60min",
}


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(code: str, cycle: int) -> str:
    """Return the CSV cache file path for a given symbol and cycle."""
    cache_dir = os.environ.get("CACHE_DIR", "./cache")
    sub_dir = _CYCLE_TO_DIR.get(cycle, f"{cycle}min")
    code_dotted = normalize_symbol(code, fmt="dotted")
    return os.path.join(cache_dir, sub_dir, f"{code_dotted}.csv")


def _write_cache(filepath: str, bars: list) -> None:
    """Write List[SecurityData] to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "open", "high", "low", "close", "volume", "amount"])
        for b in bars:
            date_str = datetime.fromtimestamp(b.date, tz=_TZ_BEIJING).strftime("%Y-%m-%d")
            w.writerow([date_str, b.open, b.high, b.low, b.close,
                        int(b.volume), b.amount])


def _cache_bar_count(filepath: str) -> int:
    """Count data rows in cached CSV (excluding header)."""
    with open(filepath, encoding="utf-8") as f:
        return sum(1 for _ in f) - 1


def _read_cache(filepath: str, count: int) -> list:
    """Read List[SecurityData] from a CSV file, returning the last *count* bars."""
    bars = []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sd = SecurityData()
            dt = datetime.strptime(row["date"], "%Y-%m-%d").replace(tzinfo=_TZ_BEIJING)
            sd.date = int(dt.timestamp())
            sd.open = float(row["open"])
            sd.high = float(row["high"])
            sd.low = float(row["low"])
            sd.close = float(row["close"])
            sd.volume = int(float(row["volume"]))
            sd.amount = float(row["amount"])
            bars.append(sd)
    if count and len(bars) > count:
        bars = bars[-count:]
    return bars


def _df_to_security_data(df) -> list:
    """Convert a DataFrame from tdx_reader to List[SecurityData].

    Expects df.index to be DatetimeIndex, with columns:
    open, high, low, close, volume, amount.
    """
    bars = []
    for ts, row in df.iterrows():
        sd = SecurityData()
        dt = ts.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_TZ_BEIJING)
        sd.date = int(dt.timestamp())
        sd.open = float(row.get("open", 0))
        sd.high = float(row.get("high", 0))
        sd.low = float(row.get("low", 0))
        sd.close = float(row.get("close", 0))
        sd.volume = int(row.get("volume", 0))
        sd.amount = float(row.get("amount", 0))
        bars.append(sd)
    return bars


def get_history(code: str, cycle: int = 1440, count: int = 1000,
                source: str = "facecat", tdx_dir: str = "",
                verify_ssl: bool = True, refresh: bool = False) -> BarSeries:
    """Fetch historical K-line data.

    Args:
        code: Symbol in any format (e.g. '600000.SH', 'SH600000').
        cycle: Bar period in minutes. 1440=daily, 1=1min, 5=5min.
        count: Number of bars (FaceCat only).
        source: 'facecat' or 'tdx'.
        tdx_dir: TDX installation directory (required if source='tdx').
        verify_ssl: SSL verification for FaceCat.
        refresh: Force re-fetch from server even if cache exists.

    Returns:
        BarSeries sorted by date ascending.
    """
    dotted = normalize_symbol(code, fmt="dotted")

    if source == "facecat":
        cache_file = _cache_path(code, cycle)

        # Read from cache if available and sufficient
        if os.path.exists(cache_file) and not refresh:
            cached_count = _cache_bar_count(cache_file)
            if cached_count >= count:
                print(f"[cache] {code} cycle={cycle} <- local")
                return BarSeries(_read_cache(cache_file, count), code=dotted, cycle=cycle)
            # else: cached data insufficient, fall through to server fetch
            print(f"[cache] {code} cycle={cycle} cached={cached_count} < requested={count}, refreshing")

        # Fetch from server and cache
        print(f"[cache] {code} cycle={cycle} <- server")
        bars = facecat.fetch_kline(code, cycle=cycle, count=count,
                                   verify_ssl=verify_ssl)
        if bars:
            _write_cache(cache_file, bars)
        return BarSeries(bars, code=dotted, cycle=cycle)
    elif source == "tdx":
        if not tdx_dir:
            raise ValueError("tdx_dir is required when source='tdx'")

        interval = _CYCLE_TO_TDX.get(cycle)
        if interval is None:
            supported = ", ".join(f"{k}({v})" for k, v in _CYCLE_TO_TDX.items())
            raise ValueError(
                f"TDX does not support cycle={cycle}. "
                f"Supported: {supported}. Use source='facecat' for other cycles."
            )

        from catquant.tdx_reader import load
        symbol = normalize_symbol(code, fmt="prefix")
        df = load("tdx", symbol=symbol, interval=interval, tdx_dir=tdx_dir)
        bars = _df_to_security_data(df)

        if count and len(bars) > count:
            bars = bars[-count:]
        return BarSeries(bars, code=dotted, cycle=cycle)
    else:
        raise ValueError(f"Unknown source: '{source}'. Use 'facecat' or 'tdx'.")


def get_latest(codes: str, verify_ssl: bool = True) -> LatestData:
    """Fetch real-time snapshot (FaceCat only).

    Args:
        codes: Symbol (e.g. '600000.SH').
        verify_ssl: SSL verification.

    Returns:
        LatestData with current market data.
    """
    return facecat.fetch_latest(codes, verify_ssl=verify_ssl)


def get_prices(codes: str = "all", count: int = 200,
               verify_ssl: bool = True) -> dict:
    """Fetch batch price overview (FaceCat only).

    Args:
        codes: 'all' or comma-separated symbols.
        count: Max results.
        verify_ssl: SSL verification.

    Returns:
        Dict[str, PriceData] keyed by symbol code.
    """
    return facecat.fetch_prices(codes, count=count, verify_ssl=verify_ssl)
