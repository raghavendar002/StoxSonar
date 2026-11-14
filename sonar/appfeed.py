"""Feeds for the StoxSonar app (site/app/): one JSON file per market and horizon.

The app is a static page, so everything it shows is prepared here after each
run and published with the site:

    site/app/feed/mid-in.json     NSE mid-term: snapshot, history, books, debates
    site/app/feed/mid-us.json     US mid-term shadow list
    site/app/feed/intra-us.json   US intraday paper days (scanner, debates, both books)
    site/app/feed/intra-in.json   India intraday paper days
    site/app/feed/meta.json       when the feeds were built and what each holds

Every debate, mid-term or intraday, is turned into the same "case" shape
(bull, bear, judge, levels, what each book did with it, bars for a chart), so
the app has one detail view for all of them. Sources that do not exist yet
(no debates before the API key is set, no India intraday before it is built)
give an empty feed with the reason, never a missing file.

    python -m sonar.appfeed            # from the repository root, after run_daily.py
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger("stoxsonar.appfeed")
ROOT = Path(__file__).resolve().parent.parent
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MID_BOOKS = ["raw", "twin", "debated", "judge"]
INTRADAY = {"us": dict(code="US", currency="USD", capital=1000, index="SPY", tz="ET"),
            "in": dict(code="IN", currency="INR", capital=100000, index="NIFTY", tz="IST")}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _clean(x):
    """JSON the browser can parse: NaN and infinity become null, all the way down."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    return x


def _load(path: Path):
    return json.loads(re.sub(r"\bNaN\b", "null", path.read_text(encoding="utf-8")))


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(obj), separators=(",", ":"), default=str), encoding="utf-8")


def _has(con, table: str) -> bool:
    return con is not None and con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _rows(con, sql: str, args=()) -> list:
    cur = con.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _pct(x, digits=1) -> Optional[float]:
    return None if x is None else round(x * 100, digits)


# ---------------------------------------------------------------------------
# Mid-term
# ---------------------------------------------------------------------------

def history(site: Path) -> list:
    """One row per published session, oldest first, from the dated snapshots."""
    out = []
    for p in sorted(site.glob("20??-??-??.json")):
        try:
            s = _load(p)
        except (ValueError, OSError):
            continue
        out.append(dict(date=s.get("as_of", p.stem), regime=s.get("regime"),
                        buys_allowed=s.get("buys_allowed"), breadth=s.get("breadth") or {},
                        breakouts=len(s.get("breakouts") or []), breakdowns=len(s.get("breakdowns") or []),
                        open=len(s.get("open_signals") or [])))
    return out


def _mid_trade(p: Optional[dict]) -> Optional[dict]:
    """A mt_picks row as the app's trade shape."""
    if not p:
        return None
    return dict(status=p["status"], entry=p["entry_px"], entry_t=p["entry_date"], exit=p["exit_px"],
                exit_t=p["exit_date"], reason=p["exit_reason"], r=p["r"], ret_pct=_pct(p["ret"]),
                excess_pct=_pct(p["excess"]), sessions=p["sessions"],
                stop=p["stop"], target=p["target"], horizon=p["horizon"])


def _wait_text(v: dict) -> Optional[str]:
    if v.get("wait_kind") in (None, "none"):
        return None
    side = "above" if v["wait_kind"] == "close_above" else "below"
    vol = f" on at least {v['wait_min_volume_ratio']:g}x normal volume" if v.get("wait_min_volume_ratio") else ""
    return f"A close {side} {v['wait_level']:g}{vol}, within {v['wait_within_sessions']} sessions."


