import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sonar import books, brain, config as C, debate, ledger, publish  # noqa: E402
from tests.test_debate import FACTS, event, fake_caller, setup, verdict  # noqa: E402

NOW = datetime(2026, 3, 2, tzinfo=timezone.utc)


def close_pick(con, symbol, r, exit_date="2026-02-02", book="debated", signal_date="2026-01-05"):
    con.execute("UPDATE mt_picks SET status='closed', r=?, ret=?, excess=0, exit_reason=?, exit_date=?, "
                "sessions=10, mfe_r=1, mae_r=-1 WHERE symbol=? AND book=? AND signal_date=?",
                (r, r / 10, "target" if r > 0 else "stop", exit_date, symbol, book, signal_date))
    con.commit()


def judged(tmp_path, results):
    """results: (symbol, verdict, conviction, r). Each is debated, then its paper trade is closed."""
    con, ev = setup(tmp_path, [event(s) for s, *_ in results])
    for s, v, c, r in results:
        kw = dict(wait_kind="close_above", wait_level=103.0, wait_within_sessions=5) if v == "Wait" else {}
        debate.run_day(con, "NSE", ev[ev.symbol == s], "2026-01-05",
                       call=fake_caller(verdict(verdict=v, conviction=c, **kw)), now=NOW)
        if v == "Wait":
            con.execute("UPDATE mt_debates SET wait_status='expired' WHERE symbol=?", (s,))
        close_pick(con, s, r)
    return con, ev


def history(con, n=80, as_of="2025-06-02"):
    """Past screen signals with finished results: tight bases won, loose ones lost."""
    con.executescript(ledger.SCHEMA)
    for i in range(n):
        tight = i % 2 == 0
        con.execute("INSERT INTO events (engine_version, market, symbol, direction, trigger_date, grade, regime, "
                    "rs_rank, mansfield, depth, vol_ratio, base_len, ret_21, bench_21, r_21, source) "
                    "VALUES ('v', 'NSE', ?, 'up', ?, 'A', 'Healthy', ?, 5, ?, 3, 40, ?, 0.0, ?, 'replay')",
                    (f"H{i}.NS", as_of, 80 + i % 10, 0.08 if tight else 0.35,
                     0.05 if tight else -0.05, 0.5 if tight else -0.5))
    con.commit()


def test_a_verdict_is_right_or_wrong_by_what_the_trade_did():
    assert brain._call("Go", None, 1.2, None) == "right" and brain._call("Go", None, -1.0, None) == "wrong"
    assert brain._call("Avoid", None, -1.0, None) == "right" and brain._call("Avoid", None, 0.8, None) == "wrong"
    assert brain._call("Wait", "expired", -1.0, None) == "right"        # waiting kept you out of a loser
    assert brain._call("Wait", "expired", 2.0, None) == "wrong"         # it ran without you
    assert brain._call("Wait", "triggered", -1.0, 1.5) == "right"       # scored on the trade it led to
    assert brain._call("Wait", "triggered", 1.0, None) is None          # that trade is still running


def test_postmortems_are_written_once_and_only_for_closed_trades(tmp_path):
    con, ev = judged(tmp_path, [("A.NS", "Go", 4, 1.5), ("B.NS", "Avoid", 3, -1.0)])
    debate.run_day(con, "NSE", pd.DataFrame([event("C.NS", date="2026-01-06")]).pipe(
        lambda d: d), "2026-01-06", call=fake_caller(verdict()), now=NOW)        # no fact pack: never judged
    new = brain.postmortems(con, "NSE")
    assert {(o["symbol"], o["call"]) for o in new} == {("A.NS", "right"), ("B.NS", "right")}
    assert brain.postmortems(con, "NSE") == []
    b = brain.scoreboard(con, "NSE")
    assert b["judged_closed"] == 2 and b["go"]["avg_r"] == 1.5 and b["avoid"]["avg_r"] == -1.0
    assert b["go_minus_avoid"] == 2.5 and b["go_minus_avoid_ci90"] is None and b["state"].startswith("Too early")


def test_track_record_uses_only_results_finished_before_the_signal(tmp_path):
    con, _ = setup(tmp_path, [])
    history(con)
    history(con, n=40, as_of="2025-12-20")          # 16 days before the signal: results not yet known then
    facts = dict(FACTS, v02=dict(FACTS["v02"], rs_rank=85, mansfield=5, depth=0.08, vol_ratio=3, base_len=40))
    h = brain.screen_history(con, "NSE", facts)
    assert h["same_grade"]["n"] == 80 and h["same_grade"]["avg_r"] == 0.0
    assert h["most_similar"]["n"] == 25 and h["most_similar"]["avg_r"] == 0.5      # the tight bases
    assert h["same_grade_and_regime"]["n"] == 80
    line = brain.headline(dict(screen_history=h))
    assert "25 most similar" in line and "+0.50R" in line
    loose = brain.screen_history(con, "NSE", dict(facts, v02=dict(facts["v02"], depth=0.35)))
    assert loose["most_similar"]["avg_r"] == -0.5
    short = brain.screen_history(con, "NSE", dict(facts, direction="down"))
    assert short == {}


