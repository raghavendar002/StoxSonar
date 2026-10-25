"""Phase 3: re-tune the bullish grade on NSE data, judged only out of sample.

    python research/retune.py reports/nse_full/backtest_signals.csv.gz > reports/retune.md

Walk-forward by calendar year. For each test year Y the score is fitted only on
breakouts triggered before Y, minus a 100-day embargo so that no training
outcome window (up to 63 sessions) overlaps the test year (purging, AFML ch. 7).
The test year's grades are then set with that fit and scored. Nothing about a
test year is seen before it is graded.

Variants compared on the same out-of-sample years:
  v0.2      the live score and cut-offs, unchanged (fitted on 2006-2018 Yahoo data)
  refit     v0.2's four features, means, spreads, clips and cut-offs refitted each year
  selected  features picked each year from a fixed pool by a stability rule:
            same sign of rank correlation in both halves of the training data,
            |t| > 2, not a near-duplicate (|rho| > 0.7) of one already picked, at most 6;
            score = equal-weight average of signed, clipped z-scores

Decision rule, fixed before the first run: a variant replaces v0.2 only if,
on tradable Grade A trades (Healthy market, above the 200-day average) in the
common out-of-sample years, it beats v0.2 on average AND median net excess
return, is positive in at least as many years, and its monthly series has a
deflated Sharpe ratio of at least 0.95 given the variants tried. Otherwise v0.2
stays.

Net excess = 21-session return from the next open minus the Nifty 500's, minus
COST for brokerage, STT, charges and slippage on a round trip.
"""

from __future__ import annotations

import json
import sys
from math import erf, sqrt

import numpy as np
import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from sonar import config as C  # noqa: E402

COST = 0.005
EMBARGO_DAYS = 100
FIRST_TRAIN_YEARS = 4
A_PCT, B_PCT = 0.80, 0.50          # same percentile cut-offs as v0.2
MAX_FEATURES = 6
POOL = ["rs_rank", "mansfield", "template", "vol_ratio", "depth", "base_len", "stage_age",
        "ext_pivot", "atr_pct", "fail_dist_atr", "from_hi52", "from_lo52", "dist_sma50",
        "dist_sma200", "slope150", "prior_63", "prior_126", "day_ret", "gap", "tight10",
        "dry_vol10", "log_value", "log_price", "bench_prior_63"]
V02 = list(C.SCORE_FEATURES)


def load(path: str) -> pd.DataFrame:
    e = pd.read_csv(path)
    u = e[e["direction"] == "up"].dropna(subset=["ret_21", "bench_21"]).copy()
    u = u[(u["ret_21"] < 3) & (u["ret_21"] > -0.95)]          # bad prints
    u["date"] = pd.to_datetime(u["trigger_date"])
    u["year"] = u["date"].dt.year
    u["net"] = u["ret_21"] - u["bench_21"] - COST
    u["fit_y"] = u["net"].clip(-0.5, 0.5)
    u["log_value"] = np.log10(u["traded_value"].clip(lower=1))
    u["log_price"] = np.log10(u["price"].clip(lower=0.01))
    u = u[u["dist_sma200"] > 0]                               # graded only above the 200-day
    u["tradable"] = u["regime"] == "Healthy"
    return u.sort_values("date").reset_index(drop=True)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + erf(x / sqrt(2)))


def _norm_ppf(p: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _norm_cdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


def deflated_sharpe(x: np.ndarray, sr_trials: list) -> float:
    """Probability the true Sharpe of `x` beats the best of len(sr_trials) lucky draws
    (Bailey and Lopez de Prado 2014). Per-period, not annualised."""
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 12 or x.std(ddof=1) == 0:
        return float("nan")
    sr = x.mean() / x.std(ddof=1)
    k = len(sr_trials)
    var_sr = np.var(sr_trials, ddof=1) if k > 1 else 0.0
    gamma = 0.5772156649
    sr0 = sqrt(var_sr) * ((1 - gamma) * _norm_ppf(1 - 1 / k) + gamma * _norm_ppf(1 - 1 / (k * np.e))) \
        if k > 1 else 0.0
    skew = pd.Series(x).skew()
    kurt = pd.Series(x).kurt() + 3
    denom = sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-9))
    return float(_norm_cdf((sr - sr0) * sqrt(n - 1) / denom))


