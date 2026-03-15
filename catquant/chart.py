"""Matplotlib chart renderer for CatQuant backtesting.

Two themes: 'dark' (night) and 'light' (day).
"""

from typing import Optional, Tuple, List, Dict, Any
import os
from datetime import datetime, timezone, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FixedLocator

__all__ = ["render"]


_TZ_BJ = timezone(timedelta(hours=8))


# ---------------------------------------------------------------------------
# Theme definitions
# ---------------------------------------------------------------------------

_THEMES = {
    "dark": {
        "figure.facecolor": "#131722",
        "axes.facecolor": "#1e222d",
        "axes.edgecolor": "#363a45",
        "axes.labelcolor": "#b2b5be",
        "axes.grid": True,
        "grid.color": "#2a2e39",
        "grid.alpha": 0.8,
        "grid.linestyle": "-",
        "grid.linewidth": 0.3,
        "text.color": "#d1d4dc",
        "xtick.color": "#787b86",
        "ytick.color": "#787b86",
        "legend.facecolor": "#1e222d",
        "legend.edgecolor": "#363a45",
        "font.size": 10,
        # custom keys (not rcParams)
        "_up_color": "#f23645",
        "_down_color": "#089981",
        "_equity_color": "#2962ff",
        "_equity_fill_alpha": 0.12,
        "_dd_color": "#f23645",
        "_dd_fill_alpha": 0.35,
        "_buy_arrow": "#f23645",
        "_sell_arrow": "#089981",
        "_info_bg": "#1e222d",
        "_info_edge": "#363a45",
        "_info_text": "#d1d4dc",
        "_title_color": "#d1d4dc",
        "_save_facecolor": None,  # use fig facecolor
    },
    "light": {
        "figure.facecolor": "#ffffff",
        "axes.facecolor": "#fafbfc",
        "axes.edgecolor": "#d0d7de",
        "axes.labelcolor": "#24292f",
        "axes.grid": True,
        "grid.color": "#d8dee4",
        "grid.alpha": 0.7,
        "grid.linestyle": "-",
        "grid.linewidth": 0.4,
        "text.color": "#24292f",
        "xtick.color": "#57606a",
        "ytick.color": "#57606a",
        "legend.facecolor": "#ffffff",
        "legend.edgecolor": "#d0d7de",
        "font.size": 10,
        # custom keys
        "_up_color": "#cf222e",
        "_down_color": "#1a7f37",
        "_equity_color": "#0969da",
        "_equity_fill_alpha": 0.08,
        "_dd_color": "#cf222e",
        "_dd_fill_alpha": 0.25,
        "_buy_arrow": "#cf222e",
        "_sell_arrow": "#1a7f37",
        "_info_bg": "#ffffff",
        "_info_edge": "#d0d7de",
        "_info_text": "#24292f",
        "_title_color": "#24292f",
        "_save_facecolor": "#ffffff",
    },
}


_OVERLAY_COLORS = [
    "#ff9800", "#2196f3", "#e040fb", "#00bcd4", "#ffeb3b",
    "#8bc34a", "#ff5722", "#9c27b0", "#009688", "#cddc39",
]


def _apply_theme(theme_name: str) -> dict:
    """Apply rcParams and return custom keys."""
    theme = _THEMES.get(theme_name, _THEMES["dark"])
    rc = {k: v for k, v in theme.items() if not k.startswith("_")}
    custom = {k: v for k, v in theme.items() if k.startswith("_")}
    plt.rcParams.update(rc)
    return custom


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _epoch_to_str(epoch):
    """Convert epoch seconds to 'YYYY-MM-DD' in Beijing time."""
    if epoch <= 0:
        return ""
    return datetime.fromtimestamp(epoch, tz=_TZ_BJ).strftime("%Y-%m-%d")