def test_the_debate_reads_the_track_record_and_keeps_what_it_read(tmp_path):
    con, ev = judged(tmp_path, [("A.NS", "Go", 4, -1.0)])
    brain.postmortems(con, "NSE")
    history(con)
    e2 = event("N.NS", date="2026-03-02")
    books.add_facts(con, "NSE", e2, dict(FACTS, symbol="N.NS", signal_date="2026-03-02"))
    log = []
    rows = debate.run_day(con, "NSE", pd.DataFrame([e2]), "2026-03-02", call=fake_caller(verdict(), log=log), now=NOW)
    pack = json.loads(log[0][3].split("\n", 1)[1])
    tr = pack["track_record"]
    assert tr["judge_record"]["closed"] == 1 and tr["judge_record"]["by_verdict"][0]["avg_r"] == -1.0
    assert tr["similar_judged_cases"][0]["verdict_was"] == "wrong" and "case_id" not in tr["similar_judged_cases"][0]
    assert "A.NS" not in log[0][3].replace('"symbol":"N.NS"', "")       # past cases carry no names
    assert tr["screen_history"]["same_grade"]["n"] == 80
    kept = json.loads(con.execute("SELECT brain FROM mt_debates WHERE symbol='N.NS'").fetchone()[0])
    assert kept["record"]["judge_record"]["closed"] == 1
    assert "Brain:" in publish.debate_telegram_text("2026-03-02", rows, [], [], 0.1) or rows[0]["base_rate"] is None


def test_a_past_case_that_closed_after_the_signal_is_not_shown(tmp_path):
    con, ev = judged(tmp_path, [("A.NS", "Go", 4, -1.0)])
    brain.postmortems(con, "NSE")
    assert brain.context(con, "NSE", dict(FACTS, signal_date="2026-01-20"))["judge_record"]["closed"] == 0
    assert brain.context(con, "NSE", dict(FACTS, signal_date="2026-02-03"))["judge_record"]["closed"] == 1


def review_caller(out, seen=None):
    def call(model, shared, instruction, effort, schema=None, system=None):
        if seen is not None:
            seen.append((model, shared, system, schema))
        return debate.Reply(json.dumps(out), 5000, 400, 0.12)
    return call


def nine(tmp_path):
    con, _ = judged(tmp_path, [(f"S{i}.NS", "Go" if i % 2 else "Avoid", 3, -1.0) for i in range(9)])
    brain.postmortems(con, "NSE")
    return con, [r[0] for r in con.execute("SELECT debate_id FROM mt_outcomes ORDER BY 1")]


def test_no_review_before_eight_closed_cases_or_twice_in_a_week(tmp_path):
    con, _ = judged(tmp_path, [(f"S{i}.NS", "Go", 3, -1.0) for i in range(7)])
    brain.postmortems(con, "NSE")
    assert brain.review(con, "NSE", call=review_caller({}), now=NOW) is None
    con.close()
    con, ids = nine(tmp_path / "b")
    out = dict(lessons_to_add=[], lesson_ids_to_drop=[], summary="Too thin to say.")
    assert brain.review(con, "NSE", call=review_caller(out), now=NOW)["added"] == []
    assert brain.review(con, "NSE", call=review_caller(out), now=NOW + timedelta(days=30)) is None   # nothing new
    assert debate.month_spend(con, "2026-03") >= 0.12                    # the review counts toward the cap


