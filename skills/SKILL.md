---
name: maoquant
version: "0.2.0"
spec: "skill-manifest/0.1"
description: A-share quantitative backtesting skill system.

capabilities:
  - name: backtest
    description: Run strategy backtest on A-share symbol
    input: { strategy: string, symbol: string, interval: string }
    output: { result_json: file, kline_png: file, equity_png: file }
    invocable: true
  - name: scan
    description: Full-market stock screening
    input: { criteria: string }
    output: { scan_results: list, csv: file }
    invocable: true
  - name: catquant-expert
    description: API reference and knowledge base
    invocable: false
  - name: data
    description: Data engine reference
    invocable: false

contracts:
  - id: data-isolation
    enforcement: architectural
    description: Raw data stays in scripts. BarSeries.__repr__ returns summary only.
  - id: a-share-compliance
    enforcement: code
    description: T+1, price limits, lot sizing, fees enforced by backtest.run().
  - id: no-emoji
    enforcement: convention
    description: No emoji in code or output.

environment:
  python: ">=3.9"
  packages: [numpy>=1.24, pandas>=2.0, matplotlib>=3.5, python-dotenv>=1.0]
  env_vars:
    - { name: FaceCat_URL, required: true, default: "https://www.jjmfc.com:9969" }
    - { name: TDX_DIR, required: false }
    - { name: CACHE_DIR, required: false, default: "./cache" }

selftest: "python -m catquant.selftest"
---

<instructions>

## Sub-Skills

| Skill | Description | User-Invocable |
|-------|-------------|----------------|
| [backtest](backtest/SKILL.md) | Run a strategy backtest | Yes |
| [scan](scan/SKILL.md) | Full-market stock screening | Yes |
| [data](data/GUIDE.md) | Data engine reference | No |
| [catquant-expert](catquant-expert/GUIDE.md) | API reference + knowledge base | No |

## Quickstart

```python
from catquant.data_engine import get_history
from catquant.backtest import run, export
from catquant.chart import render
from catquant.signals import exrem, cross_above, cross_below

bars = get_history("600000.SH", cycle=1440, count=1000)
result = run(bars, buy_signal, sell_signal, initial_capital=100000, market="sh")
export(result, bars, "backtesting/output", code="600000.SH", strategy="EMA Cross")
render(result, bars, "backtesting/output")            # kline.png
render(result, bars, "backtesting/output", "equity")  # equity.png
```

Details: see [catquant-expert](catquant-expert/GUIDE.md).

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

</instructions>
