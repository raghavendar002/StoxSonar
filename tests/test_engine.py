import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sonar import config as C, engine, ledger, publish  # noqa: E402


def make_df(closes, vols=None, start="2023-01-02"):
    closes = np.asarray(closes, float)
    idx = pd.bdate_range(start, periods=len(closes))
    vols = np.full(len(closes), 1e6) if vols is None else np.asarray(vols, float)
    opens = np.r_[closes[0], closes[:-1]]
    high = np.maximum(opens, closes) * 1.005
    low = np.minimum(opens, closes) * 0.995
    return pd.DataFrame({"Open": opens, "High": high, "Low": low, "Close": closes, "Volume": vols}, idx)


def uptrend_with_base_and_breakout():
    """Steady rise, a 60-session base ~10% deep, then a high-volume breakout and follow-through."""
    rise = np.geomspace(40, 200, 200)
    base = 190 + 9 * np.sin(np.linspace(0, 6 * np.pi, 60))     # 181..199, below the 200.x pivot
    brk = [212.0]
    after = np.linspace(213, 240, 40)
    closes = np.r_[rise, base, brk, after]
    vols = np.full(len(closes), 1e6)
    vols[260] = 3e6
    df = make_df(closes, vols)
    # The breakout candle closes at its high: no upper wick
    df.iloc[260, df.columns.get_loc("High")] = 212.0
    df.iloc[260, df.columns.get_loc("Open")] = 199.0
    df.iloc[260, df.columns.get_loc("Low")] = 198.5
    return df


def rising_bench(index):
    return pd.Series(np.linspace(10000, 13000, len(index)), index=index)


def test_raw_stage_rules():
    row = pd.Series(dict(Close=110, sma50=105, sma150=100, slope150=0.02, hi52=120, lo52=80))
    assert engine.raw_stage(row, None) == 2
    row = pd.Series(dict(Close=90, sma50=95, sma150=100, slope150=-0.02, hi52=120, lo52=80))
    assert engine.raw_stage(row, None) == 4
    flat = pd.Series(dict(Close=101, sma50=100, sma150=100, slope150=0.0, hi52=120, lo52=80))
    assert engine.raw_stage(flat, 4) == 1
    assert engine.raw_stage(flat, 2) == 3
    assert engine.raw_stage(flat, None) == 3      # upper half of the 52-week range
    assert engine.raw_stage(flat.replace(101, 95), None) == 1


def test_breakout_detected_graded_and_confirmed():
    df = uptrend_with_base_and_breakout()
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    ups = [e for e in res.events if e.direction == "up"]
    assert len(ups) == 1
    ev = ups[0]
    assert ev.trigger_date == str(df.index[260].date())
    assert ev.stage == 2 and ev.template == 8 and ev.grade == "A"
    assert ev.base_len >= C.BASE_MIN_LEN and C.BASE_MIN_DEPTH <= ev.depth <= C.BASE_MAX_DEPTH
    assert ev.status == "Confirmed"
    assert ev.outcomes["ret_21"] > 0 and ev.outcomes["r_21"] > 0


def test_weak_regime_cuts_grade():
    df = uptrend_with_base_and_breakout()
    falling = pd.Series(np.linspace(13000, 9000, len(df)), index=df.index)
    res = engine.run_market({"TEST.NS": df}, falling)
    ev = [e for e in res.events if e.direction == "up"][0]
    assert ev.regime == "Weak" and ev.grade == "B"


def test_failed_breakout():
    df = uptrend_with_base_and_breakout()
    # Collapse back into the base three sessions after the breakout
    df.iloc[263:, df.columns.get_loc("Close")] = 190.0
    df.iloc[263:, df.columns.get_loc("Open")] = 190.0
    df.iloc[263:, df.columns.get_loc("High")] = 191.0
    df.iloc[263:, df.columns.get_loc("Low")] = 189.0
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    ev = [e for e in res.events if e.direction == "up"][0]
    assert ev.status == "Failed"


def test_no_lookahead():
    """Labels for a past day must not change when later data arrives."""
    df = uptrend_with_base_and_breakout()
    bench = rising_bench(df.index)
    full = engine.run_market({"TEST.NS": df}, bench).states.set_index("date")
    cut = df.index[265]
    part = engine.run_market({"TEST.NS": df.loc[:cut]}, bench.loc[:cut]).states.set_index("date")
    cols = ["stage", "transition_to", "stage_age", "template"]
    pd.testing.assert_frame_equal(full.loc[:cut, cols], part[cols], check_dtype=False)


