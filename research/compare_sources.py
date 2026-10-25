"""Phase 2 gate: does the v0.2 backtest hold up on NSE's own, survivorship-free data?

    python research/compare_sources.py reports/yahoo/backtest.json reports/nse/backtest.json

Prints the last-10-year breakout results per grade from both runs, and passes
only if Grade A and B average excess returns differ by at most 0.5 point.
"""

import json
import sys

GATE = 0.5


def main(yahoo_path: str, nse_path: str, window: str = "10") -> int:
    runs = {}
    for name, p in (("Yahoo, listed today", yahoo_path), ("NSE files, incl. delisted", nse_path)):
        w = json.load(open(p))["windows"][window]
        runs[name] = {r["grade"]: r for r in w["track_record"]}
    cols = ["signals", "avg_excess_21_pct", "median_excess_21_pct", "win_pct_21", "failed_pct"]
    print(f"| source | grade | {' | '.join(cols)} |")
    print("|---|---|" + "---|" * len(cols))
    for name, rec in runs.items():
        for g in ("A", "B", "C"):
            r = rec.get(g, {})
            print(f"| {name} | {g} | " + " | ".join(str(r.get(c, "–")) for c in cols) + " |")
    (ya, na) = runs.values()
    ok = True
    for g in ("A", "B"):
        d = (na.get(g, {}).get("avg_excess_21_pct") or 0) - (ya.get(g, {}).get("avg_excess_21_pct") or 0)
        verdict = "pass" if abs(d) <= GATE else "FAIL"
        ok &= abs(d) <= GATE
        print(f"\nGrade {g}: NSE minus Yahoo = {d:+.2f} point(s) of 21-session excess return: {verdict}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
