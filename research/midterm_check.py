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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "check.db"
    shutil.copy(ROOT / "ledger" / "stoxsonar.db", db)
    con = sqlite3.connect(db)
    last = con.execute("SELECT MAX(as_of) FROM runs WHERE market='NSE'").fetchone()[0]
    con.execute("DELETE FROM runs WHERE market='NSE' AND as_of=?", (last,))
    con.commit()
    con.close()

    out = [f"# Mid-term books: real-data check\n\nLedger copy with the NSE run of {last} replayed. "
           "Nothing live was changed.\n"]
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
    site = tmp / "site" / "data.json"
    if site.exists():
        out.append("\n## Page summary rows\n\n```json\n"
                   + json.dumps(json.loads(site.read_text()).get("books"), indent=1) + "\n```\n")
    (ROOT / "reports" / "midterm_check.md").write_text("".join(out), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
