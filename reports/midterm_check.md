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

Status **done** · input tokens 21120 · output tokens 2598 · cost $0.09531

Levels used: judge · problems: None · wait: None

Telegram message as it would be sent:

```
StoxSonar · Bull/Bear/Judge · NSE close 2026-11-12

AVOID · AMANTA · B breakout · conviction 4/5
   If taken anyway: Buy 220.00–232.00 · stop 190.16 · target 286.00 then 310.00 · hold up to 21 sessions
   The stock is in a strong uptrend: up 43% in three months and 89% in a year, while the index rose only 0.8% over the same three months. Over the last 41 sessions it built a loose, 38%-deep base, falling from 207 in early October to about 158 in late October. On the signal day it jumped about 16.5% to 228.37 on 2.7 million shares, roughly 32 times normal volume, clearing the September high of 209.95. Many earlier sessions traded at a single price on tiny volume, which points to a thin, circuit-limited stock. The broad market is Weak, and no sector data is given.
   Brain: The 25 most similar past signals: average -0.66R over 21 sessions, 28% made money (before costs).
   For: Relative strength is top-tier: RS rank 96 and Mansfield 55.07, with a 63-day return of 43.1% against the benchmark's 0.8%. | The breakout bar closed at 228.37, near its 235.24 high and 8.8% above the 209.95 pivot, on a volume ratio of 32x. | The close is only 2.9% below the 52-week high, in Stage 2.
   Against: The screen's base rates are negative. Same grade and regime (n=251): average -0.17R, 42% wins. Most similar cases (n=25, small sample): average -0.66R, 28% wins, -4.0% excess return. Nothing in the pack shows how this signal differs. | The market regime is Weak, so a long needs more support than usual, and none is offered here. | The entry is extended: 22.5% above the 50-day average and 54.8% above the 200-day, after a 25.3% gain over 21 days.
   Wrong if: I would reconsider if price pulls back toward the 209.95 pivot on quiet volume (near the usual 30k-100k shares), holds there, and then closes back above 235.24 with heavy volume. That would give a tighter stop near the pivot instead of 16.7% away. A close below 209.95 would confirm the breakout failed.

API spend this month: $0.10 of $6

An experiment, not advice: the screen under these calls has not passed its test, and the Judge has no track record yet. Every call is logged and scored.
```

Bull:

> **Bull case, AMANTA.NS long, signal 2026-11-12**

The trend and relative strength are about as good as the screen produces. Stage 2 with template 8, RS rank 96 and Mansfield 55. The close of 228.37 is 54.8% above the 200-day average and 22.5% above the 50-day. Returns are 43% over 63 days against the benchmark's 0.8%, and 89% over 252 days. The close is 2.9% below the 52-week high and 148% above the low.

The breakout bar is decisive. It ran from a 195.14 low to a 235.24 high and closed at 228.37, near the top of the range, up about 16.5% on the day. Volume was 2.70M shares, versus a typical 20k to 100k in recent sessions. The screen's 32x volume ratio matches that. It also clears the 209.95 pivot, which is the September high, by about 8.8%. Weekly volume of 2.9M is the heaviest since the June spike week. Demand is real, and the Weak market regime hasn't stopped this stock.

Liquidity is workable: 20-day traded value is about Rs 2.05 crore, so a 13-share order is trivial.

Stop and target: the plan stop is 190.16, below the October lows around 175 to 184 only partly, so it is a reasonable structural level. Risk is 497 rupees on 13 shares. The max buy of 243.65 caps chasing. A first target is a measured move toward 260 to 270, about 1.0 to 1.1 times the 41-day base height. That is speculative.

**Honest weaknesses:** I can't dress these up. The screen's most-similar cases (n=25) averaged -0.66R with a 28% win rate. Same grade and regime (n=251) averaged -0.17R. The stop is 16.7% away, ATR is 6.7%, and many bars are single-price prints, which suggests thin trading or circuit-limit moves. A 16.5% one-day pop after a 25% monthly gain is extended.

**What proves me wrong:** a close back below 209.95 means a failed breakout. A close below 190.16 is the exit. Volume fading to the usual 30k to 60k within days would mean the spike was a one-off.

Bear:

> The case against buying AMANTA at 228.37 rests on the setup, the liquidity, and the track record.

**Track record.** The screen's own history is negative. Same grade (n=341): avg R -0.09, median -0.24, 44% wins. Same grade and Weak regime (n=251): avg R -0.17, median -0.36, 42% wins. The 25 most similar signals (small n, but matched on RS, base depth and length, and volume ratio) averaged -0.66R with 28% wins and -4.0% excess. Nothing here says this setup pays.

**Extended and late.** The close is 22.5% above the 50-day average and 54.8% above the 200-day. It is up 43% in 63 days and 89% in a year, against a benchmark up 0.8% over 63 days. ATR is 6.7% of price, so the stock moves wildly. The entry is also 8.8% above the 209.95 pivot, so this is a chase, and the plan's max_buy of 243.65 allows a further 6.7% of chasing.

