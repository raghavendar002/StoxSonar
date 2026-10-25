import numpy as np
import pandas as pd
import pytest

from sonar import exits, portfolio


def _frame(closes, start="2025-01-01"):
    c = np.asarray(closes, float)
    o = np.r_[c[0], c[:-1]]
    idx = pd.bdate_range(start, periods=len(c))
    return pd.DataFrame({"Open": o, "High": np.maximum(o, c) * 1.001, "Low": np.minimum(o, c) * 0.999,
                         "Close": c, "Volume": 1e7}, idx)


def _run(f, i, stop, rule):
    sig = pd.DataFrame([dict(symbol="AAA.NS", direction="up", trigger_date=str(f.index[i].date()), grade="A",
                             regime="Healthy", entry=f["Close"].iat[i], stop=stop, score=1.0)])
    return portfolio.simulate(sig, {"AAA.NS": f}, f["Close"], exit_rule=exits.RULES[rule])["trades"]


def test_sma50_trail_holds_past_21_sessions_and_sells_next_open():
    c = np.r_[np.linspace(50, 100, 80), np.linspace(100, 160, 60), np.linspace(160, 120, 30)]
    f = _frame(c)
    t = _run(f, 80, stop=90, rule="sma50").iloc[0]
    assert t["reason"] == "below 50-day" and t["sessions"] > 21
    day = pd.Timestamp(t["exit_date"])
    i = f.index.get_loc(day)
    g = portfolio._prep(f)
    assert g["Close"].iat[i - 1] < g["sma50"].iat[i - 1]       # decided at the previous close
    assert t["exit"] == pytest.approx(f["Open"].iat[i] * (1 - portfolio.slippage(1e9)), abs=0.01)


def test_half20_sells_half_then_the_rest():
    c = np.r_[np.linspace(50, 100, 80), np.linspace(100, 130, 30), np.linspace(130, 90, 40)]
    t = _run(_frame(c), 80, stop=90, rule="half20")
    assert list(t["reason"])[0] == "half at +20%"
    assert t["qty"].iloc[0] + t["qty"].iloc[1:].sum() == t["qty"].sum() and len(t) == 2
    assert t["exit"].iloc[0] == pytest.approx(t["entry"].iloc[0] / 1.0005 * 1.2 * 0.9995, rel=0.01)


def test_breakeven_moves_stop_to_entry():
    c = np.r_[np.linspace(50, 100, 80), np.linspace(100, 112, 6), np.linspace(112, 95, 10)]
    t = _run(_frame(c), 80, stop=90, rule="breakeven").iloc[0]
    assert t["reason"] in ("stop", "gap below stop", "below 50-day")
    assert t["exit"] >= t["entry"] * 0.98                 # never back to the original 90 stop
