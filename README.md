<h1 align="center">MaoQuant Skills</h1>

<p align="center">
<strong>Validate any A-share trading idea in one sentence.</strong>
</p>

<p align="center">
<a href="./README.zh.md">简体中文</a> | English
</p>

---

You have a trading idea. MaoQuant generates a complete backtest report with equity curves, proving whether your strategy works -- programmatically.

## Quick Start

```bash
npx skills add Fidingks/Mao-Quant
```

Then tell your AI assistant:

```
/backtest ema-crossover SH600000
```

Done. Full report with charts, metrics, and trade log.

## What You Can Do

| Just ask like this...                                          | What you get                      |
| -------------------------------------------------------------- | --------------------------------- |
| "Can I make money on Moutai with a moving average strategy?"   | Full backtest with equity curve and report |
| "Is CATL good for short-term trading? Try KDJ"                | KDJ strategy backtest, every trade marked on chart |
| "Does buying on MACD golden cross actually work? Test it on Ping An" | MACD backtest with win rate, profit factor |
| "Find me stocks with PE below 15 and high volume"             | Full-market scan, filtered stock list |
| "How much drawdown if I trade Bollinger Band bounces?"         | Bollinger band backtest, max drawdown highlighted |

Talk to it like you'd talk to a quant-savvy friend. MaoQuant handles the rest.

## Built-in Strategies

| Strategy | Logic | Best For |
|----------|-------|----------|
| **EMA Crossover** | Fast/slow EMA golden cross / death cross | Trending markets |
| **RSI** | Overbought / oversold reversal | Range-bound markets |
| **MACD** | DIF / DEA crossover | Medium-term trends |
| **KDJ** | Stochastic extreme values | Short-term swings |
| **Bollinger Bands** | Price touching upper/lower bands | Mean reversion |

## Data Sources

Dual data engine -- choose what fits:

| Engine | Coverage | Setup |
|--------|----------|-------|
| **FaceCat API** | A-shares, daily bars | Zero config, works out of the box |
| **TDX (TongDaXin)** | Full A-share, daily/1min/5min | Requires TDX client with local data |

Built-in data works immediately. No API key needed.

## A-Share Rules (Auto-Enforced)

No configuration needed. MaoQuant enforces these automatically:

- **T+1**: Buy today, earliest sell is tomorrow
- **Price Limits**: Main board +/-10%, ChiNext/STAR +/-20%, BSE +/-30%
- **Lot Sizing**: Minimum 100 shares per trade
- **Stamp Tax**: 0.1% on sell side
- **Commission**: 0.025% both sides, minimum 5 CNY

## Architecture

MaoQuant follows the [AI Skill Manifest](SPEC.md) specification. The skill system is fully self-describing:

```
skills/
  SKILL.md              # Root manifest with capabilities, contracts, environment
  backtest/SKILL.md     # Backtest skill (user-invocable)
  scan/SKILL.md         # Screening skill (user-invocable)
  data/SKILL.md         # Data engine reference
  catquant-expert/      # Knowledge base + 6 rule files
catquant/               # Python engine (backtest, indicators, charts, data)
```

Key design decisions:

- **BarSeries container**: `get_history()` returns a `BarSeries` whose `repr` shows only a summary -- raw K-line data never leaks into AI context
- **Selftest**: `python -m catquant.selftest` validates the entire environment in 10 seconds
- **Contracts**: T+1, price limits, fees, and lot sizing are enforced by the engine, not by prompts

## Environment

```bash
pip install -r requirements.txt
cp .env.sample .env     # Edit FaceCat_URL and TDX_DIR if needed
python -m catquant.selftest
```

## Supported Clients

OpenClaw, Claude Code, Cursor, Windsurf, Copilot, Cline, OpenCode, Trae, and 40+ AI coding clients.

## Our Team

Built by the [FaceCat Quantitative Research Team](https://jjmfc.com). Members from: DZH (LongRuan), East Money, Soochow Securities, GF Securities, Donghai Securities, Shanxi Securities, Xiangcai Securities, Huatai Securities, Hengtai Futures, Deutsche Bank.

## Full Service

We offer:

- **Full-market data API** -- A-share real-time and historical data with proprietary analytics
- **Custom strategy development** -- Bespoke backtesting solutions for your trading ideas

Contact us: **https://www.jjmfc.com**

---

*Built by [FaceCat Quantitative Research Team](https://jjmfc.com)*
