"""Bull, Bear and Judge on each day's candidates (mid-term, 1-3 months).

For every Grade A/B breakout or breakdown of the day (three at most), two
models argue the case for and against from the same frozen fact pack, and a
third rules: Go, Wait or Avoid, with entry zone, stop, target and a plain
description of how the stock is moving. Code then checks the Judge's levels
and falls back to v0.2's own when they break the rules.

Nothing here is trade advice yet. v0.2 has not passed its bar, so every
verdict is logged and scored against "take every pick" (sonar/books.py)
before anyone should lean on it. Breakdowns are shadow shorts: scored, never
sized.

Spend is metered from the API's own token counts and capped per calendar
month (config.DEBATE_MONTHLY_CAP_USD). When the cap is reached, debates stop
until the next month and the books keep scoring.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

import pandas as pd

from . import books
from . import config as C

log = logging.getLogger(__name__)

SYSTEM = (
    "You are one voice in a three-part review of a stock signal for a small Indian retail account "
    "(Rs 1 lakh, risk 0.5% per trade, holding one to three months, delivery only). A rule-based "
    "screen has flagged the stock. That screen has NOT yet proved it makes money, so its grade is a "
    "starting point, not evidence. Work only from the fact pack in the message: daily and weekly "
    "bars, indicators, the screen's own fields, the market regime and sector numbers. You have no "
    "news, no fundamentals and no knowledge of what happened after the signal date; do not guess at "
    "them or use anything you remember about this company's later price. Cite numbers from the fact "
    "pack for every claim. Prices are in the stock's own currency."
)

BULL = (
    "You are the Bull. Make the strongest honest case that acting on this signal is worth the risk: "
    "for a breakout, buying it; for a breakdown, shorting it. Cover trend and stage, the quality of "
    "the base, volume, strength against the index and the sector, and where a sensible stop and "
    "target sit. Say plainly what would prove you wrong. Do not oversell: a weak case stated "
    "honestly is more useful than a strong one invented. Under 280 words, plain prose."
)

BEAR = (
    "You are the Bear. Make the strongest honest case against acting on this signal: for a "
    "breakout, why the buy is likely to fail or is not worth the risk; for a breakdown, why the "
    "short is. Look for an extended price, a loose or late base, thin or fading volume, a weak "
    "market or sector, results due soon, a stop that is too wide for the reward, and anything in "
    "the bars the signal ignores. Say what would change your mind. Do not invent problems the "
    "numbers do not show. Under 280 words, plain prose."
)

JUDGE = (
    "You are the Judge. You have the fact pack and the Bull's and Bear's cases. Decide for the "
    "account described.\n"
    "- Go: act at the next open inside your entry zone.\n"
    "- Wait: the idea is sound but the price or proof is not there yet. Give ONE condition code can "
    "check on daily bars: a close above (or below) a level, optionally with volume at least some "
    "multiple of the 50-day average, within at most 10 sessions.\n"
    "- Avoid: the risk is not worth it.\n"
    "Most signals from this screen have not paid, so Go needs a reason the Bear could not answer, "
    "and Avoid is a normal, respectable verdict. When the market regime is Weak, a long needs more.\n"
    "Levels: for a breakout the stop is below the entry and the target above; for a breakdown "
    "(a shadow short) the stop is above and the target below. Keep the entry zone within 1 ATR of "
    "the signal close, the stop within 3 ATR of the entry, and the first target at least 1.5 times "
    "the entry-to-stop distance away. ATR is atr_pct times the close. Give levels even for Avoid, "
    "so the call can be scored.\n"
    "Conviction 1-5 is how sure you are of the verdict itself. how_its_moving is three or four "
    "plain sentences a non-expert can follow: the trend, the base, volume, and how the stock stands "
    "against its sector and the index. Each reason names a number from the fact pack. Weigh any "
    "lessons given under 'lessons' as rules of thumb from past calls, not as certainties."
)

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["Go", "Wait", "Avoid"]},
        "conviction": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "horizon_sessions": {"type": "integer", "enum": [21, 63]},
        "entry_low": {"type": "number"},
        "entry_high": {"type": "number"},
        "stop": {"type": "number"},
        "target": {"type": "number"},
        "target_2": {"type": "number", "description": "A second, further target, or 0 for none"},
        "wait_kind": {"type": "string", "enum": ["none", "close_above", "close_below"]},
        "wait_level": {"type": "number", "description": "0 when wait_kind is none"},
        "wait_min_volume_ratio": {"type": "number",
                                  "description": "Day's volume over its 50-day average; 0 for no volume test"},
        "wait_within_sessions": {"type": "integer", "description": "1 to 10; 0 when wait_kind is none"},
        "invalidation": {"type": "string"},
        "how_its_moving": {"type": "string"},
        "reasons_for": {"type": "array", "items": {"type": "string"}},
        "reasons_against": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "conviction", "horizon_sessions", "entry_low", "entry_high", "stop", "target",
                 "target_2", "wait_kind", "wait_level", "wait_min_volume_ratio", "wait_within_sessions",
                 "invalidation", "how_its_moving", "reasons_for", "reasons_against"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# The model call, metered
# ---------------------------------------------------------------------------

class Reply:
    def __init__(self, text: str, input_tokens: int, output_tokens: int, cost_usd: float):
        self.text, self.input_tokens, self.output_tokens, self.cost_usd = text, input_tokens, output_tokens, cost_usd


class Refused(RuntimeError):
    pass


def cost_usd(model: str, usage) -> float:
    """Dollars for one reply, from the API's own token counts."""
    p_in, p_out, p_read = C.DEBATE_PRICES[model]
    g = lambda k: getattr(usage, k, 0) or 0  # noqa: E731
    return (g("input_tokens") * p_in + g("cache_creation_input_tokens") * p_in * C.DEBATE_CACHE_WRITE
            + g("cache_read_input_tokens") * p_read + g("output_tokens") * p_out) / 1e6


