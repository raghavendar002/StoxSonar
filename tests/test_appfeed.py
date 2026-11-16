import json
import shutil
import sqlite3
from pathlib import Path

from sonar import appfeed

ROOT = Path(__file__).resolve().parent.parent
DRY = ROOT / "paper" / "out" / "2026-11-13"

MD = """# US dry run

## SO (Southern Co), rel. volume 5.6x, +2.0% today
- **Bull:** Up 2% on a down day.
- **Bear:** Defensive rotation, not news.
- **Judge: LONG on a new day high.** The strength is real. Trigger 94.52.

## LOW (Lowe's), rel. volume 1.8x
- **Bull:** Reclaimed the open.
- **Bear:** Supply above.
- **Judge: LONG only above 228.10**, a new day high.

## Guardrail deviation (logged on purpose)
Not a stock.
"""


def test_parse_debate_md():
    d = appfeed.parse_debate_md(MD)
    assert set(d) == {"SO", "LOW"}
    assert d["SO"]["name"] == "Southern Co" and d["SO"]["headline"] == "rel. volume 5.6x, +2.0% today"
    assert d["SO"]["bull"] == "Up 2% on a down day."
    assert d["SO"]["judge_title"] == "LONG on a new day high"
    assert d["SO"]["judge_text"].startswith("The strength is real")
    assert d["LOW"]["judge_title"] == "LONG only above 228.10" and d["LOW"]["judge_text"] == "A new day high."


def test_intraday_day_from_the_real_dry_run():
    day = appfeed.intraday_day(DRY, "us")
    assert day["date"] == "2026-11-13" and day["status"] == "dry_run" and day["checkpoint"] == "12:15"
    assert day["universe"] == 103 and day["signals"] == 3 and day["index"] == {"name": "SPY", "move_pct": -1.11}
    assert day["books"]["judge"]["pnl"] == -2.69 and day["books"]["twin"]["pnl"] == 0.55
    assert day["books"]["twin"]["trades"] == 2 and day["books"]["twin"]["wins"] == 1
    c = {x["symbol"]: x for x in day["cases"]}
    assert c["SO"]["judge"]["verdict"] == "Long" and c["SO"]["judge"]["conviction"] == 3
    assert c["SO"]["judge"]["levels"] == dict(entry_low=94.52, entry_high=94.52, stop=94.05, target=95.22, target_2=None)
    assert c["SO"]["outcome"]["judge"]["reason"] == "stop" and c["SO"]["outcome"]["judge"]["entry_t"] == "12:50"
    assert c["SCHW"]["judge"]["verdict"] == "No trade" and c["SCHW"]["outcome"]["judge"] == {"status": "passed"}
    assert c["SCHW"]["outcome"]["twin"]["r"] == 1.7
    assert c["LOW"]["outcome"]["judge"]["status"] == "not_triggered" and c["LOW"]["outcome"]["twin"] is None
    assert len(c["SO"]["bars"]["rows"]) == 33 and c["SO"]["bull"] and c["SO"]["bear"]
    assert [n["symbol"] for n in day["near_misses"] if n["passed"]] == ["SO", "SCHW", "LOW"]


def test_intraday_empty_market_has_a_reason(tmp_path):
    f = appfeed.intraday(tmp_path, "in")
    assert f["days"] == [] and f["as_of"] is None and "No India intraday days yet" in f["notes"][0]


