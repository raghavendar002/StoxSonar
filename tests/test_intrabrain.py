import importlib.util
import json
import pathlib
from datetime import datetime, timezone

import pandas as pd

from sonar import intrabrain as IB

spec = importlib.util.spec_from_file_location("intraday", pathlib.Path(__file__).parent.parent / "paper" / "intraday.py")
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)

TZ = "Asia/Kolkata"


def write_day(out, day, rows):
    """rows: (sym, side, decision, rule_r, judge_r, relvol)"""
    d = out / "in" / day
    d.mkdir(parents=True)
    cands, talks, shadow = [], [], []
    for sym, side, dec, rule_r, judge_r, rv in rows:
        cands.append(dict(sym=sym, side=side, stats=dict(relvol=rv, gap=0.001, move_today=0.004, last=101, vwap=100),
                          mechanical={}))
        if dec:
            talks.append(dict(sym=sym, verdict=dict(decision=dec, conviction=2, side_if_traded=side)))
        t = lambda r: dict(status="closed", r_mult=r) if r is not None else dict(status="not_triggered")  # noqa: E731
        shadow.append(dict(sym=sym, side=side, rule=t(rule_r), judge_levels=dict(t(judge_r), side=side)))
    (d / "scan.json").write_text(json.dumps(dict(meta=dict(date=day, index_move=0.002), candidates=cands)))
    (d / "debates.json").write_text(json.dumps(talks))
    (d / "settle.json").write_text(json.dumps(dict(mechanical={}, judge={}, shadow=shadow)))


def test_refusals_are_scored_against_the_rule_plan(tmp_path):
    write_day(tmp_path, "2026-11-16", [("GRASIM", "long", "NO_TRADE", 0.67, 0.3, 2.5),
                                       ("COALINDIA", "short", "NO_TRADE", 0.01, None, 1.8),
                                       ("SBIN", "long", "NO_TRADE", -1.0, -1.0, 1.6),
                                       ("TCS", "long", "NO_TRADE", None, None, 1.5)])
    cs = IB.cases("in", out=tmp_path)
    assert [c["call"] for c in cs] == ["wrong", "flat", "right", "no fill"]
    r = IB.record(cs)
    assert r["passed"]["n"] == 4 and r["passed"]["wrong"] == 1 and r["passed"]["right"] == 1
    assert r["scored"] == 3 and r["taken"]["n"] == 0


def test_memory_uses_only_earlier_days_and_stays_short(tmp_path):
    write_day(tmp_path, "2026-11-16", [("GRASIM", "long", "NO_TRADE", 0.67, 0.3, 2.5)])
    write_day(tmp_path, "2026-11-17", [("SBIN", "long", "LONG", -1.0, -1.0, 1.6)])
    cand = dict(sym="X", side="long", stats=dict(relvol=2.4, gap=0.0, move_today=0.01, last=100, vwap=99.5),
                index_move=0.001)
    assert IB.memory_block("in", cand, "2026-11-16", out=tmp_path, brain=tmp_path / "b") is None
    m = IB.memory_block("in", cand, "2026-11-17", out=tmp_path, brain=tmp_path / "b")
    assert "Calls so far: 1" in m and "+0.67R" in m and "SBIN" not in m and "GRASIM" not in m
    assert len(m.split()) < 160
    m2 = IB.memory_block("in", cand, "2026-11-18", out=tmp_path, brain=tmp_path / "b")
    assert "Calls so far: 2" in m2


def test_similar_picks_nearest_same_side():
    base = dict(gap=0.0, move_today=0.0, vs_vwap=0.0, index_move=0.0)
    pool = [dict(base, side="long", relvol=x, sym=str(x)) for x in (1.5, 2.0, 3.0, 5.0, 8.0, 12.0, 20.0)]
    pool.append(dict(base, side="short", relvol=3.0, sym="s"))
    got = IB.similar(pool, dict(base, side="long", relvol=3.1), n=2)
    assert {c["sym"] for c in got} == {"3.0", "2.0"}


class Reply:
    def __init__(self, text): self.text, self.cost_usd, self.input_tokens, self.output_tokens = text, 0.05, 1, 1


