"""Append-only record of every signal and how it turned out.

A signal's identity and grade are written once, the day it is first seen, and
never changed. Only its lifecycle status and measured outcomes are updated
later. That is what makes the track record worth showing.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from . import config as C
from .engine import Event

FROZEN = ["engine_version", "market", "symbol", "direction", "trigger_date", "grade", "stage",
          "template", "rs_rank", "mansfield", "regime", "pivot", "entry", "base_len", "depth",
          "vol_ratio", "stop", "score", "first_seen_utc", "source"]
REAL = ("rs_rank", "mansfield", "pivot", "entry", "depth", "vol_ratio", "stop", "score")
OUTCOME = ["status", "status_date", "sessions"] + [f"{k}_{h}" for h in C.HORIZONS
                                                   for k in ("ret", "bench")] + ["r_21"]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  {", ".join(c + " " + ("REAL" if c in REAL else "TEXT") for c in FROZEN)},
  {", ".join(c + (" TEXT" if c in ("status", "status_date") else " REAL") for c in OUTCOME)},
  UNIQUE (engine_version, market, symbol, direction, trigger_date)
);
CREATE TABLE IF NOT EXISTS stage_daily (
  date TEXT, market TEXT, symbol TEXT, stage INTEGER, transition_to INTEGER,
  transition_day INTEGER, stage_age INTEGER, template INTEGER, rs_rank REAL, mansfield REAL,
  PRIMARY KEY (date, market, symbol)
);
CREATE TABLE IF NOT EXISTS runs (
  as_of TEXT, market TEXT, engine_version TEXT, stocks INTEGER, regime TEXT,
  stage2_share REAL, new_events INTEGER, created_utc TEXT,
  PRIMARY KEY (as_of, market, engine_version)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    # Columns added after the first ledger was written (v0.2: stop, score)
    have = {r[1] for r in con.execute("PRAGMA table_info(events)")}
    for c in FROZEN + OUTCOME:
        if c not in have:
            con.execute(f"ALTER TABLE events ADD COLUMN {c} {'REAL' if c in REAL else 'TEXT'}")
    return con


def last_run(con, market: str):
    row = con.execute("SELECT MAX(as_of) FROM runs WHERE market=? AND engine_version=?",
                      (market, C.ENGINE_VERSION)).fetchone()
    return row[0]


def record_events(con, events: Iterable[Event], market: str, as_of: str, mode: str,
                  after: str | None = None) -> int:
    """Insert new signals and refresh outcomes of known ones. Returns how many were new.

    mode "daily": only signals triggering after `after` (the previous run) are
    added; one on `as_of` is "live", one in between (a missed run being caught
    up) is "late". Older unseen signals are never back-inserted, so the live
    record cannot be padded after the fact. mode "replay": everything, as "replay".
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new = 0
    for ev in events:
        if mode == "daily" and after and ev.trigger_date <= after:
            _update(con, ev, market)
            continue
        d = ev.to_dict()
        d.update(engine_version=C.ENGINE_VERSION, market=market, first_seen_utc=now,
                 source="replay" if mode == "replay" else ("live" if ev.trigger_date == as_of else "late"))
        cur = con.execute(
            f"INSERT OR IGNORE INTO events ({', '.join(FROZEN + OUTCOME)}) "
            f"VALUES ({', '.join('?' * len(FROZEN + OUTCOME))})",
            [d.get(c) for c in FROZEN + OUTCOME])
        if cur.rowcount:
            new += 1
        else:
            _update(con, ev, market)
    con.commit()
    return new


def _update(con, ev: Event, market: str) -> None:
    d = ev.to_dict()
    con.execute(
        f"UPDATE events SET {', '.join(c + '=?' for c in OUTCOME)} "
        "WHERE engine_version=? AND market=? AND symbol=? AND direction=? AND trigger_date=?",
        [d.get(c) for c in OUTCOME] + [C.ENGINE_VERSION, market, ev.symbol, ev.direction,
                                       ev.trigger_date])


def record_day(con, states: pd.DataFrame, market: str, as_of: str, regime: str,
               stage2_share: float, new_events: int) -> None:
    day = states[states["date"] == pd.Timestamp(as_of)]
    con.executemany(
        "INSERT OR REPLACE INTO stage_daily VALUES (?,?,?,?,?,?,?,?,?,?)",
        [(as_of, market, r.symbol, int(r.stage),
          None if pd.isna(r.transition_to) else int(r.transition_to), int(r.transition_day),
          int(r.stage_age), int(r.template), None if pd.isna(r.rs_rank) else float(r.rs_rank),
          None if pd.isna(r.mansfield) else float(r.mansfield)) for r in day.itertuples()])
    con.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?,?,?)",
                (as_of, market, C.ENGINE_VERSION, len(day), regime, stage2_share, new_events,
                 datetime.now(timezone.utc).isoformat(timespec="seconds")))
    con.commit()


def events_frame(con, market: str) -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM events WHERE market=? AND engine_version=? "
                             "ORDER BY trigger_date DESC, grade, symbol",
                             con, params=(market, C.ENGINE_VERSION))


def track_record(ev: pd.DataFrame, sources: List[str], direction: str = "up") -> pd.DataFrame:
    """Per-grade results for signals old enough to have a 21-session outcome."""
    d = ev[(ev["source"].isin(sources)) & (ev["direction"] == direction)].copy()
    rows = []
    sign = 1 if direction == "up" else -1
    for g in ["A", "B", "C"]:
        x = d[d["grade"] == g]
        closed = x[x["status"].isin(["Confirmed", "Failed", "Faded"])]
        m = x.dropna(subset=["ret_21"])
        excess = sign * (m["ret_21"] - m["bench_21"])
        rows.append(dict(
            grade=g, signals=len(x), closed=len(closed),
            confirmed_pct=_pct((closed["status"] == "Confirmed").mean()) if len(closed) else None,
            failed_pct=_pct((closed["status"] == "Failed").mean()) if len(closed) else None,
            measured_21=len(m),
            avg_excess_21_pct=_pct(excess.mean()) if len(m) else None,
            median_excess_21_pct=_pct(excess.median()) if len(m) else None,
            win_pct_21=_pct((excess > 0).mean()) if len(m) else None,
            avg_r_21=round(float(m["r_21"].mean()), 2) if len(m) else None,
        ))
    return pd.DataFrame(rows)


def _pct(x) -> float:
    return round(float(x) * 100, 1)