def test_lessons_are_kept_only_when_they_pass_the_checks(tmp_path):
    con, ids = nine(tmp_path)
    good = "When the close is more than 20% above the 50-day average, the Go verdicts lost; ask for a Wait."
    out = dict(lessons_to_add=[
        dict(text=good, case_ids=ids[:8]),
        dict(text="Stocks like S3 tend to fail after a breakout, so avoid them.", case_ids=ids[:8]),
        dict(text="Loose bases deeper than 30% failed in most cases, so lower conviction.", case_ids=ids[:5]),
        dict(text="A fourth lesson that should never be read because three is the limit per review.",
             case_ids=ids[:8])],
        lesson_ids_to_drop=[99], summary="Go has lost.")
    seen = []
    r = brain.review(con, "NSE", call=review_caller(out, seen), now=NOW)
    assert r["added"] == [good] and r["version"] == 1 and len(r["rejected"]) == 2
    assert any("names a stock" in x for x in r["rejected"]) and any("cites 5" in x for x in r["rejected"])
    assert seen[0][0] == C.DEBATE_MODEL_JUDGE and seen[0][2] == brain.review_system("NSE")
    assert "S3.NS" not in seen[0][1] and '"case_id"' in seen[0][1]       # the model sees ids, not names
    assert debate.lessons_now(con, "NSE") == [good]
    # the next debate is given the lesson
    e2 = event("N.NS", date="2026-03-02")
    books.add_facts(con, "NSE", e2, dict(FACTS, symbol="N.NS", signal_date="2026-03-02"))
    log = []
    debate.run_day(con, "NSE", pd.DataFrame([e2]), "2026-03-02", call=fake_caller(verdict(), log=log), now=NOW)
    assert json.loads(log[0][3].split("\n", 1)[1])["lessons"] == [good]
    # a later review can drop it
    con.execute("UPDATE mt_reviews SET n_cases=0, created_utc='2026-01-01T00:00:00+00:00'")
    lid = con.execute("SELECT id FROM mt_lessons").fetchone()[0]
    r2 = brain.review(con, "NSE", call=review_caller(dict(lessons_to_add=[], lesson_ids_to_drop=[lid],
                                                         summary="No longer holds.")), now=NOW)
    assert r2["dropped"] == 1 and r2["version"] == 2 and debate.lessons_now(con, "NSE") == []


def test_a_failed_review_is_logged_and_changes_nothing(tmp_path):
    con, ids = nine(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("503")
    assert brain.review(con, "NSE", call=boom, now=NOW) is None
    assert con.execute("SELECT status FROM mt_reviews").fetchone()[0] == "error"
    assert debate.lessons_now(con, "NSE") == []


def test_brain_page_and_message(tmp_path):
    con, ids = nine(tmp_path)
    publish.write_brain(con, "NSE", tmp_path / "site")
    page = (tmp_path / "site" / "brain.html").read_text()
    assert "9 of 100 needed" in page and "None yet" in page and "S0" in page
    closed = [dict(symbol="S0.NS", signal_date="2026-01-05", verdict="Avoid", conviction=3, r=-1.0,
                   exit_reason="stop", call="right")]
    text = publish.debate_telegram_text("2026-03-02", [], [], [], 0.5, closed,
                                        dict(version=1, n_cases=9, summary="Go has lost.", added=["Rule."], dropped=0))
    assert "CLOSED · S0" in text and "The verdict was right" in text and "New lesson: Rule." in text


def test_india_and_us_lessons_never_mix(tmp_path):
    con, ids = nine(tmp_path)
    good = "When the close is more than 20% above the 50-day average, the Go verdicts lost; ask for a Wait."
    r = brain.review(con, "NSE", call=review_caller(dict(lessons_to_add=[dict(text=good, case_ids=ids[:8])],
                                                         lesson_ids_to_drop=[], summary="s")), now=NOW)
    assert r["added"] == [good]
    assert debate.lessons_now(con, "NSE") == [good]
    assert debate.lessons_now(con, "US") == []            # the US Judge never reads an India lesson
    assert brain.active_lessons(con, "US") == []
    assert "US cash account" in brain.review_system("US") and "Indian" not in brain.review_system("US")


def test_old_lessons_without_a_market_are_india_s(tmp_path):
    import sqlite3
    con = sqlite3.connect(tmp_path / "old.db")
    con.executescript("CREATE TABLE mt_lessons (id INTEGER PRIMARY KEY, version INTEGER, text TEXT, cases TEXT, "
                      "n_cases INTEGER, added TEXT, dropped TEXT); CREATE TABLE mt_debates (id INTEGER PRIMARY KEY, brain TEXT);"
                      "INSERT INTO mt_lessons (version, text, n_cases, added) VALUES (1, 'old lesson', 8, '2026-01-01');")
    assert [x["text"] for x in brain.active_lessons(con, "NSE")] == ["old lesson"]
    assert brain.active_lessons(con, "US") == []


def test_us_debate_uses_the_us_account(tmp_path):
    seen = []

    def call(model, shared, instruction, effort, schema=None, system=None):
        seen.append(system)
        return debate.Reply(json.dumps(verdict()) if schema else "case", 100, 10, 0.01)
    debate.debate_one(dict(FACTS, market_code="US"), [], call)
    assert all(s and "US cash account" in s and "Rs 1 lakh" not in s for s in seen)
    assert "Rs 1 lakh" in debate.system_for("NSE")
