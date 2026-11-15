"""Run the mid-term books on real prices without touching the live ledger.

Copies the ledger, forgets its newest NSE run so the day is replayed, runs the
NSE day and the US shadow list against the copy, and writes what happened to
reports/midterm_check.md. No Telegram, no page, nothing live changes.

    python research/midterm_check.py [--limit N]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
import traceback
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run_daily  # noqa: E402


def table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_none_\n"
    cols = list(df.columns)
    rows = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for r in df.itertuples(index=False):
        rows.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in r) + " |")
    return "\n".join(rows) + "\n"


def real_debate(db: Path, tmp: Path) -> str:
    """One real debate on the newest live A/B signal, against the ledger copy.
    The key is put in place only for this call, so the replay above spends nothing."""
    import os
    from sonar import books, data, debate, engine, ledger, publish
    out = ["\n## One real debate\n\n"]
    key = os.environ.get("DEBATE_KEY")
    if not key:
        return out[0] + "No key given; skipped.\n"
    try:
        con = ledger.connect(db)
        books.init(con)
        ev = ledger.events_frame(con, "NSE")
        prices, bench = data.load_cache(tmp / "NSE.pkl")
        c = ev[(ev["source"] == "live") & ev["grade"].isin(["A", "B"]) & ev["symbol"].isin(list(prices))]
        c = c.sort_values("trigger_date", ascending=False).head(1)
        e = c.to_dict("records")[0]
        f = engine.compute_features(prices[e["symbol"]], bench)
        books.add_facts(con, "NSE", e, books.fact_pack(e, f, None, data.latest_vix("NSE"), None,
                                                       data.next_results_date(e["symbol"], e["trigger_date"])))
        os.environ["ANTHROPIC_API_KEY"] = key
        rows = debate.run_day(con, "NSE", c, e["trigger_date"])
        del os.environ["ANTHROPIC_API_KEY"]
        d = pd.read_sql_query("SELECT * FROM mt_debates WHERE market='NSE'", con).to_dict("records")[0]
        out.append(f"{e['symbol']} · {e['direction']} · grade {e['grade']} · signal {e['trigger_date']}\n\n"
                   f"Status **{d['status']}** · input tokens {d['input_tokens']} · output tokens "
                   f"{d['output_tokens']} · cost ${d['cost_usd']}\n\n")
        if d["status"] == "done":
            out.append(f"Levels used: {d['levels']} · problems: {d['level_problems']} · wait: {d['wait_status']}\n\n"
                       "Telegram message as it would be sent:\n\n```\n"
                       + publish.debate_telegram_text(e["trigger_date"], rows, [], [], d["cost_usd"]) + "\n```\n\n"
                       f"Bull:\n\n> {d['bull']}\n\nBear:\n\n> {d['bear']}\n\n"
                       "Judge:\n\n```json\n" + json.dumps(json.loads(d["judge"]), indent=1) + "\n```\n")
            out.append("\nPicks written:\n\n" + table(pd.read_sql_query(
                "SELECT book, symbol, verdict, conviction, levels, stop, target, horizon, max_buy FROM mt_picks "
                "WHERE book IN ('debated','judge')", con)))
    except Exception as ex:
        # Never print the exception's own text for an API failure: keep the log to its type and status
        out.append(f"Failed: {type(ex).__name__} {getattr(ex, 'status_code', '')}\n\n```\n"
                   + traceback.format_exc()[-1500:].replace(key or "\0", "***") + "\n```\n")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--debate", action="store_true",
                    help="also run ONE real Bull/Bear/Judge debate (needs DEBATE_KEY; costs about $0.20)")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "check.db"
    shutil.copy(ROOT / "ledger" / "stoxsonar.db", db)
    con = sqlite3.connect(db)
    # Forget the two newest NSE runs: Yahoo sometimes lacks the newest session
    # for most stocks, and the day replayed must be newer than the last run kept.
    last = [r[0] for r in con.execute(
        "SELECT DISTINCT as_of FROM runs WHERE market='NSE' ORDER BY as_of DESC LIMIT 2")]
    con.executemany("DELETE FROM runs WHERE market='NSE' AND as_of=?", [(d,) for d in last])
    con.commit()
    con.close()

    out = [f"# Mid-term books: real-data check\n\nLedger copy with the NSE runs of {', '.join(last)} forgotten "
           "and the newest session replayed. Nothing live was changed.\n"]
    extra = ["--limit", str(a.limit)] if a.limit else []
    for market in ("NSE", "US"):
        out.append(f"\n## {market}\n")
        try:
            rc = run_daily.main(["--market", market, "--db", str(db), "--site", str(tmp / "site"),
                                 "--cache", str(tmp / f"{market}.pkl")] + extra)
            out.append(f"Exit code {rc}.\n")
        except Exception:
            out.append("Run failed:\n\n```\n" + traceback.format_exc()[-3000:] + "\n```\n")
            continue
        con = sqlite3.connect(db)
        q = lambda sql: pd.read_sql_query(sql, con, params=(market,))  # noqa: E731
        out.append("Runs recorded:\n\n" + table(q(
            "SELECT as_of, stocks, regime, ROUND(stage2_share,3) stage2_share, new_events FROM runs "
            "WHERE market=? ORDER BY as_of DESC LIMIT 3")))
        out.append("\nSignals by source and grade:\n\n" + table(q(
            "SELECT source, direction, grade, COUNT(*) n, MAX(trigger_date) latest FROM events "
            "WHERE market=? GROUP BY 1,2,3 ORDER BY 1,2,3")))
        try:
            out.append("\nPicks by book and status:\n\n" + table(q(
                "SELECT book, direction, source, status, COUNT(*) n, ROUND(AVG(r),2) avg_r, "
                "ROUND(AVG(ret)*100,1) avg_ret_pct FROM mt_picks WHERE market=? GROUP BY 1,2,3,4")))
            out.append("\nEvery pick:\n\n" + table(q(
                "SELECT book, symbol, direction dir, signal_date, grade, status, entry_date, entry_px, "
                "exit_date, exit_px, exit_reason, sessions, ROUND(ret*100,1) ret_pct, r, mfe_r, mae_r "
                "FROM mt_picks WHERE market=? ORDER BY signal_date, symbol, book")))
            f = q("SELECT symbol, signal_date, LENGTH(facts) bytes, facts FROM mt_facts WHERE market=?")
            out.append(f"\nFact packs stored: {len(f)}"
                       + (f", average {int(f['bytes'].mean()):,} bytes.\n" if len(f) else ".\n"))
            if len(f):
                d = json.loads(f["facts"].iloc[0])
                d["daily_bars"], d["weekly_bars"] = d["daily_bars"][-2:], d["weekly_bars"][-2:]
                out.append("\nOne fact pack (bars cut to the last two):\n\n```json\n"
                           + json.dumps(d, indent=1) + "\n```\n")
        except Exception:
            out.append("Books tables unreadable:\n\n```\n" + traceback.format_exc()[-1500:] + "\n```\n")
        con.close()
    out.append("\n## Outside data the fact pack leans on\n\n")
    from sonar import data
    out.append(f"India VIX: {data.latest_vix('NSE')} · US VIX: {data.latest_vix('US')}\n\n")
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    out.append("Next results date from Yahoo: " + ", ".join(
        f"{t} {data.next_results_date(t, today)}" for t in
        ("RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "TATAMOTORS.NS", "AAPL")) + "\n")
    if a.debate:
        out.append(real_debate(db, tmp))
    site = tmp / "site" / "data.json"
    if site.exists():
        out.append("\n## Page summary rows\n\n```json\n"
                   + json.dumps(json.loads(site.read_text()).get("books"), indent=1) + "\n```\n")
    (ROOT / "reports" / "midterm_check.md").write_text("".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
