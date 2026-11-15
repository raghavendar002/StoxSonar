# Mid-term books: real-data check

Ledger copy with the NSE runs of 2026-11-13, 2026-11-12 forgotten and the newest session replayed. Nothing live was changed.

## NSE
Exit code 0.
Runs recorded:

| as_of | stocks | regime | stage2_share | new_events |
| --- | --- | --- | --- | --- |
| 2026-11-13 | 1322 | Weak | 0.475 | 0 |
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
| twin | down | backfill | closed | 2 | -1.05 | -11.2 |
| twin | down | backfill | open | 4 |  | -1.1 |
| twin | up | backfill | closed | 1 | -1.06 | -12.2 |
| twin | up | backfill | open | 27 |  | 2.3 |
| twin | up | live | pending | 3 |  |  |

Every pick:

| book | symbol | dir | signal_date | grade | status | entry_date | entry_px | exit_date | exit_px | exit_reason | sessions | ret_pct | r | mfe_r | mae_r |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| twin | SUPREMEIND.NS | down | 2026-10-26 | B | open | 2026-10-27 | 3247.813 |  |  |  | 13.0 | -1.8 |  | 0.58 | -0.58 |
| twin | ACUTAAS.NS | up | 2026-10-27 | C | open | 2026-10-28 | 3850.0 |  |  |  | 12.0 | 4.9 |  | 0.62 | -0.39 |
| twin | ADANIPORTS.NS | up | 2026-10-29 | C | open | 2026-10-30 | 1871.0 |  |  |  | 10.0 | 1.7 |  | 0.87 | -0.46 |
| twin | BSOFT.NS | up | 2026-10-29 | C | open | 2026-10-30 | 332.4464 |  |  |  | 10.0 | -2.4 |  | 0.4 | -0.54 |
| twin | MANAKCOAT.NS | up | 2026-10-29 | C | open | 2026-10-30 | 149.0 |  |  |  | 10.0 | 15.3 |  | 2.09 | -0.63 |
| twin | INTELLECT.NS | down | 2026-10-30 | B | open | 2026-11-02 | 504.55 |  |  |  | 9.0 | -4.0 |  | 0.35 | -0.65 |
| twin | ESCORTS.NS | down | 2026-11-02 | B | open | 2026-11-03 | 2423.0 |  |  |  | 8.0 | 0.9 |  | 0.23 | -0.45 |
| twin | POLICYBZR.NS | down | 2026-11-02 | B | closed | 2026-11-03 | 935.0 | 2026-11-12 | 1033.1072 | stop | 7.0 | -10.5 | -1.037 | 0.19 | -1.17 |
| twin | WELSPUNLIV.NS | up | 2026-11-03 | B | open | 2026-11-04 | 253.0 |  |  |  | 7.0 | -1.1 |  | 0.44 | -0.4 |
| twin | CNL.NS | up | 2026-11-04 | B | open | 2026-11-05 | 1378.6 |  |  |  | 6.0 | 5.8 |  | 0.71 | -0.33 |
| twin | EMCURE.NS | up | 2026-11-04 | C | open | 2026-11-05 | 2179.0 |  |  |  | 6.0 | 8.4 |  | 1.01 | -0.17 |
| twin | GPTINFRA.NS | down | 2026-11-04 | A | closed | 2026-11-05 | 105.5488 | 2026-11-13 | 118.0207 | stop | 6.0 | -11.8 | -1.067 | 0.0 | -1.08 |
| twin | ICIL.NS | up | 2026-11-04 | B | open | 2026-11-05 | 530.3 |  |  |  | 6.0 | 3.2 |  | 0.44 | -0.76 |
| twin | SAREGAMA.NS | up | 2026-11-04 | B | open | 2026-11-05 | 650.0 |  |  |  | 6.0 | 0.5 |  | 0.28 | -0.51 |
| twin | TASTYBITE.NS | up | 2026-11-04 | C | closed | 2026-11-05 | 11303.5 | 2026-11-06 | 9929.9464 | stop | 2.0 | -12.2 | -1.065 | 0.0 | -1.02 |
| twin | AUROPHARMA.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1777.5679 |  |  |  | 5.0 | 2.6 |  | 0.72 | -0.07 |
| twin | ICICIBANK.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1521.5 |  |  |  | 5.0 | 4.1 |  | 0.97 | -0.17 |
| twin | LUMAXTECH.NS | up | 2026-11-05 | C | open | 2026-11-06 | 2245.0 |  |  |  | 5.0 | 1.5 |  | 1.02 | -0.28 |
| twin | PARAGMILK.NS | up | 2026-11-05 | C | open | 2026-11-06 | 317.8 |  |  |  | 5.0 | 4.2 |  | 0.47 | -0.17 |
| twin | ROLEXRINGS.NS | up | 2026-11-05 | C | open | 2026-11-06 | 204.21 |  |  |  | 5.0 | 4.5 |  | 0.63 | -0.25 |
| twin | UNOMINDA.NS | up | 2026-11-05 | C | open | 2026-11-06 | 1325.0 |  |  |  | 5.0 | 4.8 |  | 0.82 | -0.33 |
| twin | ASTRAL.NS | down | 2026-11-06 | B | open | 2026-11-09 | 1260.1157 |  |  |  | 4.0 | 0.5 |  | 0.08 | -0.35 |
| twin | SAILIFE.NS | up | 2026-11-06 | B | open | 2026-11-09 | 1738.8 |  |  |  | 4.0 | 10.9 |  | 1.94 | -0.36 |
| twin | BANKBARODA.NS | up | 2026-11-09 | C | open | 2026-11-11 | 264.4 |  |  |  | 3.0 | 3.6 |  | 0.62 | -0.1 |
| twin | INDIANB.NS | up | 2026-11-09 | C | open | 2026-11-11 | 940.0 |  |  |  | 3.0 | -0.8 |  | 0.29 | -0.17 |
| twin | UNIONBANK.NS | up | 2026-11-09 | C | open | 2026-11-11 | 200.44 |  |  |  | 3.0 | 1.3 |  | 0.31 | -0.22 |
| twin | FORCEMOT.NS | up | 2026-11-11 | C | open | 2026-11-12 | 20000.0 |  |  |  | 2.0 | -2.0 |  | 0.25 | -0.41 |
| twin | NILKAMAL.NS | up | 2026-11-11 | C | open | 2026-11-12 | 2220.0 |  |  |  | 2.0 | 0.4 |  | 0.06 | -0.17 |
| twin | AMANTA.NS | up | 2026-11-12 | B | open | 2026-11-13 | 231.8 |  |  |  | 1.0 | 1.1 |  | 0.24 | -0.08 |
| twin | CUPID.NS | up | 2026-11-12 | B | open | 2026-11-13 | 388.9 |  |  |  | 1.0 | -2.9 |  | 0.1 | -0.62 |
| twin | GABRIEL.NS | up | 2026-11-12 | C | open | 2026-11-13 | 1610.0 |  |  |  | 1.0 | -3.6 |  | 0.0 | -0.49 |
| twin | PAYTM.NS | up | 2026-11-12 | C | open | 2026-11-13 | 1920.0 |  |  |  | 1.0 | 1.0 |  | 0.24 | -0.1 |
| twin | PRESTIGE.NS | up | 2026-11-12 | C | open | 2026-11-13 | 1687.4 |  |  |  | 1.0 | -2.2 |  | 0.09 | -0.33 |
| twin | SIMPLEXINF.NS | up | 2026-11-12 | C | open | 2026-11-13 | 308.6 |  |  |  | 1.0 | -3.0 |  | 0.0 | -0.38 |
| twin | ALICON.NS | up | 2026-11-13 | C | pending |  |  |  |  |  |  |  |  |  |  |
| twin | ANURAS.NS | up | 2026-11-13 | C | pending |  |  |  |  |  |  |  |  |  |  |
| twin | DHANBANK.NS | up | 2026-11-13 | C | pending |  |  |  |  |  |  |  |  |  |  |

