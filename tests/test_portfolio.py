import numpy as np
import pandas as pd
import pytest

from sonar import config as C, portfolio


def _frame(opens, lows, closes, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"Open": opens, "High": np.maximum(opens, closes), "Low": lows,
                         "Close": closes, "Volume": 1e7}, idx)


def _signal(f, i, stop, grade="A", regime="Healthy"):
    return pd.DataFrame([dict(symbol="AAA.NS", direction="up", trigger_date=str(f.index[i].date()),
                              grade=grade, regime=regime, entry=f["Close"].iat[i], stop=stop, score=1.0)])


def test_gap_through_stop_fills_at_the_open():
    n = 30
    c = np.full(n, 100.0); c[3:] = 101
    o, lo = c.copy(), c * 0.99
    o[6], lo[6], c[6] = 85, 84, 86            # opens far below the 95 stop
    f = _frame(o, lo, c)
    res = portfolio.simulate(_signal(f, 2, stop=95), {"AAA.NS": f}, f["Close"])
    t = res["trades"].iloc[0]
    assert t["reason"] == "gap below stop"
    assert t["exit"] == pytest.approx(85 * (1 - portfolio.slippage(1e9)), abs=0.01)
    assert t["pnl"] < -(t["qty"] * (t["entry"] - 95))   # lost more than the planned risk


def test_time_exit_after_hold_sessions_and_costs_charged():
    n = 40
    c = np.linspace(100, 110, n)
    f = _frame(c, c * 0.995, c)
    res = portfolio.simulate(_signal(f, 2, stop=90), {"AAA.NS": f}, f["Close"])
    t = res["trades"].iloc[0]
    assert t["reason"] == "time"
    assert str(t["exit_date"]) == str(f.index[2 + C.HOLD_SESSIONS].date())
    gross = t["qty"] * (t["exit"] - t["entry"])
    assert 0 < t["pnl"] < gross                       # costs taken out
    assert res["equity"]["equity"].iloc[-1] == pytest.approx(C.CAPITAL_RS + t["pnl"], abs=1)


def test_no_buys_in_weak_market_or_above_max_buy():
    n = 30
    c = np.full(n, 100.0)
    f = _frame(c, c * 0.99, c)
    assert portfolio.simulate(_signal(f, 2, 95, regime="Weak"), {"AAA.NS": f}, f["Close"])["trades"].empty
    o = c.copy(); o[3] = 110                          # opens 10% up, above the plan's ceiling
    g = _frame(o, c * 0.99, c)
    assert portfolio.simulate(_signal(g, 2, 95), {"AAA.NS": g}, g["Close"])["trades"].empty


def test_delisted_stock_is_closed_at_its_last_price():
    c = np.full(10, 100.0)
    f = _frame(c, c * 0.99, c)
    bench = pd.Series(1.0, index=pd.bdate_range("2026-01-01", periods=40))
    t = portfolio.simulate(_signal(f, 2, 90), {"AAA.NS": f}, bench)["trades"].iloc[0]
    assert t["reason"] == "delisted"


def _flat_with_signal(n=300):
    c = np.full(n, 100.0)
    f = _frame(c, c * 0.999, c, start="2020-01-01")
    return f, _signal(f, 2, stop=90)


def test_idle_cash_in_etf_follows_the_index_less_costs():
    f, sig = _flat_with_signal()
    bench = pd.Series(np.linspace(100, 150, len(f)), f.index)
    cash = portfolio.simulate(sig, {"AAA.NS": f}, bench)
    etf = portfolio.simulate(sig, {"AAA.NS": f}, bench, idle="etf")
    gain = etf["equity"]["equity"].iloc[-1] / cash["equity"]["equity"].iloc[-1]
    assert 1.4 < gain < 1.5                       # most money was idle and the index rose 50%
    assert etf["etf_costs"] > 0 and cash["etf_costs"] == 0


def test_etf_trend_stays_in_cash_while_index_is_below_its_average():
    f, sig = _flat_with_signal()
    bench = pd.Series(np.linspace(150, 100, len(f)), f.index)    # falling all along
    cash = portfolio.simulate(sig, {"AAA.NS": f}, bench)
    trend = portfolio.simulate(sig, {"AAA.NS": f}, bench, idle="etf_trend")
    assert trend["equity"]["equity"].iloc[-1] == pytest.approx(cash["equity"]["equity"].iloc[-1])


def test_fixed_fraction_sizing_and_risk_pct():
    f, sig = _flat_with_signal()
    q = lambda **k: portfolio.simulate(sig, {"AAA.NS": f}, f["Close"], **k)["trades"]["qty"].iloc[0]
    assert q(fixed_frac=0.10) == 100              # 10% of Rs 1 lakh at Rs 100
    assert q(risk_pct=0.01) == 2 * q()            # double the risk, double the size (within the 25% cap)


def test_liquid_fund_earns_its_rate_on_idle_cash():
    f, sig = _flat_with_signal(253)
    cash = portfolio.simulate(sig, {"AAA.NS": f}, f["Close"])
    liq = portfolio.simulate(sig, {"AAA.NS": f}, f["Close"], idle="liquid")
    gain = liq["equity"]["equity"].iloc[-1] / cash["equity"]["equity"].iloc[-1] - 1
    assert 0.04 < gain < portfolio.LIQUID_RATE + 0.002     # daily compounding
