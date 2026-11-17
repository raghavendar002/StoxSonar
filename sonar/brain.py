"""The mid-term Brain: what past signals and past verdicts teach the next debate.

Four jobs, three of them plain code:

1. Track record (code). Before a debate, look up how signals like this one
   ended: the screen's own history (every v0.2 signal with a finished
   21-session result), the 25 most similar of those, and the Judge's own past
   verdicts. Only results that were finished before the signal day are used,
   so nothing leaks backwards. This goes into the fact pack the Bull, Bear and
   Judge all read.
2. Post-mortems (code). When a judged paper trade closes, record whether the
   verdict was right and by how much.
3. Scoreboard (code). Progress against the pass test fixed in the design:
   at 100 judged picks, Go must beat Avoid with a bootstrap 90% interval
   above zero, the Judge book must beat the take-everything Twin after costs
   and API fees, and conviction 4-5 must beat 1-2.
4. Lessons (one Opus call, at most weekly). Once enough judged trades have
   closed, the model proposes short rules of thumb from the anonymised cases.
   Code keeps a lesson only if it cites at least 8 real cases and names no
   stock, holds at most 12 at a time, and versions every change.

With few closed cases the Brain says so. A track record of n=3 is shown as
n=3, and the prompts tell the models to treat small samples as weak evidence.
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from . import config as C

log = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS mt_outcomes (
  debate_id INTEGER PRIMARY KEY, market TEXT, symbol TEXT, direction TEXT, signal_date TEXT,
  grade TEXT, regime TEXT, verdict TEXT, conviction INTEGER, wait_status TEXT,
  r REAL, ret REAL, excess REAL, exit_reason TEXT, exit_date TEXT, sessions INTEGER,
  mfe_r REAL, mae_r REAL, judge_r REAL, call TEXT, created_utc TEXT
);
CREATE TABLE IF NOT EXISTS mt_reviews (
  id INTEGER PRIMARY KEY, market TEXT, created_utc TEXT, version INTEGER, status TEXT,
  n_cases INTEGER, added INTEGER, dropped INTEGER, rejected TEXT, summary TEXT,
  input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL
);
"""

KNOWN_AFTER_DAYS = 35      # calendar days for a 21-session result to be finished before a signal
SIMILAR_N = 25
NOT_NAMES = {"RS", "ATR", "SMA", "GO", "R"}    # words a lesson may use that could also be tickers

LESSONS_SCHEMA = {
    "type": "object",
    "properties": {
        "lessons_to_add": {"type": "array", "items": {
            "type": "object",
            "properties": {"text": {"type": "string"},
                           "case_ids": {"type": "array", "items": {"type": "integer"}}},
            "required": ["text", "case_ids"], "additionalProperties": False}},
        "lesson_ids_to_drop": {"type": "array", "items": {"type": "integer"}},
        "summary": {"type": "string"},
    },
    "required": ["lessons_to_add", "lesson_ids_to_drop", "summary"],
    "additionalProperties": False,
}

REVIEW_SYSTEM = (
    "You review the record of a three-part stock review (Bull, Bear, Judge) for a small Indian "
    "retail account holding one to three months. Every case is a past signal the Judge ruled on, "
    "with the numbers known on the signal day and how the paper trade then ended, in R (1R = the "
    "entry-to-stop distance) after costs. Cases carry ids, not names. Your job is to find what "
    "the Judge should do differently, and to be honest when the record is too thin to say."
)

ACCOUNT = {"NSE": "a small Indian retail account", "US": "a small US cash account"}


def review_system(market: str) -> str:
    return REVIEW_SYSTEM.replace("a small Indian retail account", ACCOUNT.get(market, ACCOUNT["NSE"]))


REVIEW = (
    "From the cases, propose at most {max_add} new lessons and name any current lessons the record "
    "no longer supports.\n"
    "A lesson is one or two plain sentences the Judge can apply on the signal day, built on "
    "numbers that are in the fact pack (for example extension above the 50-day average, base "
    "depth, volume ratio, RS rank, regime, grade, conviction). It must cite at least {min_cases} "
    "case ids that show it, and it must hold in most of the cases it applies to, not just the "
    "ones you cite. Never name a stock or a date. Do not restate a current lesson. Prefer no "
    "lesson to a weak one: with a small or mixed record, return empty lists and say why in the "
    "summary. The summary is three or four plain sentences on how the Judge is doing: where its "
    "verdicts and its conviction were right, and where they were wrong."
)