Fact packs stored: 3, average 9,323 bytes.

One fact pack (bars cut to the last two):

```json
{
 "symbol": "ALICON.NS",
 "direction": "up",
 "signal_date": "2026-11-13",
 "v02": {
  "grade": "C",
  "score": 0.547,
  "stage": 2,
  "stage_name": "Advancing",
  "template": 8,
  "rs_rank": 81.0,
  "mansfield": 28.44,
  "pivot": 909.0,
  "base_len": 25,
  "depth": 0.1737,
  "vol_ratio": 48.31,
  "entry": 976.15,
  "stop": 859.64,
  "hold_sessions": 21,
  "plan": {
   "qty": 4,
   "max_buy": 1022.75,
   "stop": 859.64,
   "value_rs": 3905,
   "risk_rs": 466,
   "worst_risk_rs": 652,
   "max_buy_pct": 4.8,
   "stop_pct": -11.9,
   "exit_by": "2026-12-14"
  }
 },
 "indicators": {
  "close": 976.15,
  "atr_pct": 0.0477,
  "dist_sma50": 0.2218,
  "dist_sma200": 0.3672,
  "from_hi52": -0.0189,
  "from_lo52": 0.6952,
  "ret_21": 0.1275,
  "ret_63": 0.2681,
  "ret_126": 0.4175,
  "ret_252": 0.0173,
  "traded_value_20d": 14316149.0,
  "bench_ret_63": 0.0026
 },
 "market": {
  "regime": "Weak",
  "stage2_share": 0.475,
  "bench_above_rising_sma200": false,
  "vix": 15.5
 },
 "sector": null,
 "next_results_date": null,
 "daily_bars": [
  [
   "2026-11-12",
   844.0,
   848.0,
   827.0,
   832.05,
   16751
  ],
  [
   "2026-11-13",
   860.0,
   995.0,
   845.3,
   976.15,
   3378534
  ]
 ],
 "weekly_bars": [
  [
   "2026-11-06",
   830.85,
   873.9,
   815.1,
   829.75,
   80969
  ],
  [
   "2026-11-13",
   839.0,
   995.0,
   827.0,
   976.15,
   3427192
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

## One real debate

AMANTA.NS · up · grade B · signal 2026-11-12

Status **done** · input tokens 19642 · output tokens 2830 · cost $0.09556

Levels used: judge · problems: None · wait: None

Telegram message as it would be sent:

```
StoxSonar · Bull/Bear/Judge · NSE close 2026-11-12

