"""Stock scanner for CatQuant -- two-layer filtering engine.

Layer 1: PriceData pre-filter (single HTTP call, full market snapshot)
Layer 2: K-line filter_fn (per-stock history, technical analysis)
"""

import csv
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from catquant.data_engine import get_history, get_prices

__all__ = ["ScanResult", "get_universe", "quick_scan", "scan", "export_scan"]


@dataclass
class ScanResult:
    """Single stock scan hit."""
    code: str = ""
    name: str = ""
    score: float = 0.0
    reason: str = ""
    metrics: dict = field(default_factory=dict)


def get_universe(source: str = "facecat", market: str = None,
                 verify_ssl: bool = True) -> List[tuple]:
    """Get available stock list as [(code, name), ...].

    Args:
        source: Data source (only 'facecat' supported).
        market: Filter by market prefix ('SH', 'SZ', 'BJ') or None for all.
        verify_ssl: SSL verification.
    """
    prices = get_prices(codes="all", count=99999, verify_ssl=verify_ssl)
    result = []
    for code, p in prices.items():
        if market:
            suffix = code.split(".")[-1].upper() if "." in code else ""
            if suffix != market.upper():
                continue
        result.append((code, p.name))
    return result


def quick_scan(pre_filter: Callable = None, max_results: int = 50,
               sort_key: str = "close", ascending: bool = False,
               verify_ssl: bool = True) -> List[dict]:
    """PriceData-only scan -- no K-line fetch, very fast.

    Args:
        pre_filter: Callable(PriceData) -> bool.
        max_results: Max results to return.
        sort_key: PriceData field name to sort by.
        ascending: Sort order.
        verify_ssl: SSL verification.

    Returns:
        List of dicts with PriceData fields.
    """
    prices = get_prices(codes="all", count=99999, verify_ssl=verify_ssl)
    hits = []
    for code, p in prices.items():
        if p.volume == 0:
            continue
        if pre_filter and not pre_filter(p):
            continue
        hits.append({
            "code": p.code,
            "name": p.name,
            "close": p.close,
            "open": p.open,
            "high": p.high,
            "low": p.low,
            "volume": p.volume,
            "amount": p.amount,
            "lastClose": p.lastClose,
            "change_pct": round((p.close / p.lastClose - 1) * 100, 2) if p.lastClose else 0,
            "pe": p.pe,
            "totalShares": p.totalShares,
            "flowShares": p.flowShares,
        })

    reverse = not ascending
    hits.sort(key=lambda x: x.get(sort_key, 0), reverse=reverse)
    return hits[:max_results]


def scan(
    filter_fn: Callable,
    pre_filter: Callable = None,
    universe: list = None,
    count: int = 250,
    cycle: int = 1440,
    source: str = "facecat",
    max_results: int = 20,
    sort_key: str = "score",
    ascending: bool = False,
    verbose: bool = True,
    verify_ssl: bool = True,
    refresh: bool = False,
) -> List[ScanResult]:
    """Two-layer stock scanner.

    Args:
        filter_fn: Callable(code, name, bars) -> dict|None.
            Return {"score": float, "reason": str, ...} for hit, None for miss.
        pre_filter: Callable(PriceData) -> bool. Fast pre-screen.
        universe: List of codes to scan, or None for full market.
        count: K-line bars to fetch per stock.
        cycle: K-line period in minutes (1440=daily).
        source: Data source for K-lines.
        max_results: Max results to return.
        sort_key: ScanResult field to sort by.
        ascending: Sort order.
        verbose: Print progress.
        verify_ssl: SSL verification.
        refresh: Force re-fetch K-lines from server (bypass cache).

    Returns:
        List[ScanResult] sorted by sort_key.
    """
    # --- Layer 1: get market snapshot and pre-filter ---
    prices = get_prices(codes="all", count=99999, verify_ssl=verify_ssl)

    if universe:
        # Normalize universe codes to dotted format
        from catquant.models import normalize_symbol
        norm_codes = set()
        for c in universe:
            try:
                norm_codes.add(normalize_symbol(c, fmt="dotted"))
            except ValueError:
                norm_codes.add(c)
        candidates = [(code, p) for code, p in prices.items() if code in norm_codes]
    else:
        candidates = list(prices.items())

    # Apply pre_filter
    filtered = []
    for code, p in candidates:
        if p.volume == 0:
            continue
        if pre_filter and not pre_filter(p):
            continue
        filtered.append((code, p.name))

    if verbose:
        print(f"Pre-filter: {len(filtered)} stocks to scan (from {len(candidates)})")

    # --- Layer 2: K-line filter ---
    hits = []
    skipped = 0

    for i, (code, name) in enumerate(filtered):
        try:
            bars = get_history(code, cycle=cycle, count=count,
                               source=source, verify_ssl=verify_ssl,
                               refresh=refresh)
            if len(bars) < 20:
                skipped += 1
                continue

            result = filter_fn(code, name, bars)
            if result is not None:
                sr = ScanResult(
                    code=code,
                    name=name,
                    score=result.get("score", 0.0),
                    reason=result.get("reason", ""),
                )
                # Everything except score/reason goes to metrics
                sr.metrics = {k: v for k, v in result.items()
                              if k not in ("score", "reason")}
                hits.append(sr)
        except Exception as e:
            skipped += 1
            if verbose:
                print(f"  Skip {code}: {e}", file=sys.stderr)
            continue

        if verbose:
            done = i + 1
            sys.stdout.write(f"\r  [{done}/{len(filtered)}] hits={len(hits)}")
            sys.stdout.flush()

    if verbose:
        print()  # newline after progress
        if skipped:
            print(f"  Skipped {skipped} stocks (data error or insufficient bars)")

    # --- Sort and truncate ---
    reverse = not ascending
    hits.sort(key=lambda sr: getattr(sr, sort_key, sr.score), reverse=reverse)
    hits = hits[:max_results]

    # --- Print results ---
    if not hits:
        print("\nNo stocks matched the scan criteria.")
        return []

    print(f"\n=== Scan Results: {len(hits)} hits ===")
    print(f"{'Code':<12} {'Name':<10} {'Score':>8} {'Reason'}")
    print("-" * 60)
    for sr in hits:
        print(f"{sr.code:<12} {sr.name:<10} {sr.score:>8.2f}  {sr.reason}")

    return hits


def export_scan(results: List[ScanResult], filepath: str):
    """Export scan results to CSV.

    Columns: code, name, score, reason, [dynamic metric columns...]

    Args:
        results: List[ScanResult] from scan() or quick_scan().
        filepath: Output .csv path.
    """
    if not results:
        print("No results to export.")
        return

    # Collect all metric keys across results
    metric_keys = []
    seen = set()
    for sr in results:
        for k in sr.metrics:
            if k not in seen:
                metric_keys.append(k)
                seen.add(k)

    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["code", "name", "score", "reason"] + metric_keys)
        for sr in results:
            row = [sr.code, sr.name, sr.score, sr.reason]
            for k in metric_keys:
                row.append(sr.metrics.get(k, ""))
            w.writerow(row)
    print(f"Exported: {filepath} ({len(results)} rows)")
