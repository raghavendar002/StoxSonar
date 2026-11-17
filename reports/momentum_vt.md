# PR 8b: the exit-brake momentum book with a 15% volatility target, Rs 100,000 account

Data 2006-01-02 to 2026-11-17, NSE daily files (delisted stocks included). Benchmark: ^CRSLDX from 2005-09-26; ^BSESN before 2005-09-26 (price index, no dividends). India VIX from 2008-03-03. Idle cash earns 5.5% a year (liquid ETF).

## Verdict: **FAIL**

Chosen on 2007-2018 by Sharpe from top 15, brake exit, top 20, brake exit, top 15, brake exit, vol target 15%, top 20, brake exit, vol target 15%: **top 15, brake exit, vol target 15%**. Judged on 2019-01-01 on, fresh Rs 1 lakh.

| test | result | pass |
|---|---|---|
| CAGR >= Nifty 500 + 5 pts | 17.1% vs 12.8% + 5 | False |
| Max drawdown < 25% | -18.5% | True |
| Ahead of the index in >= 5 of 7 years (2019-2025) | 5 of 7 | True |
| Deflated Sharpe >= 0.95 (17 trials) | 0.99 | True |


## Every variant, 2007-2018 (the choice is made here)

| variant | cagr_pct | bench_cagr_pct | edge_pts | max_dd_pct | bench_dd_pct | sharpe | invested_pct | trades | final_rs |
|---|---|---|---|---|---|---|---|---|---|
| top 10, brake none | 20.3 | 8.8 | 11.5 | -71.9 | -64.3 | 0.6 | 98 | 298 | 918078 |
| top 10, brake gate | 24.6 | 8.8 | 15.8 | -51.2 | -64.3 | 0.77 | 81 | 242 | 1397289 |
| top 10, brake exit | 21.7 | 8.8 | 12.9 | -41.5 | -64.3 | 0.74 | 60 | 341 | 1056876 |
| top 10, brake gate+vix | 23.8 | 8.8 | 14.9 | -51.2 | -64.3 | 0.74 | 81 | 242 | 1291294 |
| top 10, brake exit+vix | 21.9 | 8.8 | 13.1 | -41.5 | -64.3 | 0.75 | 60 | 341 | 1077956 |
| top 15, brake none | 18.8 | 8.8 | 10.0 | -74.9 | -64.3 | 0.58 | 98 | 395 | 790285 |
| top 15, brake gate | 23.1 | 8.8 | 14.3 | -54.1 | -64.3 | 0.75 | 82 | 336 | 1210183 |
| top 15, brake exit | 19.9 | 8.8 | 11.1 | -41.7 | -64.3 | 0.7 | 60 | 487 | 881499 |
| top 15, brake gate+vix | 23.1 | 8.8 | 14.2 | -54.1 | -64.3 | 0.75 | 82 | 333 | 1206327 |
| top 15, brake exit+vix | 20.0 | 8.8 | 11.2 | -41.7 | -64.3 | 0.71 | 60 | 486 | 891998 |
| top 20, brake none | 16.3 | 8.8 | 7.4 | -75.5 | -64.3 | 0.5 | 98 | 490 | 610212 |
| top 20, brake gate | 20.9 | 8.8 | 12.1 | -59.2 | -64.3 | 0.69 | 83 | 427 | 973703 |
| top 20, brake exit | 17.5 | 8.8 | 8.7 | -40.7 | -64.3 | 0.63 | 60 | 639 | 691798 |
| top 20, brake gate+vix | 20.2 | 8.8 | 11.3 | -59.2 | -64.3 | 0.66 | 83 | 422 | 906921 |
| top 20, brake exit+vix | 17.5 | 8.8 | 8.7 | -40.7 | -64.3 | 0.63 | 60 | 639 | 691465 |
| top 15, brake exit, vol target 15% | 14.2 | 8.8 | 5.4 | -25.7 | -64.3 | 0.72 | 39 | 623 | 490881 |
| top 20, brake exit, vol target 15% | 13.0 | 8.8 | 4.2 | -24.2 | -64.3 | 0.65 | 40 | 793 | 434547 |


## Every variant, 2019 on (shown for honesty; not used to choose)

