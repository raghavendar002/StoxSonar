import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sonar import config as C, watchdog as W  # noqa: E402


def cal(days):
    return lambda index, tz, today: [d for d in days if d <= today.isoformat()]


def write(out, mkt, day, cands=1, settle=True, shadow=True):
    d = out / mkt / day
    d.mkdir(parents=True)
    (d / "scan.json").write_text(json.dumps(dict(meta={}, candidates=[dict(sym=f"S{i}") for i in range(cands)])))
    (d / "orders.json").write_text(json.dumps(dict(decided="x", mechanical=[], judge=[])))
    if settle:
        s = dict(mechanical=dict(trades=[dict(status="closed")]), judge=dict(trades=[]))
        if shadow:
            s["shadow"] = [dict(sym="S0", rule=dict(status="closed"))] * cands
        (d / "settle.json").write_text(json.dumps(s))


def ledger_db(path, runs, events=()):
    con = sqlite3.connect(path)
    con.executescript("CREATE TABLE runs (as_of TEXT, market TEXT, engine_version TEXT);"
                      "CREATE TABLE events (market TEXT, trigger_date TEXT, source TEXT, grade TEXT, engine_version TEXT);"
                      "CREATE TABLE mt_debates (market TEXT, signal_date TEXT);"
                      "CREATE TABLE mt_picks (market TEXT, signal_date TEXT, book TEXT, exit_date TEXT, status TEXT);")
    con.executemany("INSERT INTO runs VALUES (?,?,?)", [(d, m, C.ENGINE_VERSION) for d, m in runs])
    con.executemany("INSERT INTO events VALUES (?,?,?,?,?)", [(m, d, "live", "A", C.ENGINE_VERSION) for m, d in events])
    con.commit()
    con.close()


NOW = datetime(2026, 11, 18, 18, 0, tzinfo=timezone.utc)      # Wed 23:30 IST, 13:00 New York


def test_states_learned_no_candidates_and_missed(tmp_path):
    out, db = tmp_path / "out", tmp_path / "l.db"
    write(out, "in", "2026-11-16", cands=4)
    write(out, "in", "2026-11-17", cands=0, settle=False)
    write(out, "us", "2026-11-16", cands=1)
    write(out, "us", "2026-11-17", cands=2, settle=True, shadow=False)
    ledger_db(db, [("2026-11-16", "NSE"), ("2026-11-17", "NSE"), ("2026-11-16", "US")],
              events=[("NSE", "2026-11-17")])
    res = W.check(now=NOW, repair=False, out=out, db=db, health=tmp_path / "h.json",
                  calendar=cal(["2026-11-16", "2026-11-17", "2026-11-18"]))
    c = res["categories"]
    assert [d["state"] for d in c["in-intra"]["days"]] == ["learned", "no_candidates", "missed"]
    assert c["in-intra"]["last_learned"] == "2026-11-16" and c["in-intra"]["days"][0]["scored"] == 4
    assert [d["state"] for d in c["us-intra"]["days"]] == ["learned", "not_scored", "missed"]
    # India mid-term: 16th no candidates, 17th had one and no debate; 18th overdue at 23:30 IST
    assert [d["state"] for d in c["in-mid"]["days"]] == ["no_candidates", "debates_missing", "missed"]
    assert [d["state"] for d in c["us-mid"]["days"]] == ["no_candidates"]          # 17th due tomorrow evening
    assert not (tmp_path / "h.json").exists()                                       # a dry run writes nothing


def test_repairs_are_tried_twice_then_given_up(tmp_path, monkeypatch):
    out, db, h = tmp_path / "out", tmp_path / "l.db", tmp_path / "h.json"
    write(out, "in", "2026-11-16", cands=1)
    for m in ("us",):
        write(out, m, "2026-11-16", cands=1)
    ledger_db(db, [("2026-11-16", "NSE"), ("2026-11-16", "US")])
    calls = []
    monkeypatch.setattr(W, "_sh", lambda args: calls.append(args[2:]) or False)   # every re-run fails
    monkeypatch.setattr(W, "dispatch_daily", lambda: calls.append(["daily"]) or True)
    monkeypatch.setattr(W, "failed_runs", lambda since, seen: [])
    kw = dict(out=out, db=db, health=h, calendar=cal(["2026-11-16", "2026-11-17"]))
    r1 = W.check(now=NOW, **kw)
    assert ["scan", "--mkt", "in", "--day", "2026-11-17"] in calls
    assert any("India intraday 2026-11-17" in a and "replayed" in a for a in r1["alerts"])
    assert any("India mid-term 2026-11-17" in a and "started it again" in a for a in r1["alerts"])
    assert ["daily"] in calls
    W.check(now=NOW, **kw)
    r3 = W.check(now=NOW, **kw)
    assert any("gave up" in a for a in r3["alerts"])
    n = len(calls)
    r4 = W.check(now=NOW, **kw)
    assert len(calls) == n and not r4["alerts"]                 # given up once, said once, then quiet
    assert json.loads(h.read_text())["categories"]["in-intra"]["last_learned"] == "2026-11-16"


def test_nothing_before_the_start_day_is_checked(tmp_path):
    res = W.check(now=NOW, repair=False, out=tmp_path, db=tmp_path / "none.db", health=tmp_path / "h.json",
                  calendar=cal(["2026-11-12", "2026-11-13", "2026-11-16"]))
    assert [d["date"] for d in res["categories"]["in-intra"]["days"]] == ["2026-11-16"]
    assert [d["date"] for d in res["categories"]["us-mid"]["days"]] == ["2026-11-13", "2026-11-16"]
