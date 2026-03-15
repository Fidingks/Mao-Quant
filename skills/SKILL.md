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

## PDF Reports — Full Spec (when user asks for a report)

When the user requests a PDF report, generate a **complete, high-quality report** — not a minimal one. The report must include AI commentary that interprets results in plain language, not just numbers.

### Page Structure

```
Page 1 — Cover
Page 2 — Executive Summary (metrics + AI verdict)
Page 3 — K-line Chart (embed kline.png full-width)
Page 4 — Equity Curve (embed equity.png full-width)
Page 5 — Trade Records (table, paginated if > 30 trades)
Page 6 — Risk Analysis (risk ratios + AI risk commentary)
Page 7 — Conclusion & Suggestions
```

### Chinese Font Registration (MANDATORY — do this first)

```python
import sys
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def _register_cjk_font():
    candidates = []
    if sys.platform == "win32":
        candidates = [
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/Library/Fonts/Arial Unicode MS.ttf",
        ]
    else:
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
    raise RuntimeError("No CJK font found. Windows: simsun.ttc; Linux: sudo apt install fonts-wqy-microhei")

CJK_FONT = _register_cjk_font()
```

**Never use default `Helvetica` or `Times-Roman` for Chinese — they produce garbled output.**

### Style Setup

```python
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

styles = getSampleStyleSheet()

def cn(size=10, bold=False, color=colors.black):
    return ParagraphStyle("cn", fontName=CJK_FONT, fontSize=size,
                          leading=size * 1.5, textColor=color,
                          fontWeight="Bold" if bold else "Normal")

title_style   = cn(22, bold=True)
h2_style      = cn(13, bold=True, color=colors.HexColor("#1a237e"))
body_style    = cn(10)
caption_style = cn(9, color=colors.HexColor("#555555"))
verdict_style = cn(11, bold=True)
```

### Page 1 — Cover

```
[股票名称 + 代码]          (28pt, bold, centered)
[策略名称]                 (16pt, centered)
[回测区间: YYYY-MM-DD ~ YYYY-MM-DD]
[生成时间: YYYY-MM-DD HH:MM]
[MaoQuant · 量化回测报告]  (footer)
```

### Page 2 — Executive Summary

**Metrics table** — use a 2-column grid layout:

| 指标 | 值 |
|------|---|
| 初始资金 | 100,000 元 |
| 最终资产 | X,XXX,XXX 元 |
| 总收益率 | +XX.XX% |
| 年化收益率 | +XX.XX% |
| 最大回撤 | -XX.XX% |
| 夏普比率 | X.XX |
| 索提诺比率 | X.XX |
| 卡玛比率 | X.XX |
| 总交易次数 | XX 次 |
| 胜率 | XX.XX% |
| 盈亏比 | X.XX |
| 平均持仓 | XX 天 |
| 最长连续亏损 | X 次 |

**AI 综合评语** — generate from metrics using the rules below.

### AI Commentary Rules

Generate natural-language commentary based on these thresholds. Write in Chinese, conversational tone, 3-5 sentences per section.

**Overall Verdict** (one of four tones):

```python
def overall_verdict(m):
    tr = m["total_return"]
    md = abs(m["max_drawdown"])
    sr = m["sharpe_ratio"]
    if tr > 0.3 and md < 0.2 and sr > 1.0:
        return "strong"    # "策略表现出色，..."
    elif tr > 0 and sr > 0.5:
        return "decent"    # "策略整体有效，..."
    elif tr > 0:
        return "marginal"  # "策略勉强盈利，但风险控制有待加强..."
    else:
        return "losing"    # "策略在此区间亏损，..."
```

**Commentary templates** (customize with actual numbers):

