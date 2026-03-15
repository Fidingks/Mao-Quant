"""Stock name/code resolution and data availability check.

Usage:
    python -m catquant.resolve 茅台
    python -m catquant.resolve 600519
    python -m catquant.resolve SH600519

From code:
    from catquant.resolve import resolve, check_available
    code, name = resolve("茅台")
    ok, source, hint = check_available(code)
"""

import os
import sys
from typing import Optional, Tuple, List

from catquant.data_engine import get_prices, get_history
from catquant.models import normalize_symbol

__all__ = ["resolve", "check_available", "search"]


# Common stock names that retail investors use.
# FaceCat free API only covers ~84 stocks; this table handles the rest.
_KNOWN_STOCKS = {
    "茅台": "600519.SH", "贵州茅台": "600519.SH",
    "平安": "601318.SH", "中国平安": "601318.SH",
    "比亚迪": "002594.SZ",
    "宁德时代": "300750.SZ", "宁德": "300750.SZ",
    "招商银行": "600036.SH", "招行": "600036.SH",
    "中信证券": "600030.SH",
    "五粮液": "000858.SZ",
    "美的": "000333.SZ", "美的集团": "000333.SZ",
    "格力": "000651.SZ", "格力电器": "000651.SZ",
    "万科": "000002.SZ", "万科A": "000002.SZ",
    "腾讯": "00700.HK",
    "工商银行": "601398.SH", "工行": "601398.SH",
    "建设银行": "601939.SH", "建行": "601939.SH",
    "农业银行": "601288.SH", "农行": "601288.SH",
    "中国银行": "601988.SH", "中行": "601988.SH",
    "中石油": "601857.SH", "中国石油": "601857.SH",
    "中石化": "600028.SH", "中国石化": "600028.SH",
    "中国神华": "601088.SH", "神华": "601088.SH",
    "长江电力": "600900.SH",
    "隆基绿能": "601012.SH", "隆基": "601012.SH",
    "药明康德": "603259.SH",
    "迈瑞医疗": "300760.SZ",
    "恒瑞医药": "600276.SH",
    "三一重工": "600031.SH",
    "上汽集团": "600104.SH",
    "海尔智家": "600690.SH", "海尔": "600690.SH",
    "伊利股份": "600887.SH", "伊利": "600887.SH",
    "海天味业": "603288.SH", "海天": "603288.SH",
    "紫金矿业": "601899.SH",
    "东方财富": "300059.SZ",
    "中芯国际": "688981.SH",
    "北方稀土": "600111.SH",
    "洋河股份": "002304.SZ", "洋河": "002304.SZ",
    "泸州老窖": "000568.SZ",
    "片仔癀": "600436.SH",
    "立讯精密": "002475.SZ",
    "中国中免": "601888.SH", "中免": "601888.SH",
    "京东方": "000725.SZ", "京东方A": "000725.SZ",
    "中国移动": "600941.SH",
    "中国电信": "601728.SH",
    "中国联通": "600050.SH", "联通": "600050.SH",
    "浦发银行": "600000.SH", "浦发": "600000.SH",
    "民生银行": "600016.SH",
    "兴业银行": "601166.SH",
    "保利发展": "600048.SH", "保利": "600048.SH",
    "特变电工": "600089.SH",
    "同仁堂": "600085.SH",
    "上海机场": "600009.SH",
    "包钢股份": "600010.SH",
    "宝钢股份": "600019.SH",
    "南方航空": "600029.SH",
}


def search(keyword: str, verify_ssl: bool = True) -> List[Tuple[str, str]]:
    """Search stocks by name or code fragment.

    Checks built-in table first, then FaceCat PriceData.
    Returns list of (code, name) tuples.
    """
    keyword = keyword.strip()
    if not keyword:
        return []

    results = []

    # 1. Built-in table
    for name, code in _KNOWN_STOCKS.items():
        if keyword in name or keyword == code or keyword == code.split(".")[0]:
            results.append((code, name))

    # Deduplicate by code
    seen = set()
    deduped = []
    for code, name in results:
        if code not in seen:
            seen.add(code)
            deduped.append((code, name))
    results = deduped

    # 2. FaceCat PriceData (online, covers ~84 stocks)
    try:
        price_map = get_prices("all", count=6000, verify_ssl=verify_ssl)
        for code, p in price_map.items():
            if code in seen:
                continue
            if keyword in p.name or keyword in code or keyword == code.split(".")[0]:
                results.append((code, p.name))
                seen.add(code)
    except Exception:
        pass

    return results[:20]


