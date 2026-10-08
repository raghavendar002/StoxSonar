# StoxSonar backtest, rules v0.1.0

Data to 2026-10-08. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 2332 of 2332 stocks listed today had price data; the earliest starts 1995-07-10.

**Survivorship warning:** only companies listed today are included. Companies that were delisted, went bust or merged are missing, so these results are better than reality, and the gap grows with the window.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 10 years (from 2016-10-08)

Coverage: 1128 of today's 2332 stocks have prices back to 2016-10-08; 508 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1336 today. First signal in this window: 2016-10-10.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 1264 | 1264 | 47.4 | 33.2 | 1264 | 2.7 | -0.0 | 49.6 | 0.61 |
| B | 1384 | 1374 | 45.3 | 35.2 | 1350 | 1.1 | -0.7 | 47.8 | 0.45 |
| C | 1860 | 1854 | 46.1 | 31.8 | 1844 | 1.1 | -0.8 | 46.9 | 0.36 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 10 of 11 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2016 | 0.69 | 2.69 | 0.49 | 1.95 |
| 2017 | 1.67 | 4.06 | 1.03 | 0.58 |
| 2018 | -1.8 | -4.98 | -2.13 | -5.69 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.33 | 4.08 | 0.56 | 4.24 |
| 2021 | 2.15 | 6.3 | 0.61 | -0.75 |
| 2022 | 0.26 | 0.42 | -0.12 | 0.3 |
| 2023 | 2.21 | 7.09 | 1.89 | 5.98 |
| 2024 | 0.67 | 1.11 | -0.26 | -2.31 |
| 2025 | -2.16 | -3.44 | -0.38 | -1.26 |
| 2026 | 2.61 | 7.78 | 1.7 | 6.55 |


## Last 20 years (from 2006-10-08)

Coverage: 657 of today's 2332 stocks have prices back to 2006-10-08; 177 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1336 today. First signal in this window: 2006-10-09.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 1591 | 1591 | 46.3 | 34.4 | 1591 | 2.6 | -0.0 | 49.7 | 0.59 |
| B | 1779 | 1769 | 44.4 | 35.7 | 1745 | 1.1 | -0.5 | 48.7 | 0.41 |
| C | 2295 | 2289 | 45.9 | 31.8 | 2279 | 1.1 | -0.9 | 46.7 | 0.36 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 18 of 21 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2006 | 1.28 | 0.16 | -0.47 | -4.76 |
| 2007 | 2.05 | 4.13 | -1.92 | -1.73 |
| 2008 | -1.32 | -2.44 | -0.64 | -1.53 |
| 2009 | 1.52 | 4.66 | 5.09 | 17.58 |
| 2010 | 0.31 | 0.91 | -1.32 | -5.09 |
| 2011 | 0.37 | 1.37 | -1.09 | -1.86 |
| 2012 | 0.73 | -0.39 | 0.33 | -2.5 |
| 2013 | -0.14 | 0.45 | -0.26 | 0.76 |
| 2014 | 1.8 | 4.62 | 1.65 | 13.32 |
| 2015 | 1.28 | 3.05 | 0.23 | -0.02 |
| 2016 | 0.69 | 2.69 | 0.49 | 1.95 |
| 2017 | 1.67 | 4.06 | 1.03 | 0.58 |
| 2018 | -1.8 | -4.98 | -2.13 | -5.69 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.33 | 4.08 | 0.56 | 4.24 |
| 2021 | 2.15 | 6.3 | 0.61 | -0.75 |
| 2022 | 0.26 | 0.42 | -0.12 | 0.3 |
| 2023 | 2.21 | 7.09 | 1.89 | 5.98 |
| 2024 | 0.67 | 1.11 | -0.26 | -2.31 |
| 2025 | -2.16 | -3.44 | -0.38 | -1.26 |
| 2026 | 2.61 | 7.78 | 1.7 | 6.55 |


## Last 30 years (from 1996-10-08)

