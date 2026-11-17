import numpy as np
import pandas as pd

from sonar import momentum as M


def _prices(n_stocks=40, n_days=400, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n_days)
    out = {}
    for k in range(n_stocks):
        c = 100 * np.exp(np.cumsum((k - 20) * 0.0001 + rng.normal(0, 0.012, n_days)))
        o = c * (1 + rng.normal(0, 0.002, n_days))
        out[f"S{k:02d}.NS"] = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.005,
                                            "Low": np.minimum(o, c) * 0.995, "Close": c,
                                            "Volume": 2e6}, idx)
    return out, idx


def test_book_buys_next_open_then_brake_sells_all():
    prices, idx = _prices()
    up = pd.Series(np.linspace(100, 200, len(idx)), idx)
    b = M.empty_book()
    d0, d1 = str(idx[300].date()), str(idx[301].date())
    b = M.step(b, prices, up, d0)
    assert b["pending"] and len(b["pending"]["buys"]) == M.BOOK_N and not b["holdings"]
    b = M.step(b, prices, up, d0)                       # same day twice: no change
    assert not b["holdings"]
    b = M.step(b, prices, up, d1)
    assert len(b["holdings"]) == M.BOOK_N
    h = next(iter(b["holdings"].values()))
    sym = next(iter(b["holdings"]))
    assert h["entry"] > prices[sym]["Open"].iloc[301]   # paid slippage over the open
    assert b["cash"] >= 0 and b["pending"] is None       # same month: no new rebalance
    down = up.copy(); down.iloc[302:] = 50               # index falls under its 200-day line
    b = M.step(b, prices, down, str(idx[302].date()))
    assert set(b["pending"]["sells"]) == set(b["holdings"])
    b = M.step(b, prices, down, str(idx[303].date()))
    assert not b["holdings"] and all(t["reason"] == "brake" for t in b["trades"])
    s = M.summary(b)
    assert s["brake_on"] and s["equity"] == b["equity"][-1]["equity"]


def test_book_rebalances_once_a_month():
    prices, idx = _prices()
    up = pd.Series(np.linspace(100, 200, len(idx)), idx)
    b = M.empty_book()
    months = set()
    for i in range(300, 360):
        b = M.step(b, prices, up, str(idx[i].date()))
        if b["pending"] and b["pending"]["buys"]:
            months.add(b["pending"]["day"][:7])
    assert len(b["holdings"]) <= M.BOOK_N
    assert b["rebalanced_month"] == str(idx[359].date())[:7]
    assert min(months) == str(idx[300].date())[:7]
