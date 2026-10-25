# StoxSonar backtest, rules v0.2.0

Data to 2026-10-23. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 4639 of 4639 stocks that traded on NSE since --start had price data; the earliest starts 2006-01-02.

**Source: NSE daily files.** Every stock that traded on each day is included, also those later delisted or merged, so there is no survivorship bias. Splits and bonuses are inferred from overnight gaps and back-adjusted (sonar/nse.py); dividends are not.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 18 years (from 2008-10-23)

Coverage: 1466 of the 4639 stocks that traded on NSE since --start have prices back to 2008-10-23; 243 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1451 today. First signal in this window: 2008-11-19.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 858 | 858 | 59.2 | 15.4 | 856 | 1.9 | -1.1 | 46.0 | 0.3 |
| B | 1167 | 1165 | 54.1 | 16.6 | 1152 | 0.8 | -1.4 | 45.7 | 0.19 |
| C | 1806 | 1801 | 50.6 | 16.4 | 1788 | 0.2 | -1.6 | 44.1 | 0.13 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 16 of 19 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2008 | -2.03 | -3.46 | -1.69 | -4.95 |
| 2009 | 1.34 | 3.81 | 4.97 | 18.21 |
| 2010 | -0.07 | -0.17 | -1.76 | -6.19 |
| 2011 | 0.11 | 0.95 | -1.7 | -3.46 |
| 2012 | 0.25 | -1.41 | -0.31 | -4.47 |
| 2013 | -0.92 | -1.58 | -1.18 | -1.77 |
| 2014 | 1.28 | 2.82 | 0.19 | 9.01 |
| 2015 | 1.03 | 2.45 | -0.14 | -1.15 |
| 2016 | 0.32 | 1.79 | 0.06 | 0.85 |
| 2017 | 1.43 | 3.31 | 0.18 | -1.8 |
| 2018 | -2.15 | -5.87 | -2.72 | -7.66 |
| 2019 | -0.09 | 1.23 | -2.16 | -7.26 |
| 2020 | 1.22 | 3.64 | 0.38 | 3.58 |
| 2021 | 1.97 | 5.78 | 0.36 | -1.11 |
| 2022 | -0.06 | -0.36 | -0.43 | -0.42 |
| 2023 | 2.02 | 6.27 | 1.61 | 5.18 |
| 2024 | 0.49 | 0.63 | -0.46 | -3.02 |
| 2025 | -1.57 | -1.89 | -0.4 | -1.35 |
| 2026 | 2.52 | 7.83 | 1.52 | 5.66 |


## Grade A and B breakouts, year by year

| year | grade | signals | avg_excess_21_pct | beat_pct |
|---|---|---|---|---|
| 2007 | A | 41 | 9.8 | 56.0 |
| 2007 | B | 31 | 5.3 | 61.0 |
| 2008 | A | 6 | -11.9 | 17.0 |
| 2008 | B | 2 | -28.0 | 0.0 |
| 2009 | A | 37 | -1.9 | 43.0 |
| 2009 | B | 27 | 0.3 | 41.0 |
| 2010 | A | 26 | 2.7 | 58.0 |
| 2010 | B | 44 | -0.9 | 39.0 |
| 2011 | A | 1 | 1.9 | 100.0 |
| 2011 | B | 4 | -0.8 | 25.0 |
| 2012 | A | 9 | 6.5 | 56.0 |
| 2012 | B | 21 | -2.4 | 57.0 |
| 2013 | A | 5 | -1.4 | 20.0 |
| 2013 | B | 7 | -4.4 | 29.0 |
| 2014 | A | 70 | 4.3 | 46.0 |
| 2014 | B | 57 | 3.3 | 61.0 |
| 2015 | A | 29 | 2.9 | 52.0 |
| 2015 | B | 49 | 0.1 | 37.0 |
| 2016 | A | 18 | 2.1 | 44.0 |
| 2016 | B | 56 | 3.2 | 43.0 |
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