**Stop too wide.** The stop at 190.16 is 16.7% below entry, and the plan itself shows worst-case risk of Rs 695 against 497 planned. That is above the 0.5% budget. Position size is just 13 shares (Rs 2,969), so the trade barely matters if it works and still hurts if gapped.

**Bars are erratic.** Many sessions show open=high=low=close with tiny volume (e.g. 7-13 Aug at 2-7k shares), which is the pattern of a thin, circuit-limited stock. The 41-day base is 38% deep, which is loose, and the stock fell from 207 on 7 Oct to 157.74 on 27 Oct before this jump. The 12 Nov bar ran from 198 to a 235.24 high and closed at 228.37, giving back some of the spike on 2.7M volume. The vol_ratio of 32 comes from one day, which looks like a single event spike rather than sustained demand. The earlier 11 June spike (6.0M shares, high 164) also faded into months of chop.

**Market.** The regime is Weak, and the sector and results date are unknown, so a surprise is possible.

**What would change my mind:** a pullback toward 205-210 that holds the pivot on quiet volume, or a tighter stop that keeps risk inside budget.

Judge:

```json
{
 "verdict": "Avoid",
 "conviction": 4,
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
 "invalidation": "I would reconsider if price pulls back toward the 209.95 pivot on quiet volume (near the usual 30k-100k shares), holds there, and then closes back above 235.24 with heavy volume. That would give a tighter stop near the pivot instead of 16.7% away. A close below 209.95 would confirm the breakout failed.",
 "how_its_moving": "The stock is in a strong uptrend: up 43% in three months and 89% in a year, while the index rose only 0.8% over the same three months. Over the last 41 sessions it built a loose, 38%-deep base, falling from 207 in early October to about 158 in late October. On the signal day it jumped about 16.5% to 228.37 on 2.7 million shares, roughly 32 times normal volume, clearing the September high of 209.95. Many earlier sessions traded at a single price on tiny volume, which points to a thin, circuit-limited stock. The broad market is Weak, and no sector data is given.",
 "reasons_for": [
  "Relative strength is top-tier: RS rank 96 and Mansfield 55.07, with a 63-day return of 43.1% against the benchmark's 0.8%.",
  "The breakout bar closed at 228.37, near its 235.24 high and 8.8% above the 209.95 pivot, on a volume ratio of 32x.",
  "The close is only 2.9% below the 52-week high, in Stage 2."
 ],
 "reasons_against": [
  "The screen's base rates are negative. Same grade and regime (n=251): average -0.17R, 42% wins. Most similar cases (n=25, small sample): average -0.66R, 28% wins, -4.0% excess return. Nothing in the pack shows how this signal differs.",
  "The market regime is Weak, so a long needs more support than usual, and none is offered here.",
  "The entry is extended: 22.5% above the 50-day average and 54.8% above the 200-day, after a 25.3% gain over 21 days.",
  "The stop at 190.16 is 16.7% away, about 2.5 ATR at a 6.7% ATR. Worst-case risk is Rs 695 against a Rs 500 budget, on only a 13-share position.",
  "Many bars are single-price prints on 2k-20k shares, the pattern of circuit limits and gap risk. The 11 June volume spike of 6.0M shares also faded into months of chop."
 ]
}
```

Track record the Brain gave the debate:

```json
{
 "record": {
  "note": "How past signals and past verdicts ended. Small samples are weak evidence: under about 30 cases, quote the n and do not lean on the figure.",
  "screen_history": {
   "basis": "Every earlier signal from this screen on this side with a finished 21-session result, mostly replayed history, before costs. R is the result over the entry-to-stop distance. The screen's grades were tuned on part of this history, so it may flatter the screen.",
   "same_grade": {
    "n": 341,
    "avg_r": -0.09,
    "median_r": -0.24,
    "win_pct": 44.0,
    "median_ret_pct": -1.7,
    "avg_excess_pct": 0.5
   },
   "same_grade_and_regime": {
    "n": 251,
    "avg_r": -0.17,
    "median_r": -0.36,
    "win_pct": 42.0,
    "median_ret_pct": -2.4,
    "avg_excess_pct": -0.1
   },
   "most_similar": {
    "n": 25,
    "avg_r": -0.66,
    "median_r": -0.68,
    "win_pct": 28.0,
    "median_ret_pct": -5.0,
    "avg_excess_pct": -4.0,
    "matched_on": "RS rank, Mansfield, base depth, base length, volume ratio"
   }
  },
  "judge_record": {
   "closed": 0
  },
  "similar_judged_cases": []
 },
 "lessons": []
}
```

Picks written:

| book | symbol | verdict | conviction | levels | stop | target | horizon | max_buy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| debated | AMANTA.NS | Avoid | 4 | judge | 190.16 | 286.0 | 21 |  |

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
