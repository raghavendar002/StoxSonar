# Phase 6: exit study on v0.2's entries

Same entries, sizes and initial stop for all six exits; a fresh Rs 1 lakh per run; full costs. Benchmark: Nifty 500 price index (no dividends).

## Results

| exit | period | cagr_pct | bench_cagr_pct | max_drawdown_pct | bench_max_drawdown_pct | sharpe | final_rs | trades | win_pct | avg_win_pct | avg_loss_pct | profit_factor | avg_sessions | invested_pct | max_positions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v02 | 2007-2018 | 0.84 | 9.15 | -21.9 | -64.3 | 0.14 | 110501 | 663 | 42.7 | 15.34 | -10.7 | 1.05 | 15.1 | 16.5 | 25 |
| v02 | 2019 on | 2.88 | 11.05 | -24.1 | -38.3 | 0.29 | 123973 | 901 | 40.6 | 15.43 | -10.99 | 1.1 | 15.3 | 31.4 | 32 |
| time63 | 2007-2018 | 7.22 | 9.15 | -32.4 | -64.3 | 0.58 | 230273 | 567 | 34.7 | 31.24 | -13.06 | 1.43 | 34.6 | 33.0 | 29 |
| time63 | 2019 on | 4.3 | 11.05 | -29.4 | -38.3 | 0.35 | 137462 | 578 | 32.0 | 29.78 | -14.45 | 1.12 | 35.2 | 44.5 | 33 |
| sma50 | 2007-2018 | 7.58 | 9.15 | -29.0 | -64.3 | 0.6 | 239894 | 532 | 36.3 | 26.03 | -12.04 | 1.6 | 34.6 | 32.6 | 25 |
| sma50 | 2019 on | 7.1 | 11.05 | -27.0 | -38.3 | 0.54 | 167980 | 563 | 33.2 | 27.6 | -12.58 | 1.27 | 33.2 | 42.2 | 35 |
| chandelier | 2007-2018 | 4.15 | 9.15 | -26.3 | -64.3 | 0.42 | 162787 | 616 | 37.7 | 20.2 | -10.44 | 1.29 | 24.2 | 25.9 | 27 |
| chandelier | 2019 on | 7.38 | 11.05 | -24.2 | -38.3 | 0.6 | 171369 | 685 | 33.7 | 23.65 | -11.06 | 1.27 | 23.4 | 37.4 | 30 |
| breakeven | 2007-2018 | 5.44 | 9.15 | -28.2 | -64.3 | 0.47 | 188481 | 556 | 27.3 | 28.64 | -9.42 | 1.44 | 30.7 | 31.0 | 24 |
| breakeven | 2019 on | 5.58 | 11.05 | -30.9 | -38.3 | 0.46 | 150787 | 597 | 25.5 | 31.25 | -10.7 | 1.22 | 28.9 | 39.9 | 32 |
| half20 | 2007-2018 | 3.73 | 9.15 | -29.0 | -64.3 | 0.38 | 155019 | 843 | 51.6 | 22.61 | -11.31 | 1.23 | 29.1 | 27.7 | 36 |
| half20 | 2019 on | 5.91 | 11.05 | -23.0 | -38.3 | 0.49 | 154375 | 961 | 49.9 | 23.61 | -12.71 | 1.21 | 28.9 | 39.9 | 48 |


## Decision (rule fixed before the run)

- Best Sharpe on 2007-2018: **sma50** (0.6).
- On 2019 on: CAGR 7.1% vs v0.2 exit 2.88%; max drawdown -27.0% vs -24.1%; deflated Sharpe 0.208.
- Verdict: **keep the v0.2 exit**.

## Against the plan's bar, 2019 on

| exit | cagr_pct | over_index_pts | max_drawdown_pct | years_beating_index | deflated_sharpe | passes_bar |
|---|---|---|---|---|---|---|
| v02 | 2.88 | -8.17 | -24.1 | 2 of 7 | 0.073 | False |
| time63 | 4.3 | -6.75 | -29.4 | 2 of 7 | 0.124 | False |
| sma50 | 7.1 | -3.95 | -27.0 | 2 of 7 | 0.208 | False |
| chandelier | 7.38 | -3.67 | -24.2 | 2 of 7 | 0.206 | False |
| breakeven | 5.58 | -5.47 | -30.9 | 2 of 7 | 0.157 | False |
| half20 | 5.91 | -5.14 | -23.0 | 2 of 7 | 0.153 | False |


## sma50: year by year, 2019 on (%)

| year | strategy | bench | excess |
|---|---|---|---|
| 2019 | 0.0 | 1.8 | -1.8 |
| 2020 | -7.8 | 16.7 | -24.5 |
| 2021 | 69.4 | 30.2 | 39.2 |
| 2022 | -17.1 | 3.0 | -20.1 |
| 2023 | 49.2 | 25.8 | 23.4 |
| 2024 | -3.6 | 15.2 | -18.8 |
| 2025 | -12.2 | 6.7 | -18.9 |
| 2026 | 2.8 | -10.2 | 13.0 |


### sma50: how trades ended, 2019 on

| reason | trades | avg_ret_pct | total_pnl_rs |
|---|---|---|---|
| below 50-day | 324 | 12.11 | 222615 |
| delisted | 1 | 71.67 | 3890 |
| gap below stop | 16 | -16.97 | -15513 |
| stop | 222 | -14.83 | -152818 |


