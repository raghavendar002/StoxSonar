"""Phase 7: how much money to put to work, and where idle money waits.

    python research/sizing_study.py reports/nse_full/backtest_signals.csv.gz cache/nse_panel.pkl > reports/sizing_study.md

PR 5 found the account about 90% in cash: at 0.5% risk and stops about 12%
away, each stock gets about 4% of the money. This varies three things on v0.2's
entries, each run from a fresh Rs 1 lakh with full costs:
  exit     v02 (today), sma50, chandelier (the two best in PR 6)
  sizing   risk 0.5%, 0.75% or 1% of equity to the stop, or a fixed 10% of
           equity per stock (25% cap per stock throughout)
  idle     cash (earns nothing), liquid (a liquid fund at a flat 5.5% a year),
           etf (always in the index), etf_trend (in the index only while it
           closes above its 200-day average)
48 variants, each on 2007-2018 and on 2019 on. Leverage is not tested: it only
matters once the account is fully invested, which no variant here is on average.

Decision rule, fixed before the first run:
  1. The candidate is the variant with the highest Sharpe on 2007-2018.
  2. It is recommended for paper trading only if, on 2019 on, it meets the
     plan's whole bar: CAGR at least 5 points over the Nifty 500, maximum
     drawdown under 25%, beating the index in at least 5 of 7 full years, and a
     deflated Sharpe of its monthly return over the index of at least 0.95,
     counting all 48 variants as trials.
  3. Every variant is listed with its CAGR and drawdown in both periods, so
     the trade between return and risk is visible.
The index is a price index without dividends, which understates both the
benchmark and the ETF variants by about 1-1.5 points a year.
"""

from __future__ import annotations

import itertools
import json
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
from backtest import spliced_benchmark  # noqa: E402
from exit_study import md, monthly_excess, report_data  # noqa: E402
from retune import deflated_sharpe  # noqa: E402
from sonar import exits, nse, portfolio  # noqa: E402

PERIODS = {"2007-2018": ("2007-01-01", "2018-12-31"), "2019 on": ("2019-01-01", None)}
EXITS = ("v02", "sma50", "chandelier")
SIZING = {"risk 0.5%": dict(risk_pct=0.005), "risk 0.75%": dict(risk_pct=0.0075),
          "risk 1%": dict(risk_pct=0.01), "fixed 10%": dict(fixed_frac=0.10)}
VARIANTS = list(itertools.product(EXITS, SIZING, portfolio.IDLE))
_G: dict = {}


def _run(job):
    (ex, size, idle), period = job
    start, end = PERIODS[period]
    r = portfolio.simulate(_G["sig"], _G["prices"], _G["bench"], exit_rule=exits.RULES[ex],
                           start=start, end=end, idle=idle, **SIZING[size])
    m = portfolio.metrics(r["equity"]["equity"], r["bench"], r["trades"])
    y = portfolio.yearly(r["equity"]["equity"], r["bench"])
    full = y[y.index < pd.Timestamp.today().year]
    inv = (1 - r["equity"]["cash"] / r["equity"]["equity"]).mean() * 100
    row = {"variant": f"{ex} | {size} | {idle}", "exit": ex, "sizing": size, "idle": idle, "period": period,
           **{k: m.get(k) for k in ("cagr_pct", "bench_cagr_pct", "max_drawdown_pct", "bench_max_drawdown_pct",
                                    "sharpe", "final_rs", "trades", "win_pct", "profit_factor")},
           "in_stocks_pct": round(float(inv), 1), "etf_costs_rs": r["etf_costs"],
           "years_beating": [int((full["excess"] > 0).sum()), int(len(full))]}
    return job, row, monthly_excess(r), report_data(r)