AVOID · AMANTA · B breakout · conviction 3/5
   If taken anyway: Buy 220.00–232.00 · stop 190.16 · target 286.00 then 310.00 · hold up to 21 sessions
   The stock has climbed hard, up 89% over a year and 25% in the last month, while the index barely moved (+0.8% over 63 days). Its 41-session base was loose, swinging from about 207 down to 151.71 before snapping back. The breakout day traded 2.70M shares, about 32 times normal, but past spikes like this faded within weeks. Many recent sessions traded at a single price on tiny volume, and the overall market regime is Weak.
   For: RS rank 96 and Mansfield +55 show strong outperformance against a benchmark up only 0.78% over 63 days. | The close of 228.37 cleared the 209.95 pivot by about 8.8% and sits only 2.9% below the 52-week high. | The breakout bar closed at 228.37 within a 195.14–235.24 range, in the upper part of the day.
   Against: The market regime is Weak, and no sector data is available to show support. | The stock is extended: 22.5% above the 50-day SMA, 54.8% above the 200-day, and 148% off its 52-week low. | Two earlier thrusts failed: the 11 Jun spike on 6.0M shares at a 164 high and the 24 Aug high of 205.57, which fell to 183.47 within days.
   Wrong if: The Avoid would be wrong if the stock holds above the 209.95 pivot, closes above the 235.24 breakout-day high on steady turnover, and stops printing single-price thin bars. That would show real demand rather than a one-day spike.

