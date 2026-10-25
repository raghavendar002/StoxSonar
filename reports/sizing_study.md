# Phase 7: sizing and idle cash on v0.2's entries

Fresh Rs 1 lakh per run, full costs, 25% cap per stock. Benchmark and ETF: Nifty 500 price index (no dividends). Nifty 500 itself: 9.15% a year with a -64.3% worst fall in 2007-2018; 11.05% and -38.3% from 2019 on.

## All variants, best 2007-2018 Sharpe first

| variant | cagr 07-18 | dd 07-18 | sharpe 07-18 | cagr 19-on | dd 19-on | sharpe 19-on | over index | years beating | in stocks % | dsr | passes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sma50 | risk 1% | liquid | 16.36 | -27.8 | 0.98 | 11.34 | -34.9 | 0.69 | 0.29 | 3 of 7 | 47.3 | 0.17 | False |
| sma50 | fixed 10% | liquid | 15.76 | -24.9 | 0.95 | 10.41 | -39.9 | 0.64 | -0.64 | 4 of 7 | 47.5 | 0.148 | False |
| sma50 | risk 0.75% | liquid | 14.28 | -26.4 | 0.94 | 11.8 | -31.2 | 0.76 | 0.75 | 3 of 7 | 46.2 | 0.179 | False |
| sma50 | risk 0.5% | liquid | 11.59 | -25.9 | 0.87 | 10.71 | -23.4 | 0.76 | -0.34 | 3 of 7 | 42.3 | 0.139 | False |
| chandelier | fixed 10% | liquid | 12.6 | -20.4 | 0.86 | 6.24 | -38.3 | 0.44 | -4.81 | 3 of 7 | 44.2 | 0.067 | False |
| chandelier | risk 0.75% | liquid | 10.92 | -17.3 | 0.84 | 9.63 | -28.5 | 0.69 | -1.42 | 3 of 7 | 41.5 | 0.12 | False |
| chandelier | risk 1% | liquid | 11.15 | -18.3 | 0.8 | 9.67 | -30.5 | 0.65 | -1.38 | 3 of 7 | 43.1 | 0.127 | False |
| sma50 | risk 1% | cash | 12.73 | -32.5 | 0.8 | 8.1 | -37.4 | 0.53 | -2.95 | 2 of 7 | 47.3 | 0.101 | False |
| chandelier | risk 0.5% | liquid | 8.54 | -17.2 | 0.79 | 11.19 | -22.1 | 0.86 | 0.14 | 3 of 7 | 37.3 | 0.148 | False |
| sma50 | fixed 10% | cash | 12.09 | -29.7 | 0.76 | 7.69 | -42.1 | 0.5 | -3.36 | 3 of 7 | 47.5 | 0.098 | False |
| sma50 | risk 1% | etf_trend | 13.89 | -41.8 | 0.72 | 10.19 | -40.1 | 0.59 | -0.86 | 2 of 7 | 47.3 | 0.154 | False |
| sma50 | risk 0.75% | cash | 10.49 | -30.0 | 0.72 | 8.39 | -34.4 | 0.57 | -2.66 | 2 of 7 | 46.1 | 0.104 | False |
| v02 | risk 0.5% | liquid | 5.67 | -12.1 | 0.69 | 6.91 | -22.3 | 0.6 | -4.14 | 3 of 7 | 31.5 | 0.053 | False |
| sma50 | risk 0.75% | etf_trend | 12.58 | -41.2 | 0.68 | 10.2 | -37.4 | 0.61 | -0.85 | 2 of 7 | 46.1 | 0.153 | False |
| sma50 | fixed 10% | etf_trend | 13.03 | -40.3 | 0.68 | 8.79 | -45.1 | 0.52 | -2.26 | 3 of 7 | 47.6 | 0.125 | False |
| sma50 | risk 0.5% | etf_trend | 11.65 | -40.1 | 0.67 | 9.28 | -30.8 | 0.59 | -1.77 | 2 of 7 | 42.3 | 0.118 | False |
| chandelier | fixed 10% | cash | 8.8 | -26.8 | 0.64 | 3.09 | -41.1 | 0.27 | -7.96 | 2 of 7 | 44.2 | 0.034 | False |
| sma50 | risk 1% | etf | 13.77 | -69.4 | 0.63 | 13.72 | -38.7 | 0.67 | 2.67 | 3 of 7 | 47.3 | 0.342 | False |
| v02 | risk 1% | liquid | 7.39 | -19.8 | 0.62 | 7.18 | -32.4 | 0.51 | -3.87 | 3 of 7 | 38.7 | 0.074 | False |
| v02 | fixed 10% | liquid | 7.79 | -21.3 | 0.61 | 5.19 | -36.6 | 0.39 | -5.86 | 2 of 7 | 39.1 | 0.057 | False |
| chandelier | risk 0.75% | etf_trend | 10.15 | -37.0 | 0.6 | 8.04 | -36.9 | 0.52 | -3.01 | 2 of 7 | 41.6 | 0.1 | False |
| sma50 | fixed 10% | etf | 13.02 | -68.6 | 0.6 | 12.81 | -41.6 | 0.63 | 1.76 | 3 of 7 | 47.6 | 0.294 | False |
| sma50 | risk 0.75% | etf | 12.72 | -69.1 | 0.6 | 13.86 | -38.6 | 0.69 | 2.81 | 2 of 7 | 46.1 | 0.354 | False |
| sma50 | risk 0.5% | cash | 7.58 | -29.0 | 0.6 | 7.1 | -27.0 | 0.54 | -3.95 | 2 of 7 | 42.2 | 0.071 | False |
| chandelier | fixed 10% | etf_trend | 10.48 | -37.3 | 0.59 | 4.87 | -43.0 | 0.34 | -6.18 | 2 of 7 | 44.2 | 0.055 | False |
| v02 | risk 0.75% | liquid | 6.02 | -17.9 | 0.58 | 8.28 | -28.2 | 0.61 | -2.77 | 3 of 7 | 36.3 | 0.087 | False |
| sma50 | risk 0.5% | etf | 11.86 | -68.5 | 0.58 | 13.02 | -38.5 | 0.68 | 1.97 | 2 of 7 | 42.3 | 0.318 | False |
| chandelier | risk 0.5% | etf_trend | 9.32 | -37.2 | 0.58 | 9.99 | -29.2 | 0.65 | -1.06 | 2 of 7 | 37.3 | 0.136 | False |
| chandelier | risk 0.75% | cash | 6.97 | -22.4 | 0.57 | 6.11 | -31.4 | 0.47 | -4.94 | 2 of 7 | 41.5 | 0.06 | False |
| chandelier | risk 1% | cash | 7.41 | -24.2 | 0.56 | 6.22 | -33.7 | 0.45 | -4.83 | 2 of 7 | 43.1 | 0.066 | False |
| chandelier | risk 0.75% | etf | 10.31 | -66.9 | 0.53 | 11.68 | -38.4 | 0.62 | 0.63 | 2 of 7 | 41.7 | 0.256 | False |
| chandelier | risk 1% | etf_trend | 8.89 | -36.8 | 0.53 | 7.81 | -38.0 | 0.49 | -3.24 | 2 of 7 | 43.2 | 0.101 | False |
| chandelier | fixed 10% | etf | 10.76 | -67.0 | 0.53 | 8.55 | -38.7 | 0.47 | -2.5 | 2 of 7 | 44.2 | 0.136 | False |
| chandelier | risk 0.5% | etf | 9.62 | -67.0 | 0.51 | 13.74 | -38.4 | 0.72 | 2.69 | 2 of 7 | 37.5 | 0.377 | False |
| chandelier | risk 1% | etf | 8.99 | -66.8 | 0.47 | 11.85 | -38.4 | 0.61 | 0.8 | 2 of 7 | 43.1 | 0.264 | False |
| v02 | risk 0.5% | etf_trend | 6.5 | -36.2 | 0.45 | 5.69 | -29.9 | 0.42 | -5.36 | 2 of 7 | 31.6 | 0.046 | False |
| chandelier | risk 0.5% | cash | 4.15 | -26.3 | 0.42 | 7.38 | -24.2 | 0.6 | -3.67 | 2 of 7 | 37.4 | 0.07 | False |
| v02 | risk 0.5% | etf | 6.99 | -66.5 | 0.41 | 8.74 | -38.5 | 0.51 | -2.31 | 2 of 7 | 31.7 | 0.099 | False |
| v02 | fixed 10% | etf_trend | 6.11 | -37.4 | 0.39 | 3.13 | -43.6 | 0.26 | -7.92 | 1 of 7 | 39.1 | 0.044 | False |
| v02 | risk 0.75% | etf_trend | 5.74 | -37.2 | 0.39 | 6.5 | -35.5 | 0.44 | -4.55 | 2 of 7 | 36.3 | 0.068 | False |
| v02 | risk 1% | etf_trend | 5.89 | -36.4 | 0.39 | 4.68 | -40.9 | 0.34 | -6.37 | 2 of 7 | 38.8 | 0.048 | False |
| v02 | fixed 10% | etf | 6.53 | -67.1 | 0.38 | 5.96 | -38.9 | 0.37 | -5.09 | 2 of 7 | 39.2 | 0.08 | False |
| v02 | risk 1% | etf | 6.18 | -66.6 | 0.37 | 7.54 | -38.7 | 0.44 | -3.51 | 2 of 7 | 38.8 | 0.102 | False |
| v02 | risk 0.75% | etf | 6.1 | -67.0 | 0.37 | 9.8 | -38.6 | 0.54 | -1.25 | 2 of 7 | 36.5 | 0.163 | False |
| v02 | fixed 10% | cash | 3.52 | -27.5 | 0.32 | 1.85 | -39.0 | 0.2 | -9.2 | 1 of 7 | 39.1 | 0.028 | False |
| v02 | risk 1% | cash | 3.13 | -26.1 | 0.3 | 3.88 | -35.6 | 0.32 | -7.17 | 2 of 7 | 38.7 | 0.037 | False |
| v02 | risk 0.75% | cash | 1.51 | -26.9 | 0.19 | 4.55 | -29.7 | 0.37 | -6.5 | 2 of 7 | 36.3 | 0.038 | False |
| v02 | risk 0.5% | cash | 0.84 | -21.9 | 0.14 | 2.88 | -24.1 | 0.29 | -8.17 | 2 of 7 | 31.4 | 0.018 | False |


## Decision (rule fixed before the run)

- Best Sharpe on 2007-2018: **sma50 | risk 1% | liquid** (0.98).
- On 2019 on: CAGR 11.34% vs the index 11.05% (+0.29 points); max drawdown -34.9%; beat the index in 3 of 7 full years; deflated Sharpe 0.17.
- Verdict: **no variant earns a recommendation**.
- Variants passing the whole bar on 2019 on: 0 of 48.

