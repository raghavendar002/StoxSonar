import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sonar import books, config as C, debate, ledger, publish  # noqa: E402
from tests.test_books import bars  # noqa: E402

FACTS = dict(symbol="X.NS", direction="up", signal_date="2026-01-05",
             v02=dict(grade="A", score=1.0, entry=100.0, stop=92.0),
             indicators=dict(close=100.0, atr_pct=0.03), market=dict(regime="Healthy"))


def verdict(**kw):
    v = dict(verdict="Go", conviction=4, horizon_sessions=63, entry_low=99.0, entry_high=102.0, stop=94.0,
             target=112.0, target_2=0, wait_kind="none", wait_level=0, wait_min_volume_ratio=0,
             wait_within_sessions=0, invalidation="a close under 94", how_its_moving="Rising.",
             reasons_for=["RS rank 90"], reasons_against=["ATR 3%"])
    v.update(kw)
    return v


def fake_caller(v, cost=0.05, log=None):
    def call(model, shared, instruction, effort, schema=None):
        if log is not None:
            log.append((model, effort, schema is not None, shared))
        text = json.dumps(v) if schema else "a case citing RS rank 90"
        return debate.Reply(text, 1000, 200, cost)
    return call


def event(symbol="X.NS", direction="up", grade="A", score=1.0, date="2026-01-05"):
    return dict(symbol=symbol, direction=direction, trigger_date=date, grade=grade, score=score,
                source="live", regime="Healthy", entry=100.0, stop=92.0 if direction == "up" else 108.0)


def setup(tmp_path, events):
    con = ledger.connect(tmp_path / "l.db")
    books.init(con)
    for ev in events:
        f = dict(FACTS, symbol=ev["symbol"], direction=ev["direction"], signal_date=ev["trigger_date"],
                 v02=dict(grade=ev["grade"], score=ev["score"], entry=100.0, stop=ev["stop"]))
        books.add_facts(con, "NSE", ev, f)
    return con, pd.DataFrame(events)


def test_level_checks():
    assert debate.check_levels(verdict(), FACTS) == []
    assert "wrong side" in debate.check_levels(verdict(stop=100.0), FACTS)[0]
    assert "3 ATR" in debate.check_levels(verdict(stop=88.0, target=130.0), FACTS)[0]
    assert "1.5R" in debate.check_levels(verdict(target=105.0), FACTS)[0]
    assert "1 ATR" in debate.check_levels(verdict(entry_high=104.0), FACTS)[0]
    short = dict(FACTS, direction="down")
    assert debate.check_levels(verdict(entry_low=98.0, entry_high=101.0, stop=106.0, target=88.0), short) == []
    assert debate.check_levels(verdict(), short)            # long-shaped levels on a short are rejected
    assert debate.check_wait(verdict(verdict="Wait"), FACTS)
    assert debate.check_wait(verdict(verdict="Wait", wait_kind="close_above", wait_level=103,
                                     wait_within_sessions=10), FACTS) == []


def test_go_goes_in_both_books_and_avoid_only_in_debated(tmp_path):
    con, ev = setup(tmp_path, [event("A.NS"), event("B.NS", grade="B", score=0.2)])
    calls = []
    rows = debate.run_day(con, "NSE", ev, "2026-01-05", fake_caller(verdict(), log=calls))
    assert [r["verdict"] for r in rows] == ["Go", "Go"] and rows[0]["symbol"] == "A.NS"
    assert [c[0] for c in calls[:3]] == [C.DEBATE_MODEL_ARGUE, C.DEBATE_MODEL_ARGUE, C.DEBATE_MODEL_JUDGE]
    assert [c[2] for c in calls[:3]] == [False, False, True]
    got = con.execute("SELECT book, symbol, verdict, levels, stop, target, horizon, max_buy FROM mt_picks "
                      "ORDER BY symbol, book").fetchall()
    assert got[0] == ("debated", "A.NS", "Go", "judge", 94.0, 112.0, 63, None)
    assert got[1] == ("judge", "A.NS", "Go", "judge", 94.0, 112.0, 63, 102.0)
    assert debate.run_day(con, "NSE", ev, "2026-01-05", fake_caller(verdict())) == []      # never twice

    con2, ev2 = setup(tmp_path / "b", [event()])
    debate.run_day(con2, "NSE", ev2, "2026-01-05", fake_caller(verdict(verdict="Avoid")))
    assert con2.execute("SELECT book, verdict FROM mt_picks").fetchall() == [("debated", "Avoid")]


def test_bad_levels_fall_back_to_v02(tmp_path):
    con, ev = setup(tmp_path, [event()])
    rows = debate.run_day(con, "NSE", ev, "2026-01-05", fake_caller(verdict(stop=101.0)))
    assert rows[0]["levels_ok"] is False and rows[0]["problems"]
    assert con.execute("SELECT levels, stop, target, horizon FROM mt_picks WHERE book='judge'").fetchone() == \
        ("v02", 92.0, None, C.HOLD_SESSIONS)