def mid_case(d: dict, facts: Optional[dict], picks: dict) -> dict:
    """One mt_debates row (with its fact pack and book rows) as a case."""
    v = json.loads(d["judge"]) if d.get("judge") else {}
    f = facts or {}
    v02, ind = f.get("v02") or {}, f.get("indicators") or {}
    up = d["direction"] == "up"
    stats = []
    for label, val in [("Grade", d.get("grade")), ("Score", v02.get("score")), ("RS rank", v02.get("rs_rank")),
                       ("Template", f"{v02['template']}/8" if v02.get("template") is not None else None),
                       ("Base", f"{v02['base_len']}d" if v02.get("base_len") else None),
                       ("Volume", f"{v02['vol_ratio']}x" if v02.get("vol_ratio") else None),
                       ("Vs 50-day", f"{ind['dist_sma50'] * 100:+.1f}%" if ind.get("dist_sma50") is not None else None),
                       ("From 52w high", f"{ind['from_hi52'] * 100:+.1f}%" if ind.get("from_hi52") is not None else None),
                       ("3-month", f"{ind['ret_63'] * 100:+.1f}%" if ind.get("ret_63") is not None else None),
                       ("Results due", f.get("next_results_date"))]:
        if val is not None:
            stats.append([label, str(val)])
    verdict = d.get("verdict") or v.get("verdict")
    key = (d["symbol"], d["direction"], d["signal_date"])
    twin = picks.get(("twin",) + key)
    return dict(
        id=f"{d['market']}-mid-{d['signal_date']}-{d['symbol']}-{d['direction']}",
        market="IN" if d["market"] == "NSE" else d["market"], horizon="mid",
        symbol=d["symbol"].replace(".NS", ""), name=None, date=d["signal_date"],
        side="long" if up else "short", grade=d.get("grade"),
        headline=("Breakout" if up else "Breakdown (shadow short)")
                 + (f" in a {f['market']['regime']} market" if (f.get("market") or {}).get("regime") else ""),
        stats=stats, bull=d.get("bull"), bear=d.get("bear"),
        judge=dict(verdict=verdict, tone={"Go": "go", "Wait": "wait", "Avoid": "avoid"}.get(verdict, "avoid"),
                   title=verdict, text=v.get("how_its_moving"), conviction=d.get("conviction"), leverage=None,
                   reasons_for=v.get("reasons_for") or [], reasons_against=v.get("reasons_against") or [],
                   invalidation=v.get("invalidation"), wait=_wait_text(v), wait_status=d.get("wait_status"),
                   horizon_sessions=v.get("horizon_sessions"),
                   levels=dict(entry_low=v.get("entry_low"), entry_high=v.get("entry_high"), stop=v.get("stop"),
                               target=v.get("target"), target_2=v.get("target_2") or None)),
        twin=dict(levels=dict(entry_low=v02.get("entry"), entry_high=v02.get("entry"), stop=v02.get("stop"),
                              target=(twin or {}).get("target"))) if v02 else None,
        outcome=dict(judge=_mid_trade(picks.get(("judge",) + key) or picks.get(("debated",) + key)),
                     judge_book="judge" if picks.get(("judge",) + key) else "debated",
                     twin=_mid_trade(twin)),
        bars=dict(tf="1d", rows=(f.get("daily_bars") or [])[-90:]),
        problems=d.get("level_problems"), cost_usd=d.get("cost_usd"), models=json.loads(d["models"]) if d.get("models") else None,
    )


