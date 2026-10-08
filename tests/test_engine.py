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
    rise = np.linspace(100, 200, 200)
    base = 190 + 9 * np.sin(np.linspace(0, 6 * np.pi, 60))     # 181..199, below the 200.x pivot
    brk = [207.0]
    after = np.linspace(208, 235, 40)
    closes = np.r_[rise, base, brk, after]
    vols = np.full(len(closes), 1e6)
    vols[260] = 3e6
    df = make_df(closes, vols)
    # The breakout candle closes at its high: no upper wick
    df.iloc[260, df.columns.get_loc("High")] = 207.0
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