def test_daily_limit_and_monthly_cap(tmp_path):
    evs = [event(f"S{i}.NS", score=5 - i) for i in range(5)]
    con, ev = setup(tmp_path, evs)
    now = datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
    # Each debate costs $3 x 3 calls = $9 > the cap, so only the first runs
    rows = debate.run_day(con, "NSE", ev, "2026-01-05", fake_caller(verdict(), cost=3.0))
    st = [r["status"] for r in rows]
    assert st == ["done", "not_debated_budget", "not_debated_budget",
                  "not_debated_daily_limit", "not_debated_daily_limit"]
    assert debate.budget_left(con) < 0
    assert debate.budget_left(con, datetime(2030, 1, 1, tzinfo=timezone.utc)) == C.DEBATE_MONTHLY_CAP_USD
    assert now


def test_a_failed_call_is_logged_and_does_not_stop_the_rest(tmp_path):
    con, ev = setup(tmp_path, [event("A.NS"), event("B.NS", score=0.5)])
    n = {"i": 0}

    def flaky(model, shared, instruction, effort, schema=None):
        n["i"] += 1
        if n["i"] == 1:
            raise RuntimeError("boom")
        return fake_caller(verdict())(model, shared, instruction, effort, schema)
    rows = debate.run_day(con, "NSE", ev, "2026-01-05", flaky)
    assert [r["status"] for r in rows] == ["error", "done"]


def wait_frame(closes, vols=None):
    f = bars([(c, c + 1, c - 1, c) for c in closes])
    f["Volume"] = vols or [1e6] * len(closes)
    f["vol50"] = 1e6
    return f


def test_wait_triggers_expires_or_is_voided(tmp_path):
    w = verdict(verdict="Wait", wait_kind="close_above", wait_level=103.0, wait_min_volume_ratio=1.5,
                wait_within_sessions=3)
    con, ev = setup(tmp_path, [event()])
    debate.run_day(con, "NSE", ev, "2026-01-05", fake_caller(w))
    assert debate.watched_symbols(con, "NSE") == ["X.NS"]
    # Day 1 closes above the level but on thin volume: no trigger yet
    assert debate.check_waits(con, "NSE", {"X.NS": wait_frame([100, 104], [1e6, 1e6])}) == []
    got = debate.check_waits(con, "NSE", {"X.NS": wait_frame([100, 104, 105], [1e6, 1e6, 2e6])})
    assert got[0]["status"] == "triggered" and got[0]["date"] == "2026-01-07"
    p = con.execute("SELECT signal_date, source, verdict, stop, target, max_buy FROM mt_picks WHERE book='judge'").fetchone()
    assert p == ("2026-01-07", "wait", "Wait", 94.0, 112.0, None)
    assert debate.check_waits(con, "NSE", {"X.NS": wait_frame([100, 104, 105, 106])}) == []   # settled

    con2, ev2 = setup(tmp_path / "b", [event()])
    debate.run_day(con2, "NSE", ev2, "2026-01-05", fake_caller(w))
    got = debate.check_waits(con2, "NSE", {"X.NS": wait_frame([100, 101, 101, 101, 101])})
    assert got[0]["status"] == "expired"
    assert con2.execute("SELECT COUNT(*) FROM mt_picks WHERE book='judge'").fetchone()[0] == 0

    con3, ev3 = setup(tmp_path / "c", [event()])
    debate.run_day(con3, "NSE", ev3, "2026-01-05", fake_caller(dict(w, wait_min_volume_ratio=0)))
    got = debate.check_waits(con3, "NSE", {"X.NS": wait_frame([100, 115])})      # blew through the target
    assert got[0]["status"] == "expired"


def test_cost_from_usage():
    class U:
        input_tokens, output_tokens = 1000, 500
        cache_creation_input_tokens, cache_read_input_tokens = 8000, 0
    assert debate.cost_usd("claude-sonnet-5-5", U) == pytest.approx((1000 * 2 + 8000 * 2.5 + 500 * 10) / 1e6)
    U.cache_creation_input_tokens, U.cache_read_input_tokens = 0, 8000
    assert debate.cost_usd("claude-opus-5-5", U) == pytest.approx((1000 * 4 + 8000 * 0.2 + 500 * 20) / 1e6)


def test_message_and_page(tmp_path):
    con, ev = setup(tmp_path, [event("A.NS"), event("D.NS", direction="down", grade="B", score=None)])
    short = verdict(verdict="Avoid", entry_low=98.0, entry_high=101.0, stop=106.0, target=88.0)

    def call(model, shared, instruction, effort, schema=None):
        v = short if "D.NS" in instruction else verdict()
        return fake_caller(v)(model, shared, instruction, effort, schema)
    rows = debate.run_day(con, "NSE", ev, "2026-01-05", call)
    text = publish.debate_telegram_text("2026-01-05", rows, [], debate.verdict_record(con, "NSE"), 0.3)
    assert "GO · A · A breakout · conviction 4/5" in text and "Buy 99.00–102.00 · stop 94.00" in text
    assert "AVOID · D · B breakdown, SHADOW SHORT" in text and "If taken anyway: Short" in text
    assert "$0.30 of $6" in text and "not advice" in text
    publish.write_debates(con, "NSE", tmp_path / "site")
    html = (tmp_path / "site" / "debates.html").read_text()
    assert "Bull's case" in html and "shadow short" in html and "Not started yet." in html