def init(con) -> None:
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(mt_debates)")}
    if cols and "brain" not in cols:
        con.execute("ALTER TABLE mt_debates ADD COLUMN brain TEXT")
    # Lessons are kept per market, so an India lesson never reaches a US Judge (or the reverse).
    # Lessons written before this column existed were all India's.
    cols = {r[1] for r in con.execute("PRAGMA table_info(mt_lessons)")}
    if cols and "market" not in cols:
        con.execute("ALTER TABLE mt_lessons ADD COLUMN market TEXT NOT NULL DEFAULT 'NSE'")
    con.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _has(con, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone() is not None


def _num(x) -> Optional[float]:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


# ---------------------------------------------------------------------------
# 1. Track record for one candidate
# ---------------------------------------------------------------------------

def _stats(x: pd.DataFrame, sign: int) -> dict:
    """n, average R, win rate and return over 21 sessions for a set of past signals."""
    if not len(x):
        return dict(n=0)
    ret = sign * x["ret_21"]
    out = dict(n=int(len(x)), avg_r=round(float(x["r_21"].mean()), 2),
               median_r=round(float(x["r_21"].median()), 2),
               win_pct=round(float((x["r_21"] > 0).mean() * 100), 0),
               median_ret_pct=round(float(ret.median() * 100), 1))
    ex = (sign * (x["ret_21"] - x["bench_21"])).dropna()
    if len(ex):
        out["avg_excess_pct"] = round(float(ex.mean() * 100), 1)
    return out


SIMILAR_ON = ["rs_rank", "mansfield", "depth", "log_vol", "base_len"]


def _similar(hist: pd.DataFrame, v02: dict, n: int = SIMILAR_N) -> pd.DataFrame:
    """The n past signals nearest to this one on the screen's own fields
    (each scaled by its spread across the history)."""
    me = dict(rs_rank=_num(v02.get("rs_rank")), mansfield=_num(v02.get("mansfield")),
              depth=_num(v02.get("depth")), base_len=_num(v02.get("base_len")),
              log_vol=math.log(v) if (v := _num(v02.get("vol_ratio"))) and v > 0 else None)
    use = [k for k in SIMILAR_ON if me[k] is not None and hist[k].notna().sum() >= n and hist[k].std() > 0]
    if len(hist) < 2 * n or len(use) < 3:
        return hist.iloc[0:0]
    d = sum(((hist[k] - me[k]) / hist[k].std()) ** 2 for k in use)
    return hist.loc[d.dropna().nsmallest(n).index]


def screen_history(con, market: str, facts: dict) -> dict:
    """How the screen's earlier signals of this side and grade ended, using
    only results finished before this signal day."""
    if not _has(con, "events"):
        return {}
    up = facts["direction"] == "up"
    v02 = facts["v02"]
    cutoff = str((pd.Timestamp(facts["signal_date"]) - timedelta(days=KNOWN_AFTER_DAYS)).date())
    h = pd.read_sql_query(
        "SELECT grade, regime, rs_rank, mansfield, depth, vol_ratio, base_len, ret_21, bench_21, r_21 "
        "FROM events WHERE market=? AND direction=? AND trigger_date<=? AND ret_21 IS NOT NULL "
        "AND r_21 IS NOT NULL", con, params=(market, facts["direction"], cutoff))
    if not len(h):
        return {}
    for k in ("rs_rank", "mansfield", "depth", "vol_ratio", "base_len", "ret_21", "bench_21", "r_21"):
        h[k] = pd.to_numeric(h[k], errors="coerce")
    h["log_vol"] = np.log(h["vol_ratio"].where(h["vol_ratio"] > 0))
    sign = 1 if up else -1
    grade = h[h["grade"] == v02["grade"]]
    regime = facts["market"].get("regime")
    return dict(
        basis=("Every earlier signal from this screen on this side with a finished 21-session result, "
               "mostly replayed history, before costs. R is the result over the entry-to-stop distance. "
               "The screen's grades were tuned on part of this history, so it may flatter the screen."),
        same_grade=_stats(grade, sign),
        same_grade_and_regime=_stats(grade[grade["regime"] == regime], sign),
        most_similar=dict(_stats(_similar(h, v02), sign),
                          matched_on="RS rank, Mansfield, base depth, base length, volume ratio"),
    )


def _case(o: dict, facts: Optional[dict]) -> dict:
    """One closed judged pick as an anonymous case: signal-day numbers, verdict, ending."""
    f = facts or {}
    v02, ind = f.get("v02") or {}, f.get("indicators") or {}
    g = lambda d, k, nd=2: (round(x, nd) if (x := _num(d.get(k))) is not None else None)  # noqa: E731
    return dict(case_id=o["debate_id"], side="long" if o["direction"] == "up" else "shadow short",
                grade=o["grade"], regime=o["regime"], verdict=o["verdict"], conviction=o["conviction"],
                wait=o["wait_status"], rs_rank=g(v02, "rs_rank", 0), vol_ratio=g(v02, "vol_ratio", 1),
                base_depth=g(v02, "depth"), base_len=g(v02, "base_len", 0),
                dist_sma50=g(ind, "dist_sma50"), from_hi52=g(ind, "from_hi52"), atr_pct=g(ind, "atr_pct", 3),
                ret_63_before=g(ind, "ret_63"),
                r=g(o, "r"), best_r=g(o, "mfe_r"), worst_r=g(o, "mae_r"), ended=o["exit_reason"],
                sessions=o["sessions"], verdict_was=o["call"])


def _cases(con, market: str, before: Optional[str] = None) -> List[dict]:
    if not _has(con, "mt_outcomes"):
        return []
    q, args = "SELECT * FROM mt_outcomes WHERE market=?", [market]
    if before:
        q, args = q + " AND exit_date<?", args + [before]
    rows = pd.read_sql_query(q + " ORDER BY exit_date, debate_id", con, params=args).to_dict("records")
    out = []
    for o in rows:
        f = con.execute("SELECT facts FROM mt_facts WHERE market=? AND symbol=? AND direction=? AND signal_date=?",
                        (market, o["symbol"], o["direction"], o["signal_date"])).fetchone()
        out.append(_case(o, json.loads(f[0]) if f else None))
    return out


def _judge_record(cases: List[dict]) -> dict:
    d = pd.DataFrame(cases)
    if not len(d):
        return dict(closed=0)
    by = lambda col, keys: [dict({col: k}, closed=int(len(x)), avg_r=round(float(x["r"].mean()), 2),  # noqa: E731
                                 right_pct=round(float((x["verdict_was"] == "right").mean() * 100), 0))
                            for k in keys if len(x := d[d[col] == k])]
    d["conviction_band"] = np.where(d["conviction"] >= 4, "4-5", np.where(d["conviction"] <= 2, "1-2", "3"))
    return dict(closed=int(len(d)), by_verdict=by("verdict", ["Go", "Wait", "Avoid"]),
                by_conviction=by("conviction_band", ["1-2", "3", "4-5"]))


def context(con, market: str, facts: dict) -> dict:
    """The track record that goes into one candidate's fact pack."""
    cases = _cases(con, market, before=facts["signal_date"])
    side = "long" if facts["direction"] == "up" else "shadow short"
    same = [c for c in cases if c["side"] == side]
    ind = facts.get("indicators") or {}
    key = lambda c: abs((c["dist_sma50"] or 0) - (ind.get("dist_sma50") or 0))  # noqa: E731
    return dict(
        note=("How past signals and past verdicts ended. Small samples are weak evidence: under about "
              "30 cases, quote the n and do not lean on the figure."),
        screen_history=screen_history(con, market, facts),
        judge_record=_judge_record(cases),
        similar_judged_cases=[{k: v for k, v in c.items() if k != "case_id"}
                              for c in sorted(same, key=key)[:5]],
    )


def headline(ctx: dict) -> Optional[str]:
    """One line for the message: the nearest thing to a base rate for this signal."""
    h = (ctx or {}).get("screen_history") or {}
    for k, label in (("most_similar", "The {n} most similar past signals"),
                     ("same_grade_and_regime", "{n} past signals of this grade in this kind of market"),
                     ("same_grade", "{n} past signals of this grade")):
        s = h.get(k) or {}
        if s.get("n", 0) >= 20:
            return (label.format(n=s["n"]) + f": average {s['avg_r']:+.2f}R over 21 sessions, "
                    f"{s['win_pct']:.0f}% made money (before costs).")
    return None


# ---------------------------------------------------------------------------
# 2. Post-mortems
# ---------------------------------------------------------------------------

def _call(verdict: str, wait_status: Optional[str], r: float, judge_r: Optional[float]) -> Optional[str]:
    """Was the verdict right? `r` is the trade taken at the next open whatever
    the verdict; `judge_r` is the Judge book's own trade when a Wait triggered."""
    if verdict == "Go":
        return "right" if r > 0 else "wrong"
    if verdict == "Avoid":
        return "right" if r <= 0 else "wrong"
    if wait_status == "triggered":
        if judge_r is None:
            return None                      # the triggered trade is still running
        return "right" if judge_r > 0 else "wrong"
    return "right" if r <= 0 else "wrong"    # a Wait that never triggered kept you out


def postmortems(con, market: str) -> List[dict]:
    """Write one outcome row for every judged pick that has closed since the
    last pass. Returns the new rows."""
    init(con)
    d = pd.read_sql_query(
        "SELECT d.id AS debate_id, d.market, d.symbol, d.direction, d.signal_date, d.grade, d.verdict, "
        "d.conviction, d.wait_status, d.wait_date, p.regime, p.r, p.ret, p.excess, p.exit_reason, p.exit_date, "
        "p.sessions, p.mfe_r, p.mae_r FROM mt_debates d JOIN mt_picks p ON p.market=d.market AND p.book='debated' "
        "AND p.symbol=d.symbol AND p.direction=d.direction AND p.signal_date=d.signal_date "
        "WHERE d.market=? AND d.status='done' AND p.status='closed' "
        "AND d.id NOT IN (SELECT debate_id FROM mt_outcomes)", con, params=(market,))
    new = []
    for o in d.to_dict("records"):
        judge_r = None
        if o["wait_status"] == "watching":
            continue                          # the Wait has not resolved yet
        if o["wait_status"] == "triggered":
            j = con.execute("SELECT status, r FROM mt_picks WHERE market=? AND book='judge' AND symbol=? "
                            "AND direction=? AND signal_date=?",
                            (market, o["symbol"], o["direction"], o["wait_date"])).fetchone()
            judge_r = j[1] if j and j[0] == "closed" else None
        call = _call(o["verdict"], o["wait_status"], float(o["r"]), judge_r)
        if call is None:
            continue
        row = {k: o[k] for k in ("debate_id", "market", "symbol", "direction", "signal_date", "grade", "regime",
                                 "verdict", "conviction", "wait_status", "r", "ret", "excess", "exit_reason",
                                 "exit_date", "sessions", "mfe_r", "mae_r")}
        row.update(judge_r=judge_r, call=call, created_utc=_now())
        con.execute(f"INSERT OR IGNORE INTO mt_outcomes ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                    list(row.values()))
        new.append(row)
    con.commit()
    return new


# ---------------------------------------------------------------------------
# 3. Scoreboard: progress against the pass test
# ---------------------------------------------------------------------------

def _boot_diff(a: np.ndarray, b: np.ndarray, n: int = 4000) -> Optional[List[float]]:
    """90% bootstrap interval for mean(a) - mean(b)."""
    if len(a) < 5 or len(b) < 5:
        return None
    rng = np.random.default_rng(7)
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(n)]
    return [round(float(np.percentile(d, 5)), 2), round(float(np.percentile(d, 95)), 2)]


def scoreboard(con, market: str) -> dict:
    o = (pd.read_sql_query("SELECT * FROM mt_outcomes WHERE market=?", con, params=(market,))
         if _has(con, "mt_outcomes") else pd.DataFrame())
    p = pd.read_sql_query("SELECT book, r, source FROM mt_picks WHERE market=? AND status='closed'",
                          con, params=(market,))
    spend = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM mt_debates").fetchone()[0] if _has(con, "mt_debates") else 0
    spend += con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM mt_reviews").fetchone()[0] if _has(con, "mt_reviews") else 0
    mean = lambda x: round(float(x.mean()), 2) if len(x) else None  # noqa: E731
    go = o[o["verdict"] == "Go"]["r"].to_numpy(float) if len(o) else np.array([])
    avoid = o[o["verdict"] == "Avoid"]["r"].to_numpy(float) if len(o) else np.array([])
    hi = o[o["conviction"] >= 4] if len(o) else o
    lo = o[o["conviction"] <= 2] if len(o) else o
    judge, twin = p[p["book"] == "judge"]["r"], p[p["book"] == "twin"]["r"]
    n = int(len(o))
    board = dict(
        judged_closed=n, needed=C.BRAIN_TEST_AT, kill_at=C.BRAIN_KILL_AT,
        go=dict(n=int(len(go)), avg_r=mean(go)), avoid=dict(n=int(len(avoid)), avg_r=mean(avoid)),
        go_minus_avoid=round(float(go.mean() - avoid.mean()), 2) if len(go) and len(avoid) else None,
        go_minus_avoid_ci90=_boot_diff(go, avoid),
        judge_book=dict(n=int(len(judge)), avg_r=mean(judge)), twin_book=dict(n=int(len(twin)), avg_r=mean(twin)),
        conviction_high=dict(n=int(len(hi)), right_pct=round(float((hi["call"] == "right").mean() * 100), 0) if len(hi) else None),
        conviction_low=dict(n=int(len(lo)), right_pct=round(float((lo["call"] == "right").mean() * 100), 0) if len(lo) else None),
        right_pct=round(float((o["call"] == "right").mean() * 100), 0) if n else None,
        api_spend_usd=round(float(spend), 2),
    )
    if _has(con, "mt_debates"):
        v = pd.read_sql_query("SELECT verdict, COUNT(*) AS n FROM mt_debates WHERE market=? AND status='done' "
                              "GROUP BY verdict", con, params=(market,))
        board["verdicts"] = {r.verdict: int(r.n) for r in v.itertuples()}
        board["off"] = con.execute("SELECT COUNT(*) FROM mt_debates WHERE market=? "
                                   "AND status='not_debated_switched_off'", (market,)).fetchone()[0]
    ci = board["go_minus_avoid_ci90"]
    if n < C.BRAIN_TEST_AT:
        board["state"] = f"Too early: {n} of {C.BRAIN_TEST_AT} judged trades have closed."
    else:
        ok = bool(ci and ci[0] > 0 and board["judge_book"]["avg_r"] is not None
                  and board["twin_book"]["avg_r"] is not None
                  and board["judge_book"]["avg_r"] > board["twin_book"]["avg_r"]
                  and (hi["r"].mean() if len(hi) else -9) > (lo["r"].mean() if len(lo) else 9))
        board["state"] = ("Passing the test." if ok else
                          "Failing the test." + (" Past the kill line." if n >= C.BRAIN_KILL_AT else ""))
    return board


# ---------------------------------------------------------------------------
# 4. Lessons: one model call, at most weekly, checked by code
# ---------------------------------------------------------------------------

def active_lessons(con, market: str) -> List[dict]:
    """This market's live lessons; each market (NSE, US) learns on its own."""
    if not _has(con, "mt_lessons"):
        return []
    init(con)
    return [dict(id=r[0], version=r[1], text=r[2], n_cases=r[3], added=r[4]) for r in con.execute(
        "SELECT id, version, text, n_cases, added FROM mt_lessons WHERE dropped IS NULL AND market=? ORDER BY id",
        (market,))]


def review_due(con, market: str, now: datetime) -> bool:
    n = con.execute("SELECT COUNT(*) FROM mt_outcomes WHERE market=?", (market,)).fetchone()[0]
    if n < C.BRAIN_MIN_CASES:
        return False
    last = con.execute("SELECT created_utc, n_cases FROM mt_reviews WHERE market=? ORDER BY id DESC LIMIT 1",
                       (market,)).fetchone()
    if last is None:
        return True
    age = now - datetime.fromisoformat(last[0])
    return age >= timedelta(days=C.BRAIN_REVIEW_EVERY_DAYS) and n - (last[1] or 0) >= C.BRAIN_REVIEW_MIN_NEW


def check_lesson(text: str, case_ids: List[int], known_ids: set, names: set, current: List[str],
                 min_cases: Optional[int] = None) -> Optional[str]:
    """None when the lesson can be kept, else why not."""
    need = C.BRAIN_MIN_CASES if min_cases is None else min_cases
    text = " ".join(str(text).split())
    ids = {int(i) for i in case_ids}
    if len(ids & known_ids) < need:
        return f"cites {len(ids & known_ids)} real cases, needs {need}"
    if not 20 <= len(text) <= 320:
        return "not one or two sentences"
    for name in names:
        if len(name) >= 2 and name not in NOT_NAMES and re.search(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])", text):
            return "names a stock"
    if re.search(r"\b20\d\d\b", text):
        return "names a date"
    if text.lower() in {c.lower() for c in current}:
        return "repeats a current lesson"
    return None


