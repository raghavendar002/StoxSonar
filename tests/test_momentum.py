import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import momentum as M  # noqa: E402


def _prices(n_stocks=40, n_days=700, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n_days)
    out = {}
    for k in range(n_stocks):
        drift = (k - n_stocks / 2) * 0.00008          # higher k trends up harder
        c = 100 * np.exp(np.cumsum(drift + rng.normal(0, 0.012, n_days)))
        o = c * (1 + rng.normal(0, 0.002, n_days))
        out[f"S{k:02d}.NS"] = pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.005,
                                            "Low": np.minimum(o, c) * 0.995, "Close": c,
                                            "Volume": 2e6}, idx)
    return out


def _setup(**kw):
    w = M.wide(_prices(**kw))
    days = w["Close"].index
    pos = {d: i for i, d in enumerate(days)}
    rk = M.ranks(w, pd.DatetimeIndex([days[pos[d] - 1] for d in M.month_starts(days) if pos[d] > 0]))
    return w, rk, days


def test_ranks_favour_the_strong_trends():
    w, rk, days = _setup()
    last = rk[max(rk)]
    assert len(last) == 40
    top = last.nsmallest(10).index
    assert np.mean([int(s[1:3]) for s in top]) > 25


def test_holds_at_most_n_and_charges_costs():
    w, rk, days = _setup()
    bench = w["Close"].mean(axis=1)
    br = M.brake_series(bench, None, days)
    br["under"] = False
    r = M.simulate(w, rk, br, M.Variant(10, "none"), str(days[300].date()), None)
    eq = r["equity"]
    assert eq["positions"].max() <= 10
    assert eq["positions"].iloc[-1] == 10
    assert (eq["cash"] >= -1e-6).all()
    first = int(np.argmax(eq["positions"].to_numpy() > 0))
    assert first > 0 and eq["positions"].iloc[:first].eq(0).all()   # buys wait for a month start
    paid = eq["cash"].iloc[first - 1] - eq["cash"].iloc[first]
    assert paid > 0


def test_exit_brake_goes_to_cash_and_gate_blocks_buys():
    w, rk, days = _setup()
    bench = w["Close"].mean(axis=1)
    br = M.brake_series(bench, None, days)
    br["under"] = False
    br.loc[days[450]:, "under"] = True
    start = str(days[300].date())
    ex = M.simulate(w, rk, br, M.Variant(10, "exit"), start, None)["equity"]
    assert ex["positions"].iloc[-1] == 0
    assert ex["equity"].iloc[-1] > ex["cash"].iloc[-1] - 1e-6
    gate = M.simulate(w, rk, br, M.Variant(10, "gate"), start, None)["equity"]
    assert gate["positions"].iloc[-1] <= 10
    # cash grows at the liquid rate while flat
    tail = ex.loc[days[470]:, "equity"]
    yrs = (tail.index[-1] - tail.index[0]).days / 365.25
    assert abs((tail.iloc[-1] / tail.iloc[0]) ** (1 / yrs) - 1 - M.LIQUID_RATE) < 0.002


def test_risk_sizing_leaves_cash_idle():
    w, rk, days = _setup()
    bench = w["Close"].mean(axis=1)
    br = M.brake_series(bench, None, days)
    br["under"] = False
    full = M.simulate(w, rk, br, M.Variant(10, "none"), str(days[300].date()), None)["equity"]
    risk = M.simulate(w, rk, br, M.Variant(10, "none", risk_pct=0.002), str(days[300].date()), None)["equity"]
    assert (risk["cash"] / risk["equity"]).mean() > (full["cash"] / full["equity"]).mean()


def test_run_writes_a_report(tmp_path, monkeypatch):
    w, rk, days = _setup(n_days=900)
    bench = w["Close"].mean(axis=1)
    monkeypatch.setattr(M, "FIT", (str(days[260].date()), str(days[600].date())))
    monkeypatch.setattr(M, "CHECK_FROM", str(days[601].date()))
    text = M.run(w, bench, None, tmp_path)
    assert "Verdict" in text and (tmp_path / "check_2019_on.csv").exists()


def test_vol_target_holds_less_when_the_basket_is_wild():
    w, rk, days = _setup()
    bench = w["Close"].mean(axis=1)
    br = M.brake_series(bench, None, days)
    br["under"] = False
    start = str(days[300].date())
    full = M.simulate(w, rk, br, M.Variant(10, "exit"), start, None)["equity"]
    vt = M.simulate(w, rk, br, M.Variant(10, "exit", vt=0.02), start, None)["equity"]
    assert (vt["cash"] / vt["equity"]).mean() > (full["cash"] / full["equity"]).mean() + 0.2


def test_vt_study_only_chooses_among_its_candidates(tmp_path, monkeypatch):
    w, rk, days = _setup(n_days=900)
    bench = w["Close"].mean(axis=1)
    monkeypatch.setattr(M, "FIT", (str(days[260].date()), str(days[600].date())))
    monkeypatch.setattr(M, "CHECK_FROM", str(days[601].date()))
    s = M.vt_study()
    assert len(s["variants"]) == 17
    text = M.run(w, bench, None, tmp_path, **s)
    chosen = text.split("**")[3]
    assert chosen in [c.name for c in s["candidates"]]