class Scorer:
    """Signed, clipped z-scores averaged over `features`, fitted on one training set."""

    def __init__(self, train: pd.DataFrame, features: list, signs: dict | None = None):
        self.features = features
        self.signs = signs or {f: 1.0 for f in features}
        self.params = {}
        for f in features:
            x = train[f].dropna()
            lo, hi = x.quantile(0.01), x.quantile(0.99)
            xc = x.clip(lo, hi)
            self.params[f] = (lo, hi, xc.mean(), xc.std() or 1.0)
        s = self.score(train)
        self.cut_a, self.cut_b = s.quantile(A_PCT), s.quantile(B_PCT)

    def score(self, d: pd.DataFrame) -> pd.Series:
        zs = []
        for f in self.features:
            lo, hi, m, sd = self.params[f]
            zs.append(self.signs[f] * (d[f].fillna(lo).clip(lo, hi) - m) / sd)
        return pd.concat(zs, axis=1).mean(axis=1)

    def grade(self, d: pd.DataFrame) -> pd.Series:
        s = self.score(d)
        return pd.Series(np.where(s >= self.cut_a, "A", np.where(s >= self.cut_b, "B", "C")), index=d.index)


def _rho(a: pd.Series, b: pd.Series) -> float:
    """Spearman rank correlation without scipy."""
    return a.rank().corr(b.rank())


