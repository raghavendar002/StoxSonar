"""Long-history backtest of the published rules. Never touches the live ledger.

    python backtest.py --windows 10 20 30

Downloads all available history for today's NSE universe, replays the engine
day by day, and writes reports/backtest.md with, per look-back window:
  * how many of today's stocks have data and pass the liquidity floor then,
  * breakout results per grade (same measures as the page's track record),
  * Stage 2 vs Stage 4 forward returns against the benchmark, year by year.

Survivorship: only stocks listed today are included. Delisted and merged
companies are missing, so every number here is flattering, and more so the
further back the window goes.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from sonar import config as C
from sonar import data, engine
from sonar.ledger import track_record

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("backtest")


def spliced_benchmark() -> pd.Series:
    """Nifty 500, extended back with Nifty 50 then Sensex by chaining returns."""
    import yfinance as yf
    parts = []
    for t in (C.BENCHMARK, C.BENCHMARK_FALLBACK, "^BSESN"):
        df = yf.download(t, period="max", interval="1d", auto_adjust=True, progress=False)
        if len(df):
            s = df["Close"]
            s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
            s.index = pd.DatetimeIndex(s.index).tz_localize(None)
            parts.append((t, s.dropna()))
            log.info("%s from %s", t, s.index.min().date())
    if not parts:
        raise RuntimeError("no benchmark")
    name, out = parts[0]
    used = [f"{name} from {out.index.min().date()}"]
    for name, s in parts[1:]:
        start = out.index.min()
        earlier = s[s.index < start]
        if earlier.empty or start not in s.index:
            continue
        scaled = earlier * (out.loc[start] / s.loc[start])
        out = pd.concat([scaled, out]).sort_index()
        used.append(f"{name} before {start.date()}")
    out.attrs["sources"] = used
    return out


class StageSink:
    """Aggregates stage forward returns and coverage without keeping every row."""

    def __init__(self):
        self.sums = defaultdict(float)      # (year, stage, h) -> sum of excess return
        self.counts = defaultdict(int)
        self.liquid_by_date = pd.Series(dtype=float)

    def __call__(self, symbol, st, f):
        if st.empty:
            return
        idx = pd.DatetimeIndex(st["date"])
        close, bench = f["Close"], f["bench"]
        for h in (21, 63):
            fwd = (close.shift(-h) / close - 1) - (bench.shift(-h) / bench - 1)
            x = fwd.reindex(idx).to_numpy()
            ok = ~np.isnan(x)
            for (yr, stg), v in pd.Series(x[ok]).groupby(
                    [idx.year[ok], st["stage"].to_numpy()[ok]]).agg(["sum", "count"]).iterrows():
                self.sums[(yr, stg, h)] += v["sum"]
                self.counts[(yr, stg, h)] += int(v["count"])
        self.liquid_by_date = self.liquid_by_date.add(pd.Series(1.0, index=idx), fill_value=0)

    def table(self, since_year: int) -> pd.DataFrame:
        rows = []
        years = sorted({k[0] for k in self.counts if k[0] >= since_year})
        for yr in years:
            r = {"year": yr}
            for stg in (2, 4):
                for h in (21, 63):
                    n = self.counts.get((yr, stg, h), 0)
                    r[f"s{stg}_{h}"] = round(self.sums[(yr, stg, h)] / n * 100, 2) if n else None
            rows.append(r)
        return pd.DataFrame(rows)


def per_year(ev: pd.DataFrame) -> pd.DataFrame:
    d = ev[(ev["direction"] == "up") & ev["grade"].isin(["A", "B"])].dropna(subset=["ret_21"]).copy()
    d["year"] = d["trigger_date"].str[:4].astype(int)
    d["excess"] = d["ret_21"] - d["bench_21"]
    g = d.groupby(["year", "grade"])["excess"]
    out = pd.DataFrame({"signals": g.size(), "avg_excess_21_pct": (g.mean() * 100).round(1),
                        "beat_pct": (g.apply(lambda x: (x > 0).mean()) * 100).round(0)})
    return out.reset_index()


def md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data._\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        lines.append("| " + " | ".join("–" if (v is None or v != v) else str(v) for v in r) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--windows", type=int, nargs="+", default=[10, 20, 30])
    ap.add_argument("--out", type=Path, default=ROOT / "reports")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--universe-csv", type=Path, default=ROOT / "universe" / "nse_sec_list.csv")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    tickers = data.load_universe(a.universe_csv)
    if a.limit:
        tickers = tickers[:a.limit]
    bench = spliced_benchmark()
    prices = data.fetch_prices(tickers, period="max")
    as_of = bench.index.max()
    first_bar = pd.Series({s: df.index.min() for s, df in prices.items() if len(df)})
    log.info("%d of %d tickers have data; earliest %s", len(first_bar), len(tickers), first_bar.min().date())

    sink = StageSink()
    res = engine.run_market(prices, bench, state_sink=sink)
    ev = pd.DataFrame([e.to_dict() for e in res.events])
    ev["source"] = "replay"
    a.out.mkdir(parents=True, exist_ok=True)
    ev.to_csv(a.out / "backtest_signals.csv.gz", index=False)
    res.regime.to_csv(a.out / "backtest_regime.csv.gz")

    md = [f"# StoxSonar backtest, rules v{C.ENGINE_VERSION}", "",
          f"Data to {as_of.date()}. Benchmark: {'; '.join(bench.attrs.get('sources', []))}. "
          f"{len(first_bar)} of {len(tickers)} stocks listed today had price data; the earliest starts "
          f"{first_bar.min().date()}.", "",
          "**Survivorship warning:** only companies listed today are included. Companies that were "
          "delisted, went bust or merged are missing, so these results are better than reality, "
          "and the gap grows with the window.", "",
          "Excess = stock return minus benchmark return over the same 21 sessions after the signal. "
          "R = 21-session move divided by the distance to the failure level.", ""]
    summary = {"as_of": str(as_of.date()), "tickers": len(tickers), "with_data": len(first_bar),
               "windows": {}}
    liquid = sink.liquid_by_date.sort_index()
    for w in sorted(a.windows):
        start = as_of - pd.DateOffset(years=w)
        has_data = int((first_bar <= start).sum())
        near = liquid[liquid.index >= start]
        liquid_then = int(near.iloc[0]) if len(near) and liquid.index.min() <= start else 0
        sub = ev[ev["trigger_date"] >= str(start.date())] if len(ev) else ev
        signals_start = sub["trigger_date"].min() if len(sub) else "none"
        yearly = sink.table(start.year)
        both = yearly.dropna(subset=["s2_21", "s4_21"])
        s2_wins = int((both["s2_21"] > both["s4_21"]).sum())
        tr = track_record(sub, ["replay"])
        md += [f"## Last {w} years (from {start.date()})", "",
               f"Coverage: {has_data} of today's {len(first_bar)} stocks have prices back to {start.date()}; "
               f"{liquid_then} of them were liquid (Rs 1 crore/day) and labelled at the start of the "
               f"window, against {int(liquid.iloc[-1]) if len(liquid) else 0} today. "
               f"First signal in this window: {signals_start}.", "",
               "### Breakouts by grade", "", md_table(tr),
               "### Stage 2 vs Stage 4, average excess return per year (%)", "",
               "s2_21 = Stage 2 stocks, next 21 sessions; s4_63 = Stage 4, next 63 sessions. "
               "Stage 2 should beat Stage 4 in most years, not just on average.", "",
               f"Stage 2 beat Stage 4 over 21 sessions in {s2_wins} of {len(both)} years.", "",
               md_table(yearly), ""]
        summary["windows"][w] = {"start": str(start.date()), "has_data": has_data,
                                 "liquid_at_start": liquid_then, "first_signal": signals_start,
                                 "stage2_beat_stage4_years": [s2_wins, len(both)],
                                 "track_record": tr.to_dict("records")}
    md += ["## Grade A and B breakouts, year by year", "", md_table(per_year(ev))]
    (a.out / "backtest.md").write_text("\n".join(md), encoding="utf-8")
    (a.out / "backtest.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log.info("wrote %s", a.out / "backtest.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
