---
name: maoquant
version: "0.3.0"
spec: "skill-manifest/0.1"
description: A-share quantitative backtesting skill system.
argument-hint: "[backtest|scan] [args...]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep

environment:
  python: ">=3.9"
  packages: [numpy>=1.24, pandas>=2.0, matplotlib>=3.5, python-dotenv>=1.0]
  env_vars:
    - { name: FaceCat_URL, required: true, default: "https://www.jjmfc.com:9969" }
    - { name: TDX_DIR, required: false }
    - { name: CACHE_DIR, required: false, default: "./cache" }

selftest: "cd $SKILL_DIR && python -m catquant.selftest"
---

<instructions>

## Principles (MUST follow, read this FIRST)

1. **NEVER ask the user for parameters.** User says "茅台均线能赚钱吗" → you pick strategy=ema-crossover, symbol=600519.SH, interval=D, and run it. Use sensible defaults for everything.
2. **Resolve stock names yourself.** "茅台" = 600519.SH, "平安" = 601318.SH. Use `catquant.resolve.resolve(query)` to map names to codes. NEVER ask the user "请问茅台的代码是什么".
3. **Validate data BEFORE running backtest — NEVER skip this.** Call `check_available(code)` and if it returns `False`, STOP immediately and tell the user. Do NOT assume data exists. Do NOT create a script without checking first. Most stocks are NOT covered by the free API.
4. **Handle errors gracefully.** If data source fails, suggest alternatives (TDX local data, or contact developer). Never show raw Python tracebacks to the user.
5. **One sentence = one complete result.** The user's single sentence should produce a full backtest report with charts. No intermediate questions, no "请确认参数" dialogues.

---

## Setup

The `catquant` package lives inside this skill directory (`$SKILL_DIR`). Every generated script must:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "$SKILL_DIR"))
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
```

First run: `pip install -r $SKILL_DIR/requirements.txt` if dependencies are missing.

---

## Step 0: Resolve stock and validate data (MANDATORY — do NOT skip)

**STOP. You MUST complete BOTH steps below BEFORE writing any backtest or scan script. If you skip `check_available`, the script WILL fail and the user gets nothing.**

```python
from catquant.resolve import resolve, check_available

# Step 0a: Resolve name to code
code, name = resolve("茅台")         # -> ("600519.SH", "茅台")

# Step 0b: Check data — YOU MUST DO THIS, DO NOT ASSUME DATA EXISTS
ok, source, hint = check_available(code)
if not ok:
    print(hint)   # Tell the user WHY it failed and HOW to fix it
    sys.exit(1)   # STOP HERE. Do NOT create a backtest script.
```

**CRITICAL: If `check_available` returns `(False, ...)` you MUST:**
1. **STOP** — do NOT proceed to create or run any backtest script
2. Tell the user the stock is not covered, in plain language
3. Give actionable next steps:
   - If TDX_DIR is set but stock not found → "Please download this stock's data in your TDX client"
   - If TDX_DIR is not set → "Set up TDX local data, or contact https://www.jjmfc.com for full-market access"
4. **Do NOT silently fail, do NOT produce an empty backtest, do NOT skip this check**

The free FaceCat API only covers ~84 stocks. Most stocks (including 茅台、比亚迪、宁德时代 etc.) are NOT covered. You MUST verify before proceeding.

**If `ok` is True:** use the returned `source` value in `get_history()`:
- `source="facecat"` (default) or `source="tdx", tdx_dir=os.environ["TDX_DIR"]`

---

## Command: backtest

Parse `$ARGUMENTS`: `backtest [strategy] [symbol] [interval]`

- strategy: ema-crossover, rsi, macd, kdj, boll. **Default: ema-crossover** (do NOT ask)
- symbol: stock name or code. **Default: SH600000** (do NOT ask)
- interval: D, 5m, 1m. **Default: D** (do NOT ask)

**Steps**:

1. Resolve stock name → code (Step 0 above)
2. Validate data availability (Step 0 above)
3. Read [catquant-expert](catquant-expert/GUIDE.md) for API and strategy patterns
4. Create script at `backtesting/{strategy_name}/{symbol}_{strategy}_backtest.py`
5. Script must: load data, compute signals, run backtest, export JSON, render charts with indicator lines, print metrics
6. Run the script
7. Explain the backtest report in plain language to the user

### Chart Rendering

**Always render charts with the strategy's indicator lines.** Use `overlays` for lines on the price chart and `panels` for indicator subplots:

| Strategy | overlays (on price) | panels (subplots) |
|----------|--------------------|--------------------|
| **EMA Cross** | EMA fast + EMA slow lines | MACD panel (DIF/DEA + MACD bars + zero_line) |
| **MACD** | EMA(12) + EMA(26) lines | MACD panel (DIF/DEA + MACD bars + zero_line) |
| **RSI** | EMA(14) line | RSI panel (RSI line) |
| **KDJ** | -- | KDJ panel (K/D/J lines) |
| **BOLL** | Upper + Mid + Lower lines + fill | -- |
| **Custom** | Indicator lines used in signals | Relevant oscillator |

Example:
```python
render(result, bars, outdir, "kline",
    overlays=[
        {"data": ema5,  "label": "EMA5",  "color": "#ff9800"},
        {"data": ema20, "label": "EMA20", "color": "#2196f3"},
    ],
    panels=[{
        "title": "MACD",
        "lines": [
            {"data": dif, "label": "DIF", "color": "#2962ff"},
            {"data": dea, "label": "DEA", "color": "#ff6d00"},
        ],
        "bars": [{"data": macd, "label": "MACD"}],
        "zero_line": True,
    }])
