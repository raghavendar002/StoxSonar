# StoxSonar backtest, rules v0.2.0

Data to 2026-10-23. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 2358 of 2358 stocks listed today had price data; the earliest starts 1995-07-10.

**Survivorship warning:** only companies listed today are included. Companies that were delisted, went bust or merged are missing, so these results are better than reality, and the gap grows with the window.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 10 years (from 2016-10-23)

Coverage: 1138 of the 2358 stocks listed today have prices back to 2016-10-23; 532 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1335 today. First signal in this window: 2016-10-25.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 610 | 610 | 61.1 | 14.3 | 610 | 2.1 | -1.1 | 45.6 | 0.34 |
| B | 867 | 866 | 56.0 | 15.1 | 857 | 1.2 | -0.9 | 47.6 | 0.26 |
| C | 1368 | 1364 | 51.2 | 16.1 | 1352 | 0.3 | -1.6 | 44.5 | 0.18 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 10 of 11 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2016 | 0.69 | 2.76 | 0.48 | 1.92 |
| 2017 | 1.67 | 4.05 | 0.94 | 0.25 |
| 2018 | -1.81 | -4.98 | -2.14 | -5.7 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.34 | 4.12 | 0.56 | 4.25 |
| 2021 | 2.16 | 6.3 | 0.61 | -0.69 |
| 2022 | 0.23 | 0.38 | -0.11 | 0.32 |
| 2023 | 2.2 | 7.05 | 1.91 | 6.01 |
| 2024 | 0.66 | 1.07 | -0.28 | -2.39 |
| 2025 | -2.17 | -3.43 | -0.38 | -1.27 |
| 2026 | 2.35 | 7.73 | 1.6 | 5.97 |


## Grade A and B breakouts, year by year

| year | grade | signals | avg_excess_21_pct | beat_pct |
|---|---|---|---|---|
| 1998 | B | 1 | 2.4 | 100.0 |
| 1999 | A | 2 | -20.6 | 0.0 |
| 1999 | B | 4 | 97.0 | 50.0 |
| 2000 | A | 1 | -25.4 | 0.0 |
| 2001 | B | 1 | -14.4 | 0.0 |
| 2002 | B | 1 | 5.5 | 100.0 |
| 2003 | A | 10 | 0.1 | 50.0 |
| 2003 | B | 8 | 7.5 | 75.0 |
| 2004 | A | 7 | -5.9 | 14.0 |
| 2004 | B | 8 | -14.2 | 25.0 |
| 2005 | A | 20 | -5.4 | 50.0 |
| 2005 | B | 22 | -3.6 | 32.0 |
| 2006 | A | 11 | -4.4 | 27.0 |
| 2006 | B | 16 | 0.5 | 50.0 |
| 2007 | A | 20 | 9.1 | 65.0 |
| 2007 | B | 27 | 2.4 | 48.0 |
| 2008 | A | 5 | -10.5 | 20.0 |
| 2009 | A | 23 | 1.7 | 57.0 |
| 2009 | B | 21 | -0.4 | 43.0 |
| 2010 | A | 19 | 1.9 | 58.0 |
| 2010 | B | 29 | -1.7 | 34.0 |
| 2011 | A | 1 | 1.9 | 100.0 |
| 2011 | B | 3 | -8.5 | 0.0 |
| 2012 | A | 6 | 5.7 | 83.0 |
| 2012 | B | 11 | -4.5 | 45.0 |
| 2013 | A | 3 | 0.2 | 33.0 |
| 2013 | B | 6 | 1.4 | 50.0 |
| 2014 | A | 45 | 4.0 | 44.0 |
| 2014 | B | 45 | 3.4 | 62.0 |
| 2015 | A | 20 | -1.0 | 55.0 |
| 2015 | B | 36 | 1.4 | 39.0 |
| 2016 | A | 12 | -0.6 | 33.0 |
| 2016 | B | 43 | 3.4 | 44.0 |
| 2017 | A | 66 | 4.3 | 45.0 |
| 2017 | B | 84 | 1.4 | 40.0 |
| 2018 | A | 23 | -0.7 | 30.0 |
| 2018 | B | 30 | -3.1 | 47.0 |
| 2019 | B | 8 | 1.1 | 62.0 |
| 2020 | A | 20 | 1.3 | 50.0 |
| 2020 | B | 54 | 1.1 | 41.0 |
| 2021 | A | 183 | 3.9 | 49.0 |
| 2021 | B | 159 | 2.0 | 46.0 |
| 2022 | A | 40 | -1.6 | 42.0 |
| 2022 | B | 88 | 0.7 | 53.0 |
| 2023 | A | 106 | 3.7 | 45.0 |
| 2023 | B | 152 | 4.0 | 55.0 |
| 2024 | A | 144 | -0.9 | 44.0 |
| 2024 | B | 176 | 0.2 | 48.0 |
| 2025 | A | 14 | 0.3 | 43.0 |
| 2025 | B | 51 | -1.3 | 39.0 |
| 2026 | A | 11 | 6.9 | 64.0 |
| 2026 | B | 49 | -0.0 | 47.0 |