def api_call(model: str, shared: str, instruction: str, effort: str, schema: Optional[dict] = None) -> Reply:
    """One message. `shared` (the fact pack) comes first and is cached, so the
    Bear's call re-reads what the Bull's call wrote."""
    import anthropic
    client = anthropic.Anthropic()
    out_cfg: dict = {"effort": effort}
    if schema is not None:
        out_cfg["format"] = {"type": "json_schema", "schema": schema}
    r = client.messages.create(
        model=model, max_tokens=12000, system=SYSTEM, output_config=out_cfg,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": shared, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": instruction}]}])
    if r.stop_reason == "refusal":
        raise Refused(f"{model} declined")
    if r.stop_reason == "max_tokens":
        raise RuntimeError(f"{model} ran out of output room")
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    u = r.usage
    tokens_in = (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0) \
        + (getattr(u, "cache_read_input_tokens", 0) or 0)
    return Reply(text, tokens_in, u.output_tokens or 0, cost_usd(model, u))


Caller = Callable[..., Reply]


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------

def month_spend(con, month: str) -> float:
    """Dollars spent on debates in `month` (YYYY-MM), every market."""
    row = con.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM mt_debates WHERE substr(created_utc, 1, 7)=?",
                      (month,)).fetchone()
    return float(row[0])