def test_review_waits_for_enough_calls_then_checks_lessons(tmp_path):
    rows = [(f"S{i}", "long", "NO_TRADE", 0.5 if i % 3 else -0.5, None, 2.0) for i in range(12)]
    write_day(tmp_path, "2026-11-16", rows)
    brain = tmp_path / "brain"
    now = datetime(2026, 11, 20, tzinfo=timezone.utc)
    assert IB.review("in", 20.0, call=lambda *a, **k: 1 / 0, now=now, out=tmp_path, brain=brain) is None
    write_day(tmp_path, "2026-11-17", [(f"T{i}", "long", "NO_TRADE", 0.4, None, 2.0) for i in range(10)])
    seen = {}

    def fake(model, shared, instruction, effort, schema=None, system=None):
        seen["shared"] = shared
        return Reply(json.dumps(dict(
            lessons_to_add=[dict(text="When relative volume is above 2x and price holds above VWAP, a long breakout "
                                      "has paid more often than not, so a refusal needs a specific reason.",
                                 case_ids=list(range(10))),
                            dict(text="Avoid S1 on Mondays.", case_ids=list(range(10)))],
            lesson_ids_to_drop=[], summary="The Judge refused too much.")))
    row = IB.review("in", 20.0, call=fake, now=now, out=tmp_path, brain=brain)
    assert row["added"] == 1 and len(row["rejected"]) == 1
    assert "S1" not in seen["shared"] and "2026-11-16" not in seen["shared"]
    assert len(IB.active_lessons("in", brain)) == 1
    # not again within a week
    assert IB.review("in", 20.0, call=fake, now=now, out=tmp_path, brain=brain) is None
    # too little budget left
    assert IB.review("in", 0.5, call=fake, now=datetime(2026, 12, 30, tzinfo=timezone.utc),
                     out=tmp_path, brain=brain) is None


def mk(rows, start="2026-11-16 09:31"):
    idx = pd.date_range(start, periods=len(rows), freq="1min", tz=TZ)
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


def test_shadow_scores_a_refusal_the_twin_book_never_took():
    b = mk([[100, 100.1, 99.9, 100], [100, 100.6, 100, 100.5], [100.5, 102, 100.4, 101.9]])
    scan = dict(candidates=[dict(sym="X", side="long", mechanical=dict(side="long", trigger=100.5, stop=99.5,
                                                                         target=101.5, latest_entry="14:00",
                                                                         cutoff="15:15"))])
    talks = {"X": dict(verdict=dict(decision="NO_TRADE", side_if_traded="long", trigger=100.5, stop=99.9,
                                    target=101.8))}
    sh = I.shadow("in", scan, talks, {"X.NS": b}, b.index[0])
    assert sh[0]["rule"]["reason"] == "target" and sh[0]["rule"]["r_mult"] > 0.5
    assert sh[0]["judge_levels"]["reason"] == "target" and sh[0]["judge_levels"]["side"] == "long"
    assert IB.call_of("NO_TRADE", sh[0]["rule"]["r_mult"], sh[0]["judge_levels"]["r_mult"]) == "wrong"


def test_judge_prompt_carries_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "SPEND", tmp_path / "spend.json")
    monkeypatch.setattr(I, "judge_memory", lambda *a: "YOUR TRACK RECORD test")
    seen = []

    class R:
        def __init__(self, text): self.text, self.cost_usd = text, 0.01

    def fake(model, shared, instruction, effort, schema=None, system=None):
        seen.append(instruction)
        if schema:
            return R(json.dumps(dict(decision="NO_TRADE", side_if_traded="long", trigger=100.2, stop=99.7,
                                     target=101.0, conviction=2, headline="h", title="t", text="x")))
        return R("argument")

    scan = dict(meta={"index_move": 0.001, "date": "2026-11-17"},
                candidates=[dict(sym="X", side="long", stats={"last": 100.0}, mechanical={}, bars_5m=[])])
    talks, _ = I.debate("in", scan, caller=fake)
    assert "YOUR TRACK RECORD" in seen[2] and "YOUR TRACK RECORD" not in seen[0] + seen[1]
    assert talks[0]["memory"] == "YOUR TRACK RECORD test"
