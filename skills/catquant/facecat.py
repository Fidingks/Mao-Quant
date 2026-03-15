"""FaceCat HTTP data source for CatQuant."""

import os
import ssl
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from catquant.models import SecurityData, LatestData, PriceData, normalize_symbol

__all__ = ["fetch_kline", "fetch_latest", "fetch_prices"]

_TZ_BEIJING = timezone(timedelta(hours=8))


def _get_base_url() -> str:
    """Read FaceCat_URL from environment or use default."""
    url = os.environ.get("FaceCat_URL", "https://www.jjmfc.com:9969")
    return url.rstrip("/") + "/quote"


def _fetch(params: dict, verify_ssl: bool = True) -> str:
    """HTTP GET with query params, return response text."""
    base = _get_base_url()
    qs = urllib.parse.urlencode(params)
    url = f"{base}?{qs}"

    ctx = None
    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _parse_date_to_epoch(date_str: str) -> int:
    """Parse 'YYYY-MM-DD' or 'YYYY/MM/DD' to epoch seconds at Beijing midnight."""
    date_str = date_str.strip().replace("/", "-")
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    dt = dt.replace(tzinfo=_TZ_BEIJING)
    return int(dt.timestamp())


def _safe_float(s: str, default: float = 0.0) -> float:
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return default


def _safe_int(s: str, default: int = 0) -> int:
    try:
        return int(float(s.strip()))
    except (ValueError, AttributeError):
        return default


def fetch_kline(code: str, cycle: int = 1440, count: int = 1000,
                verify_ssl: bool = True) -> list:
    """Fetch K-line data from FaceCat API.

    Args:
        code: Symbol in any format (e.g. '600000.SH' or 'SH600000').
        cycle: 1440=daily, 1=1min, 5=5min, etc.
        count: Number of bars to fetch.
        verify_ssl: Whether to verify SSL certificate.

    Returns:
        List[SecurityData] sorted by date ascending.
    """
    code = normalize_symbol(code, fmt="dotted")
    text = _fetch({
        "func": "getkline",
        "code": code,
        "cycle": str(cycle),
        "count": str(count),
    }, verify_ssl=verify_ssl)

    bars = []
    lines = text.strip().split("\n")
    for line in lines[2:]:  # skip header lines (name + column headers)
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 7:
            continue
        sd = SecurityData()
        sd.date = _parse_date_to_epoch(parts[0])
        sd.open = _safe_float(parts[1])
        sd.high = _safe_float(parts[2])
        sd.low = _safe_float(parts[3])
        sd.close = _safe_float(parts[4])
        sd.volume = _safe_int(parts[5])
        sd.amount = _safe_float(parts[6])
        bars.append(sd)
    return bars


def fetch_latest(codes: str, verify_ssl: bool = True) -> LatestData:
    """Fetch real-time snapshot for a single security.

    Args:
        codes: Symbol (e.g. '600000.SH').
        verify_ssl: Whether to verify SSL certificate.

    Returns:
        LatestData with current market snapshot.
    """
    codes = normalize_symbol(codes, fmt="dotted")
    text = _fetch({"func": "getnewdata", "codes": codes}, verify_ssl=verify_ssl)

    parts = text.strip().split(",")
    ld = LatestData()
    if len(parts) < 10:
        return ld

    ld.code = parts[0].strip()
    ld.name = parts[1].strip()
    ld.close = _safe_float(parts[2])
    ld.high = _safe_float(parts[3])
    ld.low = _safe_float(parts[4])
    ld.open = _safe_float(parts[5])
    ld.volume = _safe_int(parts[6])
    ld.amount = _safe_float(parts[7])
    ld.lastClose = _safe_float(parts[8])

    # bid prices [9-13], bid volumes [14-18]
    ld.buyPrices = [_safe_float(parts[i]) for i in range(9, 14) if i < len(parts)]
    ld.buyVolumes = [_safe_int(parts[i]) for i in range(14, 19) if i < len(parts)]
    # ask prices [19-23], ask volumes [24-28]
    ld.sellPrices = [_safe_float(parts[i]) for i in range(19, 24) if i < len(parts)]
    ld.sellVolumes = [_safe_int(parts[i]) for i in range(24, 29) if i < len(parts)]
    # datetime [29]
    if len(parts) > 29:
        ld.datetime = parts[29].strip()

    return ld


def fetch_prices(codes: str = "all", count: int = 200,
                 verify_ssl: bool = True) -> dict:
    """Fetch batch price overview.

    Args:
        codes: 'all' for all stocks, or comma-separated codes.
        count: Max number of results.
        verify_ssl: Whether to verify SSL certificate.

    Returns:
        Dict[str, PriceData] keyed by dotted symbol code.
    """
    text = _fetch({
        "func": "price",
        "codes": codes,
        "count": str(count),
    }, verify_ssl=verify_ssl)

    result = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 10:
            continue

        pd_obj = PriceData()
        pd_obj.code = parts[0].strip()
        pd_obj.name = parts[1].strip()
        pd_obj.close = _safe_float(parts[2])
        pd_obj.high = _safe_float(parts[3])
        pd_obj.low = _safe_float(parts[4])
        pd_obj.open = _safe_float(parts[5])
        pd_obj.volume = _safe_int(parts[6])
        pd_obj.amount = _safe_float(parts[7])
        pd_obj.lastClose = _safe_float(parts[8])
        if len(parts) > 9:
            pd_obj.totalShares = _safe_int(parts[9])
        if len(parts) > 10:
            pd_obj.flowShares = _safe_int(parts[10])
        if len(parts) > 11:
            pd_obj.pe = _safe_float(parts[11])
        if len(parts) > 14:
            pd_obj.upperLimit = _safe_float(parts[14])
        if len(parts) > 15:
            pd_obj.lowerLimit = _safe_float(parts[15])
        if len(parts) > 16:
            pd_obj.date = parts[16].strip()

        result[pd_obj.code] = pd_obj

    return result