render(result, bars, outdir, "equity")
```

---

## Command: scan

Parse `$ARGUMENTS`: `scan [screening criteria]`

Natural language criteria. **Default: scan all stocks** (do NOT ask for clarification if criteria is clear enough).

**Steps**:

1. Parse criteria into pre_filter (PriceData fields) and filter_fn (K-line indicators)
2. Create script at `scanning/{name}_scan.py`
3. Run and show results

### Scan types

- **Price/volume/PE only**: `quick_scan(pre_filter)` — instant, no K-line download
- **Needs indicators**: `scan(filter_fn, pre_filter)` — two-layer, downloads K-lines

### pre_filter (Layer 1)

```python
lambda p: p.volume > 0 and p.close > 3 and "ST" not in p.name
```

Fields: `p.code, p.name, p.close, p.open, p.high, p.low, p.volume, p.amount, p.lastClose, p.pe, p.totalShares, p.flowShares, p.upperLimit, p.lowerLimit`

### filter_fn (Layer 2)

```python
def filter_fn(code, name, bars):
    if len(bars) < 30: return None
    close, high, low, vol = bars_to_arrays(bars)
    # compute indicators...
    if condition: return {"score": value, "reason": "..."}
    return None
```

### API

```python
scan(filter_fn, pre_filter=None, universe=None, count=250,
     cycle=1440, source="facecat", max_results=20,
     sort_key="score", ascending=False, verbose=True, refresh=False)

quick_scan(pre_filter=None, max_results=50, sort_key="close", ascending=False)
```

---

## PDF Reports (Chinese font — MANDATORY)

When generating PDF reports with `reportlab`, **Chinese characters WILL be garbled unless you register a CJK font first.** Always include the following block at the top of any PDF-generating script:

```python
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _register_cjk_font():
    """Register a CJK font for reportlab. Tries common paths across platforms."""
    candidates = []
    if sys.platform == "win32":
        candidates = [
            r"C:\Windows\Fonts\simsun.ttc",   # SimSun (宋体) — most common
            r"C:\Windows\Fonts\msyh.ttc",      # Microsoft YaHei (微软雅黑)
            r"C:\Windows\Fonts\simhei.ttf",    # SimHei (黑体)
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode MS.ttf",
        ]
    else:  # Linux
        candidates = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    for path in candidates:
        try:
            pdfmetrics.registerFont(TTFont("CJK", path))
            return "CJK"
        except Exception:
            continue
    raise RuntimeError(
        "No CJK font found. On Windows install SimSun; on Linux: "
        "sudo apt install fonts-wqy-microhei"
    )

CJK_FONT = _register_cjk_font()
```

Then use `CJK_FONT` as the font name for all Chinese text in the PDF:

```python
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

styles = getSampleStyleSheet()
cn_style = ParagraphStyle("CN", parent=styles["Normal"], fontName=CJK_FONT, fontSize=10)
Paragraph("策略名称：均线交叉", cn_style)
```

**Do NOT use the default `Helvetica` or `Times-Roman` fonts for Chinese content — they produce garbled output (乱码).**

---

## Constraints

1. **Raw data never enters AI context** — use `catquant.data_engine` inside scripts only
2. **A-share compliance auto-enforced** by `backtest.run()`:
   - T+1, price limits (10%/20%/30%), lot sizing (100 shares), fees
3. Scripts go in `backtesting/` or `scanning/`
4. No emoji in code or output
5. Charts via `catquant.chart.render()`
6. PDF reports must use a registered CJK font (see PDF Reports section above)

## Reference

- [catquant-expert](catquant-expert/GUIDE.md) — API, indicators, strategy patterns
- [data](data/GUIDE.md) — Data engine, SecurityData, symbol format

</instructions>
