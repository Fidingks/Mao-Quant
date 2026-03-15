---
name: china-market-costs
description: A-share transaction cost model - commission, stamp tax, transfer fee
metadata:
  tags: fees, costs, commission, stamp-tax, A-share
  last_verified: "2026-03-15"
---

# A-Share Transaction Costs

## Fee Breakdown

| Fee | Rate | Direction | Notes |
|-----|------|-----------|-------|
| Commission (佣金) | 0.025% (万2.5) | Buy + Sell | Min 5 CNY per trade |
| Stamp Tax (印花税) | 0.1% (千1) | Sell only | Since 2023-08-28 (halved from 0.2%) |
| Transfer Fee (过户费) | 0.001% (十万分之一) | Buy + Sell | Shanghai only, negligible |

## Round-Trip Cost

```
Buy:  0.025% commission
Sell: 0.025% commission + 0.1% stamp tax
Total round-trip: ~0.15%
```

## catquant Fee Configuration

catquant handles fees via `catquant.fees.calculate_cost()`, which separates buy/sell:

```python
from catquant.fees import calculate_cost

buy_fee = calculate_cost(amount, side="buy", market="sh")   # commission only
sell_fee = calculate_cost(amount, side="sell", market="sh")  # commission + stamp tax
```

The `backtest.run()` function applies fees automatically based on `market` parameter.

## By Market Segment

| Segment | Commission | Stamp Tax | Transfer Fee |
|---------|-----------|-----------|-------------|
| Main Board (主板) | 万2.5 | 千1 (sell) | 十万分之1.6 (SH only) |
| ChiNext (创业板) | 万2.5 | 千1 (sell) | None |
| STAR (科创板) | 万2.5 | 千1 (sell) | 十万分之1.6 |
| BSE (北交所) | 万2.5 | 千1 (sell) | None |
| ETF | 万2.5 | None | None |

## Notes

- Commission rates vary by broker. 万2.5 is typical for retail. Some discount brokers offer 万1.5.
- Stamp tax was halved from 0.2% to 0.1% on 2023-08-28.
- catquant separates buy/sell fees precisely, no averaging needed.
