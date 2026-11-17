"""The intraday Brain: what the intraday Judge's own past calls teach the next one.

The mid-term Brain (sonar/brain.py) works from the ledger database; intraday
days live as files in paper/out/<mkt>/<date>/, so this module reads those.
The pattern is the same:

1. Scoring (code, at each settle). paper/intraday.py plays two shadow trades
   for EVERY debated candidate on the day's 1-minute bars, whether or not a
   book took it: the scanner's rule plan (what the Twin would have done) and
   the Judge's own levels (a No trade still names the levels it would have
   used). They land in settle.json under "shadow". So a refusal is scored
   against what the rule trade made, even when the Twin's two slots were full.
2. Track record (code, before each Judge call). A short block: the Judge's
   record so far, how the rule plan has done, the five most similar past
   setups and what happened in each, and any active lessons. Only days before
   the debate day are read, so nothing leaks backwards. Only the Judge reads
   it, to keep the bill small.
3. Lessons (one Opus call, at most weekly). Once 20 calls have been scored,
   the model may propose short rules of thumb from anonymised cases. Code keeps
   one only if it cites at least 8 real cases and names no stock or date,
   holds at most 8, and versions every change. Stored in paper/brain/<mkt>.json.

How a call is scored, in R after costs (1R = trigger-to-stop distance):
  - LONG or SHORT: right if the Judge's levels made money, wrong if not;
    "no fill" if its trigger never traded.
  - NO_TRADE: right if the rule trade lost at least 0.1R, wrong if it made at
    least 0.1R, flat in between, "no fill" if the rule trigger never traded.
"""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, List, Optional

import numpy as np

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "out"
BRAIN = ROOT / "paper" / "brain"

FLAT_R = 0.1             # a refused rule trade within +-0.1R is neither right nor wrong
SIMILAR_N = 5
MIN_CASES = 8            # a lesson must cite this many scored calls
REVIEW_AT = 20           # no review before this many scored calls exist
REVIEW_EVERY_DAYS = 7
REVIEW_MIN_NEW = 10      # scored calls since the last review
MAX_LESSONS = 8
MAX_ADD = 2
REVIEW_RESERVE_USD = 1.0     # a review runs only if this much of the month's intraday cap is left
NAME = {"in": "India", "us": "US"}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _num(x) -> Optional[float]:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------

def call_of(decision: Optional[str], rule_r: Optional[float], judge_r: Optional[float]) -> Optional[str]:
    if decision in ("LONG", "SHORT"):
        return "no fill" if judge_r is None else ("right" if judge_r > 0 else "wrong")
    if decision == "NO_TRADE":
        if rule_r is None:
            return "no fill"
        return "right" if rule_r <= -FLAT_R else "wrong" if rule_r >= FLAT_R else "flat"
    return None


def _r(t: Optional[dict]) -> Optional[float]:
    return _num(t.get("r_mult")) if t and t.get("status") == "closed" else None


def day_cases(folder: Path, mkt: str) -> List[dict]:
    """Every candidate of one settled day with its numbers, the Judge's call and both shadow results."""
    if not (folder / "settle.json").exists() or not (folder / "scan.json").exists():
        return []
    settle = _load(folder / "settle.json")
    shadow = {s["sym"]: s for s in settle.get("shadow") or []}
    if not shadow:
        return []                                   # settled before shadow scoring existed
    scan = _load(folder / "scan.json")
    talk = {d["sym"]: d for d in _load(folder / "debates.json")} if (folder / "debates.json").exists() else {}
    meta = scan.get("meta") or {}
    idx = _num(meta.get("index_move", meta.get("spy_move_today")))
    out = []
    for c in scan.get("candidates") or []:
        s, st = shadow.get(c["sym"]), c.get("stats") or {}
        if s is None:
            continue
        v = (talk.get(c["sym"]) or {}).get("verdict") or {}
        dec = v.get("decision")
        rule_r, judge_r = _r(s.get("rule")), _r(s.get("judge_levels"))
        last, vwap = _num(st.get("last")), _num(st.get("vwap"))
        out.append(dict(
            date=meta.get("date") or folder.name, sym=c["sym"], side=c.get("side", "long"),
            relvol=_num(st.get("relvol")), gap=_num(st.get("gap")), move_today=_num(st.get("move_today")),
            vs_vwap=(last / vwap - 1) if last and vwap else None, index_move=idx,
            decision=dec, judge_side=(s.get("judge_levels") or {}).get("side"),
            conviction=v.get("conviction"), rule_r=rule_r, judge_r=judge_r,
            call=call_of(dec, rule_r, judge_r)))
    return out


