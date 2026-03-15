---
name: pitfalls
description: Common mistakes in A-share backtesting and how to avoid them
metadata:
  tags: pitfalls, mistakes, checklist, bugs
  last_verified: "2026-03-15"
---

# Common A-Share Backtesting Pitfalls

## 1. Ignoring T+1
- **Mistake**: Allowing same-day buy and sell.
- **Fix**: Use `price_field="open"` in `backtest.run()` for T+1 compliant execution. The engine also prevents selling on the same bar as entry.

## 2. Trading at Price Limits
- **Mistake**: Buying at 涨停 or selling at 跌停 (impossible in real market).
- **Fix**: catquant engine handles this automatically via `limit_pct` parameter and `_is_limit_up()`/`_is_limit_down()` checks.

## 3. Wrong Lot Size
- **Mistake**: Buying fractional shares or less than 100.
- **Fix**: catquant engine rounds to 100-share lots via `_calc_shares()`.

## 4. Incorrect Indicator Implementation
- **Mistake**: Hand-rolling indicators with subtle bugs.
- **Fix**: Use `catquant.indicators` which provides tested implementations of MA, EMA, MACD, KDJ, RSI, BOLL, etc.

## 5. Survivorship Bias
- **Mistake**: Only testing stocks that still exist today.
- **Note**: Historical data inherently has this bias. Acknowledge it in reports.

## 6. Look-Ahead Bias
- **Mistake**: Using future data to generate signals.
- **Fix**: Always use previous bar values for cross-over detection. Compare `[i-1]` vs `[i]`.

## 7. Ignoring Fees
- **Mistake**: Running backtest without fees.
- **Fix**: catquant engine applies A-share fees automatically via `catquant.fees` module.

## 8. Not Cleaning Signals
- **Mistake**: Multiple consecutive buy/sell signals causing logic errors.
- **Fix**: Always use `catquant.signals.exrem()` to clean signals.

## Pre-Launch Checklist

- [ ] T+1 enforced (price_field="open" or engine buy_bar check)
- [ ] Price limit filtering active (limit_pct set correctly)
- [ ] Lot size = 100 (handled by engine)
- [ ] Fees applied (handled by engine)
- [ ] Signals cleaned with exrem
- [ ] No look-ahead bias
- [ ] Benchmark comparison included
- [ ] Results explained in plain language