def test_hysteresis_needs_five_sessions():
    # Long rise (Stage 2), then a sharp fall that flips the raw rule to Stage 4
    closes = np.r_[np.linspace(100, 200, 300), np.linspace(200, 120, 120)]
    df = make_df(closes)
    st = engine.run_market({"X.NS": df}, rising_bench(df.index)).states
    st = st.set_index("date")["stage"]
    changes = st[st != st.shift()].index[1:]
    for d in changes:
        i = st.index.get_loc(d)
        assert (st.iloc[i - 5:i] == st.iloc[i - 1]).all()   # old stage held while confirming


def test_ledger_never_back_inserts_or_regrades(tmp_path):
    df = uptrend_with_base_and_breakout()
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    con = ledger.connect(tmp_path / "l.db")
    ev = [e for e in res.events if e.direction == "up"][0]
    later = str(df.index[-1].date())
    # A daily run whose previous run was after the trigger date must not add it
    assert ledger.record_events(con, [ev], "NSE", later, "daily", after=later) == 0
    assert ledger.record_events(con, [ev], "NSE", ev.trigger_date, "daily", after="2000-01-01") == 1
    ev.grade, ev.status = "C", "Failed"
    ledger.record_events(con, [ev], "NSE", later, "daily", after=later)
    row = ledger.events_frame(con, "NSE").iloc[0]
    assert row["grade"] == "A" and row["status"] == "Failed" and row["source"] == "live"


def test_page_renders_without_prices(tmp_path):
    df = uptrend_with_base_and_breakout().iloc[:261]
    bench = rising_bench(df.index)
    res = engine.run_market({"TEST.NS": df}, bench)
    con = ledger.connect(tmp_path / "l.db")
    as_of = str(df.index[-1].date())
    ledger.record_events(con, res.events, "NSE", as_of, "daily", after="2000-01-01")
    snap = publish.build_snapshot(res.states, ledger.events_frame(con, "NSE"), res.regime, as_of)
    assert [b["symbol"] for b in snap["breakouts"]] == ["TEST"]
    page = publish.render_html(snap)
    assert "TEST" in page and "207" not in page      # no raw price on the page
    assert "TEST" in publish.telegram_text(snap)


def test_daily_run_never_republishes_the_last_session(tmp_path, monkeypatch):
    import run_daily
    from sonar import data as D
    df = uptrend_with_base_and_breakout()
    D.save_cache(tmp_path / "c.pkl", {"TEST.NS": df}, rising_bench(df.index))
    posts = []
    monkeypatch.setattr(publish, "send_telegram", lambda text: posts.append(text))
    out = tmp_path / "gh_output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    args = ["--use-cache", "--cache", str(tmp_path / "c.pkl"), "--db", str(tmp_path / "l.db"),
            "--site", str(tmp_path / "site"), "--telegram"]
    assert run_daily.main(args + ["--mode", "replay"]) == 0
    out.write_text("")
    posts.clear()
    # Same data again: the newest session is already published, so no post
    assert run_daily.main(args + ["--mode", "daily"]) == 0
    assert posts == [] and "published=true" not in out.read_text()
    # One more session arrives: it is published once
    nxt = df.iloc[[-1]].copy()
    nxt.index = nxt.index + pd.offsets.BDay(1)
    df2 = pd.concat([df, nxt])
    D.save_cache(tmp_path / "c.pkl", {"TEST.NS": df2}, rising_bench(df2.index))
    assert run_daily.main(args + ["--mode", "daily"]) == 0
    assert len(posts) == 1 and str(nxt.index[0].date()) in posts[0]
    assert "published=true" in out.read_text()


def test_intraday_bar_is_never_a_completed_session():
    import run_daily
    from datetime import datetime, timezone
    # 13:27 IST on a Wednesday: today's bar is partial, so the last complete day is Tuesday
    assert run_daily.last_complete_day(datetime(2026, 10, 14, 7, 57, tzinfo=timezone.utc)) == "2026-10-13"
    # 19:00 IST: today's session is done
    assert run_daily.last_complete_day(datetime(2026, 10, 14, 13, 30, tzinfo=timezone.utc)) == "2026-10-14"


