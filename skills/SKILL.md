---
name: maoquant
version: "0.2.0"
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

selftest: "cd skills && python -m catquant.selftest"
---

<instructions>

Parse `$ARGUMENTS`: first word is command (`backtest` or `scan`), rest are command args.
If no arguments or unrecognized command, ask the user.

## Setup

The `catquant` package lives inside this skill directory. Every generated script must add it to `sys.path`:

```python
import sys, os
# Add skill directory to path so catquant can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "$SKILL_DIR"))
```

`$SKILL_DIR` is the relative path from the script to this skill's directory (where `catquant/` lives).
First run: `pip install -r $SKILL_DIR/requirements.txt` and `cp $SKILL_DIR/.env.sample .env` if `.env` doesn't exist.

---

## Command: backtest

**Arguments**: `backtest [strategy] [symbol] [interval]`

- strategy: ema-crossover, rsi, macd, kdj, boll (default: ema-crossover)
- symbol: e.g. SH600000, SZ000001 (default: SH600000)
- interval: D, 5m, 1m (default: D)

**Steps**:

1. Read [catquant-expert](catquant-expert/GUIDE.md) for workflow, API, and strategy patterns
2. Create script at `backtesting/{strategy_name}/{symbol}_{strategy}_backtest.py`
3. The script must: load data, compute signals, run backtest, export JSON, render charts, print metrics
4. Explain the backtest report in plain language

### Chart Rendering

**Always render charts with the strategy's indicator lines.** Use `overlays` for lines on the price chart and `panels` for separate indicator subplots. Pick the configuration matching the strategy:

| Strategy | overlays (on price) | panels (subplots) |
|----------|--------------------|--------------------|
| **EMA Cross** | EMA fast + EMA slow lines | MACD panel (DIF/DEA lines + MACD bars + zero_line) |
| **MACD** | EMA(12) + EMA(26) lines | MACD panel (DIF/DEA lines + MACD bars + zero_line) |
| **RSI** | EMA(14) line | RSI panel (RSI line + overbought/oversold hlines) |
| **KDJ** | -- | KDJ panel (K/D/J lines) |
| **BOLL** | Upper + Mid + Lower lines + fill between upper/lower | -- |
| **Custom** | Any indicator lines used in signals | Relevant oscillator if applicable |

Example (EMA crossover):
```python
ema5 = ema_series(close, 5)
ema20 = ema_series(close, 20)
dif, dea, macd = getMACDData(close)

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

**Color palette**: `#ff9800` (orange), `#2196f3` (blue), `#e040fb` (purple), `#00bcd4` (cyan), `#8bc34a` (green).
Lines: `#2962ff` (DIF), `#ff6d00` (DEA), `#e040fb` (J line). Bars auto-colored red/green by sign.

---

## Command: scan

**Arguments**: `scan [screening criteria]`

Screening criteria in natural language. If empty, ask the user.

**Steps**:

1. Parse criteria into pre_filter (PriceData) and filter_fn (K-line) layers
2. Create script at `scanning/{name}_scan.py`
3. Run and show results

### Choosing scan type

- **Price/volume/PE only** (no K-line needed): `quick_scan(pre_filter)` -- instant
- **Needs history** (MA, MACD, patterns): `scan(filter_fn, pre_filter)` -- two-layer

### pre_filter (Layer 1)

Receives `PriceData`. Key fields:
`p.code`, `p.name`, `p.close`, `p.open`, `p.high`, `p.low`, `p.volume`, `p.amount`,
`p.lastClose`, `p.pe`, `p.totalShares`, `p.flowShares`, `p.upperLimit`, `p.lowerLimit`

```python
p.volume > 0 and p.close > 3 and "ST" not in p.name  # typical
```

### filter_fn (Layer 2)

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

### scan() / quick_scan()

```python
scan(filter_fn, pre_filter=None, universe=None, count=250,
     cycle=1440, source="facecat", max_results=20,
     sort_key="score", ascending=False, verbose=True, refresh=False)

quick_scan(pre_filter=None, max_results=50, sort_key="close", ascending=False)
```

---

## Constraints

1. **数据不进上下文** — 通过 `catquant.data_engine` 在脚本内获取数据；禁止将原始 K 线打印给 agent；禁止直接构造 API 请求
2. **A 股规则不可违反** — `catquant.backtest.run()` 已内置：
   - T+1: 当日买入不可当日卖出（`price_field="open"`）
   - 涨跌停: 主板 ±10%，创业板/科创板 ±20%，北交所 ±30%
   - 整手交易: 最小 100 股
   - 费用: 佣金万 2.5 + 印花税千 1（卖出）+ 过户费十万分之 1.6（沪市）
3. **脚本放 `backtesting/` 目录**，扫描脚本放 `scanning/`
4. **代码和输出中禁止 emoji**
5. **图表用 matplotlib**（`catquant.chart.render()`）

## Reference

- [catquant-expert](catquant-expert/GUIDE.md) — API reference, indicators, strategy patterns
- [data](data/GUIDE.md) — Data engine, SecurityData, symbol format

</instructions>
