# StoxSonar backtest, rules v0.2.0

Data to 2026-10-23. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 4116 of 4116 stocks that traded on NSE since --start had price data; the earliest starts 2015-01-01.

**Source: NSE daily files.** Every stock that traded on each day is included, also those later delisted or merged, so there is no survivorship bias. Prices are adjusted for splits and bonuses from NSE's own previous-close figures.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 10 years (from 2016-10-23)

Coverage: 1799 of the 4116 stocks that traded on NSE since --start have prices back to 2016-10-23; 681 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1451 today. First signal in this window: 2016-10-25.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 664 | 664 | 61.4 | 15.7 | 663 | 1.8 | -1.2 | 45.4 | 0.31 |
| B | 910 | 908 | 54.2 | 16.1 | 895 | 0.7 | -1.5 | 45.6 | 0.21 |
| C | 1438 | 1433 | 50.2 | 16.7 | 1421 | 0.1 | -1.8 | 43.2 | 0.14 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 10 of 11 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2016 | 0.46 | 1.98 | 0.29 | 1.08 |
| 2017 | 1.43 | 3.31 | 0.18 | -1.8 |
| 2018 | -2.15 | -5.87 | -2.72 | -7.66 |
| 2019 | -0.09 | 1.23 | -2.16 | -7.26 |
| 2020 | 1.22 | 3.64 | 0.38 | 3.58 |
| 2021 | 1.98 | 5.78 | 0.36 | -1.11 |
| 2022 | -0.06 | -0.36 | -0.43 | -0.42 |
| 2023 | 2.02 | 6.27 | 1.61 | 5.18 |
| 2024 | 0.49 | 0.63 | -0.46 | -3.02 |
| 2025 | -1.57 | -1.89 | -0.4 | -1.35 |
| 2026 | 2.52 | 7.83 | 1.52 | 5.66 |


## Grade A and B breakouts, year by year

| year | grade | signals | avg_excess_21_pct | beat_pct |
|---|---|---|---|---|
| 2016 | A | 18 | 2.1 | 44.0 |
| 2016 | B | 53 | 4.2 | 45.0 |
| 2017 | A | 78 | 3.3 | 42.0 |
| 2017 | B | 98 | 1.0 | 42.0 |
| 2018 | A | 23 | -3.7 | 26.0 |
| 2018 | B | 33 | -4.3 | 42.0 |
| 2019 | B | 8 | -3.6 | 38.0 |
| 2020 | A | 22 | -0.8 | 41.0 |
| 2020 | B | 54 | -0.8 | 37.0 |
| 2021 | A | 198 | 3.9 | 50.0 |
| 2021 | B | 167 | 1.5 | 43.0 |
| 2022 | A | 40 | 0.3 | 48.0 |
| 2022 | B | 85 | -0.3 | 51.0 |
| 2023 | A | 110 | 3.7 | 49.0 |
| 2023 | B | 159 | 4.0 | 55.0 |
| 2024 | A | 163 | -2.1 | 40.0 |
| 2024 | B | 179 | 0.2 | 47.0 |
| 2025 | A | 14 | -1.2 | 43.0 |
| 2025 | B | 56 | -1.8 | 38.0 |
| 2026 | A | 13 | 16.3 | 69.0 |
| 2026 | B | 48 | -0.2 | 44.0 |
