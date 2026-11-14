# Mid-term books: real-data check

Ledger copy with the NSE runs of 2026-11-13, 2026-11-12 forgotten and the newest session replayed. Nothing live was changed.

## NSE
Exit code 0.
Runs recorded:

| as_of | stocks | regime | stage2_share | new_events |
| --- | --- | --- | --- | --- |
| 2026-11-12 | 1320 | Weak | 0.471 | 0 |
| 2026-11-11 | 1320 | Weak | 0.471 | 2 |
| 2026-11-09 | 1319 | Weak | 0.472 | 4 |

Signals by source and grade:

| source | direction | grade | n | latest |
| --- | --- | --- | --- | --- |
| late | up | B | 2 | 2026-10-13 |
| late | up | C | 1 | 2026-10-13 |
| live | down | A | 3 | 2026-11-04 |
| live | down | B | 5 | 2026-11-06 |
| live | down | C | 1 | 2026-10-30 |
| live | down | W | 14 | 2026-11-09 |
| live | up | B | 12 | 2026-11-12 |
| live | up | C | 31 | 2026-11-13 |
| replay | down | A | 102 | 2026-10-21 |
| replay | down | B | 362 | 2026-09-29 |
| replay | down | C | 107 | 2026-10-12 |
| replay | down | W | 276 | 2026-10-22 |
| replay | up | A | 153 | 2026-08-31 |
| replay | up | B | 361 | 2026-10-13 |
| replay | up | C | 972 | 2026-10-23 |

Picks by book and status:

| book | direction | source | status | n | avg_r | avg_ret_pct |
| --- | --- | --- | --- | --- | --- | --- |
| twin | down | backfill | closed | 1 | -1.04 | -10.5 |
| twin | down | backfill | open | 5 |  | -3.2 |
| twin | up | backfill | closed | 1 | -1.06 | -12.2 |
| twin | up | backfill | open | 21 |  | 3.7 |
| twin | up | live | pending | 6 |  |  |

Every pick:

| book | symbol | dir | signal_date | grade | status | entry_date | entry_px | exit_date | exit_px | exit_reason | sessions | ret_pct | r | mfe_r | mae_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| twin | SUPREMEIND.NS | down | 2026-10-26 | B | open | 2026-10-27 | 3247.813 |  |  |  | 12.0 | -2.8 |  | 0.58 | -0.58 |
| twin | ACUTAAS.NS | up | 2026-10-27 | C | open | 2026-10-28 | 3850.0 |  |  |  | 11.0 | 3.8 |  | 0.6 | -0.39 |
| twin | ADANIPORTS.NS | up | 2026-10-29 | C | open | 2026-10-30 | 1871.0 |  |  |  | 9.0 | 3.1 |  | 0.87 | -0.46 |
| twin | BSOFT.NS | up | 2026-10-29 | C | open | 2026-10-30 | 332.4464 |  |  |  | 9.0 | -1.4 |  | 0.4 | -0.54 |
| twin | MANAKCOAT.NS | up | 2026-10-29 | C | open | 2026-10-30 | 149.0 |  |  |  | 9.0 | 18.5 |  | 2.09 | -0.63 |
| twin | INTELLECT.NS | down | 2026-10-30 | B | open | 2026-11-02 | 504.55 |  |  |  | 8.0 | -3.9 |  | 0.35 | -0.65 |
| twin | ESCORTS.NS | down | 2026-11-02 | B | open | 2026-11-03 | 2423.0 |  |  |  | 7.0 | -0.3 |  | 0.23 | -0.45 |
| twin | POLICYBZR.NS | down | 2026-11-02 | B | closed | 2026-11-03 | 935.0 | 2026-11-12 | 1033.1072 | stop | 7.0 | -10.5 | -1.037 | 0.19 | -1.17 |
| twin | WELSPUNLIV.NS | up | 2026-11-03 | B | open | 2026-11-04 | 253.0 |  |  |  | 6.0 | -2.1 |  | 0.44 | -0.4 |
| twin | CNL.NS | up | 2026-11-04 | B | open | 2026-11-05 | 1378.6 |  |  |  | 5.0 | 7.0 |  | 0.71 | -0.33 |
| twin | EMCURE.NS | up | 2026-11-04 | C | open | 2026-11-05 | 2179.0 |  |  |  | 5.0 | 6.2 |  | 0.77 | -0.17 |
| twin | GPTINFRA.NS | down | 2026-11-04 | A | open | 2026-11-05 | 105.5488 |  |  |  | 5.0 | -8.0 |  | 0.0 | -0.83 |
| twin | ICIL.NS | up | 2026-11-04 | B | open | 2026-11-05 | 530.3 |  |  |  | 5.0 | 4.8 |  | 0.44 | -0.76 |
| twin | SAREGAMA.NS | up | 2026-11-04 | B | open | 2026-11-05 | 650.0 |  |  |  | 5.0 | -1.2 |  | 0.28 | -0.51 |
| twin | TASTYBITE.NS | up | 2026-11-04 | C | closed | 2026-11-05 | 11303.5 | 2026-11-06 | 9929.9464 | stop | 2.0 | -12.2 | -1.065 | 0.0 | -1.02 |
| twin | AUROPHARMA.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1777.5679 |  |  |  | 4.0 | 1.7 |  | 0.72 | -0.07 |
| twin | ICICIBANK.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1521.5 |  |  |  | 4.0 | 4.5 |  | 0.97 | -0.17 |
| twin | LUMAXTECH.NS | up | 2026-11-05 | C | open | 2026-11-06 | 2245.0 |  |  |  | 4.0 | 4.3 |  | 1.02 | -0.28 |
| twin | PARAGMILK.NS | up | 2026-11-05 | C | open | 2026-11-06 | 317.8 |  |  |  | 4.0 | 2.5 |  | 0.47 | -0.17 |
| twin | ROLEXRINGS.NS | up | 2026-11-05 | C | open | 2026-11-06 | 204.21 |  |  |  | 4.0 | 6.9 |  | 0.63 | -0.25 |
| twin | UNOMINDA.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1325.0 |  |  |  | 4.0 | 4.6 |  | 0.82 | -0.33 |
| twin | ASTRAL.NS | down | 2026-11-06 | B | open | 2026-11-09 | 1260.1157 |  |  |  | 3.0 | -1.1 |  | 0.08 | -0.35 |
| twin | SAILIFE.NS | up | 2026-11-06 | B | open | 2026-11-09 | 1738.8 |  |  |  | 3.0 | 9.6 |  | 1.82 | -0.36 |
| twin | BANKBARODA.NS | up | 2026-11-09 | C | open | 2026-11-11 | 264.4 |  |  |  | 2.0 | 4.4 |  | 0.62 | -0.1 |
| twin | INDIANB.NS | up | 2026-11-09 | C | open | 2026-11-11 | 940.0 |  |  |  | 2.0 | 0.6 |  | 0.29 | -0.17 |
| twin | UNIONBANK.NS | up | 2026-11-09 | C | open | 2026-11-11 | 200.44 |  |  |  | 2.0 | 2.0 |  | 0.26 | -0.22 |
| twin | FORCEMOT.NS | up | 2026-11-11 | C | open | 2026-11-12 | 20000.0 |  |  |  | 1.0 | -0.8 |  | 0.25 | -0.41 |
| twin | NILKAMAL.NS | up | 2026-11-11 | C | open | 2026-11-12 | 2220.0 |  |  |  | 1.0 | -1.5 |  | 0.06 | -0.14 |
| twin | AMANTA.NS | up | 2026-11-12 | B | pending |  |  |  |  |  |  |  |  |  |  |
| twin | CUPID.NS | up | 2026-11-12 | B | pending |  |  |  |  |  |  |  |  |  |  |
| twin | GABRIEL.NS | up | 2026-11-12 | C | pending |  |  |  |  |  |  |  |  |  |  |
| twin | PAYTM.NS | up | 2026-11-12 | C | pending |  |  |  |  |  |  |  |  |  |  |
| twin | PRESTIGE.NS | up | 2026-11-12 | C | pending |  |  |  |  |  |  |  |  |  |  |
| twin | SIMPLEXINF.NS | up | 2026-11-12 | C | pending |  |  |  |  |  |  |  |  |  |  |

