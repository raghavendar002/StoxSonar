"""The missed-run check: did all four books run, and did each one feed its Brain?

The four categories, each with its own Brain (nothing is shared between them):

  in-intra   India intraday   paper/out/in/<day>/   Brain: paper/brain/in.json
  us-intra   US intraday      paper/out/us/<day>/   Brain: paper/brain/us.json
  in-mid     India mid-term   ledger, market NSE    Brain: mt_outcomes / mt_lessons WHERE market='NSE'
  us-mid     US mid-term      ledger, market US     Brain: mt_outcomes / mt_lessons WHERE market='US'

For every market day of the last week this module works out, from the files
and the ledger alone, what happened: the run went through and the day's calls
were logged and scored ("learned"), the day had no candidates (nothing to
learn, said plainly), or something is missing. Then it repairs what it can:

  - an intraday scan that never ran is replayed from the day's 5-minute bars as
    it stood 15 minutes after the open (paper/intraday.py scan --day), so the
    Judge sees exactly what an on-time run would have; then the day is settled;
  - an intraday day that was never settled is settled (1-minute bars last ~7 days);
  - a mid-term run that never went through is started again (daily.yml);
  - mid-term candidates that never got a debate are debated.

Each repair is tried at most twice per day and category; after that it gives up
and says so. Anything missed, repaired or failed goes to Telegram. The result is
written to paper/health.json, which the app's Brain tab shows ("last learned").

    python -m sonar.watchdog            # check and repair
    python -m sonar.watchdog --dry-run  # check only
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "paper" / "out"
HEALTH = ROOT / "paper" / "health.json"
DB = ROOT / "ledger" / "stoxsonar.db"
log = logging.getLogger("watchdog")

CATS = {
    "in-intra": dict(name="India intraday", kind="intra", mkt="in", tz="Asia/Kolkata", index="^NSEI"),
    "us-intra": dict(name="US intraday", kind="intra", mkt="us", tz="America/New_York", index="SPY"),
    "in-mid": dict(name="India mid-term", kind="mid", mkt="NSE", tz="Asia/Kolkata", index="^NSEI"),
    "us-mid": dict(name="US mid-term", kind="mid", mkt="US", tz="America/New_York", index="SPY"),
}
# When each step is overdue, in the market's own clock (hours, minutes after midnight of the day)
DUE = {
    "in-intra": dict(scan=(10, 15), settle=(16, 30)),     # scan 09:31, settle 15:46 IST
    "us-intra": dict(scan=(10, 30), settle=(16, 45)),     # scan 09:46, settle 16:10 ET (02:40 IST)
    "in-mid": dict(run=(21, 30)),                         # cron-job.org 16:45 / 18:45 / 20:45 IST
    "us-mid": dict(run=(40, 0)),                          # next evening's 16:45 IST dispatch also runs the US list
}
# The first day each book was live; nothing before it is checked or rebuilt.
START = {"in-intra": "2026-11-16", "us-intra": "2026-11-16", "in-mid": "2026-11-16", "us-mid": "2026-11-13"}
LOOKBACK_DAYS = 7          # calendar days checked
MAX_TRIES = 2              # repairs per day, category and step
SETTLE_MAX_AGE = 6         # calendar days: Yahoo's 1-minute bars run out after about a week
REPLAY_MAX_AGE = 50        # calendar days: 5-minute bars last 60


# ---------------------------------------------------------------------------
# Market days
# ---------------------------------------------------------------------------

def market_days(index: str, tz: str, today: date) -> Optional[List[str]]:
    """The sessions in the lookback window, from the index's daily bars; None if Yahoo can't be reached."""
    try:
        import yfinance as yf
        df = yf.download(index, period="1mo", interval="1d", progress=False, auto_adjust=True)
        if not len(df):
            return None
        days = sorted({d.date() for d in pd.DatetimeIndex(df.index)})
    except Exception as e:                                       # fall back to weekdays
        log.warning("no market calendar for %s: %s", index, e)
        return None
    start = today - timedelta(days=LOOKBACK_DAYS)
    return [d.isoformat() for d in days if start <= d <= today]


def weekdays(today: date) -> List[str]:
    return [(today - timedelta(days=i)).isoformat() for i in range(LOOKBACK_DAYS, -1, -1)
            if (today - timedelta(days=i)).weekday() < 5]


def overdue(day: str, tz: str, hm, now: datetime) -> bool:
    h, m = hm
    at = pd.Timestamp(day).tz_localize(tz) + pd.Timedelta(hours=h, minutes=m)
    return pd.Timestamp(now).tz_convert(tz) >= at


# ---------------------------------------------------------------------------
# What happened on a day (files and ledger only, no network)
# ---------------------------------------------------------------------------

def _read(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def intra_day(mkt: str, day: str, out: Path = OUT) -> dict:
    """One intraday day: scanned?, settled?, how many calls the Brain scored."""
    d = out / mkt / day
    orders, scan, settle = _read(d / "orders.json"), _read(d / "scan.json"), _read(d / "settle.json")
    cands = len((scan or {}).get("candidates") or [])
    row = dict(date=day, scanned=orders is not None, replayed=bool((orders or {}).get("replayed")),
               candidates=cands, settled=settle is not None)
    if settle is not None:
        shadow = settle.get("shadow") or []
        row["scored"] = sum(1 for s in shadow if (s.get("rule") or {}).get("status") not in (None, "no_data"))
        row["twin_trades"] = sum(1 for t in (settle.get("mechanical") or {}).get("trades") or []
                                 if t.get("status") == "closed")
        row["judge_trades"] = sum(1 for t in (settle.get("judge") or {}).get("trades") or []
                                  if t.get("status") == "closed")
    if orders is None:
        row["state"] = "missed"
    elif cands == 0:
        row["state"] = "no_candidates"
    elif settle is None:
        row["state"] = "not_settled"
    elif "shadow" not in settle:
        row["state"] = "not_scored"          # settled before the Brain existed
    else:
        row["state"] = "learned"
    return row


def mid_day(con: Optional[sqlite3.Connection], market: str, day: str) -> dict:
    """One mid-term day: did the run cover it, and were its candidates debated and booked?"""
    row = dict(date=day, ran=False, candidates=0, debated=0, twin=0, closed=0)
    if con is None:
        row["state"] = "missed"
        return row
    has = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    from . import config as C
    if "runs" in has:
        r = con.execute("SELECT MIN(as_of) FROM runs WHERE market=? AND as_of>=? AND engine_version=?",
                        (market, day, C.ENGINE_VERSION)).fetchone()[0]
        row["ran"] = r is not None
        row["late"] = r is not None and r > day           # a later run picked the day's signals up as "late"
    if "events" in has:
        row["candidates"] = con.execute(
            # Only live signals are debated (a day picked up late by the next run is booked, not debated)
            "SELECT COUNT(*) FROM events WHERE market=? AND trigger_date=? AND source='live' "
            f"AND grade IN ({','.join('?' * len(C.DEBATE_GRADES))}) AND engine_version=?",
            (market, day, *C.DEBATE_GRADES, C.ENGINE_VERSION)).fetchone()[0]
    if "mt_debates" in has:
        row["debated"] = con.execute("SELECT COUNT(*) FROM mt_debates WHERE market=? AND signal_date=?",
                                     (market, day)).fetchone()[0]
    if "mt_picks" in has:
        row["twin"] = con.execute("SELECT COUNT(*) FROM mt_picks WHERE market=? AND signal_date=? AND book='twin'",
                                  (market, day)).fetchone()[0]
        row["closed"] = con.execute("SELECT COUNT(*) FROM mt_picks WHERE market=? AND exit_date=? "
                                    "AND status='closed'", (market, day)).fetchone()[0]
    live = (con.execute("SELECT COUNT(*) FROM events WHERE market=? AND source='live'", (market,)).fetchone()[0]
            if "events" in has else 0)
    if not row["ran"]:
        row["state"] = "missed"
    elif row["candidates"] and row["debated"] < row["candidates"] and live:
        row["state"] = "debates_missing"
    elif not row["candidates"]:
        row["state"] = "no_candidates"
    else:
        row["state"] = "learned"
    return row


# ---------------------------------------------------------------------------
# Repairs
# ---------------------------------------------------------------------------

def _sh(args: List[str]) -> bool:
    log.info("running %s", " ".join(args))
    r = subprocess.run(args, cwd=ROOT)
    return r.returncode == 0


def dispatch_daily() -> bool:
    """Start daily.yml again (it publishes any finished close it has not published)."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        log.info("no GITHUB_TOKEN; cannot restart daily.yml")
        return False
    import requests
    r = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/daily.yml/dispatches",
                      headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                      json={"ref": "main", "inputs": {"mode": "daily"}}, timeout=30)
    log.info("daily.yml dispatch: HTTP %s", r.status_code)
    return r.status_code == 204