API spend this month: $0.10 of $6

An experiment, not advice: the screen under these calls has not passed its test, and the Judge has no track record yet. Every call is logged and scored.
```

Bull:

> **Bull case for AMANTA.NS breakout, 2026-11-12 (honest, with caveats)**

**Trend and stage:** Stage 2, template 8, and the close of 228.37 sits 22.5% above the 50-day SMA and 54.8% above the 200-day. Returns are strong at every horizon: 21d +25%, 63d +43%, 126d +70%, 252d +89%. The 63-day benchmark return is only +0.8%, so this is real outperformance. RS rank is 96 and Mansfield is +55.

**Base and breakout:** The close is 2.9% below the 52-week high and clears the 209.95 pivot (the 10 Sep high) by about 8.8%. The weekly bar closed at the high end of its range (228.37 against a 235.24 high). The base is 41 sessions long, but the 38% depth is loose, not tight.

**Volume:** The breakout day traded 2.70M shares, about 32x the ratio the screen cites. Volume is unusually high, and the stock has absorbed volume spikes before (6.0M on 11 Jun) and held above those levels.

**Stop and target:** The screen's stop is 190.16, 16.7% below entry. The risk-sized plan is 13 shares, about Rs 2,969, risking Rs 497 (worst case Rs 695). That is a small position, so the stop width is affordable. The stop sits below the October pullback area (lows near 151–175) only partly, so a tighter stop below 195 (the pre-breakout close) is arguable but would be noisy at ATR 6.7%. A reasonable target is a 2:1 or better move toward 270–280, which fits a one-month hold ending around 11 Dec.

**What would prove me wrong:** A close back below 209.95 within a few sessions, meaning a failed breakout. A close below 196, the prior day's close, would also be a warning. The 190.16 stop is the hard line.

**Honest weaknesses:** The market regime is Weak. Sector data and results dates are missing. The stock is 148% above its 52-week low and has had a gap-and-fade pattern, with the 205 high in August and the 207 high in October both reversed. Many of the bars show thin trading, with single-price prints and tiny volume, which suggests circuit-style or illiquid action. Slippage is a real risk, and the max buy is 243.65. This is a modest-conviction B grade, not a strong case.

Bear:

> The Bear case: this is a late, extended, illiquid-looking spike in a weak market, and the plan's own risk numbers don't hold up.

**Extension.** The close of 228.37 is 22.5% above the 50-day average and 54.8% above the 200-day. The stock is up 25% in 21 sessions, 43% in 63 and 89% in 252, while the benchmark gained 0.78% over 63 days. It is 148% off its 52-week low. Buying here means paying for a move that has already happened.

**The base is not a base.** The pivot of 209.95 was the 9/10 intraday high. Since then the stock has ranged from 151.71 to 207.56, with a depth of 38%. A 41-day, 38%-deep structure is loose, not tight. The stock fell from 207 on 10/7 to 160 on 10/21, a 23% drop, and only recovered in the last six sessions.

**Volume is a one-day event.** The vol_ratio of 32 comes from 2.70M shares on a day with a 40-point range (low 195.14, high 235.24), and the close sits well below the high. That looks like a news or operator spike, not accumulation. The 6/11 spike (6.0M shares, high 164) was followed by a fade to 159 within weeks, and the 8/24 high of 205 reversed to 183 within four sessions. Both earlier thrusts failed.

**Bar quality.** Many sessions show open=high=low=close with tiny volume (7/6, 7/7, 8/6 to 8/12, 9/3 to 9/9). That points to circuit-limit style trading and thin liquidity. Traded value of about Rs 2.0 crore a day is modest, and exits may be hard if the stock turns.

**Risk math.** The stop at 190.16 is 16.7% below entry, and the max buy of 243.65 is 6.7% above. The 13-share plan carries Rs 497 risk, but worst-case risk is Rs 695, about 40% more. ATR is 6.7% daily, so the stop is only about 2.5 ATRs away. A gap through it on a thin stock is plausible. The market regime is Weak, and no sector data is available to offset that.

**What would change my mind:** a pullback that holds above 209.95 on contracting volume, or a few closes above 228 with steady turnover and no circuit-style bars.

Judge:

```json
{
 "verdict": "Avoid",
 "conviction": 3,
 "horizon_sessions": 21,
 "entry_low": 220.0,
 "entry_high": 232.0,
 "stop": 190.16,
 "target": 286.0,
 "target_2": 310.0,
 "wait_kind": "none",
 "wait_level": 0,
 "wait_min_volume_ratio": 0,
 "wait_within_sessions": 0,
 "invalidation": "The Avoid would be wrong if the stock holds above the 209.95 pivot, closes above the 235.24 breakout-day high on steady turnover, and stops printing single-price thin bars. That would show real demand rather than a one-day spike.",
 "how_its_moving": "The stock has climbed hard, up 89% over a year and 25% in the last month, while the index barely moved (+0.8% over 63 days). Its 41-session base was loose, swinging from about 207 down to 151.71 before snapping back. The breakout day traded 2.70M shares, about 32 times normal, but past spikes like this faded within weeks. Many recent sessions traded at a single price on tiny volume, and the overall market regime is Weak.",
 "reasons_for": [
  "RS rank 96 and Mansfield +55 show strong outperformance against a benchmark up only 0.78% over 63 days.",
  "The close of 228.37 cleared the 209.95 pivot by about 8.8% and sits only 2.9% below the 52-week high.",
  "The breakout bar closed at 228.37 within a 195.14\u2013235.24 range, in the upper part of the day.",
  "Stage 2 with template 8 and returns positive at all horizons (+43% over 63 days, +70% over 126 days)."
 ],
 "reasons_against": [
  "The market regime is Weak, and no sector data is available to show support.",
  "The stock is extended: 22.5% above the 50-day SMA, 54.8% above the 200-day, and 148% off its 52-week low.",
  "Two earlier thrusts failed: the 11 Jun spike on 6.0M shares at a 164 high and the 24 Aug high of 205.57, which fell to 183.47 within days.",
  "The base is 38% deep, and the stock dropped 23% from 207.56 on 7 Oct to the 151.71 low on 21 Oct.",
  "Many bars are single-price prints on thin volume (8/6\u20138/12, 9/3\u20139/16), and 20-day traded value is only about Rs 2.05 crore, so gap and slippage risk is high.",
  "The stop at 190.16 is 16.7% away, about 2.5 ATR at a 6.7% daily ATR. Worst-case risk of Rs 695 exceeds the Rs 500 budget.",
  "The first target at 1.5R requires about 286, roughly 25% above entry within 21 sessions, which is a stretch after a 25% month."
 ]
}
```

Picks written:

| book | symbol | verdict | conviction | levels | stop | target | horizon | max_buy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| debated | AMANTA.NS | Avoid | 3 | judge | 190.16 | 286.0 | 21 |  |

## Page summary rows

```json
[
 {
  "book": "twin",
  "direction": "down",
  "picks": 6,
  "closed": 2,
  "open": 4,
  "skipped": 0,
  "avg_r": -1.05,
  "median_r": -1.05,
  "win_pct": 0.0,
  "avg_excess_pct": -7.7
 },
 {
  "book": "twin",
  "direction": "up",
  "picks": 31,
  "closed": 1,
  "open": 27,
  "skipped": 0,
  "avg_r": -1.06,
  "median_r": -1.06,
  "win_pct": 0.0,
  "avg_excess_pct": -13.9
 }
]
```
