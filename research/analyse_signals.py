"""Which signal features separate good breakouts from bad ones?

Reads reports/backtest_signals.csv.gz and reports/backtest_regime.csv.gz
(written by backtest.py) and prints, for each feature, results by quintile in
a training period (2006-2018) and a test period (2019 on). A feature is only
worth using if it points the same way in both.

    python research/analyse_signals.py > reports/feature_study.txt
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPLIT_YEAR = 2018

FEATURES = ["template", "rs_rank", "mansfield", "vol_ratio", "depth", "base_len", "stage_age",
            "ext_pivot", "atr_pct", "fail_dist_atr", "from_hi52", "from_lo52", "dist_sma50",
            "dist_sma200", "slope150", "prior_63", "prior_126", "day_ret", "gap", "tight10",
            "dry_vol10", "traded_value", "price", "bench_prior_63", "stage2_share"]


def load() -> pd.DataFrame:
    e = pd.read_csv(ROOT / "reports" / "backtest_signals.csv.gz")
    reg = pd.read_csv(ROOT / "reports" / "backtest_regime.csv.gz", index_col=0, parse_dates=True)
    u = e[(e["direction"] == "up")].dropna(subset=["ret_21"]).copy()
    # Bad prints: a 21-session move beyond +300% / -95% is almost always a data error
    u = u[(u["ret_21"] < 3) & (u["ret_21"] > -0.95) & (u["trigger_date"] >= "2006")]
    u["stage2_share"] = reg["stage2_share"].reindex(pd.to_datetime(u["trigger_date"])).to_numpy()
    u["x"] = (u["ret_21"] - u["bench_21"]).clip(-0.5, 0.5)
    u["x63"] = (u["ret_63"] - u["bench_63"]).clip(-0.8, 0.8)
    u["year"] = u["trigger_date"].str[:4].astype(int)
    u["period"] = np.where(u["year"] <= SPLIT_YEAR, "train", "test")
    return u


def summary(g: pd.DataFrame) -> pd.Series:
    return pd.Series({"n": len(g), "avg21": g["x"].mean() * 100, "med21": g["x"].median() * 100,
                      "win21": (g["x"] > 0).mean() * 100, "avg63": g["x63"].mean() * 100,
                      "fail": (g["status"] == "Failed").mean() * 100})


def by_quintile(u: pd.DataFrame, col: str) -> pd.DataFrame:
    train = u[u["period"] == "train"][col].dropna()
    if train.nunique() < 5:
        bins = sorted(u[col].dropna().unique())
        key = u[col]
    else:
        edges = np.unique(np.quantile(train, [0, .2, .4, .6, .8, 1]))
        edges[0], edges[-1] = -np.inf, np.inf
        key = pd.cut(u[col], edges)
    t = u.groupby([key, "period"], observed=True).apply(summary, include_groups=False)
    return t.round(1).unstack("period")


def spread(t: pd.DataFrame, period: str) -> float:
    s = t[("avg21", period)].dropna()
    return round(float(s.iloc[-1] - s.iloc[0]), 2) if len(s) > 1 else float("nan")


def main():
    u = load()
    pd.set_option("display.width", 200)
    print(f"Signals after cleaning: {len(u)} (train {sum(u.period == 'train')}, test {sum(u.period == 'test')})")
    print("Excess = return minus Nifty 500 over 21 sessions after the breakout close, clipped at +/-50%.\n")
    rows = []
    for col in FEATURES:
        if col not in u:
            continue
        t = by_quintile(u, col)
        rows.append((col, spread(t, "train"), spread(t, "test")))
        print(f"== {col}\n{t.to_string()}\n")
    print("== Top-minus-bottom quintile, avg 21-session excess (%)")
    print(pd.DataFrame(rows, columns=["feature", "train", "test"]).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