def _draw_candlestick(ax, indices, opens, highs, lows, closes, up_color, down_color):
    """Draw candlestick chart. A-share convention: red = up, green = down."""
    n = len(indices)
    width = 0.6
    for i in range(n):
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        if c >= o:
            color = up_color
            body_low = o
            body_height = c - o if c > o else 0.001 * o
        else:
            color = down_color
            body_low = c
            body_height = o - c

        ax.vlines(indices[i], l, h, color=color, linewidth=0.8)
        ax.bar(indices[i], body_height, bottom=body_low, width=width,
               color=color, edgecolor=color, linewidth=0.5)


def _set_date_ticks(ax, dates_str, N):
    """Set x-axis date labels using FixedLocator to avoid warnings."""
    ax.xaxis.set_major_locator(MaxNLocator(nbins=12, integer=True))
    tick_locs = [int(loc) for loc in ax.get_xticks() if 0 <= int(loc) < N]
    ax.xaxis.set_major_locator(FixedLocator(tick_locs))
    ax.set_xticklabels(
        [dates_str[i] if 0 <= i < N else "" for i in tick_locs],
        rotation=45, ha="right", fontsize=8,
    )


def _draw_indicator_panel(ax, indices, panel: dict, t: dict):
    """Draw an indicator panel (MACD/KDJ/RSI etc.)."""
    # Lines
    for line_def in panel.get("lines", []):
        data = np.array(line_def["data"])
        color = line_def.get("color", _OVERLAY_COLORS[0])
        lw = line_def.get("linewidth", 1.2)
        label = line_def.get("label", "")
        ax.plot(indices[:len(data)], data[:len(indices)],
                color=color, linewidth=lw, label=label)

    # Bars (MACD-style: positive = up_color, negative = down_color)
    for bar_def in panel.get("bars", []):
        data = np.array(bar_def["data"])
        label = bar_def.get("label", "")
        n = min(len(data), len(indices))
        colors = [t["_up_color"] if data[i] >= 0 else t["_down_color"]
                  for i in range(n)]
        ax.bar(indices[:n], data[:n], width=0.6, color=colors, alpha=0.7,
               label=label)

    # Fill between (Bollinger band fill etc.)
    for fill_def in panel.get("fill", []):
        upper = np.array(fill_def["upper"])
        lower = np.array(fill_def["lower"])
        color = fill_def.get("color", t["_equity_color"])
        alpha = fill_def.get("alpha", 0.1)
        n = min(len(upper), len(lower), len(indices))
        ax.fill_between(indices[:n], lower[:n], upper[:n],
                        color=color, alpha=alpha)

    # Zero line for oscillators
    if panel.get("zero_line", False):
        ax.axhline(0, color=t["_info_edge"], linewidth=0.5, linestyle="-")

    title = panel.get("title", "")
    if title:
        ax.set_ylabel(title, fontsize=9)
    if any(l.get("label") for l in panel.get("lines", [])):
        ax.legend(loc="upper left", fontsize=7, ncol=3)


# ---------------------------------------------------------------------------
# Kline chart (3+ subplots)
# ---------------------------------------------------------------------------

