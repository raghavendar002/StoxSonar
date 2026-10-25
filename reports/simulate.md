# Phase 5: a Rs 100,000 account trading v0.2.0 as suggested

Buys: Grade A or B breakouts in a Healthy market, sized to risk 0.5% of equity, at the next open unless it gaps past the plan's ceiling. Exits: the 2.5-ATR stop (filled at the open on a gap through it) or the close 21 sessions after the signal. Costs: STT, exchange and SEBI fees, stamp duty, GST, DP charge, and 0.05-0.5% slippage each way by liquidity. Benchmark: Nifty 500 price index (no dividends, so about 1-1.5 points a year flattering to us).

## Headline

| period | max positions | start | end | cagr_pct | bench_cagr_pct | max_drawdown_pct | bench_max_drawdown_pct | sharpe | final_rs | trades | win_pct | avg_win_pct | avg_loss_pct | profit_factor | avg_sessions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2007-2018 (cap chosen here) | no cap | 2007-01-10 | 2018-12-31 | 0.84 | 9.15 | -21.9 | -64.3 | 0.14 | 110501 | 663 | 42.7 | 15.34 | -10.7 | 1.05 | 15.1 |
| 2007-2018 (cap chosen here) | 8 | 2007-01-10 | 2018-12-31 | 1.19 | 9.15 | -12.6 | -64.3 | 0.24 | 115157 | 452 | 43.6 | 14.98 | -10.1 | 1.12 | 15.4 |
| 2007-2018 (cap chosen here) | 5 | 2007-01-10 | 2018-12-31 | 1.89 | 9.15 | -8.4 | -64.3 | 0.46 | 125198 | 328 | 47.3 | 14.54 | -10.08 | 1.29 | 15.8 |
| 2019 on (unseen by v0.2's fit and by the cap choice) | no cap | 2019-04-01 | 2026-10-23 | 2.88 | 11.05 | -24.1 | -38.3 | 0.29 | 123973 | 901 | 40.6 | 15.43 | -10.99 | 1.1 | 15.3 |
| 2019 on (unseen by v0.2's fit and by the cap choice) | 8 | 2019-04-01 | 2026-10-23 | -0.42 | 11.05 | -17.5 | -38.3 | -0.03 | 96850 | 402 | 40.3 | 14.63 | -10.27 | 0.97 | 14.9 |
| 2019 on (unseen by v0.2's fit and by the cap choice) | 5 | 2019-04-01 | 2026-10-23 | -0.91 | 11.05 | -17.1 | -38.3 | -0.17 | 93289 | 268 | 39.6 | 14.57 | -10.53 | 0.91 | 14.9 |
| All years | no cap | 2007-01-10 | 2026-10-23 | 1.76 | 10.06 | -23.1 | -64.3 | 0.22 | 141253 | 1565 | 41.5 | 15.38 | -10.64 | 1.09 | 15.2 |
| All years | 8 | 2007-01-10 | 2026-10-23 | 0.66 | 10.06 | -16.9 | -64.3 | 0.14 | 113925 | 854 | 42.2 | 14.82 | -10.14 | 1.06 | 15.2 |
| All years | 5 | 2007-01-10 | 2026-10-23 | 0.86 | 10.06 | -16.3 | -64.3 | 0.21 | 118455 | 596 | 44.0 | 14.54 | -10.21 | 1.1 | 15.4 |


Cap chosen on 2007-2018 by Sharpe: **5**. The sections below use it.

## 2019 on (unseen by v0.2's fit and by the cap choice), max positions 5: year by year (%)

| year | strategy | bench | excess |
|---|---|---|---|
| 2019 | 0.0 | 1.8 | -1.8 |
| 2020 | -4.9 | 16.7 | -21.6 |
| 2021 | 14.8 | 30.2 | -15.4 |
| 2022 | -8.4 | 3.0 | -11.4 |
| 2023 | 4.6 | 25.8 | -21.2 |
| 2024 | -10.3 | 15.2 | -25.5 |
| 2025 | -2.1 | 6.7 | -8.8 |
| 2026 | 1.5 | -10.2 | 11.7 |


### 2019 on (unseen by v0.2's fit and by the cap choice), max positions 5: how trades ended

| reason | trades | avg_ret_pct | total_pnl_rs |
|---|---|---|---|
| gap below stop | 13 | -15.0 | -9371 |
| stop | 100 | -12.99 | -55858 |
| time | 155 | 8.59 | 58518 |


Average invested: 10% of the account; average open positions 2.1.

## All years, max positions 5: year by year (%)

| year | strategy | bench | excess |
|---|---|---|---|
| 2007 | 9.0 | 66.6 | -57.6 |
| 2008 | -1.7 | -57.1 | 55.4 |
| 2009 | -2.9 | 88.6 | -91.5 |
| 2010 | -0.2 | 14.1 | -14.3 |
| 2011 | -1.0 | -27.2 | 26.2 |
| 2012 | 4.5 | 31.8 | -27.3 |
| 2013 | -2.0 | 3.6 | -5.6 |
| 2014 | 7.6 | 37.8 | -30.2 |
| 2015 | 1.7 | -0.7 | 2.4 |
| 2016 | 0.0 | 3.8 | -3.8 |
| 2017 | 7.8 | 35.9 | -28.1 |
| 2018 | 0.8 | -3.4 | 4.2 |
| 2019 | 0.0 | 7.7 | -7.7 |
| 2020 | -4.9 | 16.7 | -21.6 |
| 2021 | 14.9 | 30.2 | -15.3 |
| 2022 | -7.9 | 3.0 | -10.9 |
| 2023 | 4.9 | 25.8 | -20.9 |
| 2024 | -9.9 | 15.2 | -25.1 |
| 2025 | -1.9 | 6.7 | -8.6 |
| 2026 | 1.4 | -10.2 | 11.6 |


### All years, max positions 5: how trades ended

| reason | trades | avg_ret_pct | total_pnl_rs |
|---|---|---|---|
| gap below stop | 25 | -14.86 | -20486 |
| stop | 212 | -12.37 | -139153 |
| time | 359 | 9.46 | 178094 |


Average invested: 9% of the account; average open positions 1.9.