def _midterm_db():
    con = sqlite3.connect(":memory:")
    con.executescript("""
    CREATE TABLE mt_picks (id INTEGER PRIMARY KEY, market TEXT, book TEXT, symbol TEXT, direction TEXT, signal_date TEXT,
      grade TEXT, score REAL, regime TEXT, source TEXT, levels TEXT, signal_close REAL, stop REAL, target REAL, horizon INTEGER,
      max_buy REAL, status TEXT, entry_date TEXT, entry_px REAL, exit_date TEXT, exit_px REAL, exit_reason TEXT, sessions INTEGER,
      ret REAL, cost REAL, r REAL, bench_ret REAL, excess REAL, mfe_r REAL, mae_r REAL, created_utc TEXT, updated_utc TEXT,
      verdict TEXT, conviction INTEGER);
    CREATE TABLE mt_facts (market TEXT, symbol TEXT, direction TEXT, signal_date TEXT, facts TEXT, created_utc TEXT);
    CREATE TABLE mt_debates (id INTEGER PRIMARY KEY, market TEXT, symbol TEXT, direction TEXT, signal_date TEXT, grade TEXT,
      status TEXT, bull TEXT, bear TEXT, judge TEXT, verdict TEXT, conviction INTEGER, levels TEXT, level_problems TEXT,
      wait_status TEXT, wait_date TEXT, models TEXT, input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL, created_utc TEXT);
    """)
    v = dict(verdict="Wait", conviction=4, horizon_sessions=21, entry_low=100, entry_high=102, stop=95, target=112, target_2=0,
             wait_kind="close_above", wait_level=103.5, wait_min_volume_ratio=1.5, wait_within_sessions=5,
             invalidation="A close under 95.", how_its_moving="Tight base under the highs.",
             reasons_for=["RS rank 96"], reasons_against=["Weak market"])
    facts = dict(v02=dict(grade="B", score=1.2, template=8, rs_rank=96.0, base_len=30, vol_ratio=2.1, entry=101.0, stop=94.0),
                 indicators=dict(dist_sma50=0.08, from_hi52=-0.01, ret_63=0.31), market=dict(regime="Weak"),
                 next_results_date=None, daily_bars=[[f"2026-10-{d:02d}", 99, 101, 98, 100, 1000] for d in range(1, 31)])
    con.execute("INSERT INTO mt_debates (market, symbol, direction, signal_date, grade, status, bull, bear, judge, verdict, "
                "conviction, wait_status, models, cost_usd) VALUES ('NSE','ABC.NS','up','2026-11-12','B','done','Bull text',"
                "'Bear text',?, 'Wait', 4, 'watching', '[\"a\",\"b\"]', 0.17)", (json.dumps(v),))
    con.execute("INSERT INTO mt_debates (market, symbol, direction, signal_date, grade, status) "
                "VALUES ('NSE','ERR.NS','up','2026-11-12','B','error')")
    con.execute("INSERT INTO mt_facts VALUES ('NSE','ABC.NS','up','2026-11-12',?, '')", (json.dumps(facts),))
    for book, r, status in [("twin", 1.5, "closed"), ("debated", None, "open"), ("twin", -1.0, "closed")]:
        sym = "ABC.NS" if r != -1.0 else "XYZ.NS"
        con.execute("INSERT INTO mt_picks (market, book, symbol, direction, signal_date, grade, status, entry_px, stop, target, "
                    "horizon, r, ret, excess) VALUES ('NSE',?,?,'up','2026-11-12','B',?,101,94,115,21,?,?,?)",
                    (book, sym, status, r, None if r is None else r * 0.07, None if r is None else r * 0.05))
    return con


def test_midterm_case_and_books(tmp_path):
    con = _midterm_db()
    (tmp_path / "data.json").write_text('{"as_of": "2026-11-13", "regime": "Weak", "x": NaN}')
    (tmp_path / "2026-11-13.json").write_text('{"as_of": "2026-11-13", "regime": "Weak", "breadth": {"Advancing": 47.5}, '
                                              '"breakouts": [], "breakdowns": [], "open_signals": [1, 2]}')
    f = appfeed.midterm(con, tmp_path, "NSE")
    assert f["as_of"] == "2026-11-13" and f["snapshot"]["x"] is None
    assert f["history"] == [dict(date="2026-11-13", regime="Weak", buys_allowed=None, breadth={"Advancing": 47.5},
                                 breakouts=0, breakdowns=0, open=2)]
    assert len(f["cases"]) == 1                       # the failed debate is left out
    c = f["cases"][0]
    assert c["symbol"] == "ABC" and c["market"] == "IN" and c["side"] == "long" and c["bull"] == "Bull text"
    assert c["judge"]["verdict"] == "Wait" and c["judge"]["tone"] == "wait" and c["judge"]["conviction"] == 4
    assert c["judge"]["wait"] == "A close above 103.5 on at least 1.5x normal volume, within 5 sessions."
    assert c["judge"]["levels"]["target_2"] is None and c["judge"]["levels"]["stop"] == 95
    assert c["outcome"]["twin"]["r"] == 1.5 and c["outcome"]["judge"]["status"] == "open" and c["outcome"]["judge_book"] == "debated"
    assert c["twin"]["levels"]["stop"] == 94.0 and len(c["bars"]["rows"]) == 30
    twin = [b for b in f["books"] if b["book"] == "twin"][0]
    assert twin["picks"] == 2 and twin["closed"] == 2 and twin["avg_r"] == 0.25 and twin["win_pct"] == 50.0 and twin["total_r"] == 0.5
    assert not f["notes"]