def test_lagging_benchmark_is_carried_forward(monkeypatch):
    from sonar import data as D
    bench = rising_bench(pd.bdate_range("2026-01-01", periods=10))
    monkeypatch.setattr(D, "fetch_benchmark_symbol", lambda t, period=None: pd.Series(dtype=float))
    to = bench.index[-1] + pd.offsets.BDay(1)
    ext = D.extend_benchmark(bench, to)
    assert ext.index.max() == to and ext.iloc[-1] == bench.iloc[-1]
def test_score_grades_and_gate():
    strong = dict(rs_rank=95, prior_126=1.2, dist_sma200=0.6, ext_pivot=0.06)
    weak = dict(rs_rank=40, prior_126=0.1, dist_sma200=0.05, ext_pivot=0.021)
    assert engine.grade_event("up", 2, engine.momentum_score(strong), True, False) == "A"
    assert engine.grade_event("up", 2, engine.momentum_score(weak), True, False) == "C"
    # Below the 200-day average nothing grades above C, however strong the score
    assert engine.grade_event("up", 2, engine.momentum_score(strong), False, False) == "C"
    assert engine.grade_event("up", 2, engine.momentum_score(strong), True, True) == "B"


def test_breakout_needs_two_percent_clearance():
    df = uptrend_with_base_and_breakout()
    for col in ("Close", "High"):
        df.iloc[260, df.columns.get_loc(col)] = 202.0      # about 1% above the ~200 pivot
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    assert not [e for e in res.events if e.trigger_date == str(df.index[260].date())]


def test_bad_print_blocks_signal_and_outcomes():
    df = uptrend_with_base_and_breakout()
    df.iloc[240, df.columns.get_loc("Close")] *= 2           # one-day doubling on normal volume
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    assert not [e for e in res.events if e.trigger_date == str(df.index[260].date())]


def test_fail_line_is_atr_based_and_outcomes_start_next_open():
    df = uptrend_with_base_and_breakout()
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    ev = [e for e in res.events if e.direction == "up"][0]
    atr = engine.compute_features(df, rising_bench(df.index))["atr_pct"].iloc[260]
    assert ev.stop == pytest.approx(ev.entry * (1 - C.STOP_ATR * atr))
    assert ev.outcomes["ret_21"] == pytest.approx(df["Close"].iloc[281] / df["Open"].iloc[261] - 1, abs=1e-4)


def test_shadow_grade_is_logged_and_changes_nothing(tmp_path):
    df = uptrend_with_base_and_breakout()
    res = engine.run_market({"TEST.NS": df}, rising_bench(df.index))
    ev = [e for e in res.events if e.direction == "up"][0]
    assert ev.grade == "A"                                  # live grade unchanged
    assert ev.shadow_score is not None and ev.shadow_grade in ("A", "B", "C")
    con = ledger.connect(tmp_path / "l.db")
    ledger.record_events(con, [ev], "NSE", ev.trigger_date, "daily", after="2000-01-01")
    row = ledger.events_frame(con, "NSE").iloc[0]
    assert row["shadow_grade"] == ev.shadow_grade and row["shadow_score"] == pytest.approx(ev.shadow_score)


def test_shadow_score_signs_and_gates():
    means = {k: v[2] for k, v in C.SHADOW_FEATURES.items()}
    assert engine.shadow_score(means) == pytest.approx(0)
    tighter = dict(means, tight10=means["tight10"] / 2)    # tighter is better (sign -1)
    assert engine.shadow_score(tighter) > 0
    assert engine.shadow_grade(9.9, above_sma200=False, weak_regime=False) == "C"
    assert engine.shadow_grade(9.9, above_sma200=True, weak_regime=True) == "B"


def test_old_ledger_gains_shadow_columns(tmp_path):
    import sqlite3
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, engine_version TEXT, market TEXT, symbol TEXT, "
                "direction TEXT, trigger_date TEXT, UNIQUE (engine_version, market, symbol, direction, trigger_date))")
    con.close()
    have = {r[1] for r in ledger.connect(path).execute("PRAGMA table_info(events)")}
    assert {"shadow_score", "shadow_grade"} <= have