def review(con, market: str, call: Optional[Callable] = None, now: Optional[datetime] = None,
           budget_left: Optional[float] = None) -> Optional[dict]:
    """Run the lessons review when it is due and affordable. Returns what
    changed, or None when nothing ran."""
    init(con)
    now = now or datetime.now(timezone.utc)
    if not review_due(con, market, now):
        return None
    from . import debate                     # here, not at the top: debate imports this module
    call = call or debate.api_call
    left = debate.budget_left(con, now) if budget_left is None else budget_left
    if left < C.DEBATE_RESERVE_USD:
        log.info("lessons review due but the month's budget is spent")
        return None
    cases = _cases(con, market)
    lessons = active_lessons(con, market)
    shared = "CASES AND CURRENT LESSONS\n" + json.dumps(
        dict(cases=cases, judge_record=_judge_record(cases), scoreboard=scoreboard(con, market),
             current_lessons=[dict(id=x["id"], text=x["text"], n_cases=x["n_cases"]) for x in lessons]),
        separators=(",", ":"))
    version = (con.execute("SELECT COALESCE(MAX(version), 0) FROM mt_reviews WHERE market=?",
                           (market,)).fetchone()[0] or 0) + 1
    base = dict(market=market, created_utc=now.isoformat(timespec="seconds"), version=version, n_cases=len(cases))

    def log_review(**kw):
        row = dict(base, **kw)
        con.execute(f"INSERT INTO mt_reviews ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
                    list(row.values()))
        con.commit()

    try:
        reply = call(C.DEBATE_MODEL_JUDGE, shared,
                     REVIEW.format(max_add=C.BRAIN_MAX_ADD, min_cases=C.BRAIN_MIN_CASES), "high",
                     LESSONS_SCHEMA, system=review_system(market))
        out = json.loads(reply.text)
    except Exception as e:                   # a failed review costs a week, never the day's run
        log.warning("lessons review failed: %s %s", type(e).__name__, str(e)[:300])
        log_review(status="error", added=0, dropped=0, cost_usd=0)
        return None
    known = {c["case_id"] for c in cases}
    names = {r[0].split(".")[0] for r in con.execute("SELECT DISTINCT symbol FROM mt_outcomes WHERE market=?",
                                                     (market,))}
    today = now.strftime("%Y-%m-%d")
    dropped = 0
    for lid in {int(i) for i in out["lesson_ids_to_drop"]} & {x["id"] for x in lessons}:
        con.execute("UPDATE mt_lessons SET dropped=? WHERE id=? AND market=?", (today, lid, market))
        dropped += 1
    room = C.BRAIN_MAX_LESSONS - (len(lessons) - dropped)
    current = [x["text"] for x in lessons]
    added, rejected = [], []
    for item in out["lessons_to_add"][:C.BRAIN_MAX_ADD]:
        text = " ".join(str(item["text"]).split())
        why = check_lesson(text, item["case_ids"], known, names, current + added)
        if why is None and len(added) >= room:
            why = f"already {C.BRAIN_MAX_LESSONS} lessons"
        if why:
            rejected.append(f"{why}: {text[:120]}")
            continue
        ids = sorted({int(i) for i in item["case_ids"]} & known)
        con.execute("INSERT INTO mt_lessons (market, version, text, cases, n_cases, added) VALUES (?,?,?,?,?,?)",
                    (market, version, text, json.dumps(ids), len(ids), today))
        added.append(text)
    log_review(status="done", added=len(added), dropped=dropped, rejected="\n".join(rejected) or None,
               summary=" ".join(str(out["summary"]).split())[:1200], input_tokens=reply.input_tokens,
               output_tokens=reply.output_tokens, cost_usd=round(reply.cost_usd, 5))
    return dict(version=version, added=added, dropped=dropped, rejected=rejected, summary=out["summary"],
                n_cases=len(cases), cost_usd=reply.cost_usd)


def last_review(con, market: str) -> Optional[dict]:
    if not _has(con, "mt_reviews"):
        return None
    r = con.execute("SELECT created_utc, version, n_cases, added, dropped, summary, rejected FROM mt_reviews "
                    "WHERE market=? AND status='done' ORDER BY id DESC LIMIT 1", (market,)).fetchone()
    return r and dict(date=r[0][:10], version=r[1], n_cases=r[2], added=r[3], dropped=r[4], summary=r[5],
                      rejected=r[6])