| variant | cagr_pct | bench_cagr_pct | edge_pts | max_dd_pct | bench_dd_pct | sharpe | invested_pct | trades | final_rs | years_ahead_of_7 | deflated_sharpe | fit_max_dd_pct | passes_bar_2019_on |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top 10, brake none | 30.0 | 12.8 | 17.2 | -39.8 | -38.3 | 0.94 | 97 | 246 | 789570 | 5 | 0.97 | -71.9 | False |
| top 10, brake gate | 24.2 | 12.8 | 11.3 | -40.8 | -38.3 | 0.83 | 84 | 210 | 550112 | 4 | 0.96 | -51.2 | False |
| top 10, brake exit | 20.5 | 12.8 | 7.7 | -27.6 | -38.3 | 0.78 | 64 | 266 | 435567 | 5 | 0.97 | -41.5 | False |
| top 10, brake gate+vix | 26.3 | 12.8 | 13.5 | -35.6 | -38.3 | 0.91 | 83 | 205 | 629138 | 4 | 0.98 | -51.2 | False |
| top 10, brake exit+vix | 21.4 | 12.8 | 8.6 | -27.4 | -38.3 | 0.84 | 63 | 259 | 460409 | 5 | 0.98 | -41.5 | False |
| top 15, brake none | 28.3 | 12.8 | 15.4 | -36.1 | -38.3 | 0.91 | 98 | 352 | 711336 | 4 | 0.97 | -74.9 | False |
| top 15, brake gate | 29.1 | 12.8 | 16.3 | -31.3 | -38.3 | 1.01 | 86 | 297 | 748383 | 4 | 0.99 | -54.1 | False |
| top 15, brake exit | 24.2 | 12.8 | 11.4 | -19.9 | -38.3 | 1.01 | 64 | 386 | 552030 | 5 | 1.0 | -41.7 | True |
| top 15, brake gate+vix | 29.6 | 12.8 | 16.8 | -32.1 | -38.3 | 1.05 | 85 | 287 | 772003 | 4 | 0.99 | -54.1 | False |
| top 15, brake exit+vix | 25.0 | 12.8 | 12.2 | -18.8 | -38.3 | 1.08 | 63 | 375 | 581276 | 5 | 1.0 | -41.7 | True |
| top 20, brake none | 29.5 | 12.8 | 16.7 | -36.0 | -38.3 | 0.97 | 98 | 418 | 766604 | 6 | 0.98 | -75.5 | False |
| top 20, brake gate | 26.1 | 12.8 | 13.2 | -29.3 | -38.3 | 0.93 | 86 | 362 | 620812 | 4 | 0.98 | -59.2 | False |
| top 20, brake exit | 24.7 | 12.8 | 11.8 | -18.9 | -38.3 | 1.07 | 64 | 480 | 568489 | 5 | 1.0 | -40.7 | True |
| top 20, brake gate+vix | 26.1 | 12.8 | 13.3 | -29.9 | -38.3 | 0.96 | 84 | 349 | 623190 | 4 | 0.98 | -59.2 | False |
| top 20, brake exit+vix | 25.4 | 12.8 | 12.6 | -18.4 | -38.3 | 1.16 | 63 | 465 | 596034 | 5 | 1.0 | -40.7 | True |
| top 15, brake exit, vol target 15% | 17.1 | 12.8 | 4.3 | -18.5 | -38.3 | 1.03 | 42 | 451 | 347738 | 5 | 0.99 | -25.7 | False |
| top 20, brake exit, vol target 15% | 18.5 | 12.8 | 5.7 | -17.3 | -38.3 | 1.16 | 42 | 553 | 381339 | 5 | 1.0 | -24.2 | True |


## top 15, brake exit, vol target 15%, 2019 on, year by year (%)

| date | strategy | bench | excess |
|---|---|---|---|
| 2019 | -13.1 | 7.3 | -20.4 |
| 2020 | 18.1 | 16.7 | 1.4 |
| 2021 | 42.3 | 30.2 | 12.1 |
| 2022 | 7.9 | 3.0 | 4.9 |
| 2023 | 36.8 | 25.8 | 11.0 |
| 2024 | 12.8 | 15.2 | -2.4 |
| 2025 | 10.2 | 6.7 | 3.5 |
| 2026 | 29.9 | -0.2 | 30.1 |


### How positions ended

| reason | trades | avg_ret_pct | total_pnl_rs |
|---|---|---|---|
| brake | 179 | 5.5 | 89792 |
| delisted | 6 | 4.2 | 1717 |
| rank | 198 | 9.8 | 32415 |
| vol trim | 68 | 52.0 | 79533 |


## Side check: the same rules sized by 0.5% risk per trade (2.5-ATR stop distance), 2019 on

| variant | cagr_pct | bench_cagr_pct | edge_pts | max_dd_pct | bench_dd_pct | sharpe | invested_pct | trades | final_rs |
|---|---|---|---|---|---|---|---|---|---|
| top 15, brake exit, vol target 15%, 0.5% risk sizing | 16.7 | 12.8 | 3.8 | -16.6 | -38.3 | 1.08 | 39 | 432 | 337026 |