def debate_day(market: str, day: str) -> bool:
    """Debate a mid-term day's candidates that never got one (a failed or skipped step)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    import run_daily                                         # noqa: E402  (repo root is on the path)
    from . import ledger
    con = ledger.connect(DB)
    try:
        run_daily.run_debates(con, market, day, ROOT / "site", [], telegram=True)
    finally:
        con.close()
    return True


def failed_runs(since: datetime, seen: List[int]) -> List[dict]:
    """daily.yml and intraday.yml runs that failed since `since`, not yet reported."""
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return []
    import requests
    out = []
    for wf in ("daily.yml", "intraday.yml"):
        try:
            r = requests.get(f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/runs",
                             headers={"Authorization": f"Bearer {token}"},
                             params={"per_page": 30, "created": f">={since:%Y-%m-%dT%H:%M:%SZ}"}, timeout=30)
            runs = r.json().get("workflow_runs") or []
        except Exception as e:
            log.warning("could not list %s runs: %s", wf, e)
            continue
        out += [dict(id=x["id"], workflow=wf, url=x["html_url"], created=x["created_at"])
                for x in runs if x.get("conclusion") == "failure" and x["id"] not in seen]
    return out


def _repair_intra(key, cat, day, r, now, today, tries, alerts, out) -> dict:
    """Re-run a missing intraday scan (replayed as of the checkpoint) and/or settle."""
    settle_due = overdue(day, cat["tz"], DUE[key]["settle"], now)
    if r["scanned"]:
        step = "settle" if settle_due and r["state"] in ("not_settled", "not_scored") else None
    else:
        step = "scan"
    if step is None:
        return r
    t = f"{key}:{day}:{step}"
    if tries.get(t) == -1:
        return dict(r, state="holiday")
    age = (today - date.fromisoformat(day)).days
    max_age = REPLAY_MAX_AGE if step == "scan" else SETTLE_MAX_AGE
    if tries.get(t, 0) >= MAX_TRIES or age > max_age:
        if tries.get(t) != 99:
            why = "too old to rebuild" if age > max_age else f"{MAX_TRIES} tries failed"
            alerts.append(f"{cat['name']} {day}: the {step} is still missing; gave up ({why})")
            tries[t] = 99
        return r
    tries[t] = tries.get(t, 0) + 1
    ok = True
    if step == "scan":
        ok = _sh([sys.executable, "paper/intraday.py", "scan", "--mkt", cat["mkt"], "--day", day])
        r = intra_day(cat["mkt"], day, out)
        if ok and not r["scanned"]:
            # The replay found no opening range: the exchange was shut (a holiday). Nothing to learn.
            tries[t] = -1
            return dict(r, state="holiday")
    if ok and settle_due and r["scanned"] and r["candidates"]:
        ok = _sh([sys.executable, "paper/intraday.py", "settle", "--mkt", cat["mkt"], "--day", day])
    r = intra_day(cat["mkt"], day, out)
    what = ("the scan had not run; replayed it as of 15 minutes after the open" if step == "scan"
            else "the day had not been settled; settled it")
    alerts.append(f"{cat['name']} {day}: {what}" + ("" if ok else " (the re-run failed; will try again)"))
    return r


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

def check(now: Optional[datetime] = None, repair: bool = True, out: Path = OUT, db: Path = DB,
          health: Path = HEALTH, calendar=market_days) -> dict:
    now = now or datetime.now(timezone.utc)
    prev = _read(health) or {}
    tries: Dict[str, int] = prev.get("tries") or {}
    alerts: List[str] = []
    cats = {}
    for key, cat in CATS.items():
        today = pd.Timestamp(now).tz_convert(cat["tz"]).date()
        days = calendar(cat["index"], cat["tz"], today)
        exact = days is not None
        days = days if exact else weekdays(today)
        rows = []
        for day in (d for d in days if d >= START[key]):
            due = DUE[key]
            if cat["kind"] == "intra":
                if not overdue(day, cat["tz"], due["scan"], now):
                    continue
                r = intra_day(cat["mkt"], day, out)
                if repair:
                    r = _repair_intra(key, cat, day, r, now, today, tries, alerts, out)
                rows.append(r)
            else:
                if not overdue(day, cat["tz"], due["run"], now):
                    continue
                con = sqlite3.connect(db) if db.exists() else None
                try:
                    r = mid_day(con, cat["mkt"], day)
                finally:
                    if con is not None:
                        con.close()
                if r["state"] == "missed" and not exact:
                    r["state"] = "missed_or_holiday"
                if repair and r["state"] in ("missed", "debates_missing"):
                    step = "run" if r["state"] == "missed" else "debate"
                    t = f"{key}:{day}:{step}"
                    if tries.get(t, 0) < MAX_TRIES:
                        tries[t] = tries.get(t, 0) + 1
                        ok = dispatch_daily() if step == "run" else debate_day(cat["mkt"], day)
                        alerts.append(f"{cat['name']} {day}: "
                                      + ("the evening run had not gone through; started it again" if step == "run"
                                         else f"{r['candidates'] - r['debated']} candidate(s) had no debate; debated them")
                                      + ("" if ok else " (could not, will try again)"))
                    elif tries.get(t) != 99:
                        alerts.append(f"{cat['name']} {day}: {step} still missing after {MAX_TRIES} tries; gave up")
                        tries[t] = 99
                rows.append(r)
        learned = [r for r in rows if r["state"] in ("learned", "no_candidates")]
        cats[key] = dict(name=cat["name"], days=rows[-10:], calendar="exchange" if exact else "weekdays",
                         last_ok=learned[-1]["date"] if learned else None,
                         last_learned=next((r["date"] for r in reversed(rows) if r["state"] == "learned"), None))
    seen = prev.get("reported_runs") or []
    fails = failed_runs(now - timedelta(days=1), seen) if repair else []
    for f in fails:
        alerts.append(f"{f['workflow']} failed at {f['created'][:16].replace('T', ' ')} UTC: {f['url']}")
    # keep only recent tries so the file stays small
    cutoff = (now - timedelta(days=LOOKBACK_DAYS + 3)).date().isoformat()
    tries = {k: v for k, v in tries.items() if k.split(":")[1] >= cutoff}
    res = dict(checked_utc=now.isoformat(timespec="seconds"), categories=cats, alerts=alerts, tries=tries,
               reported_runs=(seen + [f["id"] for f in fails])[-60:])
    if repair:
        health.parent.mkdir(parents=True, exist_ok=True)
        health.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def telegram_text(res: dict) -> str:
    lines = ["StoxSonar · missed-run check", ""] + [f"• {a}" for a in res["alerts"]] + [""]
    for c in res["categories"].values():
        lines.append(f"{c['name']}: last learned {c['last_learned'] or 'never'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="check only: no repairs, no file, no message")
    ap.add_argument("--telegram", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    res = check(repair=not a.dry_run)
    print(json.dumps(dict(alerts=res["alerts"], categories=res["categories"]), indent=1))
    if a.telegram and res["alerts"]:
        from . import publish
        try:
            publish.send_telegram(telegram_text(res))
        except Exception as e:
            log.warning("Telegram alert failed: %s", e)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    sys.exit(main())
