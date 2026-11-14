"""Phase 6: does a different exit turn v0.2's entries into a better account?

    python research/exit_study.py reports/nse_full/backtest_signals.csv.gz cache/nse_panel.pkl > reports/exit_study.md

Same entries, sizes and initial stop for every rule (sonar/exits.py); only the
way out differs. Each rule runs a fresh Rs 1 lakh account on 2007-2018 and,
separately, on 2019 on. No position cap beyond cash and the 25% per-stock limit.

Decision rule, fixed before the first run:
  1. The candidate is the rule with the highest Sharpe on 2007-2018.
  2. It is recommended over v0.2's exit only if, on 2019 on, its CAGR is higher,
     its maximum drawdown is no more than 5 points deeper, and the deflated
     Sharpe of its monthly return over the Nifty 500 is at least 0.95, counting
     all six rules as trials.
  3. Separately, every rule is checked against the plan's bar on 2019 on: CAGR
     at least 5 points over the index, drawdown under 25%, beating the index in
     at least 5 of 7 full years.
Nothing here changes the live app; adopting an exit is its own PR.
"""

from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
from backtest import spliced_benchmark  # noqa: E402
from retune import deflated_sharpe  # noqa: E402
from sonar import exits, nse, portfolio  # noqa: E402

TRAIN = ("2007-01-01", "2018-12-31")
TEST = ("2019-01-01", None)


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        rows.append("| " + " | ".join("–" if v is None or v != v else str(v) for v in r) + " |")
    return "\n".join(rows) + "\n"


def monthly_excess(r: dict) -> pd.Series:
    m = pd.DataFrame({"s": r["equity"]["equity"], "b": r["bench"]}).resample("ME").last().pct_change().dropna()
    return m["s"] - m["b"]


def report_data(r: dict, trades_cols=("charges", "slippage")) -> dict:
    """What the HTML report draws: weekly equity, drawdown and exposure, years, costs."""
    eq, tr = r["equity"], r["trades"]
    inv = 1 - eq["cash"] / eq["equity"]
    wk = pd.DataFrame({"equity": eq["equity"], "bench": r["bench"], "dd": eq["equity"] / eq["equity"].cummax() - 1,
                       "bdd": r["bench"] / r["bench"].cummax() - 1, "invested": inv, "positions": eq["positions"]})
    wk = wk.resample("W-FRI").agg({"equity": "last", "bench": "last", "dd": "min", "bdd": "min",
                                   "invested": "mean", "positions": "mean"}).dropna()
    y = portfolio.yearly(eq["equity"], r["bench"])
    y["invested_pct"] = (inv.groupby(inv.index.year).mean() * 100).round(1)
    y["max_positions"] = eq["positions"].groupby(eq.index.year).max()
    out = {"weekly": {"date": [d.strftime("%Y-%m-%d") for d in wk.index],
                      **{c: [round(float(v), 4) for v in wk[c]] for c in wk.columns}},
           "yearly": y.reset_index().rename(columns={"date": "year", "index": "year"}).to_dict("records"),
           "avg_invested_pct": round(float(inv.mean() * 100), 1), "avg_positions": round(float(eq["positions"].mean()), 2),
           "max_positions": int(eq["positions"].max())}
    if len(tr):
        tr = tr.assign(year=pd.to_datetime(tr["exit_date"]).dt.year)
        out["costs_rs"] = {c: round(float(tr[c].sum())) for c in trades_cols if c in tr}
        out["costs_by_year"] = tr.groupby("year")[[c for c in trades_cols if c in tr]].sum().round().reset_index().to_dict("records")
        out["by_reason"] = tr.groupby("reason").agg(trades=("pnl", "size"), avg_ret_pct=("ret", lambda x: round(x.mean() * 100, 2)),
                                                    total_pnl_rs=("pnl", lambda x: round(x.sum()))).reset_index().to_dict("records")
        out["ret_hist"] = [int(n) for n in pd.cut(tr["ret"].clip(-0.4, 1.0), bins=[i / 20 for i in range(-8, 21)],
                                                  include_lowest=True).value_counts(sort=False)]
        out["best_trades"] = tr.nlargest(5, "pnl")[["symbol", "entry_date", "exit_date", "ret", "pnl"]].astype(str).to_dict("records")
        out["worst_trades"] = tr.nsmallest(5, "pnl")[["symbol", "entry_date", "exit_date", "ret", "pnl", "reason"]].astype(str).to_dict("records")
    return out


