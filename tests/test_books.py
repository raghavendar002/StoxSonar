import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sonar import books, engine, ledger  # noqa: E402
from tests.test_engine import rising_bench, uptrend_with_base_and_breakout  # noqa: E402


def bars(rows, start="2026-01-05"):
    """rows: (open, high, low, close); bench flat at 100, traded value Rs 20 cr."""
    idx = pd.bdate_range(start, periods=len(rows))
    f = pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx, dtype=float)
    f["bench"] = 100.0
    f["traded_value"] = 2e8
    return f


def pick(**kw):
    p = dict(market="NSE", book="twin", symbol="X.NS", direction="up", signal_date="2026-01-05",
             signal_close=100.0, stop=90.0, target=None, horizon=3, max_buy=None)
    p.update(kw)
    return p


def test_time_exit_after_costs():
    f = bars([(100, 100, 100, 100), (101, 103, 100, 102), (102, 104, 101, 103),
              (103, 106, 102, 105), (105, 107, 104, 106)])
    r = books.score(pick(), f)
    assert r["status"] == "closed" and r["exit_reason"] == "time"
    assert r["entry_px"] == 101 and r["exit_px"] == 105 and r["exit_date"] == "2026-01-08"
    risk = (101 - 90) / 101
    assert r["r"] == pytest.approx((105 / 101 - 1 - r["cost"]) / risk, abs=1e-3)
    assert 0.002 < r["cost"] < 0.01          # STT both sides, stamp, slippage


def test_stop_and_gap_through_stop():
    f = bars([(100, 100, 100, 100), (101, 102, 89, 95), (95, 96, 94, 95)])
    assert books.score(pick(), f)["exit_px"] == 90                 # traded through: fills at the stop
    f = bars([(100, 100, 100, 100), (85, 86, 84, 85), (85, 86, 84, 85)])
    r = books.score(pick(), f)
    assert r["exit_reason"] == "stop" and r["exit_px"] == 85        # opened below: fills at the open
    assert books.score(pick(book="raw"), f)["status"] == "skipped"  # raw never buys under the stop


def test_target_and_both_touched_counts_as_stop():
    f = bars([(100, 100, 100, 100), (101, 112, 100, 110), (110, 111, 109, 110)])
    r = books.score(pick(target=110.0), f)
    assert r["exit_reason"] == "target" and r["exit_px"] == 110
    f = bars([(100, 100, 100, 100), (101, 112, 89, 100), (100, 101, 99, 100)])
    assert books.score(pick(target=110.0), f)["exit_reason"] == "stop"


def test_raw_skips_gap_above_buy_ceiling_and_open_while_running():
    f = bars([(100, 100, 100, 100), (106, 107, 105, 106), (106, 107, 105, 106)])
    assert books.score(pick(book="raw", max_buy=104.0), f)["status"] == "skipped"
    f = bars([(100, 100, 100, 100), (101, 102, 100, 101)])
    r = books.score(pick(horizon=21), f)
    assert r["status"] == "open" and r["sessions"] == 1
    assert books.score(pick(), bars([(100, 100, 100, 100)]))["status"] == "pending"


def test_shadow_short():
    f = bars([(100, 100, 100, 100), (99, 100, 95, 96), (96, 97, 90, 91), (91, 92, 88, 89)])
    r = books.score(pick(direction="down", stop=110.0), f)
    assert r["exit_reason"] == "time" and r["ret"] == pytest.approx(1 - 89 / 99, abs=1e-4)
    assert r["r"] > 0


def test_us_costs_are_slippage_only():
    assert books.cost_pct("US", 100, None, None) == pytest.approx(2 * books.US_SLIPPAGE)


def test_which_signals_go_in_which_book():
    ev = pd.DataFrame([
        dict(symbol="A.NS", direction="up", trigger_date="2026-01-05", grade="A", regime="Healthy",
             source="live", entry=100.0, stop=90.0, score=1.0),
        dict(symbol="B.NS", direction="up", trigger_date="2026-01-05", grade="B", regime="Weak",
             source="live", entry=100.0, stop=90.0, score=0.1),
        dict(symbol="C.NS", direction="up", trigger_date="2026-01-05", grade="C", regime="Healthy",
             source="live", entry=100.0, stop=90.0, score=-1.0),
        dict(symbol="D.NS", direction="down", trigger_date="2026-01-05", grade="A", regime="Healthy",
             source="live", entry=100.0, stop=110.0, score=None),
        dict(symbol="E.NS", direction="down", trigger_date="2026-01-05", grade="W", regime="Healthy",
             source="live", entry=100.0, stop=110.0, score=None),
        dict(symbol="F.NS", direction="up", trigger_date="2026-01-05", grade="A", regime="Healthy",
             source="replay", entry=100.0, stop=90.0, score=1.0),
    ])
    got = {(p["book"], p["symbol"]) for p in books.new_picks(ev, "NSE", ["live", "late"])}
    assert got == {("raw", "A.NS"), ("twin", "A.NS"), ("twin", "B.NS"), ("twin", "C.NS"), ("twin", "D.NS")}


def test_picks_are_written_once_and_finished_picks_never_change(tmp_path):
    con = ledger.connect(tmp_path / "l.db")
    books.init(con)
    p = pick(score=1.0, grade="A", regime="Healthy", source="live", levels="v02")
    assert books.add_picks(con, [p]) == 1
    assert books.add_picks(con, [dict(p, stop=50.0)]) == 0          # identity is frozen
    f = bars([(100, 100, 100, 100), (101, 103, 100, 102), (102, 104, 101, 103), (103, 106, 102, 105)])
    assert books.update(con, "NSE", {"X.NS": f}) == 1
    row = con.execute("SELECT status, stop, exit_px FROM mt_picks").fetchone()
    assert row == ("closed", 90.0, 105.0)
    f2 = f.copy()
    f2["Close"] = 50.0                                               # later data cannot rewrite it
    assert books.update(con, "NSE", {"X.NS": f2}) == 0
    assert con.execute("SELECT exit_px FROM mt_picks").fetchone()[0] == 105.0
    s = books.summary(con, "NSE")
    assert s[0]["book"] == "twin" and s[0]["closed"] == 1 and s[0]["avg_r"] > 0


def test_fact_pack_holds_only_what_was_known_on_the_signal_day():
    df = uptrend_with_base_and_breakout()
    f = engine.compute_features(df, rising_bench(df.index))
    sd = str(f.index[260].date())
    ev = dict(symbol="X.NS", direction="up", trigger_date=sd, grade="A", score=1.0, stage="2", template="8",
              rs_rank=90.0, mansfield=5.0, pivot=200.5, base_len=60, depth=0.1, vol_ratio=3.0,
              entry=212.0, stop=200.0, regime="Healthy")
    fp = books.fact_pack(ev, f, None, 14.2)
    assert fp["daily_bars"][-1][0] == sd and len(fp["daily_bars"]) == 120
    assert len(fp["weekly_bars"]) <= 52 and fp["weekly_bars"][-1][0] <= sd
    assert fp["market"]["vix"] == 14.2 and fp["v02"]["plan"]["stop"] == 200.0
    assert fp["indicators"]["dist_sma200"] > 0
    assert fp["v02"]["stage"] == 2 and fp["v02"]["stage_name"] == "Advancing" and fp["v02"]["template"] == 8