def cases(mkt: str, before: Optional[str] = None, out: Path = OUT) -> List[dict]:
    """All scored candidates for a market, oldest first; only days before `before` when given."""
    base = out / mkt
    if not base.is_dir():
        return []
    rows = []
    for p in sorted(base.glob("20*")):
        if p.is_dir() and (before is None or p.name < before):
            rows += day_cases(p, mkt)
    return rows


def record(cs: List[dict]) -> dict:
    """The Judge's calls and the rule plan, counted."""
    judged = [c for c in cs if c["decision"]]
    took = [c for c in judged if c["decision"] in ("LONG", "SHORT")]
    passed = [c for c in judged if c["decision"] == "NO_TRADE"]
    took_r = [c["judge_r"] for c in took if c["judge_r"] is not None]
    pass_rule = [c["rule_r"] for c in passed if c["rule_r"] is not None]
    rule = [c["rule_r"] for c in cs if c["rule_r"] is not None]
    cnt = lambda xs, k: sum(1 for c in xs if c["call"] == k)  # noqa: E731
    avg = lambda xs: round(float(np.mean(xs)), 2) if xs else None  # noqa: E731
    return dict(
        candidates=len(cs), calls=len(judged),
        taken=dict(n=len(took), filled=len(took_r), avg_r=avg(took_r), right=cnt(took, "right"),
                   wrong=cnt(took, "wrong")),
        passed=dict(n=len(passed), right=cnt(passed, "right"), wrong=cnt(passed, "wrong"),
                    flat=cnt(passed, "flat"), no_fill=cnt(passed, "no fill"), rule_avg_r=avg(pass_rule)),
        rule_plan=dict(n=len(rule), avg_r=avg(rule),
                       win_pct=round(100 * sum(r > 0 for r in rule) / len(rule)) if rule else None),
        scored=sum(1 for c in judged if c["call"] in ("right", "wrong", "flat")),
    )


FEATURES = ("relvol", "gap", "move_today", "vs_vwap", "index_move")


def _feat(c: dict, k: str) -> Optional[float]:
    x = c.get(k)
    if x is None:
        return None
    return math.log(x) if k == "relvol" and x > 0 else x


def similar(cs: List[dict], cand: dict, n: int = SIMILAR_N) -> List[dict]:
    """The n past candidates on the same side nearest to this one, each feature scaled by its spread."""
    pool = [c for c in cs if c["side"] == cand["side"]]
    if len(pool) <= n:
        return pool[::-1]
    spread = {}
    for k in FEATURES:
        xs = [v for c in pool if (v := _feat(c, k)) is not None]
        spread[k] = max(float(np.std(xs)), 1e-4) if len(xs) >= 3 else None

    def dist(c):
        d = 0.0
        for k in FEATURES:
            a, b = _feat(c, k), _feat(cand, k)
            if spread[k] and a is not None and b is not None:
                d += ((a - b) / spread[k]) ** 2
        return d
    return sorted(pool, key=dist)[:n]


# ---------------------------------------------------------------------------
# Lessons store
# ---------------------------------------------------------------------------

def _store_path(mkt: str, brain: Path = BRAIN) -> Path:
    return brain / f"{mkt}.json"


def load_store(mkt: str, brain: Path = BRAIN) -> dict:
    p = _store_path(mkt, brain)
    return _load(p) if p.exists() else dict(lessons=[], reviews=[])


def active_lessons(mkt: str, brain: Path = BRAIN) -> List[dict]:
    return [x for x in load_store(mkt, brain)["lessons"] if not x.get("dropped")]


# ---------------------------------------------------------------------------
# The block the Judge reads
# ---------------------------------------------------------------------------

def _pct(x) -> str:
    return "?" if x is None else f"{x * 100:+.1f}%"


def _rr(x) -> str:
    return "no fill" if x is None else f"{x:+.2f}R"


