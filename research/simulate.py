"""Phase 5: what would a Rs 1 lakh account have made trading v0.2 exactly as the app suggests?

    python research/simulate.py reports/nse_full/backtest_signals.csv.gz cache/nse_panel.pkl > reports/simulate.md

Reads the signals written by `backtest.py --source nse` and the NSE price cache
it built, replays one account day by day (sonar/portfolio.py), and reports the
whole period and the 2019-on years separately, each from a fresh Rs 1 lakh.
Position caps of 5 and 8 are shown beside "no cap" for information only; the
plan's default is no cap beyond cash and the 25% per-stock limit.

The benchmark is the Nifty 500 price index: it leaves out dividends, worth
roughly 1-1.5% a year, so the strategy's lead over it is overstated by that much.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backtest import spliced_benchmark  # noqa: E402
from sonar import config as C, nse, portfolio  # noqa: E402

PERIODS = [("2007-01-01", "All years"), ("2019-01-01", "2019 on (unseen by v0.2's fit)")]
CAPS = [None, 8, 5]


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        rows.append("| " + " | ".join("–" if v is None or v != v else str(v) for v in r) + " |")
    return "\n".join(rows) + "\n"


def main(signals_path: str, cache_path: str, out_dir: str = "reports/sim") -> int:
    sig = pd.read_csv(signals_path)
    with open(cache_path, "rb") as fh:          # written by backtest.py on this runner
        prices = nse.to_price_dict(pickle.load(fh))
    bench = spliced_benchmark()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"# Phase 5: a Rs {C.CAPITAL_RS:,} account trading v{C.ENGINE_VERSION} as suggested", "",
             "Buys: Grade A or B breakouts in a Healthy market, sized to risk "
             f"{C.RISK_PCT * 100:.1f}% of equity, at the next open unless it gaps past the plan's ceiling. "
             f"Exits: the {C.STOP_ATR}-ATR stop (filled at the open on a gap through it) or the close "
             f"{C.HOLD_SESSIONS} sessions after the signal. Costs: STT, exchange and SEBI fees, stamp duty, "
             "GST, DP charge, and 0.05-0.5% slippage each way by liquidity. "
             "Benchmark: Nifty 500 price index (no dividends, so about 1-1.5 points a year flattering to us).", ""]
    rows, keep = [], {}
    for start, label in PERIODS:
        for cap in CAPS:
            r = portfolio.simulate(sig, prices, bench, max_positions=cap, start=start)
            m = portfolio.metrics(r["equity"]["equity"], r["bench"], r["trades"])
            rows.append({"period": label, "max positions": cap or "no cap", **m})
            if cap is None:
                keep[label] = r
    lines += ["## Headline", "", md(pd.DataFrame(rows)), ""]
    for label, r in keep.items():
        eq, tr = r["equity"], r["trades"]
        tag = "all" if label.startswith("All") else "2019"
        eq.to_csv(out / f"equity_{tag}.csv")
        tr.to_csv(out / f"trades_{tag}.csv", index=False)
        lines += [f"## {label}: year by year (%)", "", md(portfolio.yearly(eq["equity"], r["bench"]).reset_index()
                                                       .rename(columns={"index": "year"})), ""]
        if len(tr):
            why = tr.groupby("reason").agg(trades=("pnl", "size"), avg_ret_pct=("ret", lambda x: round(x.mean() * 100, 2)),
                                           total_pnl_rs=("pnl", lambda x: round(x.sum())))
            lines += [f"### {label}: how trades ended", "", md(why.reset_index()), "",
                      f"Average invested: {(1 - eq['cash'] / eq['equity']).mean() * 100:.0f}% of the account; "
                      f"average open positions {eq['positions'].mean():.1f}.", ""]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
