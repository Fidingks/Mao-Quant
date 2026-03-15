---
name: backtest
spec: "skill-manifest/0.1"
description: Run a strategy backtest on an A-share symbol using catquant engine.
argument-hint: "[strategy] [symbol] [interval]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
input:
  strategy: { type: string, default: ema-crossover, enum: [ema-crossover, rsi, macd, kdj, boll] }
  symbol: { type: string, default: SH600000 }
  interval: { type: string, default: D, enum: [D, 5m, 1m] }
output:
  result_json: { type: file, path: "backtesting/{strategy}/result.json" }
  kline_png: { type: file, path: "backtesting/{strategy}/kline.png" }
  equity_png: { type: file, path: "backtesting/{strategy}/equity.png" }
---

Create a catquant backtest script.

## Arguments

Parse `$ARGUMENTS` as: strategy symbol interval

- `$0` = strategy (ema-crossover, rsi, macd, kdj, boll). Default: ema-crossover
- `$1` = symbol (e.g., SH600000, SZ000001). Default: SH600000
- `$2` = interval (D, 5m, 1m). Default: D

If no arguments, ask the user.

## Instructions

1. Read [catquant-expert](../catquant-expert/GUIDE.md) for workflow, API, and strategy patterns
2. Create script at `backtesting/{strategy_name}/{symbol}_{strategy}_backtest.py`
3. The script must: load data, compute signals, run backtest, export JSON, render charts, print metrics
4. Explain the backtest report in plain language

## Chart Rendering

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

## Example

`/backtest ema-crossover SH600000 D`
`/backtest macd SZ300750 5m`
