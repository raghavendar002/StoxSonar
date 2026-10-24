"""Side-by-side daily closes, NSE (adjusted and raw) vs Yahoo, for the worst gap signals.

    python research/inspect_gaps.py reports/phase2_worst.csv cache/nse_panel.pkl 6
"""

import pickle
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sonar import nse  # noqa: E402


def main(worst_csv: str, cache: str, k: str = "6") -> int:
    worst = pd.read_csv(worst_csv).head(int(k))
    with open(cache, "rb") as fh:          # written by backtest.py on the same runner
        panel = pickle.load(fh)
    for r in worst.itertuples(index=False):
        sym = r.symbol.removesuffix(".NS")
        t = pd.Timestamp(r.trigger_date)
        lo, hi = t - pd.Timedelta(days=5), t + pd.Timedelta(days=40)
        raw = panel[panel["symbol"] == sym]
        adj = nse.adjust(raw).set_index("date")["close"].rename("nse_adj")
        raw = raw.set_index("date")[["close", "prev_close"]].rename(columns={"close": "nse_raw"})
        y = yf.download(r.symbol, start=lo, end=hi, auto_adjust=True, progress=False)["Close"]
        y = (y.iloc[:, 0] if isinstance(y, pd.DataFrame) else y).rename("yahoo")
        y.index = pd.DatetimeIndex(y.index).tz_localize(None)
        df = pd.concat([raw, adj, y], axis=1).sort_index().loc[lo:hi]
        df["ratio"] = (df["nse_adj"] / df["yahoo"]).round(4)
        print(f"\n### {r.symbol}, signal {r.trigger_date}\n")
        print(df.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