def _book_rows(con, market: str) -> list:
    """Per book and side: counts and results after costs (the same sums as sonar.books.summary)."""
    out = []
    picks = _rows(con, "SELECT * FROM mt_picks WHERE market=?", (market,))
    for book in MID_BOOKS:
        for direction in ("up", "down"):
            x = [p for p in picks if p["book"] == book and p["direction"] == direction]
            if not x:
                continue
            closed = sorted(p["r"] for p in x if p["status"] == "closed" and p["r"] is not None)
            exc = [p["excess"] for p in x if p["status"] == "closed" and p["excess"] is not None]
            n = len(closed)
            out.append(dict(
                book=book, direction=direction, picks=len(x), closed=n,
                open=sum(p["status"] == "open" for p in x),
                avg_r=round(sum(closed) / n, 2) if n else None,
                median_r=round((closed[n // 2] + closed[(n - 1) // 2]) / 2, 2) if n else None,
                win_pct=round(100 * sum(r > 0 for r in closed) / n, 1) if n else None,
                total_r=round(sum(closed), 2) if n else None,
                avg_excess_pct=round(100 * sum(exc) / len(exc), 1) if exc else None))
    return out


def _pick_rows(con, market: str) -> list:
    out = []
    for p in _rows(con, "SELECT * FROM mt_picks WHERE market=? ORDER BY signal_date DESC, symbol", (market,)):
        out.append(dict(book=p["book"], symbol=p["symbol"].replace(".NS", ""), direction=p["direction"],
                        signal_date=p["signal_date"], grade=p["grade"], verdict=p["verdict"],
                        conviction=p["conviction"], status=p["status"], entry=p["entry_px"], entry_t=p["entry_date"],
                        exit=p["exit_px"], exit_t=p["exit_date"], reason=p["exit_reason"], sessions=p["sessions"],
                        horizon=p["horizon"], stop=p["stop"], target=p["target"], r=p["r"], ret_pct=_pct(p["ret"]),
                        excess_pct=_pct(p["excess"])))
    return out


def _mid_cases(con, market: str) -> list:
    if not _has(con, "mt_debates"):
        return []
    facts = {}
    if _has(con, "mt_facts"):
        for r in _rows(con, "SELECT * FROM mt_facts WHERE market=?", (market,)):
            try:
                facts[(r["symbol"], r["direction"], r["signal_date"])] = json.loads(r["facts"])
            except (TypeError, ValueError):
                pass
    picks = {}
    if _has(con, "mt_picks"):
        for p in _rows(con, "SELECT * FROM mt_picks WHERE market=?", (market,)):
            picks[(p["book"], p["symbol"], p["direction"], p["signal_date"])] = p
    rows = _rows(con, "SELECT * FROM mt_debates WHERE market=? AND status='done' "
                      "ORDER BY signal_date DESC, id DESC", (market,))
    return [mid_case(d, facts.get((d["symbol"], d["direction"], d["signal_date"])), picks) for d in rows]


def _us_signals(con) -> list:
    """The US shadow list: A/B signals from the last 60 calendar days, newest first."""
    if not _has(con, "events"):
        return []
    rows = _rows(con, "SELECT * FROM events WHERE market='US' AND grade IN ('A','B') AND source!='replay' "
                      "ORDER BY trigger_date DESC LIMIT 200")
    return [dict(symbol=r["symbol"], grade=r["grade"], direction=r["direction"], trigger_date=r["trigger_date"],
                 status=r["status"], sessions=int(r["sessions"] or 0), score=r["score"], rs_rank=r["rs_rank"],
                 regime=r["regime"],
                 stop_pct=round((r["stop"] / r["entry"] - 1) * 100, 1) if r["stop"] and r["entry"] else None,
                 ret_21_pct=_pct(r["ret_21"])) for r in rows]


def midterm(con, site: Path, market: str) -> dict:
    """market: 'NSE' or 'US'."""
    code = "IN" if market == "NSE" else "US"
    feed = dict(market=code, horizon="mid", currency="INR" if code == "IN" else "USD",
                as_of=None, snapshot=None, history=[], books=[], picks=[], cases=[], signals=[], notes=[])
    if market == "NSE":
        if (site / "data.json").exists():
            feed["snapshot"] = _load(site / "data.json")
            feed["as_of"] = feed["snapshot"].get("as_of")
        feed["history"] = history(site)
    else:
        feed["signals"] = _us_signals(con)
        last = con.execute("SELECT MAX(as_of) FROM runs WHERE market='US'").fetchone() if _has(con, "runs") else None
        feed["as_of"] = last[0] if last else None
        if not feed["as_of"]:
            feed["notes"].append("The US shadow list has not run yet. It starts once the mid-term "
                                 "Bull/Bear/Judge change (PR 9) is merged.")
    if _has(con, "mt_picks"):
        feed["books"] = _book_rows(con, market)
        feed["picks"] = _pick_rows(con, market)
    elif market == "NSE":
        feed["notes"].append("Paper books start once the mid-term Bull/Bear/Judge change (PR 9) is merged.")
    feed["cases"] = _mid_cases(con, market)
    if not feed["cases"] and market == "NSE":
        feed["notes"].append("No debates yet. Bull, Bear and Judge run on the first evening after PR 9 is "
                             "merged and the ANTHROPIC_API_KEY secret is set.")
    return feed


# ---------------------------------------------------------------------------
# Intraday
# ---------------------------------------------------------------------------

_HEAD = re.compile(r"^##\s+([A-Z][A-Z0-9.&-]*)\s*(?:\(([^)]*)\))?\s*,?\s*(.*)$")
_PART = re.compile(r"^-\s+\*\*(Bull|Bear|Judge)\s*:?\s*(.*?)\*\*\s*(.*)$")


def parse_debate_md(text: str) -> dict:
    """The dry run's debate.md: '## SYM (Name), headline' then Bull / Bear / Judge bullets."""
    out, cur = {}, None
    for line in text.splitlines():
        m = _HEAD.match(line)
        if m:
            cur = None
            if m.group(2) is not None:      # a stock heading has its name in brackets
                cur = out.setdefault(m.group(1), dict(name=m.group(2), headline=m.group(3).strip()))
            continue
        m = _PART.match(line.strip())
        if m and cur is not None:
            who, title, body = m.group(1).lower(), m.group(2).strip(" :."), m.group(3).strip()
            if who == "judge":
                body = body.lstrip(" ,.;:")
                cur["judge_title"], cur["judge_text"] = title, body[:1].upper() + body[1:]
            else:
                cur[who] = (title + " " + body).strip() if title else body
    return out


def _intra_trade(t: Optional[dict]) -> Optional[dict]:
    if not t:
        return None
    hhmm = lambda s: s[11:16] if s else None
    return dict(status=t.get("status"), entry=t.get("entry"), entry_t=hhmm(t.get("entry_t")), exit=t.get("exit"),
                exit_t=hhmm(t.get("exit_t")), reason=t.get("reason"), qty=t.get("qty"), pnl=t.get("pnl"),
                r=t.get("r_mult"))


def _book(settle: dict, capital: float) -> dict:
    trades = settle.get("trades") or []
    closed = [t for t in trades if t.get("status") == "closed"]
    return dict(end_cash=settle.get("end_cash"),
                pnl=round(sum(t.get("pnl") or 0 for t in closed), 2),
                r=round(sum(t.get("r_mult") or 0 for t in closed), 2),
                trades=len(closed), wins=sum((t.get("pnl") or 0) > 0 for t in closed),
                ret_pct=round((settle["end_cash"] / capital - 1) * 100, 2) if settle.get("end_cash") else None)


def intraday_day(folder: Path, mkt: str) -> Optional[dict]:
    """One day's scan.json, orders.json, settle.json and debate.md (or debates.json) as a day with cases."""
    cfg = INTRADAY[mkt]
    if not (folder / "scan.json").exists():
        return None
    scan = _load(folder / "scan.json")
    orders = _load(folder / "orders.json") if (folder / "orders.json").exists() else {}
    settle = _load(folder / "settle.json") if (folder / "settle.json").exists() else {}
    if (folder / "debates.json").exists():
        talk = {d["sym"]: d for d in _load(folder / "debates.json")}
    elif (folder / "debate.md").exists():
        talk = parse_debate_md((folder / "debate.md").read_text(encoding="utf-8"))
    else:
        talk = {}
    meta = scan.get("meta") or {}
    date = meta.get("date") or folder.name
    j_orders = {o["sym"]: o for o in orders.get("judge") or []}
    m_orders = {o["sym"]: o for o in orders.get("mechanical") or []}
    j_trades = {t["sym"]: t for t in (settle.get("judge") or {}).get("trades") or []}
    m_trades = {t["sym"]: t for t in (settle.get("mechanical") or {}).get("trades") or []}
    cases = []
    for c in scan.get("candidates") or []:
        sym, st, t = c["sym"], c.get("stats") or {}, talk.get(c["sym"], {})
        jo, mo = j_orders.get(sym), m_orders.get(sym) or c.get("mechanical")
        took = jo is not None
        debated = bool(t.get("bull") or t.get("judge_text"))
        verdict = ("Long" if took else "No trade") if (debated or orders) else None
        stats = []
        for label, val in [("Rel. volume", f"{st['relvol']:.1f}x" if st.get("relvol") else None),
                           ("Today", f"{st['move_today'] * 100:+.1f}%" if st.get("move_today") is not None else None),
                           ("Gap", f"{st['gap'] * 100:+.1f}%" if st.get("gap") is not None else None),
                           ("Last", f"{st['last']:.2f}" if st.get("last") else None),
                           ("VWAP", f"{st['vwap']:.2f}" if st.get("vwap") else None),
                           ("Opening range", f"{st['or_lo']:.2f} – {st['or_hi']:.2f}" if st.get("or_hi") else None),
                           ("Prev. close", f"{st['prev_close']:.2f}" if st.get("prev_close") else None),
                           ("5-min ATR", f"{st['atr5']:.2f}" if st.get("atr5") else None)]:
            if val is not None:
                stats.append([label, val])
        jt = _intra_trade(j_trades.get(sym))
        if jt is None and debated and not took:
            jt = dict(status="passed")
        cases.append(dict(
            id=f"{cfg['code']}-intra-{date}-{sym}", market=cfg["code"], horizon="intra", symbol=sym,
            name=t.get("name"), date=date, side="long", grade=None, headline=t.get("headline"),
            stats=stats, bull=t.get("bull"), bear=t.get("bear"),
            judge=dict(verdict=verdict, tone="go" if took else "avoid", title=t.get("judge_title") or verdict,
                       text=t.get("judge_text"), conviction=(jo or {}).get("conviction"),
                       leverage=(jo or {}).get("leverage", 1 if took else None),
                       reasons_for=[], reasons_against=[], invalidation=None, wait=None,
                       levels=dict(entry_low=jo["trigger"], entry_high=jo["trigger"], stop=jo["stop"],
                                   target=jo["target"], target_2=None) if took else None) if verdict else None,
            twin=dict(levels=dict(entry_low=mo["trigger"], entry_high=mo["trigger"], stop=mo["stop"],
                                  target=mo["target"])) if mo else None,
            outcome=dict(judge=jt, judge_book="judge", twin=_intra_trade(m_trades.get(sym))),
            bars=dict(tf="5m", rows=c.get("bars_5m") or []), problems=None, cost_usd=None, models=None))
    passed = {c["sym"] for c in scan.get("candidates") or []}
    return dict(
        date=date, status="dry_run" if "dry run" in (orders.get("note") or "").lower() else "live",
        note=orders.get("note"), checkpoint=(meta.get("checkpoint_et") or meta.get("checkpoint") or "")[11:16] or None,
        tz=cfg["tz"], index=dict(name=cfg["index"], move_pct=_pct(meta.get("spy_move_today", meta.get("index_move")), 2)),
        universe=meta.get("universe"), signals=meta.get("signals"),
        near_misses=[dict(symbol=n["sym"], relvol=round(n["relvol"], 2), move_pct=_pct(n.get("move_today"), 2),
                          dist_pct=_pct(n.get("dist_or_hi"), 2), passed=n["sym"] in passed)
                     for n in meta.get("near_misses") or []],
        books=dict(twin=_book(settle.get("mechanical") or {}, cfg["capital"]),
                   judge=_book(settle.get("judge") or {}, cfg["capital"])) if settle else None,
        cases=cases)


def intraday(paper: Path, mkt: str) -> dict:
    """All days for one market. Days live in paper/out/<mkt>/<date>/; the first
    US dry run sits directly in paper/out/<date>/."""
    cfg = INTRADAY[mkt]
    folders = [p for p in (paper / mkt).glob("*") if p.is_dir() and DAY.match(p.name)] if (paper / mkt).is_dir() else []
    if mkt == "us" and paper.is_dir():
        folders += [p for p in paper.glob("*") if p.is_dir() and DAY.match(p.name)]
    days = [d for d in (intraday_day(p, mkt) for p in sorted(folders, key=lambda p: p.name, reverse=True)) if d]
    notes = []
    if not days:
        notes.append("India intraday paper trading is not built yet: the scanner and its fixed-rule twin come first."
                     if mkt == "in" else "No US intraday days yet.")
    elif all(d["status"] == "dry_run" for d in days):
        notes.append("Dry run only so far: one test day with the Judge played by hand, to prove the plumbing. "
                     "Daily paper trading has not started.")
    return dict(market=cfg["code"], horizon="intra", currency=cfg["currency"], capital=cfg["capital"],
                as_of=days[0]["date"] if days else None, days=days, notes=notes)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(db: Path, site: Path, paper: Path) -> dict:
    con = sqlite3.connect(db) if db.exists() else None
    out = site / "app" / "feed"
    feeds = {"mid-in": midterm(con, site, "NSE"), "mid-us": midterm(con, site, "US"),
             "intra-in": intraday(paper, "in"), "intra-us": intraday(paper, "us")}
    meta = dict(built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), feeds={})
    for name, feed in feeds.items():
        _write(out / f"{name}.json", feed)
        meta["feeds"][name] = dict(as_of=feed.get("as_of"), cases=len(feed.get("cases") or [])
                                   + sum(len(d["cases"]) for d in feed.get("days") or []),
                                   days=len(feed.get("days") or feed.get("history") or []))
    _write(out / "meta.json", meta)
    if con is not None:
        con.close()
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=ROOT / "ledger" / "stoxsonar.db")
    ap.add_argument("--site", type=Path, default=ROOT / "site")
    ap.add_argument("--paper", type=Path, default=ROOT / "paper" / "out")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    meta = build(a.db, a.site, a.paper)
    log.info("app feeds: %s", meta["feeds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
