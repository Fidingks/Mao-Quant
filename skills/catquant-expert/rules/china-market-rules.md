---
name: china-market-rules
description: A-share trading rules - T+1, price limits, lot sizing, trading hours
metadata:
  tags: T+1, price-limit, lot-size, trading-hours, A-share
  last_verified: "2026-03-15"
---

# A-Share Trading Rules

## T+1 Settlement

- Stocks bought on day T **cannot be sold until T+1**.
- In catquant `backtest.run()`, use `price_field="open"` for T+1 compliant execution: signals on bar[i] execute on bar[i+1] open.
- The engine tracks `buy_bar` and prevents selling on the same bar as entry.

## Price Limits (涨跌停)

| Board | Limit | Codes |
|-------|-------|-------|
| Main Board (主板) | +/-10% | SH600xxx, SH601xxx, SZ000xxx, SZ001xxx |
| ChiNext (创业板) | +/-20% | SZ300xxx, SZ301xxx |
| STAR Market (科创板) | +/-20% | SH688xxx, SH689xxx |
| BSE (北交所) | +/-30% | BJ8xxxxx, BJ4xxxxx |
| ST stocks | +/-5% | Any with ST prefix |

### Impact on Backtesting

- **涨停 (limit up)**: Cannot buy. catquant engine automatically blocks buy orders at limit up.
- **跌停 (limit down)**: Cannot sell. catquant engine automatically blocks sell orders at limit down.
- Auto-detected by `backtest.get_limit_pct(code)` or set via `limit_pct` parameter.

## Lot Sizing (整手交易)

- **Minimum buy**: 100 shares (1 lot / 1手)
- **Sell**: Can sell any quantity (odd lots allowed for closing)
- catquant engine rounds shares to nearest 100 via `_calc_shares()`.

## Trading Hours

| Session | Time |
|---------|------|
| Morning | 09:30 - 11:30 |
| Afternoon | 13:00 - 15:00 |
| Total | 4 hours / day |

- Pre-market auction (集合竞价): 09:15 - 09:25
- Closing auction: 14:57 - 15:00

## Benchmark Indices

| Index | Code | Description |
|-------|------|-------------|
| CSI 300 (沪深300) | SH000300 | Large cap, most common benchmark |
| CSI 500 (中证500) | SH000905 | Mid cap |
| SSE Composite (上证指数) | SH000001 | Shanghai all shares |
| SZSE Component (深证成指) | SZ399001 | Shenzhen main |
| ChiNext Index (创业板指) | SZ399006 | Growth / tech |