Coverage: 60 of today's 2332 stocks have prices back to 1996-10-08; 1 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 1336 today. First signal in this window: 1996-11-21.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 1672 | 1672 | 46.0 | 34.6 | 1672 | 3.4 | -0.1 | 49.6 | 0.81 |
| B | 1921 | 1911 | 44.0 | 35.5 | 1887 | 1.1 | -0.5 | 48.5 | 0.44 |
| C | 2397 | 2391 | 46.0 | 31.7 | 2381 | 1.0 | -0.9 | 46.7 | 0.37 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 25 of 30 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 1997 | 2.07 | 4.95 | -1.96 | -3.23 |
| 1998 | 4.83 | 20.54 | 0.27 | -4.58 |
| 1999 | 4.68 | 14.82 | -2.66 | -2.3 |
| 2000 | 0.06 | -3.07 | 1.8 | 4.14 |
| 2001 | 0.87 | 1.45 | -0.31 | -0.42 |
| 2002 | 0.74 | 1.12 | 0.14 | 0.05 |
| 2003 | 1.62 | 3.6 | -2.0 | -3.35 |
| 2004 | 0.04 | 3.72 | 4.11 | 5.39 |
| 2005 | 0.43 | 1.29 | -1.4 | -5.57 |
| 2006 | 1.28 | 0.16 | -0.47 | -4.76 |
| 2007 | 2.05 | 4.13 | -1.92 | -1.73 |
| 2008 | -1.32 | -2.44 | -0.64 | -1.53 |
| 2009 | 1.52 | 4.66 | 5.09 | 17.58 |
| 2010 | 0.31 | 0.91 | -1.32 | -5.09 |
| 2011 | 0.37 | 1.37 | -1.09 | -1.86 |
| 2012 | 0.73 | -0.39 | 0.33 | -2.5 |
| 2013 | -0.14 | 0.45 | -0.26 | 0.76 |
| 2014 | 1.8 | 4.62 | 1.65 | 13.32 |
| 2015 | 1.28 | 3.05 | 0.23 | -0.02 |
| 2016 | 0.69 | 2.69 | 0.49 | 1.95 |
| 2017 | 1.67 | 4.06 | 1.03 | 0.58 |
| 2018 | -1.8 | -4.98 | -2.13 | -5.69 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.33 | 4.08 | 0.56 | 4.24 |
| 2021 | 2.15 | 6.3 | 0.61 | -0.75 |
| 2022 | 0.26 | 0.42 | -0.12 | 0.3 |
| 2023 | 2.21 | 7.09 | 1.89 | 5.98 |
| 2024 | 0.67 | 1.11 | -0.26 | -2.31 |
| 2025 | -2.16 | -3.44 | -0.38 | -1.26 |
| 2026 | 2.61 | 7.78 | 1.7 | 6.55 |


## Grade A and B breakouts, year by year

| year | grade | signals | avg_excess_21_pct | beat_pct |
|---|---|---|---|---|
| 1997 | B | 2 | – | 0.0 |
| 1999 | A | 4 | 3.0 | 50.0 |
| 1999 | B | 6 | -5.6 | 33.0 |
| 2000 | A | 1 | -28.1 | 0.0 |
| 2000 | B | 1 | -13.5 | 0.0 |
| 2001 | B | 2 | -4.4 | 50.0 |
| 2002 | B | 3 | 25.2 | 100.0 |
| 2003 | A | 11 | -11.5 | 45.0 |
| 2003 | B | 30 | 2.2 | 53.0 |
| 2004 | A | 13 | -3.8 | 31.0 |
| 2004 | B | 13 | 6.2 | 46.0 |
| 2005 | A | 37 | -0.3 | 57.0 |
| 2005 | B | 50 | -1.1 | 40.0 |
| 2006 | A | 17 | 97.6 | 41.0 |
| 2006 | B | 39 | -1.0 | 46.0 |
| 2007 | A | 30 | 3.0 | 50.0 |
| 2007 | B | 44 | 0.7 | 45.0 |
| 2008 | A | 6 | -12.4 | 17.0 |
| 2008 | B | 8 | -4.8 | 50.0 |
| 2009 | A | 32 | 1.2 | 50.0 |
| 2009 | B | 46 | -0.1 | 48.0 |
| 2010 | A | 62 | 0.1 | 52.0 |
| 2010 | B | 49 | 1.7 | 61.0 |
| 2011 | A | 2 | -3.0 | 50.0 |
| 2011 | B | 11 | -3.9 | 36.0 |
| 2012 | A | 22 | 0.9 | 45.0 |
| 2012 | B | 23 | -0.8 | 52.0 |
| 2013 | A | 12 | 0.8 | 67.0 |
| 2013 | B | 16 | 2.6 | 44.0 |
| 2014 | A | 79 | 5.4 | 48.0 |
| 2014 | B | 97 | 2.8 | 59.0 |
| 2015 | A | 50 | 1.5 | 52.0 |
| 2015 | B | 56 | 1.9 | 46.0 |
| 2016 | A | 48 | 2.3 | 44.0 |
| 2016 | B | 53 | -1.4 | 49.0 |
| 2017 | A | 150 | 4.3 | 47.0 |
| 2017 | B | 99 | 0.3 | 47.0 |
| 2018 | A | 55 | -0.4 | 44.0 |
| 2018 | B | 39 | -3.8 | 33.0 |
| 2019 | B | 56 | 0.5 | 50.0 |
| 2020 | A | 32 | 0.6 | 47.0 |
| 2020 | B | 105 | 3.2 | 50.0 |
| 2021 | A | 265 | 5.2 | 54.0 |
| 2021 | B | 279 | 1.9 | 49.0 |
| 2022 | A | 108 | -0.6 | 44.0 |
| 2022 | B | 123 | 2.2 | 51.0 |
| 2023 | A | 240 | 4.2 | 54.0 |
| 2023 | B | 223 | 1.1 | 48.0 |
| 2024 | A | 320 | 1.2 | 49.0 |
| 2024 | B | 229 | 0.8 | 45.0 |
| 2025 | A | 48 | -0.3 | 50.0 |
| 2025 | B | 80 | -1.8 | 46.0 |
| 2026 | A | 28 | 5.9 | 57.0 |
| 2026 | B | 105 | 2.6 | 52.0 |
