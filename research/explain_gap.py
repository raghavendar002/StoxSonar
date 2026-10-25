"""Where does the NSE-vs-Yahoo gap in Grade A and B come from?

    python research/explain_gap.py reports/yahoo/backtest_signals.csv.gz reports/nse/backtest_signals.csv.gz \
        universe/nse_sec_list.csv

Splits the last 10 years of up breakouts into:
  both       the same stock and day signalled in both sources (data agreement)
  nse_gone   NSE-only, on a stock Yahoo does not list today (delisted, merged or renamed)
  nse_other  NSE-only, on a stock Yahoo has (a price difference moved the signal)
  yahoo_only Yahoo-only signals
If the gap is survivorship, it sits in nse_gone and `both` agrees.
"""

import sys

import pandas as pd

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from sonar import data  # noqa: E402


def load(p: str) -> pd.DataFrame:
    d = pd.read_csv(p)
    start = str((pd.Timestamp(d["trigger_date"].max()) - pd.DateOffset(years=10)).date())
    d = d[(d["direction"] == "up") & (d["trigger_date"] >= start) & d["grade"].isin(["A", "B"])]
    d = d.dropna(subset=["ret_21"]).copy()
    d["excess"] = (d["ret_21"] - d["bench_21"]) * 100
    return d[["symbol", "trigger_date", "grade", "ret_21", "excess"] +
             [c for c in ("entry", "fail_level") if c in d.columns]]


def outside(d: pd.DataFrame, keys: pd.MultiIndex) -> pd.DataFrame:
    return d[~pd.MultiIndex.from_frame(d[["symbol", "trigger_date"]]).isin(keys)]


def row(name, g, x):
    s = x["excess"]
    return (f"| {g} | {name} | {len(s)} | {s.mean():.2f} | {s.median():.2f} | "
            f"{(s > 0).mean() * 100:.0f} |" if len(s) else f"| {g} | {name} | 0 | – | – | – |")


def main(yahoo_path: str, nse_path: str, universe_csv: str) -> int:
    y, n = load(yahoo_path), load(nse_path)
    listed = set(data.load_universe(universe_csv))
    print("| grade | group | signals | avg_excess_21_pct | median | beat_pct |\n|---|---|---|---|---|---|")
    for g in ("A", "B"):
        yg, ng = y[y["grade"] == g], n[n["grade"] == g]
        both = ng.merge(yg, on=["symbol", "trigger_date"], suffixes=("", "_y"))
        key = pd.MultiIndex.from_frame(both[["symbol", "trigger_date"]])
        nse_only = outside(ng, key)
        gone = nse_only[~nse_only["symbol"].isin(listed)]
        print(row("both, NSE prices", g, both))
        print(row("both, Yahoo prices", g, both.assign(excess=both["excess_y"])))
        print(row("nse_gone", g, gone))
        print(row("nse_other", g, nse_only.drop(gone.index)))
        print(row("yahoo_only", g, outside(yg, key)))
        if len(both):
            diff = (both["ret_21"] - both["ret_21_y"]).abs() * 100
            print(f"| {g} | both: median abs return gap | {len(both)} | {diff.median():.2f} | "
                  f"over 1 pt: {(diff > 1).mean() * 100:.0f}% | |")
    # The worst disagreements on shared signals, to check by hand against NSE's own files
    both = n.merge(y, on=["symbol", "trigger_date"], suffixes=("_nse", "_yahoo"))
    both["gap_pt"] = ((both["ret_21_nse"] - both["ret_21_yahoo"]) * 100).round(1)
    worst = both.reindex(both["gap_pt"].abs().sort_values(ascending=False).index).head(25)
    cols = ["symbol", "trigger_date", "grade_nse", "grade_yahoo", "ret_21_nse", "ret_21_yahoo", "gap_pt"]
    cols += [c for c in ("entry_nse", "entry_yahoo") if c in worst.columns]
    worst[["symbol", "trigger_date"]].to_csv("reports/phase2_worst.csv", index=False)
    print("\n### Largest 21-session return gaps on the same signal\n")
    print("| " + " | ".join(cols) + " |\n|" + "---|" * len(cols))
    for r in worst[cols].itertuples(index=False):
        print("| " + " | ".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in r) + " |")
    print(f"\nShare of shared signals with NSE lower by >1 pt: {(both['gap_pt'] < -1).mean() * 100:.0f}%, "
          f"higher by >1 pt: {(both['gap_pt'] > 1).mean() * 100:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
