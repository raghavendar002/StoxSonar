import json
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
    assert f["days"] == [] and f["as_of"] is None and "not built yet" in f["notes"][0]


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
    meta = appfeed.build(tmp_path / "missing.db", site, ROOT / "paper" / "out")
    names = {p.name for p in (site / "app" / "feed").iterdir()}
    assert names == {"mid-in.json", "mid-us.json", "intra-in.json", "intra-us.json", "meta.json"}
    for n in names:
        text = (site / "app" / "feed" / n).read_text()
        assert "NaN" not in text
        json.loads(text, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert meta["feeds"]["intra-us"]["cases"] == 3 and meta["feeds"]["mid-in"]["as_of"] == "2026-11-13"