def resolve(query: str, verify_ssl: bool = True) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a stock name, code, or fragment to (code, name).

    Accepts:
        "茅台" / "贵州茅台"       -> name lookup
        "600519"                  -> code lookup
        "SH600519" / "600519.SH" -> direct normalize

    Returns:
        (code, name) or (None, None) if not found.
    """
    query = query.strip()
    if not query:
        return None, None

    # Direct match in known stocks table
    if query in _KNOWN_STOCKS:
        code = _KNOWN_STOCKS[query]
        return code, query

    # Full symbol format (SH600519, 600519.SH, SZ000001, etc.)
    upper = query.upper()
    if (upper.startswith("SH") or upper.startswith("SZ")) and len(upper) >= 8:
        dotted = normalize_symbol(upper, fmt="dotted")
        name = _find_name(dotted, verify_ssl)
        return dotted, name or query
    if "." in query:
        dotted = normalize_symbol(query, fmt="dotted")
        name = _find_name(dotted, verify_ssl)
        return dotted, name or query

    # Pure digits -> assume code
    if query.isdigit() and len(query) == 6:
        # Guess exchange: 6xx = SH, 0xx/3xx = SZ
        if query.startswith("6"):
            dotted = f"{query}.SH"
        else:
            dotted = f"{query}.SZ"
        name = _find_name(dotted, verify_ssl)
        return dotted, name or query

    # Fuzzy name search
    results = search(query, verify_ssl)
    if results:
        return results[0]

    return None, None


def _find_name(code: str, verify_ssl: bool = True) -> Optional[str]:
    """Find stock name by code."""
    # Check known table
    for name, c in _KNOWN_STOCKS.items():
        if c == code:
            return name

    # Check PriceData
    try:
        price_map = get_prices("all", count=6000, verify_ssl=verify_ssl)
        p = price_map.get(code)
        if p:
            return p.name
    except Exception:
        pass

    return None


def check_available(code: str, verify_ssl: bool = True) -> Tuple[bool, str, str]:
    """Check if historical data is available for the given code.

    Tries FaceCat first, then TDX if configured.

    Returns:
        (available, source, hint)
        - source: "facecat", "tdx", or "none"
        - hint: suggestion message if not available
    """
    dotted = normalize_symbol(code, fmt="dotted")

    # Try FaceCat
    try:
        bars = get_history(dotted, count=5, source="facecat", verify_ssl=verify_ssl)
        if bars and len(bars) > 0:
            return True, "facecat", ""
    except Exception:
        pass

    # Try TDX if configured
    tdx_dir = os.environ.get("TDX_DIR", "")
    if tdx_dir and os.path.isdir(tdx_dir):
        try:
            bars = get_history(dotted, count=5, source="tdx", tdx_dir=tdx_dir)
            if bars and len(bars) > 0:
                return True, "tdx", ""
        except Exception:
            pass
        return False, "none", (
            f"{dotted} not found in TDX data. "
            f"Please open TDX client and download this stock's data first."
        )

    return False, "none", (
        f"{dotted} is not covered by the free FaceCat API (only ~84 stocks supported). "
        f"Options: (1) Set TDX_DIR in .env and use TongDaXin local data, "
        f"or (2) Contact the developer at https://www.jjmfc.com for full-market data access."
    )


# CLI entry point
if __name__ == "__main__":
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv())

    if len(sys.argv) < 2:
        print("Usage: python -m catquant.resolve <stock_name_or_code>")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    code, name = resolve(query, verify_ssl=False)

    if code is None:
        print(f"Not found: {query}")
        sys.exit(1)

    print(f"Resolved: {name} ({code})")

    ok, source, hint = check_available(code, verify_ssl=False)
    if ok:
        print(f"Data available via: {source}")
    else:
        print(f"Data NOT available. {hint}")