def main(signals_path: str, cache_path: str) -> int:
    _G["sig"] = pd.read_csv(signals_path)
    with open(cache_path, "rb") as fh:              # written by backtest.py on this runner
        _G["prices"] = nse.to_price_dict(pickle.load(fh))
    _G["bench"] = spliced_benchmark()
    jobs = [(v, p) for v in VARIANTS for p in PERIODS]
    with ProcessPoolExecutor(max_workers=os.cpu_count() or 2) as pool:   # workers inherit _G by fork
        results = list(pool.map(_run, jobs))
    rows = [r for _, r, _, _ in results]
    ex = {job[0]: x for job, _, x, _ in results if job[1] == "2019 on"}
    data = {f"{' | '.join(job[0])}|{job[1]}": d for job, _, _, d in results}
    tab = pd.DataFrame(rows)
    train = tab[tab["period"] == "2007-2018"].set_index("variant")
    test = tab[tab["period"] == "2019 on"].set_index("variant")
    srs = [float(s.mean() / s.std(ddof=1)) for s in ex.values() if len(s) > 2 and s.std(ddof=1) > 0]
    dsr = {" | ".join(v): round(deflated_sharpe(s.to_numpy(), srs), 3) for v, s in ex.items()}
    test["deflated_sharpe"] = pd.Series(dsr)
    test["over_index_pts"] = (test["cagr_pct"] - test["bench_cagr_pct"]).round(2)
    test["passes_bar"] = [bool(r.over_index_pts >= 5 and r.max_drawdown_pct > -25 and r.years_beating[0] >= 5
                               and r.deflated_sharpe >= 0.95) for r in test.itertuples()]
    cand = train["sharpe"].astype(float).idxmax()
    c = test.loc[cand]

    both = pd.DataFrame({"variant": test.index,
                         "cagr 07-18": train.loc[test.index, "cagr_pct"].values,
                         "dd 07-18": train.loc[test.index, "max_drawdown_pct"].values,
                         "sharpe 07-18": train.loc[test.index, "sharpe"].values,
                         "cagr 19-on": test["cagr_pct"].values, "dd 19-on": test["max_drawdown_pct"].values,
                         "sharpe 19-on": test["sharpe"].values, "over index": test["over_index_pts"].values,
                         "years beating": [f"{a} of {b}" for a, b in test["years_beating"]],
                         "in stocks %": test["in_stocks_pct"].values, "dsr": test["deflated_sharpe"].values,
                         "passes": test["passes_bar"].values}).sort_values("sharpe 07-18", ascending=False)
    b_tr, b_te = train.iloc[0], test.iloc[0]
    lines = ["# Phase 7: sizing and idle cash on v0.2's entries", "",
             "Fresh Rs 1 lakh per run, full costs, 25% cap per stock. Benchmark and ETF: Nifty 500 price index "
             f"(no dividends). Nifty 500 itself: {b_tr['bench_cagr_pct']}% a year with a {b_tr['bench_max_drawdown_pct']}% "
             f"worst fall in 2007-2018; {b_te['bench_cagr_pct']}% and {b_te['bench_max_drawdown_pct']}% from 2019 on.", "",
             "## All variants, best 2007-2018 Sharpe first", "", md(both), "",
             "## Decision (rule fixed before the run)", "",
             f"- Best Sharpe on 2007-2018: **{cand}** ({train.loc[cand, 'sharpe']}).",
             f"- On 2019 on: CAGR {c['cagr_pct']}% vs the index {c['bench_cagr_pct']}% ({c['over_index_pts']:+} points); "
             f"max drawdown {c['max_drawdown_pct']}%; beat the index in {c['years_beating'][0]} of {c['years_beating'][1]} "
             f"full years; deflated Sharpe {c['deflated_sharpe']}.",
             f"- Verdict: **{'recommend ' + cand + ' for paper trading' if c['passes_bar'] else 'no variant earns a recommendation'}**.",
             f"- Variants passing the whole bar on 2019 on: {int(test['passes_bar'].sum())} of {len(test)}.", ""]
    print("\n".join(lines))
    Path("reports").mkdir(exist_ok=True)
    json.dump({"table": rows, "candidate": cand, "recommend": bool(c["passes_bar"]), "deflated_sharpe": dsr},
              open("reports/sizing_study.json", "w"), indent=1, default=str)
    json.dump(data, open("reports/sizing_study_data.json", "w"), default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