def test_build_writes_every_feed_as_strict_json(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    (site / "data.json").write_text('{"as_of": "2026-11-13", "track": [{"confirmed_pct": NaN}]}')
    # A copy of the one frozen dry-run day, never the live paper folder: that grows with every
    # intraday run, and a count taken from it would fail the daily run the day after it passed.
    paper = tmp_path / "paper"
    shutil.copytree(DRY, paper / DRY.name)
    meta = appfeed.build(tmp_path / "missing.db", site, paper)
    names = {p.name for p in (site / "app" / "feed").iterdir()}
    assert names == {"mid-in.json", "mid-us.json", "intra-in.json", "intra-us.json", "meta.json"}
    for n in names:
        text = (site / "app" / "feed" / n).read_text()
        assert "NaN" not in text
        json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert meta["feeds"]["intra-us"]["cases"] == 3 and meta["feeds"]["mid-in"]["as_of"] == "2026-11-13"


def test_midterm_lists_skipped_debates_and_the_brain(tmp_path):
    con = _midterm_db()
    con.execute("CREATE TABLE runs (as_of TEXT, market TEXT, regime TEXT)")
    con.execute("INSERT INTO runs VALUES ('2026-11-13', 'NSE', 'Weak')")
    con.execute("INSERT INTO mt_debates (market, symbol, direction, signal_date, grade, status) "
                "VALUES ('NSE','OFF.NS','down','2026-11-13','A','not_debated_switched_off')")
    (tmp_path / "data.json").write_text('{"as_of": "2026-11-13"}')
    f = appfeed.midterm(con, tmp_path, "NSE")
    skipped = {x["symbol"]: x for x in f["skipped"]}
    assert set(skipped) == {"ERR", "OFF"} and "switched off" in skipped["OFF"]["why"]
    b = f["brain"]
    assert b["scoreboard"]["judged_closed"] == 0 and b["scoreboard"]["state"].startswith("Too early")
    assert b["scoreboard"]["verdicts"] == {"Wait": 1} and b["scoreboard"]["twin_book"]["n"] == 2
    assert b["switch"] == dict(regime="Weak", off=False, why=None, after=20, min_share_pct=10)
    assert b["budget"]["cap_usd"] == 6.0 and b["lessons"] == []
    assert f["cases"][0]["base_rate"] is None        # no track record was stored with this debate
    json.dumps(appfeed._clean(f), default=str)


def _live_day(folder):
    """One India day in the layout paper/intraday.py writes."""
    folder.mkdir(parents=True)
    cand = lambda sym, side, trig, stop, tgt: dict(  # noqa: E731
        sym=sym, side=side, stats=dict(relvol=2.3, last=trig, move_today=0.01),
        mechanical=dict(side=side, trigger=trig, stop=stop, target=tgt), bars_5m=[["09:15", 1, 2, 0.5, 1.5, 100]])
    scan = dict(meta=dict(date="2026-11-16", market="in", checkpoint="2026-11-16 09:30:00+05:30", index_move=-0.0042,
                          universe=80, signals=3, near_misses=[dict(sym="TRENT", relvol=2.3, dist_or_hi=0.001, move_today=0.01)]),
                candidates=[cand("TRENT", "long", 6503.0, 6470.0, 6570.0), cand("SBIN", "short", 811.6, 816.5, 801.8),
                            cand("DLF", "long", 745.0, 741.0, 753.0)])
    v = lambda d, side, c: dict(decision=d, side_if_traded=side, trigger=811.0, stop=816.0, target=801.0,  # noqa: E731
                                conviction=c, headline="h", title="t", text="x")
    talks = [dict(sym="TRENT", name=None, headline="Above the range", bull="b", bear="r", judge_title="Long above 6,510",
                  judge_text="Real drive.", verdict=dict(v("LONG", "long", 4), trigger=6510.0, stop=6470.0, target=6590.0),
                  problems=[], cost_usd=0.21),
             dict(sym="SBIN", name=None, headline="Under the range", bull="b", bear="r", judge_title="No trade: late",
                  judge_text="Late.", verdict=v("NO_TRADE", "short", 2), problems=["stop on the wrong side"], cost_usd=0.2),
             dict(sym="DLF", skipped="monthly intraday debate cap reached")]
    orders = dict(decided="2026-11-16T04:12:00+00:00", note="Live paper day.",
                  mechanical=[dict(sym="TRENT", side="long", trigger=6503.0, stop=6470.0, target=6570.0),
                              dict(sym="SBIN", side="short", trigger=811.6, stop=816.5, target=801.8)],
                  judge=[dict(sym="TRENT", side="long", trigger=6510.0, stop=6470.0, target=6590.0, conviction=4, leverage=2)])
    settle = dict(mechanical=dict(trades=[dict(status="closed", sym="SBIN", side="short", entry=811.6, exit=802.1, reason="target",
                                               entry_t="2026-11-16 09:52:00+05:30", exit_t="2026-11-16 12:40:00+05:30",
                                               qty=61.0, pnl=451.5, r_mult=1.5),
                                          dict(status="stale", sym="TRENT", side="long", qty=7.0, note="late")], end_cash=100451.5),
                  judge=dict(trades=[dict(status="not_triggered", sym="TRENT", side="long", qty=12.0)], end_cash=100000.0))
    for name, obj in [("scan", scan), ("debates", talks), ("orders", orders), ("settle", settle)]:
        (folder / f"{name}.json").write_text(json.dumps(obj))


def test_intraday_reads_a_live_india_day_with_shorts(tmp_path):
    _live_day(tmp_path / "in" / "2026-11-16")
    (tmp_path / "in" / "2026-11-17").mkdir()
    (tmp_path / "in" / "2026-11-17" / "scan.json").write_text("{not json")      # a broken day is skipped, not fatal
    f = appfeed.intraday(tmp_path, "in")
    assert f["as_of"] == "2026-11-16" and len(f["days"]) == 1 and not f["notes"]
    d = f["days"][0]
    assert d["status"] == "live" and d["checkpoint"] == "09:30" and d["index"] == dict(name="NIFTY", move_pct=-0.42)
    assert d["cost_usd"] == 0.41 and d["books"]["twin"]["pnl"] == 451.5 and d["books"]["judge"]["trades"] == 0
    c = {x["symbol"]: x for x in d["cases"]}
    assert c["TRENT"]["side"] == "long" and c["TRENT"]["judge"]["verdict"] == "Long" and c["TRENT"]["judge"]["leverage"] == 2
    assert c["TRENT"]["outcome"]["judge"]["status"] == "not_triggered" and c["TRENT"]["outcome"]["twin"]["status"] == "stale"
    s = c["SBIN"]
    assert s["side"] == "short" and s["judge"]["verdict"] == "No trade" and s["judge"]["tone"] == "avoid"
    assert s["judge"]["levels_if_traded"] and s["judge"]["levels"]["stop"] == 816.0 and s["judge"]["conviction"] == 2
    assert s["outcome"]["judge"] == {"status": "passed"} and s["outcome"]["twin"]["entry_t"] == "09:52"
    assert s["problems"] == "stop on the wrong side" and s["cost_usd"] == 0.2
    assert c["DLF"]["judge"] is None and c["DLF"]["not_debated"] == "monthly intraday debate cap reached"