def main(signals_path: str, cache_path: str) -> int:
    sig = pd.read_csv(signals_path)
    with open(cache_path, "rb") as fh:          # written by backtest.py on this runner
        prices = nse.to_price_dict(pickle.load(fh))
    bench = spliced_benchmark()
    runs, rows = {}, []
    for name, rule in exits.RULES.items():
        for label, (start, end) in (("2007-2018", TRAIN), ("2019 on", TEST)):
            r = portfolio.simulate(sig, prices, bench, exit_rule=rule, start=start, end=end)
            runs[(name, label)] = r
            m = portfolio.metrics(r["equity"]["equity"], r["bench"], r["trades"])
            inv = (1 - r["equity"]["cash"] / r["equity"]["equity"]).mean() * 100
            rows.append({"exit": name, "period": label, **{k: m.get(k) for k in (
                "cagr_pct", "bench_cagr_pct", "max_drawdown_pct", "bench_max_drawdown_pct", "sharpe", "final_rs",
                "trades", "win_pct", "avg_win_pct", "avg_loss_pct", "profit_factor", "avg_sessions")},
                "invested_pct": round(float(inv), 1), "max_positions": int(r["equity"]["positions"].max())})
    tab = pd.DataFrame(rows)
    train = tab[tab["period"] == "2007-2018"].set_index("exit")
    test = tab[tab["period"] == "2019 on"].set_index("exit")
    cand = train["sharpe"].astype(float).idxmax()
    ex = {n: monthly_excess(runs[(n, "2019 on")]) for n in exits.RULES}
    srs = [float(s.mean() / s.std(ddof=1)) for s in ex.values() if len(s) > 2 and s.std(ddof=1) > 0]
    dsr = {n: round(deflated_sharpe(s.to_numpy(), srs), 3) for n, s in ex.items()}
    years = {}
    for n in exits.RULES:
        r = runs[(n, "2019 on")]
        y = portfolio.yearly(r["equity"]["equity"], r["bench"])
        full = y[y.index < pd.Timestamp.today().year]
        years[n] = (int((full["excess"] > 0).sum()), int(len(full)), y)

    base, c = test.loc["v02"], test.loc[cand]
    beats = cand != "v02" and c["cagr_pct"] > base["cagr_pct"] and \
        c["max_drawdown_pct"] >= base["max_drawdown_pct"] - 5 and dsr[cand] >= 0.95
    lines = ["# Phase 6: exit study on v0.2's entries", "",
             "Same entries, sizes and initial stop for all six exits; a fresh Rs 1 lakh per run; full costs. "
             "Benchmark: Nifty 500 price index (no dividends).", "",
             "## Results", "", md(tab), "",
             "## Decision (rule fixed before the run)", "",
             f"- Best Sharpe on 2007-2018: **{cand}** ({train.loc[cand, 'sharpe']}).",
             f"- On 2019 on: CAGR {c['cagr_pct']}% vs v0.2 exit {base['cagr_pct']}%; max drawdown "
             f"{c['max_drawdown_pct']}% vs {base['max_drawdown_pct']}%; deflated Sharpe {dsr[cand]}.",
             f"- Verdict: **{'recommend ' + cand + ' over the v0.2 exit' if beats else 'keep the v0.2 exit'}**.", "",
             "## Against the plan's bar, 2019 on", "",
             md(pd.DataFrame([{"exit": n, "cagr_pct": test.loc[n, "cagr_pct"],
                               "over_index_pts": round(test.loc[n, "cagr_pct"] - test.loc[n, "bench_cagr_pct"], 2),
                               "max_drawdown_pct": test.loc[n, "max_drawdown_pct"],
                               "years_beating_index": f"{years[n][0]} of {years[n][1]}",
                               "deflated_sharpe": dsr[n],
                               "passes_bar": bool(test.loc[n, "cagr_pct"] - test.loc[n, "bench_cagr_pct"] >= 5
                                                  and test.loc[n, "max_drawdown_pct"] > -25
                                                  and years[n][0] >= 5 and dsr[n] >= 0.95)}
                              for n in exits.RULES])), "",
             f"## {cand}: year by year, 2019 on (%)", "", md(years[cand][2].reset_index().rename(columns={"date": "year"})), ""]
    tr = runs[(cand, "2019 on")]["trades"]
    if len(tr):
        why = tr.groupby("reason").agg(trades=("pnl", "size"), avg_ret_pct=("ret", lambda x: round(x.mean() * 100, 2)),
                                       total_pnl_rs=("pnl", lambda x: round(x.sum())))
        lines += [f"### {cand}: how trades ended, 2019 on", "", md(why.reset_index()), ""]
    print("\n".join(lines))
    Path("reports").mkdir(exist_ok=True)
    json.dump({"table": rows, "candidate": cand, "recommend": bool(beats), "deflated_sharpe": dsr,
               "years_beating_index": {n: years[n][:2] for n in exits.RULES}},
              open("reports/exit_study.json", "w"), indent=1, default=str)
    json.dump({f"{n}|{p}": report_data(r) for (n, p), r in runs.items()},
              open("reports/exit_study_data.json", "w"), default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
