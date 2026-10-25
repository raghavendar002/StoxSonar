# Phase 3 re-tune, walk-forward on NSE data

Up breakouts above the 200-day average: 3736 from 2007-01-10 to 2026-09-22. Net = 21-session excess over the Nifty 500 minus 0.5% round-trip cost. Out-of-sample years compared: 2019-2026. Tradable = Healthy market (the app suggests no buys when Weak).

## Tradable trades by grade, out of sample

| variant | grade | n | avg_net_pct | median_net_pct | win_pct |
|---|---|---|---|---|---|
| v02 | A | 560 | 1.32 | -1.55 | 44.1 |
| v02 | B | 605 | 0.82 | -1.45 | 45.1 |
| v02 | C | 541 | -0.24 | -2.9 | 39.6 |
| refit | A | 366 | 1.29 | -1.7 | 42.6 |
| refit | B | 537 | 0.35 | -1.7 | 44.1 |
| refit | C | 803 | 0.55 | -2.3 | 42.5 |
| selected | A | 356 | 2.36 | -0.74 | 47.2 |
| selected | B | 582 | 0.3 | -2.0 | 42.3 |
| selected | C | 768 | 0.12 | -2.83 | 41.7 |


## Grade A: is it worth trading?

Monthly = the average of each month's Grade A trades, so a busy month counts once. Deflated Sharpe = probability the edge is real after allowing for the three variants tried.

| variant | years_positive | monthly_mean_pct | monthly_t | deflated_sharpe | A_minus_C_pct |
|---|---|---|---|---|---|
| v02 | 3 of 7 | 0.63 | 0.62 | 0.556 | 1.56 |
| refit | 3 of 7 | 0.99 | 0.8 | 0.631 | 0.74 |
| selected | 4 of 7 | 1.26 | 1.61 | 0.866 | 2.24 |


## Grade A average net excess by year (%)

| year | v02 | refit | selected | n_v02 | n_refit | n_selected |
|---|---|---|---|---|---|---|
| 2019 | – | – | – | 0.0 | 0.0 | 0.0 |
| 2020 | -1.3 | -1.5 | -7.3 | 22.0 | 17.0 | 11.0 |
| 2021 | 3.4 | 3.4 | 3.9 | 198.0 | 143.0 | 117.0 |
| 2022 | -0.2 | -1.8 | 1.0 | 40.0 | 23.0 | 26.0 |
| 2023 | 3.2 | 2.2 | 5.1 | 110.0 | 67.0 | 98.0 |
| 2024 | -2.6 | -2.7 | -0.4 | 163.0 | 98.0 | 82.0 |
| 2025 | -1.7 | -3.3 | -2.7 | 14.0 | 8.0 | 15.0 |
| 2026 | 15.8 | 19.6 | 1.7 | 13.0 | 10.0 | 7.0 |


## Decision (rule fixed before the run)

- refit: does not beat v0.2 by the rule
- selected: does not beat v0.2 by the rule
- v0.2 Grade A deflated Sharpe on its own: 0.556 (edge not proven)

## Features the stability rule picked each year (sign: +1 higher is better)

- 2012: none
- 2013: none
- 2014: none
- 2015: base_len (-1)
- 2016: none
- 2017: none
- 2018: from_hi52 (+1)
- 2019: none
- 2020: from_hi52 (+1), template (+1)
- 2021: from_hi52 (+1), template (+1)
- 2022: template (+1), from_hi52 (+1), tight10 (-1), depth (-1)
- 2023: from_hi52 (+1), template (+1), depth (-1)
- 2024: from_hi52 (+1), depth (-1), template (+1), tight10 (-1), dist_sma50 (-1)
- 2025: depth (-1), dist_sma50 (-1), tight10 (-1), atr_pct (-1)
- 2026: depth (-1), dist_sma50 (-1), atr_pct (-1), tight10 (-1), from_hi52 (+1)
