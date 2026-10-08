# StoxSonar backtest, rules v0.2.0

Data to 2026-10-08. Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26. 2332 of 2332 stocks listed today had price data; the earliest starts 1995-07-10.

**Survivorship warning:** only companies listed today are included. Companies that were delisted, went bust or merged are missing, so these results are better than reality, and the gap grows with the window.

Excess = stock return minus benchmark return over the same 21 sessions after the signal. R = 21-session move divided by the distance to the failure level.

## Last 10 years (from 2016-10-08)

Coverage: 1128 of today's 2332 stocks have prices back to 2016-10-08; 508 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 204 today. First signal in this window: 2016-10-10.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 606 | 606 | 61.2 | 14.2 | 606 | 1.9 | -1.2 | 45.2 | 0.32 |
| B | 865 | 857 | 56.0 | 15.3 | 843 | 1.1 | -1.1 | 47.1 | 0.26 |
| C | 1361 | 1351 | 51.6 | 15.9 | 1339 | 0.3 | -1.6 | 44.3 | 0.18 |

### Stage 2 vs Stage 4, average excess return per year (%)

s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. Stage 2 should beat Stage 4 in most years, not just on average.

Stage 2 beat Stage 4 over 21 sessions in 10 of 11 years.

| year | s2_21 | s2_63 | s4_21 | s4_63 |
|---|---|---|---|---|
| 2016 | 0.68 | 2.69 | 0.49 | 1.95 |
| 2017 | 1.67 | 4.06 | 1.03 | 0.58 |
| 2018 | -1.8 | -4.98 | -2.13 | -5.69 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.33 | 4.08 | 0.56 | 4.24 |
| 2021 | 2.15 | 6.3 | 0.61 | -0.75 |
| 2022 | 0.26 | 0.42 | -0.12 | 0.3 |
| 2023 | 2.21 | 7.09 | 1.89 | 5.98 |
| 2024 | 0.67 | 1.11 | -0.26 | -2.31 |
| 2025 | -2.16 | -3.44 | -0.38 | -1.26 |
| 2026 | 2.6 | 7.76 | 1.7 | 6.58 |


## Last 20 years (from 2006-10-08)

Coverage: 657 of today's 2332 stocks have prices back to 2006-10-08; 177 of them were liquid (Rs 1 crore/day) and labelled at the start of the window, against 204 today. First signal in this window: 2006-10-09.

### Breakouts by grade

| grade | signals | closed | confirmed_pct | failed_pct | measured_21 | avg_excess_21_pct | median_excess_21_pct | win_pct_21 | avg_r_21 |
|---|---|---|---|---|---|---|---|---|---|
| A | 757 | 757 | 59.8 | 14.4 | 757 | 2.1 | -0.9 | 46.8 | 0.32 |
| B | 1079 | 1071 | 55.0 | 15.9 | 1057 | 1.2 | -1.1 | 46.9 | 0.24 |
| C | 1672 | 1662 | 51.6 | 16.1 | 1650 | 0.3 | -1.7 | 43.9 | 0.16 |

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
| 2016 | 0.68 | 2.69 | 0.49 | 1.95 |
| 2017 | 1.67 | 4.06 | 1.03 | 0.58 |
| 2018 | -1.8 | -4.98 | -2.13 | -5.69 |
| 2019 | 0.01 | 1.59 | -1.33 | -5.41 |
| 2020 | 1.33 | 4.08 | 0.56 | 4.24 |
| 2021 | 2.15 | 6.3 | 0.61 | -0.75 |
| 2022 | 0.26 | 0.42 | -0.12 | 0.3 |
| 2023 | 2.21 | 7.09 | 1.89 | 5.98 |
| 2024 | 0.67 | 1.11 | -0.26 | -2.31 |
| 2025 | -2.16 | -3.44 | -0.38 | -1.26 |
| 2026 | 2.6 | 7.76 | 1.7 | 6.58 |


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
| 2005 | B | 21 | -3.8 | 29.0 |
| 2006 | A | 11 | -4.4 | 27.0 |
| 2006 | B | 16 | 0.5 | 50.0 |
| 2007 | A | 20 | 9.1 | 65.0 |
| 2007 | B | 27 | 2.4 | 48.0 |
| 2008 | A | 5 | -10.5 | 20.0 |
| 2009 | A | 23 | 1.7 | 57.0 |
| 2009 | B | 20 | -0.6 | 40.0 |
| 2010 | A | 19 | 1.9 | 58.0 |
| 2010 | B | 30 | -1.4 | 37.0 |
| 2011 | A | 1 | 1.9 | 100.0 |
| 2011 | B | 3 | -8.5 | 0.0 |
| 2012 | A | 6 | 5.7 | 83.0 |
| 2012 | B | 11 | -4.5 | 45.0 |
| 2013 | A | 3 | 0.2 | 33.0 |
| 2013 | B | 6 | 1.4 | 50.0 |
| 2014 | A | 44 | 4.0 | 43.0 |
| 2014 | B | 47 | 3.7 | 64.0 |
| 2015 | A | 21 | -0.0 | 57.0 |
| 2015 | B | 36 | 1.4 | 39.0 |
| 2016 | A | 12 | -0.6 | 33.0 |
| 2016 | B | 43 | 3.4 | 44.0 |
| 2017 | A | 64 | 3.9 | 44.0 |
| 2017 | B | 84 | 1.4 | 40.0 |
| 2018 | A | 23 | -0.7 | 30.0 |
| 2018 | B | 30 | -3.1 | 47.0 |
| 2019 | B | 8 | 1.1 | 62.0 |
| 2020 | A | 20 | 1.2 | 50.0 |
| 2020 | B | 55 | 0.8 | 40.0 |
| 2021 | A | 181 | 3.5 | 48.0 |
| 2021 | B | 155 | 2.0 | 45.0 |
| 2022 | A | 39 | -1.4 | 44.0 |
| 2022 | B | 88 | 0.2 | 52.0 |
| 2023 | A | 106 | 3.7 | 45.0 |
| 2023 | B | 151 | 3.7 | 55.0 |
| 2024 | A | 143 | -0.8 | 45.0 |
| 2024 | B | 176 | 0.2 | 48.0 |
| 2025 | A | 14 | 0.3 | 43.0 |
| 2025 | B | 50 | -0.9 | 40.0 |
| 2026 | A | 11 | 6.9 | 64.0 |
| 2026 | B | 36 | -0.1 | 42.0 |
