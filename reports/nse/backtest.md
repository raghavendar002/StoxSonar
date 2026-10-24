# StoxSonar backtest, rules v0.2.0

Data to 2026-10-23. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 3830 of 3830 stocks listed today had price data; the earliest starts 2015-01-01.

**Source: NSE daily files.** Every stock that traded on each day is included, also those later delisted or merged, so there is no survivorship bias. Prices are adjusted for splits and bonuses from NSE's own previous-close figures.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 10 years (from 2016-10-23)

Coverage: 1728 of today's 3830 stocks have prices back to 2016-10-23; 680 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1417 today. First signal in this window: 2016-10-25.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 643 | 643 | 58.5 | 15.9 | 642 | 0.5 | -2.3 | 43.3 | 0.21 |
| B | 846 | 841 | 56.8 | 15.1 | 828 | 1.6 | -0.4 | 48.6 | 0.3 |
| C | 1377 | 1372 | 50.7 | 16.4 | 1363 | -0.1 | -1.6 | 44.2 | 0.11 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 8 of 11 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2016 | -0.19 | 0.28 | 0.11 | 0.4 |
| 2017 | 1.03 | 2.39 | 0.37 | -1.11 |
| 2018 | -2.48 | -6.78 | -2.6 | -7.42 |
| 2019 | -0.52 | 0.28 | -2.16 | -6.63 |
| 2020 | 1.0 | 2.36 | 0.58 | 3.27 |
| 2021 | 1.84 | 5.42 | 0.5 | -1.37 |
| 2022 | -0.25 | -0.88 | -0.59 | -0.92 |
| 2023 | 1.46 | 4.31 | 1.61 | 4.8 |
| 2024 | 0.04 | -0.68 | -0.43 | -2.82 |
| 2025 | -1.75 | -2.1 | -0.65 | -1.85 |
| 2026 | 2.07 | 5.28 | 1.71 | 5.97 |


## Grade A and B breakouts, year by year

| year | grade | signals | avg_excess_21_pct | beat_pct |
|---|---|---|---|---|
| 2016 | A | 19 | 0.5 | 42.0 |
| 2016 | B | 48 | 2.2 | 48.0 |
| 2017 | A | 76 | 2.7 | 42.0 |
| 2017 | B | 91 | 1.1 | 40.0 |
| 2018 | A | 25 | -3.6 | 28.0 |
| 2018 | B | 30 | -4.6 | 47.0 |
| 2019 | B | 7 | -4.7 | 29.0 |
| 2020 | A | 20 | 0.3 | 45.0 |
| 2020 | B | 51 | 0.6 | 43.0 |
| 2021 | A | 194 | 3.7 | 52.0 |
| 2021 | B | 162 | 1.8 | 44.0 |
| 2022 | A | 42 | 2.2 | 48.0 |
| 2022 | B | 81 | -0.1 | 51.0 |
| 2023 | A | 103 | 1.3 | 40.0 |
| 2023 | B | 151 | 4.8 | 58.0 |
| 2024 | A | 152 | -5.1 | 36.0 |
| 2024 | B | 151 | 1.4 | 51.0 |
| 2025 | A | 17 | 0.0 | 47.0 |
| 2025 | B | 49 | 1.3 | 51.0 |
| 2026 | A | 10 | 7.3 | 60.0 |
| 2026 | B | 50 | 1.2 | 46.0 |