def budget_left(con, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    return C.DEBATE_MONTHLY_CAP_USD - month_spend(con, now.strftime("%Y-%m"))


# ---------------------------------------------------------------------------
# Candidates and the Judge's levels
# ---------------------------------------------------------------------------

def candidates(events: pd.DataFrame, as_of: str) -> List[dict]:
    """Today's live Grade A/B breakouts and breakdowns, best first: grade, then
    v0.2's score. Everything past DEBATE_MAX_PER_DAY is left to the books."""
    d = events[(events["trigger_date"] == as_of) & (events["source"] == "live")
               & events["grade"].isin(C.DEBATE_GRADES)].copy()
    d["_s"] = d["score"].fillna(-9.0)
    d = d.sort_values(["grade", "_s", "symbol"], ascending=[True, False, True])
    return d.drop(columns="_s").to_dict("records")


def check_levels(v: dict, facts: dict) -> List[str]:
    """Why the Judge's levels cannot be used; empty when they can."""
    up = facts["direction"] == "up"
    close = facts["indicators"]["close"]
    atr = (facts["indicators"]["atr_pct"] or 0) * close
    lo, hi, stop, target = v["entry_low"], v["entry_high"], v["stop"], v["target"]
    bad = []
    if not all(isinstance(x, (int, float)) and x > 0 for x in (lo, hi, stop, target)):
        return ["a level is missing or not positive"]
    if lo > hi:
        bad.append("entry zone is upside down")
    if atr <= 0:
        return bad + ["no ATR to measure against"]
    if abs(lo - close) > C.JUDGE_ENTRY_MAX_ATR * atr or abs(hi - close) > C.JUDGE_ENTRY_MAX_ATR * atr:
        bad.append("entry zone is more than 1 ATR from the signal close")
    mid = (lo + hi) / 2
    risk = mid - stop if up else stop - mid
    if (stop >= lo) if up else (stop <= hi):
        bad.append("stop is on the wrong side of the entry zone")
    elif risk > C.JUDGE_STOP_MAX_ATR * atr:
        bad.append("stop is more than 3 ATR from the entry")
    reward = target - mid if up else mid - target
    if risk > 0 and reward < C.JUDGE_TARGET_MIN_R * risk:
        bad.append("target is less than 1.5R away")
    return bad


def check_wait(v: dict, facts: dict) -> List[str]:
    if v["verdict"] != "Wait":
        return []
    bad = []
    if v["wait_kind"] not in ("close_above", "close_below") or not v["wait_level"] or v["wait_level"] <= 0:
        bad.append("Wait without a condition code can check")
    if not 1 <= int(v["wait_within_sessions"] or 0) <= C.WAIT_MAX_SESSIONS:
        bad.append("Wait window is not 1 to 10 sessions")
    return bad


def pick_from(v: dict, facts: dict, book: str, levels_ok: bool, signal_date: Optional[str] = None,
              signal_close: Optional[float] = None, source: str = "live") -> dict:
    """A paper trade for the debated or judge book. With unusable levels the
    trade falls back to v0.2's stop and time exit, and says so."""
    up = facts["direction"] == "up"
    v02 = facts["v02"]
    p = dict(market=facts.get("market_code", "NSE"), book=book, symbol=facts["symbol"],
             direction=facts["direction"], signal_date=signal_date or facts["signal_date"],
             grade=v02["grade"], score=v02.get("score"), regime=facts["market"]["regime"], source=source,
             signal_close=signal_close or v02["entry"], verdict=v["verdict"], conviction=int(v["conviction"]))
    if levels_ok:
        p.update(levels="judge", stop=float(v["stop"]), target=float(v["target"]),
                 horizon=int(v["horizon_sessions"]),
                 max_buy=float(v["entry_high"] if up else v["entry_low"]))
    else:
        p.update(levels="v02", stop=v02["stop"], target=None, horizon=C.HOLD_SESSIONS, max_buy=None)
    return p


# ---------------------------------------------------------------------------
# One debate
# ---------------------------------------------------------------------------

def shared_text(facts: dict, lessons: List[str]) -> str:
    return ("FACT PACK (frozen at the signal close; nothing after it is known)\n"
            + json.dumps(dict(facts, lessons=lessons), separators=(",", ":")))


def debate_one(facts: dict, lessons: List[str], call: Caller = api_call) -> dict:
    """Bull, Bear, Judge for one candidate. Returns the texts, the parsed
    verdict, token counts and cost. Raises if any call fails; the caller logs it."""
    shared = shared_text(facts, lessons)
    kind = "breakout (a long)" if facts["direction"] == "up" else "breakdown (a shadow short)"
    head = f"The signal is a {kind} in {facts['symbol']} on {facts['signal_date']}.\n\n"
    bull = call(C.DEBATE_MODEL_ARGUE, shared, head + BULL, "medium")
    bear = call(C.DEBATE_MODEL_ARGUE, shared, head + BEAR, "medium")
    judge = call(C.DEBATE_MODEL_JUDGE, shared,
                 f"{head}BULL'S CASE\n{bull.text}\n\nBEAR'S CASE\n{bear.text}\n\n{JUDGE}", "high", VERDICT_SCHEMA)
    v = json.loads(judge.text)
    parts = (bull, bear, judge)
    return dict(bull=bull.text, bear=bear.text, verdict=v,
                input_tokens=sum(p.input_tokens for p in parts),
                output_tokens=sum(p.output_tokens for p in parts),
                cost_usd=round(sum(p.cost_usd for p in parts), 5))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save(con, market: str, ev: dict, status: str, **kw) -> None:
    cols = dict(market=market, symbol=ev["symbol"], direction=ev["direction"], signal_date=ev["trigger_date"],
                grade=ev["grade"], status=status, created_utc=_now(),
                models=json.dumps([C.DEBATE_MODEL_ARGUE, C.DEBATE_MODEL_JUDGE]))
    cols.update(kw)
    con.execute(f"INSERT OR IGNORE INTO mt_debates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                list(cols.values()))
    con.commit()


def lessons_now(con) -> List[str]:
    return [r[0] for r in con.execute("SELECT text FROM mt_lessons WHERE dropped IS NULL ORDER BY id")]


def run_day(con, market: str, events: pd.DataFrame, as_of: str, call: Caller = api_call,
            now: Optional[datetime] = None) -> List[dict]:
    """Debate today's candidates. Returns one row per candidate for the
    message and the page. A candidate already debated is never debated twice."""
    out = []
    cands = candidates(events, as_of)
    lessons = lessons_now(con)
    for n, ev in enumerate(cands):
        key = (market, ev["symbol"], ev["direction"], ev["trigger_date"])
        if con.execute("SELECT 1 FROM mt_debates WHERE market=? AND symbol=? AND direction=? AND signal_date=?",
                       key).fetchone():
            continue
        row = dict(symbol=ev["symbol"], direction=ev["direction"], grade=ev["grade"])
        f = con.execute("SELECT facts FROM mt_facts WHERE market=? AND symbol=? AND direction=? AND signal_date=?",
                        key).fetchone()
        if n >= C.DEBATE_MAX_PER_DAY:
            _save(con, market, ev, "not_debated_daily_limit", cost_usd=0)
            out.append(dict(row, status="not_debated_daily_limit"))
            continue
        if f is None:
            _save(con, market, ev, "no_fact_pack", cost_usd=0)
            out.append(dict(row, status="no_fact_pack"))
            continue
        if budget_left(con, now) < C.DEBATE_RESERVE_USD:
            _save(con, market, ev, "not_debated_budget", cost_usd=0)
            out.append(dict(row, status="not_debated_budget"))
            continue
        facts = dict(json.loads(f[0]), market_code=market)
        try:
            d = debate_one(facts, lessons, call)
        except Exception as e:  # one failed debate must not stop the others or the day
            log.warning("debate failed for %s: %s", ev["symbol"], type(e).__name__)
            _save(con, market, ev, "refused" if isinstance(e, Refused) else "error", cost_usd=0)
            out.append(dict(row, status="error"))
            continue
        v = d["verdict"]
        level_problems = check_levels(v, facts)
        wait_problems = check_wait(v, facts)      # a Wait code cannot watch is logged, flagged, never triggered
        problems = level_problems + wait_problems
        ok = not level_problems
        watching = v["verdict"] == "Wait" and not problems   # a triggered Wait trades at the Judge's levels
        _save(con, market, ev, "done", bull=d["bull"], bear=d["bear"], judge=json.dumps(v),
              verdict=v["verdict"], conviction=int(v["conviction"]), levels="judge" if ok else "v02",
              level_problems="; ".join(problems) or None, wait_status="watching" if watching else None,
              input_tokens=d["input_tokens"], output_tokens=d["output_tokens"], cost_usd=d["cost_usd"])
        # The debated book always fills at the next open, so every verdict is scored the same way
        picks = [dict(pick_from(v, facts, "debated", ok), max_buy=None)]
        if v["verdict"] == "Go":
            picks.append(pick_from(v, facts, "judge", ok))
        books.add_picks(con, picks)
        out.append(dict(row, status="done", verdict=v["verdict"], conviction=int(v["conviction"]),
                        levels_ok=ok, problems=problems, v=v, cost_usd=d["cost_usd"],
                        regime=facts["market"]["regime"], close=facts["indicators"]["close"]))
    return out


# ---------------------------------------------------------------------------
# Waits: checked by code after every close, no model
# ---------------------------------------------------------------------------

def check_waits(con, market: str, frames: Dict[str, pd.DataFrame]) -> List[dict]:
    """Move each watched Wait to triggered or expired on the bars since its
    signal. A triggered Wait joins the judge book from its trigger day."""
    rows = pd.read_sql_query("SELECT * FROM mt_debates WHERE market=? AND wait_status='watching'",
                             con, params=(market,))
    changed = []
    for r in rows.to_dict("records"):
        f = frames.get(r["symbol"])
        v = json.loads(r["judge"])
        sd = pd.Timestamp(r["signal_date"])
        if f is None or sd not in f.index:
            continue
        i = f.index.get_loc(sd)
        after = f.iloc[i + 1:i + 1 + int(v["wait_within_sessions"])]
        up = r["direction"] == "up"
        status, when = None, None
        for d, bar in after.iterrows():
            vol_ok = not v["wait_min_volume_ratio"] or (
                bar.vol50 and bar.Volume >= v["wait_min_volume_ratio"] * bar.vol50)
            hit = bar.Close > v["wait_level"] if v["wait_kind"] == "close_above" else bar.Close < v["wait_level"]
            if hit and vol_ok:
                status, when = "triggered", d
                break
        if status is None and len(f) - 1 - i >= int(v["wait_within_sessions"]):
            status, when = "expired", after.index[-1]
        if status is None:
            continue
        note = None
        if status == "triggered":
            close = float(f.loc[when, "Close"])
            # The Judge's stop and target stand; if price has already run through either, there is no trade
            sane = (v["stop"] < close < v["target"]) if up else (v["target"] < close < v["stop"])
            if sane:
                facts = con.execute("SELECT facts FROM mt_facts WHERE market=? AND symbol=? AND direction=? "
                                    "AND signal_date=?", (market, r["symbol"], r["direction"],
                                                          r["signal_date"])).fetchone()
                p = pick_from(dict(v, verdict="Wait"), dict(json.loads(facts[0]), market_code=market), "judge",
                              True, signal_date=str(when.date()), signal_close=close, source="wait")
                p["max_buy"] = None      # the condition was the entry test; buy the next open
                books.add_picks(con, [p])
            else:
                status, note = "expired", "condition met but the stop or target was already passed"
        con.execute("UPDATE mt_debates SET wait_status=?, wait_date=?, level_problems=COALESCE(?, level_problems) "
                    "WHERE id=?", (status, str(when.date()), note, r["id"]))
        changed.append(dict(symbol=r["symbol"], direction=r["direction"], status=status, date=str(when.date()),
                            v=v, signal_date=r["signal_date"]))
    con.commit()
    return changed


def watched_symbols(con, market: str) -> List[str]:
    return [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM mt_debates WHERE market=? AND wait_status='watching'", (market,))]


# ---------------------------------------------------------------------------
# Record: how each verdict turned out
# ---------------------------------------------------------------------------

def verdict_record(con, market: str) -> List[dict]:
    """Closed 'debated' picks by verdict: the test of whether Go beats Avoid."""
    d = pd.read_sql_query("SELECT verdict, r, excess FROM mt_picks WHERE market=? AND book='debated' "
                          "AND status='closed'", con, params=(market,))
    out = []
    for verdict in ("Go", "Wait", "Avoid"):
        x = d[d["verdict"] == verdict]
        out.append(dict(verdict=verdict, closed=len(x),
                        avg_r=round(float(x["r"].mean()), 2) if len(x) else None,
                        win_pct=round(float((x["r"] > 0).mean() * 100), 1) if len(x) else None))
    return out