def select(train: pd.DataFrame) -> tuple:
    """Stable features and their signs, strongest first."""
    half = train["date"].iloc[len(train) // 2]
    h1, h2 = train[train["date"] < half], train[train["date"] >= half]
    cands = []
    for f in POOL:
        if f not in train or train[f].notna().mean() < 0.9:
            continue
        rho = _rho(train[f], train["fit_y"])
        r1 = _rho(h1[f], h1["fit_y"])
        r2 = _rho(h2[f], h2["fit_y"])
        n = train[f].notna().sum()
        if not np.isfinite([rho, r1, r2]).all() or np.sign(r1) != np.sign(r2) or np.sign(rho) != np.sign(r1):
            continue
        t = rho * sqrt((n - 2) / max(1 - rho ** 2, 1e-9))
        if abs(t) > 2:
            cands.append((abs(rho), f, float(np.sign(rho))))
    picked, signs = [], {}
    for _, f, sg in sorted(cands, reverse=True):
        if any(abs(_rho(train[f], train[g])) > 0.7 for g in picked):
            continue
        picked.append(f)
        signs[f] = sg
        if len(picked) == MAX_FEATURES:
            break
    return picked, signs


def v02_grade(d: pd.DataFrame) -> pd.Series:
    s = d["score"]
    return pd.Series(np.where(s >= C.SCORE_A, "A", np.where(s >= C.SCORE_B, "B", "C")), index=d.index)


def walk_forward(u: pd.DataFrame) -> tuple:
    first = u["year"].min() + FIRST_TRAIN_YEARS
    last = u["year"].max()
    out, picks = [], {}
    for y in range(first, last + 1):
        cutoff = pd.Timestamp(f"{y}-01-01") - pd.Timedelta(days=EMBARGO_DAYS)
        train, test = u[u["date"] < cutoff], u[u["year"] == y].copy()
        if len(test) == 0 or len(train) < 300:
            continue
        test["g_v02"] = v02_grade(test)
        test["g_refit"] = Scorer(train, V02).grade(test)
        feats, signs = select(train)
        picks[y] = {f: int(signs[f]) for f in feats}
        test["g_selected"] = Scorer(train, feats, signs).grade(test) if feats else "C"
        out.append(test)
    return pd.concat(out, ignore_index=True), picks


def stats(x: pd.Series) -> dict:
    return {"n": int(len(x)), "avg_net_pct": round(x.mean() * 100, 2) if len(x) else None,
            "median_net_pct": round(x.median() * 100, 2) if len(x) else None,
            "win_pct": round((x > 0).mean() * 100, 1) if len(x) else None}


def monthly(d: pd.DataFrame) -> pd.Series:
    """Average net excess of the month's trades: overlapping trades are not independent."""
    return d.groupby(d["date"].dt.to_period("M"))["net"].mean()


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        rows.append("| " + " | ".join("–" if v is None or v != v else str(v) for v in r) + " |")
    return "\n".join(rows) + "\n"


def main(path: str) -> int:
    u = load(path)
    oos, picks = walk_forward(u)
    variants = ["v02", "refit", "selected"]
    v02_oos_from = 2019                         # v0.2 was fitted on data to 2018
    common = oos[oos["year"] >= v02_oos_from]
    trade = common[common["tradable"]]
    lines = [f"# Phase 3 re-tune, walk-forward on NSE data", "",
             f"Up breakouts above the 200-day average: {len(u)} from {u['date'].min().date()} to "
             f"{u['date'].max().date()}. Net = 21-session excess over the Nifty 500 minus "
             f"{COST * 100:.1f}% round-trip cost. Out-of-sample years compared: {v02_oos_from}-"
             f"{oos['year'].max()}. Tradable = Healthy market (the app suggests no buys when Weak).", ""]

    rows, summary = [], {}
    sr_trials = []
    for v in variants:
        a = trade[trade[f"g_{v}"] == "A"]
        mser = monthly(a)
        sr_trials.append(mser.mean() / mser.std(ddof=1) if len(mser) > 2 else 0.0)
    for v in variants:
        g = f"g_{v}"
        s_v = {}
        for grade in "ABC":
            x = trade[trade[g] == grade]["net"]
            r = stats(x)
            s_v[grade] = r
            rows.append({"variant": v, "grade": grade, **r})
        a = trade[trade[g] == "A"]
        yearly = a.groupby("year")["net"].mean()
        mser = monthly(a)
        s_v["A_years_positive"] = [int((yearly > 0).sum()), int(len(yearly))]
        s_v["A_monthly_mean_pct"] = round(mser.mean() * 100, 2) if len(mser) else None
        s_v["A_monthly_t"] = round(mser.mean() / mser.std(ddof=1) * sqrt(len(mser)), 2) if len(mser) > 2 else None
        s_v["A_deflated_sharpe"] = round(deflated_sharpe(mser.to_numpy(), sr_trials), 3)
        s_v["A_minus_C_pct"] = round((s_v["A"]["avg_net_pct"] or 0) - (s_v["C"]["avg_net_pct"] or 0), 2)
        summary[v] = s_v
    lines += ["## Tradable trades by grade, out of sample", "", md(pd.DataFrame(rows)), ""]
    lines += ["## Grade A: is it worth trading?", "",
              "Monthly = the average of each month's Grade A trades, so a busy month counts once. "
              "Deflated Sharpe = probability the edge is real after allowing for the three variants tried.", ""]
    lines.append(md(pd.DataFrame([{"variant": v, "years_positive": f"{s['A_years_positive'][0]} of {s['A_years_positive'][1]}",
                                    "monthly_mean_pct": s["A_monthly_mean_pct"], "monthly_t": s["A_monthly_t"],
                                    "deflated_sharpe": s["A_deflated_sharpe"], "A_minus_C_pct": s["A_minus_C_pct"]}
                                   for v, s in summary.items()])))
    yr = trade.groupby("year").apply(lambda d: pd.Series(
        {v: round(d[d[f"g_{v}"] == "A"]["net"].mean() * 100, 1) for v in variants} |
        {f"n_{v}": int((d[f"g_{v}"] == "A").sum()) for v in variants}), include_groups=False)
    lines += ["", "## Grade A average net excess by year (%)", "", md(yr.reset_index()), ""]

    base = summary["v02"]
    verdicts = {}
    for v in ("refit", "selected"):
        s = summary[v]
        ok = (s["A"]["avg_net_pct"] or -99) > (base["A"]["avg_net_pct"] or -99) and \
             (s["A"]["median_net_pct"] or -99) > (base["A"]["median_net_pct"] or -99) and \
             s["A_years_positive"][0] >= base["A_years_positive"][0] and \
             (s["A_deflated_sharpe"] or 0) >= 0.95
        verdicts[v] = ok
    lines += ["## Decision (rule fixed before the run)", ""]
    for v, ok in verdicts.items():
        lines.append(f"- {v}: {'REPLACES v0.2' if ok else 'does not beat v0.2 by the rule'}")
    lines.append(f"- v0.2 Grade A deflated Sharpe on its own: {base['A_deflated_sharpe']} "
                 f"({'edge looks real' if (base['A_deflated_sharpe'] or 0) >= 0.95 else 'edge not proven'})")
    lines += ["", "## Features the stability rule picked each year (sign: +1 higher is better)", ""]
    for y, p in picks.items():
        lines.append(f"- {y}: " + (", ".join(f"{f} ({s:+d})" for f, s in p.items()) or "none"))
    # Final fit on everything, for adoption if the rule says so
    feats, signs = select(u[u["date"] < u["date"].max() - pd.Timedelta(days=EMBARGO_DAYS)])
    final = Scorer(u, feats, signs) if feats else None
    print("\n".join(lines))
    json.dump({"summary": summary, "verdicts": verdicts, "picks": {str(k): v for k, v in picks.items()},
               "final_fit": None if final is None else {
                   "features": {f: [*map(float, final.params[f]), signs[f]] for f in feats},
                   "cut_a": float(final.cut_a), "cut_b": float(final.cut_b)}},
              open(path.replace("backtest_signals.csv.gz", "retune.json"), "w"), indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