Fact packs stored: 6, average 9,710 bytes.

One fact pack (bars cut to the last two):

```json
{
 "symbol": "AMANTA.NS",
 "direction": "up",
 "signal_date": "2026-11-12",
 "v02": {
  "grade": "B",
  "score": 1.131,
  "stage": "2",
  "stage_name": null,
  "template": "8",
  "rs_rank": 96.0,
  "mansfield": 55.07,
  "pivot": 209.9499969482422,
  "base_len": "41",
  "depth": 0.3838902356930125,
  "vol_ratio": 32.00363719339793,
  "entry": 228.3699951171875,
  "stop": 190.15749141148157,
  "hold_sessions": 21,
  "plan": {
   "qty": 13,
   "max_buy": 243.65,
   "stop": 190.16,
   "value_rs": 2969,
   "risk_rs": 497,
   "worst_risk_rs": 695,
   "max_buy_pct": 6.7,
   "stop_pct": -16.7,
   "exit_by": "2026-12-11"
  }
 },
 "indicators": {
  "close": 228.37,
  "atr_pct": 0.0669,
  "dist_sma50": 0.2251,
  "dist_sma200": 0.5478,
  "from_hi52": -0.0292,
  "from_lo52": 1.4823,
  "ret_21": 0.2533,
  "ret_63": 0.4311,
  "ret_126": 0.7006,
  "ret_252": 0.8902,
  "traded_value_20d": 20477552.0,
  "bench_ret_63": 0.0078
 },
 "market": {
  "regime": "Weak",
  "stage2_share": 0.4712,
  "bench_above_rising_sma200": false,
  "vix": 15.5
 },
 "sector": null,
 "next_results_date": null,
 "daily_bars": [
  [
   "2026-11-11",
   204.49,
   204.5,
   194.85,
   196.04,
   98913
  ],
  [
   "2026-11-12",
   198.24,
   235.24,
   195.14,
   228.37,
   2699204
  ]
 ],
 "weekly_bars": [
  [
   "2026-11-06",
   163.0,
   200.0,
   161.05,
   195.28,
   1164695
  ],
  [
   "2026-11-12",
   206.99,
   235.24,
   194.85,
   228.37,
   2899538
  ]
 ],
 "columns": "date, open, high, low, close, volume"
}
```

## US
Exit code 0.
Runs recorded:

| as_of | stocks | regime | stage2_share | new_events |
| --- | --- | --- | --- | --- |
| 2026-11-13 | 500 | Healthy | 0.478 | 469 |

Signals by source and grade:

| source | direction | grade | n | latest |
| --- | --- | --- | --- | --- |
| replay | down | A | 66 | 2026-11-05 |
| replay | down | B | 110 | 2026-11-04 |
| replay | down | C | 38 | 2026-09-16 |
| replay | down | W | 124 | 2026-11-05 |
| replay | up | A | 27 | 2026-08-27 |
| replay | up | B | 41 | 2026-11-09 |
| replay | up | C | 63 | 2026-11-04 |

Picks by book and status:

_none_

Every pick:

_none_

Fact packs stored: 0.

## Outside data the fact pack leans on

India VIX: 15.5 · US VIX: 19.299999237060547

Next results date from Yahoo: RELIANCE.NS 2027-01-15, TCS.NS None, INFY.NS 2027-01-13, HDFCBANK.NS 2027-01-16, TATAMOTORS.NS None, AAPL 2027-01-28

## Page summary rows

```json
[
 {
  "book": "twin",
  "direction": "down",
  "picks": 6,
  "closed": 1,
  "open": 5,
  "skipped": 0,
  "avg_r": -1.04,
  "median_r": -1.04,
  "win_pct": 0.0,
  "avg_excess_pct": -4.9
 },
 {
  "book": "twin",
  "direction": "up",
  "picks": 28,
  "closed": 1,
  "open": 21,
  "skipped": 0,
  "avg_r": -1.06,
  "median_r": -1.06,
  "win_pct": 0.0,
  "avg_excess_pct": -13.9
 }
]
```