def render_kline(result: "BacktestResult", bars: list, outdir: str = ".",
                 out: Optional[str] = None, size: Tuple[float, float] = (19.2, 10.8),
                 dpi: int = 100, theme: str = "dark",
                 overlays: Optional[List[Dict[str, Any]]] = None,
                 panels: Optional[List[Dict[str, Any]]] = None) -> str:
    """Render K-line chart with trade markers, volume, and equity curve.

    Args:
        overlays: Lines on the price chart. Each dict has:
            data (array), label (str), color (str, optional),
            linewidth (float, optional, default 1.2).
            Example: [{"data": ema5, "label": "EMA5", "color": "#ff9800"}]
        panels: Indicator subplots below volume. Each dict has:
            title (str), lines (list of line dicts), bars (list of bar dicts),
            fill (list of fill dicts), zero_line (bool).
            Example: {"title": "MACD", "lines": [...], "bars": [...], "zero_line": True}
    """
    t = _apply_theme(theme)
    overlays = overlays or []
    panels = panels or []

    N = len(bars)
    dates_str = [_epoch_to_str(b.date) for b in bars]
    opens = np.array([b.open for b in bars])
    highs = np.array([b.high for b in bars])
    lows = np.array([b.low for b in bars])
    closes = np.array([b.close for b in bars])
    volumes = np.array([b.volume for b in bars], dtype=np.float64)
    indices = np.arange(N)

    # Dynamic layout: price, volume, [panels...], equity
    n_panels = len(panels)
    if n_panels == 0:
        ratios = [60, 15, 25]
    elif n_panels == 1:
        ratios = [48, 12, 18, 22]
    else:
        panel_h = max(12, 30 // n_panels)
        ratios = [45, 10] + [panel_h] * n_panels + [20]

    n_axes = 3 + n_panels
    fig, axes = plt.subplots(
        n_axes, 1, figsize=size, dpi=dpi,
        gridspec_kw={"height_ratios": ratios, "hspace": 0.08},
        sharex=True,
    )
    ax_k = axes[0]
    ax_v = axes[1]
    panel_axes = list(axes[2:2 + n_panels])
    ax_e = axes[-1]

    # --- Candlestick ---
    _draw_candlestick(ax_k, indices, opens, highs, lows, closes,
                      t["_up_color"], t["_down_color"])

    # --- Overlays on price chart ---
    color_idx = 0
    for ov in overlays:
        data = np.array(ov["data"])
        color = ov.get("color", _OVERLAY_COLORS[color_idx % len(_OVERLAY_COLORS)])
        lw = ov.get("linewidth", 1.2)
        label = ov.get("label", "")
        ax_k.plot(indices[:len(data)], data[:len(indices)],
                  color=color, linewidth=lw, label=label, alpha=0.9)
        color_idx += 1
    if overlays:
        ax_k.legend(loc="upper right", fontsize=7, ncol=min(len(overlays), 4))

    # Trade markers
    for tr in result.trades:
        if 0 <= tr.entry_bar < N:
            ax_k.annotate("", xy=(tr.entry_bar, lows[tr.entry_bar] * 0.995),
                          xytext=(tr.entry_bar, lows[tr.entry_bar] * 0.985),
                          arrowprops=dict(arrowstyle="->", color=t["_buy_arrow"], lw=1.5))
        if 0 <= tr.exit_bar < N:
            ax_k.annotate("", xy=(tr.exit_bar, highs[tr.exit_bar] * 1.005),
                          xytext=(tr.exit_bar, highs[tr.exit_bar] * 1.015),
                          arrowprops=dict(arrowstyle="->", color=t["_sell_arrow"], lw=1.5))

    # Metrics panel
    m = result.metrics
    info = (
        f"Return   {m.get('total_return', 0)*100:+.2f}%\n"
        f"Annual   {m.get('annual_return', 0)*100:+.2f}%\n"
        f"Sharpe   {m.get('sharpe_ratio', 0):.2f}\n"
        f"MaxDD    {m.get('max_drawdown', 0)*100:.2f}%\n"
        f"Trades   {m.get('total_trades', 0)}\n"
        f"WinRate  {m.get('win_rate', 0)*100:.1f}%\n"
        f"PF       {m.get('profit_factor', 0):.2f}"
    )
    ax_k.text(0.01, 0.97, info, transform=ax_k.transAxes,
              fontsize=12, verticalalignment="top", fontfamily="monospace",
              fontweight="bold",
              bbox=dict(boxstyle="round,pad=0.6", facecolor=t["_info_bg"],
                        edgecolor=t["_info_edge"], alpha=0.92, linewidth=1.5),
              color=t["_info_text"])

    ax_k.set_ylabel("Price")
    ax_k.set_title("K-Line", fontsize=14, fontweight="bold", color=t["_title_color"])

    # --- Volume ---
    vol_colors = [t["_up_color"] if closes[i] >= opens[i] else t["_down_color"]
                  for i in range(N)]
    ax_v.bar(indices, volumes, width=0.6, color=vol_colors, alpha=0.7)
    ax_v.set_ylabel("Volume")

    # --- Indicator panels ---
    for i, panel in enumerate(panels):
        _draw_indicator_panel(panel_axes[i], indices, panel, t)

    # --- Equity curve ---
    ax_e.plot(indices, result.equity, color=t["_equity_color"],
              linewidth=1.2, label="Equity")
    ax_e.fill_between(indices, result.equity,
                      alpha=t["_equity_fill_alpha"], color=t["_equity_color"])

    # Max drawdown marker
    if len(result.drawdown) > 0:
        dd_idx = int(np.argmin(result.drawdown))
        dd_val = result.drawdown[dd_idx]
        if dd_val < 0:
            dd_date = dates_str[dd_idx] if dd_idx < len(dates_str) else ""
            ax_e.axvline(dd_idx, color=t["_dd_color"], linewidth=0.8,
                         linestyle="--", alpha=0.6)
            ax_e.annotate(
                f"MaxDD {dd_val*100:.1f}%\n{dd_date}",
                xy=(dd_idx, result.equity[dd_idx]),
                xytext=(dd_idx + N * 0.05, result.equity[dd_idx]),
                fontsize=9, fontweight="bold", color=t["_dd_color"],
                arrowprops=dict(arrowstyle="->", color=t["_dd_color"],
                                lw=1.2, connectionstyle="arc3,rad=0.2"),
            )

    ax_e.set_ylabel("Equity")
    ax_e.legend(loc="upper left", fontsize=8)

    # X-axis date labels
    _set_date_ticks(ax_e, dates_str, N)

    if out is None:
        out = os.path.join(outdir, "kline.png")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    save_fc = t["_save_facecolor"] or fig.get_facecolor()
    fig.savefig(out, bbox_inches="tight", facecolor=save_fc)
    plt.close(fig)
    print(f"Chart: {out}")
    return out


# ---------------------------------------------------------------------------
# Equity chart (2 subplots)
# ---------------------------------------------------------------------------

def render_equity(result: "BacktestResult", bars: list, outdir: str = ".",
                  out: Optional[str] = None, size: Tuple[float, float] = (19.2, 10.8),
                  dpi: int = 100, theme: str = "dark") -> str:
    """Render equity curve with drawdown area."""
    t = _apply_theme(theme)

    N = len(bars)
    dates_str = [_epoch_to_str(b.date) for b in bars]
    indices = np.arange(N)

    fig, (ax_eq, ax_dd) = plt.subplots(
        2, 1, figsize=size, dpi=dpi,
        gridspec_kw={"height_ratios": [65, 35], "hspace": 0.08},
        sharex=True,
    )

    # --- Equity ---
    ax_eq.plot(indices, result.equity, color=t["_equity_color"],
               linewidth=1.5, label="Equity")
    ax_eq.fill_between(indices, result.equity,
                       alpha=t["_equity_fill_alpha"], color=t["_equity_color"])

    # Metrics summary panel
    m = result.metrics
    eq_info = (
        f"Return   {m.get('total_return', 0)*100:+.2f}%\n"
        f"Annual   {m.get('annual_return', 0)*100:+.2f}%\n"
        f"Sharpe   {m.get('sharpe_ratio', 0):.2f}\n"
        f"MaxDD    {m.get('max_drawdown', 0)*100:.2f}%\n"
        f"WinRate  {m.get('win_rate', 0)*100:.1f}%"
    )
    ax_eq.text(0.01, 0.97, eq_info, transform=ax_eq.transAxes,
               fontsize=12, verticalalignment="top", fontfamily="monospace",
               fontweight="bold",
               bbox=dict(boxstyle="round,pad=0.6", facecolor=t["_info_bg"],
                         edgecolor=t["_info_edge"], alpha=0.92, linewidth=1.5),
               color=t["_info_text"])

    # Peak equity marker
    peak_idx = int(np.argmax(result.equity))
    peak_val = result.equity[peak_idx]
    peak_date = dates_str[peak_idx] if peak_idx < len(dates_str) else ""
    # Place text to the left if peak is in right half, else to the right
    text_offset = -N * 0.15 if peak_idx > N * 0.5 else N * 0.10
    ax_eq.annotate(
        f"Peak {peak_val:,.0f}\n{peak_date}",
        xy=(peak_idx, peak_val),
        xytext=(peak_idx + text_offset, peak_val * 0.92),
        fontsize=9, fontweight="bold", color=t["_equity_color"],
        arrowprops=dict(arrowstyle="->", color=t["_equity_color"],
                        lw=1.2, connectionstyle="arc3,rad=-0.2"),
    )

    ax_eq.set_ylabel("Equity")
    ax_eq.set_title("Equity Curve", fontsize=14, fontweight="bold",
                    color=t["_title_color"])
    ax_eq.legend(loc="upper right", fontsize=9)

    # --- Drawdown ---
    ax_dd.fill_between(indices, result.drawdown * 100, 0,
                       color=t["_dd_color"], alpha=t["_dd_fill_alpha"],
                       label="Drawdown")
    ax_dd.plot(indices, result.drawdown * 100, color=t["_dd_color"], linewidth=0.8)

    # Max drawdown annotation
    if len(result.drawdown) > 0:
        dd_idx = int(np.argmin(result.drawdown))
        dd_val = result.drawdown[dd_idx]
        if dd_val < 0:
            dd_date = dates_str[dd_idx] if dd_idx < len(dates_str) else ""
            ax_dd.annotate(
                f"MaxDD {dd_val*100:.1f}%\n{dd_date}",
                xy=(dd_idx, dd_val * 100),
                xytext=(dd_idx + N * 0.08, dd_val * 100 * 0.6),
                fontsize=10, fontweight="bold", color=t["_dd_color"],
                arrowprops=dict(arrowstyle="->", color=t["_dd_color"],
                                lw=1.5, connectionstyle="arc3,rad=0.2"),
            )

    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.legend(loc="lower left", fontsize=9)

    # X-axis date labels
    _set_date_ticks(ax_dd, dates_str, N)

    if out is None:
        out = os.path.join(outdir, "equity.png")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    save_fc = t["_save_facecolor"] or fig.get_facecolor()
    fig.savefig(out, bbox_inches="tight", facecolor=save_fc)
    plt.close(fig)
    print(f"Chart: {out}")
    return out


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render(result: "BacktestResult", bars: list, outdir: str = ".", chart_type: str = "kline",
           out: Optional[str] = None, size: Tuple[float, float] = (19.2, 10.8),
           dpi: int = 100, theme: str = "dark",
           overlays: Optional[List[Dict[str, Any]]] = None,
           panels: Optional[List[Dict[str, Any]]] = None) -> str:
    """Render chart from BacktestResult + bars.

    Args:
        result: BacktestResult from backtest.run().
        bars: List[SecurityData] used in backtest.
        outdir: Output directory for PNG.
        chart_type: "kline" or "equity".
        out: Output PNG path override.
        size: Figure size in inches (width, height).
        dpi: Resolution.
        theme: "dark" (night) or "light" (day).
        overlays: Lines on price chart (kline only).
            [{"data": array, "label": str, "color": str}]
        panels: Indicator subplots (kline only).
            [{"title": str, "lines": [...], "bars": [...], "zero_line": bool}]

    Returns:
        Output PNG file path.
    """
    if chart_type == "kline":
        return render_kline(result, bars, outdir=outdir, out=out,
                            size=size, dpi=dpi, theme=theme,
                            overlays=overlays, panels=panels)
    elif chart_type == "equity":
        return render_equity(result, bars, outdir=outdir, out=out,
                             size=size, dpi=dpi, theme=theme)
    else:
        raise ValueError(f"Unknown chart_type: {chart_type!r} (use 'kline' or 'equity')")