def memory_block(mkt: str, cand: dict, day: str, out: Path = OUT, brain: Path = BRAIN) -> Optional[str]:
    """A short text for the Judge, or None when there is nothing yet to remember."""
    cs = cases(mkt, before=day, out=out)
    lessons = active_lessons(mkt, brain)
    if not cs and not lessons:
        return None
    lines = [f"YOUR TRACK RECORD ({NAME[mkt]} intraday, scored by code after each close; R is the result over "
             "the stop distance after costs. Under about 30 cases every figure is weak evidence: quote the n, "
             "and let today's numbers come first)."]
    if cs:
        r = record(cs)
        t, p, rp = r["taken"], r["passed"], r["rule_plan"]
        lines.append(f"Calls so far: {r['calls']}. Trades you took: {t['n']}"
                     + (f" ({t['right']} won, {t['wrong']} lost, avg {_rr(t['avg_r'])})" if t["filled"] else "")
                     + f". No-trade calls: {p['n']}"
                     + (f" ({p['right']} right because the rule trade lost, {p['wrong']} wrong because it won, "
                        f"{p['flat'] + p['no_fill']} flat or never filled; the rule trades you refused averaged "
                        f"{_rr(p['rule_avg_r'])})" if p["n"] else "") + ".")
        if rp["n"]:
            lines.append(f"The scanner's rule plan on all {rp['n']} filled candidates: avg {_rr(rp['avg_r'])}, "
                         f"{rp['win_pct']}% made money.")
        st = cand.get("stats") or {}
        last, vwap = _num(st.get("last")), _num(st.get("vwap"))
        me = dict(side=cand.get("side", "long"), relvol=_num(st.get("relvol")), gap=_num(st.get("gap")),
                  move_today=_num(st.get("move_today")), vs_vwap=(last / vwap - 1) if last and vwap else None,
                  index_move=_num(cand.get("index_move")))
        sim = similar(cs, me)
        if sim:
            lines.append(f"Most similar past {me['side']} setups:")
            for c in sim:
                rv = f"{c['relvol']:.1f}x" if c["relvol"] else "?"
                you = (f"you said {c['decision']}" + (f" (conv {c['conviction']})" if c.get("conviction") else "")
                       if c["decision"] else "not debated")
                lines.append(f"- relvol {rv}, gap {_pct(c['gap'])}, today {_pct(c['move_today'])}, "
                             f"vs VWAP {_pct(c['vs_vwap'])}, index {_pct(c['index_move'])}: {you}; "
                             f"rule plan {_rr(c['rule_r'])}"
                             + (f"; your levels {_rr(c['judge_r'])}" if c["decision"] else "") + ".")
    if lessons:
        lines.append(f"LESSONS from the weekly review, each backed by at least {MIN_CASES} scored calls:")
        lines += [f"{i}. {x['text']}" for i, x in enumerate(lessons, 1)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The weekly lessons review
# ---------------------------------------------------------------------------

REVIEW_SYSTEM = (
    "You review the record of a three-part intraday trade review (Bull, Bear, Judge) for a small paper "
    "account. Each case is one stock flagged by a 15-minute opening-range breakout scanner, with the numbers "
    "known at the decision time, the Judge's call, and how two shadow trades then ended in R after costs: "
    "the scanner's fixed rule plan, and the Judge's own levels. Cases carry ids, not names. Your job is to "
    "find what the Judge should do differently, and to be honest when the record is too thin to say."
)
REVIEW = (
    "From the cases, propose at most {max_add} new lessons and name any current lessons the record no longer "
    "supports. A lesson is one or two plain sentences the Judge can apply at the decision time, built on "
    "numbers it sees (relative volume, gap, move so far, distance from VWAP, index move, side, conviction). "
    "It must cite at least {min_cases} case ids that show it, and must hold in most of the cases it applies "
    "to, not only the ones cited. A refusal is wrong when the rule plan made money: say so if the Judge "
    "refuses too much. Never name a stock or a date. Prefer no lesson to a weak one. The summary is three "
    "plain sentences on where the Judge's calls were right and where they were wrong."
)
LESSONS_SCHEMA = {
    "type": "object",
    "properties": {
        "lessons_to_add": {"type": "array", "items": {
            "type": "object",
            "properties": {"text": {"type": "string"}, "case_ids": {"type": "array", "items": {"type": "integer"}}},
            "required": ["text", "case_ids"], "additionalProperties": False}},
        "lesson_ids_to_drop": {"type": "array", "items": {"type": "integer"}},
        "summary": {"type": "string"},
    },
    "required": ["lessons_to_add", "lesson_ids_to_drop", "summary"],
    "additionalProperties": False,
}


def review_due(mkt: str, cs: List[dict], now: datetime, brain: Path = BRAIN) -> bool:
    n = record(cs)["scored"]
    if n < REVIEW_AT:
        return False
    done = [r for r in load_store(mkt, brain)["reviews"] if r.get("status") == "done"]
    if not done:
        return True
    last = done[-1]
    age = now - datetime.fromisoformat(last["created_utc"])
    return age >= timedelta(days=REVIEW_EVERY_DAYS) and n - (last.get("n_scored") or 0) >= REVIEW_MIN_NEW


def review(mkt: str, budget_left: float, call: Optional[Callable] = None, now: Optional[datetime] = None,
           out: Path = OUT, brain: Path = BRAIN) -> Optional[dict]:
    """Run the lessons review when due and affordable; returns the review row (with cost_usd) or None."""
    from . import brain as B
    from . import config as C
    now = now or datetime.now(timezone.utc)
    cs = cases(mkt, out=out)
    if not review_due(mkt, cs, now, brain):
        return None
    if budget_left < REVIEW_RESERVE_USD:
        log.info("intraday lessons review due but the month's budget is short")
        return None
    if call is None:
        from . import debate
        call = debate.api_call
    store = load_store(mkt, brain)
    lessons = [x for x in store["lessons"] if not x.get("dropped")]
    judged = [c for c in cs if c["decision"]]
    anon = [dict(case_id=i, **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in c.items()
                               if k not in ("sym", "date")}) for i, c in enumerate(judged)]
    shared = "CASES AND CURRENT LESSONS\n" + json.dumps(
        dict(record=record(cs), cases=anon, current_lessons=[dict(id=x["id"], text=x["text"]) for x in lessons]),
        separators=(",", ":"))
    version = max([r.get("version", 0) for r in store["reviews"]] or [0]) + 1
    row = dict(created_utc=now.isoformat(timespec="seconds"), version=version, n_scored=record(cs)["scored"])
    try:
        reply = call(C.DEBATE_MODEL_JUDGE, shared, REVIEW.format(max_add=MAX_ADD, min_cases=MIN_CASES), "medium",
                     LESSONS_SCHEMA, system=REVIEW_SYSTEM)
        res = json.loads(reply.text)
    except Exception as e:                      # a failed review costs a week, never the settle
        log.warning("intraday lessons review failed: %s %s", type(e).__name__, str(e)[:300])
        store["reviews"].append(dict(row, status="error", cost_usd=0))
        _save(mkt, store, brain)
        return None
    known = {c["case_id"] for c in anon}
    names = {c["sym"] for c in cs}
    today = now.strftime("%Y-%m-%d")
    dropped = 0
    for x in lessons:
        if x["id"] in {int(i) for i in res["lesson_ids_to_drop"]}:
            x["dropped"] = today
            dropped += 1
    room = MAX_LESSONS - (len(lessons) - dropped)
    current, added, rejected = [x["text"] for x in lessons], [], []
    next_id = max([x["id"] for x in store["lessons"]] or [0]) + 1
    for item in res["lessons_to_add"][:MAX_ADD]:
        text = " ".join(str(item["text"]).split())
        why = B.check_lesson(text, item["case_ids"], known, names, current + added, min_cases=MIN_CASES)
        if why is None and len(added) >= room:
            why = f"already {MAX_LESSONS} lessons"
        if why:
            rejected.append(f"{why}: {text[:120]}")
            continue
        ids = sorted({int(i) for i in item["case_ids"]} & known)
        store["lessons"].append(dict(id=next_id, version=version, text=text, n_cases=len(ids), added=today,
                                     cases=[f"{judged[i]['date']} {judged[i]['sym']}" for i in ids]))
        next_id += 1
        added.append(text)
    row.update(status="done", added=len(added), dropped=dropped, rejected=rejected,
               summary=" ".join(str(res["summary"]).split())[:1200], cost_usd=round(reply.cost_usd, 5))
    store["reviews"].append(row)
    _save(mkt, store, brain)
    return row


def _save(mkt: str, store: dict, brain: Path = BRAIN) -> None:
    brain.mkdir(parents=True, exist_ok=True)
    _store_path(mkt, brain).write_text(json.dumps(store, indent=1), encoding="utf-8")


# ---------------------------------------------------------------------------
# For the app
# ---------------------------------------------------------------------------

def summary(mkt: str, out: Path = OUT, brain: Path = BRAIN) -> dict:
    cs = cases(mkt, out=out)
    store = load_store(mkt, brain)
    done = [r for r in store["reviews"] if r.get("status") == "done"]
    return dict(record=record(cs), lessons=[x for x in store["lessons"] if not x.get("dropped")],
                last_review=done[-1] if done else None, min_cases=MIN_CASES, review_at=REVIEW_AT,
                review_every_days=REVIEW_EVERY_DAYS, max_lessons=MAX_LESSONS,
                calls={f"{c['date']}|{c['sym']}": dict(call=c["call"], rule_r=c["rule_r"], judge_r=c["judge_r"])
                       for c in cs})