```
strong:   "策略在{years}年回测中表现出色，累计收益{tr:.1%}，年化{ar:.1%}。
           最大回撤控制在{md:.1%}以内，夏普比率{sr:.2f}显示风险调整后收益优秀。
           适合作为核心策略参考。"

decent:   "策略整体有效，累计盈利{tr:.1%}，但存在一定波动。
           最大回撤{md:.1%}在可接受范围内，夏普比率{sr:.2f}处于合理水平。
           建议配合止损策略使用。"

marginal: "策略勉强盈利{tr:.1%}，但胜率仅{wr:.1%}，盈亏比{pf:.2f}偏低。
           最大回撤{md:.1%}较大，持仓期间心理压力较高。
           建议优化参数或换用其他策略。"

losing:   "策略在此区间亏损{tr:.1%}，共{total}笔交易，胜率{wr:.1%}。
           最大回撤达{md:.1%}，说明策略与该股票当前趋势不匹配。
           建议尝试其他策略或等待趋势确认。"
```

**Win rate interpretation**:
- `win_rate > 0.6 and profit_factor < 1.2` → "胜率较高但盈亏比偏低，可能存在小赚大亏的问题，注意设置止盈。"
- `win_rate < 0.4 and profit_factor > 2.0` → "胜率较低但盈亏比优秀，属于趋势跟踪型策略，需要心理承受能力。"
- `max_consecutive_losses > 5` → "最长连续亏损{n}次，实盘时需做好心态管理。"

**Risk rating** (show as colored badge):
```python
def risk_rating(m):
    md = abs(m["max_drawdown"])
    if md < 0.15: return ("低风险", "#4caf50")
    elif md < 0.25: return ("中等风险", "#ff9800")
    elif md < 0.40: return ("较高风险", "#f44336")
    else: return ("高风险", "#b71c1c")
```

### Page 5 — Trade Records Table

Columns: `序号 | 买入日期 | 买入价 | 卖出日期 | 卖出价 | 股数 | 手续费 | 盈亏(元) | 持仓天数`

- Profitable rows: light green background (`#e8f5e9`)
- Loss rows: light red background (`#ffebee`)
- Open positions: light yellow (`#fffde7`) + "持仓中" in 卖出日期 column
- If > 30 trades, show first 15 + last 15 with a "…共 N 笔交易" separator

```python
from reportlab.platypus import TableStyle
from reportlab.lib import colors

def trade_row_style(trades):
    styles = []
    for i, t in enumerate(trades):
        row = i + 1  # header is row 0
        if t["exit_date"] == "":
            bg = colors.HexColor("#fffde7")
        elif t["pnl"] > 0:
            bg = colors.HexColor("#e8f5e9")
        else:
            bg = colors.HexColor("#ffebee")
        styles.append(("BACKGROUND", (0, row), (-1, row), bg))
    return styles
```

### Page 6 — Risk Analysis

Display these ratios with plain-language explanation next to each:

| 指标 | 值 | 含义 |
|------|----|----|
| 夏普比率 | X.XX | > 1.0 表示风险调整后收益良好 |
| 索提诺比率 | X.XX | 仅考虑下行波动，> 1.0 为佳 |
| 卡玛比率 | X.XX | 年化收益/最大回撤，> 0.5 可接受 |
| 最大回撤 | -XX% | 最大亏损幅度 |
| 最长回撤持续 | XX 天 | 深度亏损持续时间 |

**AI 风险评语**: 2-3 sentences interpreting the risk profile:
```
"该策略最大回撤{md:.1%}，最长持续{dur}个交易日。
 卡玛比率{calmar:.2f}，说明每承受1%的最大回撤，
 可获得{calmar:.2f}%的年化收益。{rating}。"
```

### Page 7 — Conclusion & Suggestions

Always include these 4 sections:

1. **策略总结** — one paragraph summarizing what the strategy does and how it performed
2. **优势** — bullet list of strong points (high win rate / controlled drawdown / good Sharpe / etc.)
3. **风险提示** — bullet list of weaknesses (high drawdown / low win rate / short sample / etc.)
4. **改进建议** — concrete suggestions:
   - If `avg_holding_bars < 5`: "持仓过短，频繁交易产生较高手续费，建议提高信号阈值"
   - If `max_drawdown < -0.30`: "最大回撤偏大，建议加入止损 `stop_loss=0.08`"
   - If `total_trades < 10`: "样本量不足，建议延长回测区间或换用更频繁触发的策略"
   - If `win_rate < 0.35`: "胜率较低，建议配合趋势过滤条件（如均线方向）"

### Output Path

Save to: `backtesting/{strategy}/{symbol}_report.pdf`

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
