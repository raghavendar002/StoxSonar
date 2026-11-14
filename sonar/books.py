"""Mid-term books: every candidate signal turned into a paper trade and scored.

Four books run side by side (design: "Mid-term Bull/Bear/Judge"):
  raw      v0.2 as it trades today: Grade A/B breakouts, no buys in a Weak
           market, skip when the next open gaps past the buy ceiling
  twin     every candidate, longs and shadow shorts, no regime filter, always
           filled at the next open, at v0.2's levels: "take every pick"
  debated  every candidate the Judge ruled on, whatever the verdict, at the
           Judge's levels: shows how Go, Wait and Avoid each turned out
  judge    what the Judge would actually trade: Go picks, and Wait picks from
           the day their condition is met
judge against debated measures the Judge's picking; debated against twin
(same stocks) measures its levels.

A pick's identity and levels are written once; only its fill and exit are
filled in later, and once it has exited it never changes again. Exits are
decided by fixed rules on daily bars, so nothing here needs a model and the
books can be rebuilt from prices alone.

Exit rules, checked bar by bar from the day after the signal:
  * entry at the next open
  * stop: a bar trading through the stop exits at the stop, or at the open if
    it opened beyond it (gaps fill worse)
  * target, if set: a bar reaching it exits at the target, or at the open if
    it opened beyond it. A bar that touches both counts as the stop
  * time: the close `horizon` sessions after the signal
Results are after costs, in R (the entry-to-stop distance) and as return
against the market's benchmark.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from . import config as C
from . import portfolio as P
from .plan import trade_plan

BOOKS = ("raw", "twin", "debated", "judge")
NOTIONAL_FALLBACK = 25_000   # Rs, for the fixed depository charge when no plan sizes the trade
US_SLIPPAGE = 0.0005         # one-way, S&P 500 names; no commission, no STT

SCHEMA = """
CREATE TABLE IF NOT EXISTS mt_picks (
  id INTEGER PRIMARY KEY,
  market TEXT, book TEXT, symbol TEXT, direction TEXT, signal_date TEXT,
  grade TEXT, score REAL, regime TEXT, source TEXT, levels TEXT,
  signal_close REAL, stop REAL, target REAL, horizon INTEGER, max_buy REAL,
  status TEXT, entry_date TEXT, entry_px REAL, exit_date TEXT, exit_px REAL, exit_reason TEXT,
  sessions INTEGER, ret REAL, cost REAL, r REAL, bench_ret REAL, excess REAL,
  mfe_r REAL, mae_r REAL, created_utc TEXT, updated_utc TEXT, verdict TEXT, conviction INTEGER,
  UNIQUE (market, book, symbol, direction, signal_date)
);
CREATE TABLE IF NOT EXISTS mt_facts (
  market TEXT, symbol TEXT, direction TEXT, signal_date TEXT, facts TEXT, created_utc TEXT,
  PRIMARY KEY (market, symbol, direction, signal_date)
);
"""
# Written by later PRs; created now so the ledger's shape is settled once.
SCHEMA_LATER = """
CREATE TABLE IF NOT EXISTS mt_debates (
  id INTEGER PRIMARY KEY, market TEXT, symbol TEXT, direction TEXT, signal_date TEXT, grade TEXT,
  status TEXT, bull TEXT, bear TEXT, judge TEXT, verdict TEXT, conviction INTEGER,
  levels TEXT, level_problems TEXT, wait_status TEXT, wait_date TEXT, models TEXT,
  input_tokens INTEGER, output_tokens INTEGER, cost_usd REAL, created_utc TEXT,
  UNIQUE (market, symbol, direction, signal_date)
);
CREATE TABLE IF NOT EXISTS mt_lessons (
  id INTEGER PRIMARY KEY, version INTEGER, text TEXT, cases TEXT, n_cases INTEGER,
  added TEXT, dropped TEXT
);
"""
IDENTITY = ["market", "book", "symbol", "direction", "signal_date", "grade", "score", "regime",
            "source", "levels", "signal_close", "stop", "target", "horizon", "max_buy",
            "verdict", "conviction"]
RESULT = ["status", "entry_date", "entry_px", "exit_date", "exit_px", "exit_reason", "sessions",
          "ret", "cost", "r", "bench_ret", "excess", "mfe_r", "mae_r"]


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA + SCHEMA_LATER)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Which signals become picks
# ---------------------------------------------------------------------------

def in_raw(ev: dict) -> bool:
    """v0.2's own suggestions: Grade A/B breakouts, none in a Weak market."""
    return (ev["direction"] == "up" and ev["grade"] in ("A", "B")
            and not (C.NO_LONGS_WHEN_WEAK and ev["regime"] == "Weak"))


def in_twin(ev: dict) -> bool:
    """Every candidate: all breakouts (C grades too, scored for free) and the
    A/B breakdowns, which are shadow shorts."""
    if ev["direction"] == "up":
        return ev["grade"] in ("A", "B", "C")
    return ev["grade"] in ("A", "B")


def new_picks(events: pd.DataFrame, market: str, sources: Iterable[str]) -> List[dict]:
    """Raw and twin picks for the given ledger events, with v0.2's levels."""
    out = []
    for ev in events[events["source"].isin(list(sources))].to_dict("records"):
        if not ev.get("stop") or not ev.get("entry"):
            continue
        plan = trade_plan(ev["entry"], ev["stop"], ev["trigger_date"]) if ev["direction"] == "up" else None
        base = dict(market=market, symbol=ev["symbol"], direction=ev["direction"],
                    signal_date=ev["trigger_date"], grade=ev["grade"], score=ev.get("score"),
                    regime=ev["regime"], source=ev["source"], levels="v02",
                    signal_close=ev["entry"], stop=ev["stop"], target=None,
                    horizon=C.HOLD_SESSIONS, max_buy=plan["max_buy"] if plan else None)
        if in_raw(ev):
            out.append(dict(base, book="raw"))
        if in_twin(ev):
            out.append(dict(base, book="twin", max_buy=None))
    return out


def add_picks(con, picks: List[dict], source_override: Optional[str] = None) -> int:
    now, n = _now(), 0
    for p in picks:
        if source_override:
            p = dict(p, source=source_override)
        cur = con.execute(
            f"INSERT OR IGNORE INTO mt_picks ({', '.join(IDENTITY)}, status, created_utc, updated_utc) "
            f"VALUES ({', '.join('?' * len(IDENTITY))}, 'pending', ?, ?)",
            [p.get(c) for c in IDENTITY] + [now, now])
        n += cur.rowcount
    con.commit()
    return n


# ---------------------------------------------------------------------------
# Scoring one pick on daily bars
# ---------------------------------------------------------------------------

def cost_pct(market: str, entry: float, traded_value: Optional[float], notional: Optional[float]) -> float:
    """Round-trip cost as a share of the position's value."""
    if market == "US":
        return 2 * US_SLIPPAGE
    slip = P.slippage(traded_value or 0.0)
    value = notional or NOTIONAL_FALLBACK
    return (P.buy_cost(value) + P.sell_cost(value)) / value + 2 * slip


def score(pick: dict, f: pd.DataFrame) -> dict:
    """Fill and exit for one pick on its stock's daily bars `f` (Open/High/Low/
    Close plus `bench`, `traded_value`). Returns the RESULT fields; status is
    'pending' (no bar after the signal yet), 'open', 'closed' or 'skipped'."""
    sd = pd.Timestamp(pick["signal_date"])
    if sd not in f.index:
        return dict(status="pending")
    i = f.index.get_loc(sd)
    if i + 1 >= len(f):
        return dict(status="pending")
    up = pick["direction"] == "up"
    sign = 1 if up else -1
    O, H, L, Cl = (f[k].to_numpy(float) for k in ("Open", "High", "Low", "Close"))
    stop, target = pick["stop"], pick.get("target")
    entry = O[i + 1]
    res = dict(entry_date=str(f.index[i + 1].date()), entry_px=round(float(entry), 4))
    # max_buy is the entry limit: a long is skipped above it, a shadow short below it
    if pick.get("max_buy") and (entry > pick["max_buy"] if up else entry < pick["max_buy"]):
        return dict(res, status="skipped", exit_reason="gap past the entry limit")
    if pick["book"] in ("debated", "judge") and (entry <= stop if up else entry >= stop):
        return dict(res, status="skipped", exit_reason="opened beyond the stop")
    if up and entry <= stop and pick["book"] == "raw":
        return dict(res, status="skipped", exit_reason="opened below stop")
    risk = abs(entry - stop) / entry
    if risk <= 0:
        return dict(res, status="skipped", exit_reason="no room to stop")
    last = i + pick["horizon"]
    exit_px, reason, j = None, None, None
    for j in range(i + 1, min(last, len(f) - 1) + 1):
        hit_stop = L[j] <= stop if up else H[j] >= stop
        if hit_stop:
            gap = O[j] <= stop if up else O[j] >= stop
            exit_px, reason = (O[j] if gap else stop), "stop"
            break
        if target:
            hit_t = H[j] >= target if up else L[j] <= target
            if hit_t:
                gap = O[j] >= target if up else O[j] <= target
                exit_px, reason = (O[j] if gap else target), "target"
                break
        if j == last:
            exit_px, reason = Cl[j], "time"
            break
    j_end = j if exit_px is not None else len(f) - 1
    hi = H[i + 1:j_end + 1].max()
    lo = L[i + 1:j_end + 1].min()
    fav, adv = (hi / entry - 1, lo / entry - 1) if up else (1 - lo / entry, 1 - hi / entry)
    res.update(mfe_r=round(float(fav / risk), 2), mae_r=round(float(adv / risk), 2),
               sessions=int(j_end - i))
    if exit_px is None:
        mark = Cl[j_end]
        res.update(status="open", ret=round(float(sign * (mark / entry - 1)), 4))
        return res
    tv = f["traded_value"].iloc[i] if "traded_value" in f else None
    plan = trade_plan(pick["signal_close"], stop, pick["signal_date"]) if up else None
    notional = plan["value_rs"] if plan else None
    cost = cost_pct(pick["market"], entry, None if tv is None or pd.isna(tv) else float(tv), notional)
    ret = sign * (exit_px / entry - 1)
    b = f["bench"].iloc[j] / f["bench"].iloc[i + 1] - 1 if "bench" in f else np.nan
    bench = None if pd.isna(b) else float(b)
    res.update(status="closed", exit_date=str(f.index[j].date()), exit_px=round(float(exit_px), 4),
               exit_reason=reason, ret=round(float(ret), 4), cost=round(float(cost), 5),
               r=round(float((ret - cost) / risk), 3), bench_ret=None if bench is None else round(bench, 4),
               excess=None if bench is None else round(float(ret - cost - sign * bench), 4))
    return res


def update(con, market: str, frames: Dict[str, pd.DataFrame]) -> int:
    """Re-score every pick that has not finished. `frames` maps symbol to its
    feature frame. Returns how many picks closed or were skipped on this pass."""
    rows = pd.read_sql_query(
        "SELECT * FROM mt_picks WHERE market=? AND status IN ('pending','open')", con, params=(market,))
    done, now = 0, _now()
    for p in rows.to_dict("records"):
        f = frames.get(p["symbol"])
        if f is None:
            continue
        res = score(p, f)
        if res["status"] in ("closed", "skipped"):
            done += 1
        con.execute(f"UPDATE mt_picks SET {', '.join(c + '=?' for c in RESULT)}, updated_utc=? WHERE id=?",
                    [res.get(c) for c in RESULT] + [now, p["id"]])
    con.commit()
    return done


def open_symbols(con, market: str) -> List[str]:
    return [r[0] for r in con.execute(
        "SELECT DISTINCT symbol FROM mt_picks WHERE market=? AND status IN ('pending','open')", (market,))]


# ---------------------------------------------------------------------------
# Fact pack: what the debate will read, frozen on the signal day
# ---------------------------------------------------------------------------

def _r(x, nd=4):
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) or pd.isna(x) else round(float(x), nd)


def sector_stats(states: pd.DataFrame, prices: Dict[str, pd.DataFrame], sectors: Dict[str, str],
                 as_of: str) -> Dict[str, dict]:
    """Per sector on `as_of`, from our own prices: how many liquid members,
    what share are Advancing (stage 2), and their median 21- and 63-session
    returns. `sectors` maps a bare symbol (no .NS) to a sector name."""
    day = states[states["date"] == pd.Timestamp(as_of)] if len(states) else states
    rows = []
    for r in day.itertuples():
        sec = sectors.get(r.symbol.replace(".NS", ""))
        c = prices[r.symbol]["Close"] if r.symbol in prices else None
        if sec is None or c is None or len(c) < 64:
            continue
        rows.append((sec, r.stage == 2, c.iloc[-1] / c.iloc[-22] - 1, c.iloc[-1] / c.iloc[-64] - 1))
    if not rows:
        return {}
    d = pd.DataFrame(rows, columns=["sector", "adv", "r21", "r63"])
    return {sec: dict(sector=sec, members=int(len(x)), advancing_pct=_r(x["adv"].mean() * 100, 1),
                      median_ret_21=_r(x["r21"].median()), median_ret_63=_r(x["r63"].median()))
            for sec, x in d.groupby("sector")}


def fact_pack(ev: dict, f: pd.DataFrame, regime_row: Optional[pd.Series] = None,
              vix: Optional[float] = None, sector: Optional[dict] = None,
              results_date: Optional[str] = None) -> dict:
    """Numbers only, all known at the signal close. `sector` is this stock's
    row from sector_stats; `results_date` the next results date if known."""
    sd = pd.Timestamp(ev["trigger_date"])
    f = f.loc[:sd]
    row = f.iloc[-1]
    c = f["Close"]
    daily = f.iloc[-120:][["Open", "High", "Low", "Close", "Volume"]]
    ohlcv = f[["Open", "High", "Low", "Close", "Volume"]]
    wk = ohlcv.groupby(ohlcv.index.to_period("W-FRI"))
    weekly = wk.agg({"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"})
    # Each week is labelled by its last session, so the signal week is never dated after the signal
    weekly.index = pd.DatetimeIndex(wk.apply(lambda g: g.index.max()))
    weekly = weekly.dropna().iloc[-52:]

    def bars(df):
        return [[str(d.date()), *(_r(v, 2) for v in r[:4]), int(r[4])] for d, r in zip(df.index, df.to_numpy())]

    def ret(n):
        return _r(c.iloc[-1] / c.iloc[-1 - n] - 1) if len(c) > n else None

    plan = trade_plan(ev["entry"], ev["stop"], ev["trigger_date"]) if ev["direction"] == "up" else None
    return dict(
        symbol=ev["symbol"], direction=ev["direction"], signal_date=ev["trigger_date"],
        v02=dict(grade=ev["grade"], score=ev.get("score"), stage=ev["stage"],
                 stage_name=C.STAGE_NAMES.get(ev["stage"]), template=ev.get("template"),
                 rs_rank=ev.get("rs_rank"), mansfield=ev.get("mansfield"), pivot=ev["pivot"],
                 base_len=ev.get("base_len"), depth=ev.get("depth"), vol_ratio=ev.get("vol_ratio"),
                 entry=ev["entry"], stop=ev["stop"], hold_sessions=C.HOLD_SESSIONS, plan=plan),
        indicators=dict(close=_r(row.Close, 2), atr_pct=_r(row.atr_pct),
                        dist_sma50=_r(row.Close / row.sma50 - 1), dist_sma200=_r(row.Close / row.sma200 - 1),
                        from_hi52=_r(row.Close / row.hi52 - 1), from_lo52=_r(row.Close / row.lo52 - 1),
                        ret_21=ret(21), ret_63=ret(63), ret_126=ret(126), ret_252=ret(252),
                        traded_value_20d=_r(row.traded_value, 0),
                        bench_ret_63=_r(f["bench"].iloc[-1] / f["bench"].iloc[-64] - 1) if len(f) > 63 else None),
        market=dict(regime=ev["regime"],
                    stage2_share=_r(regime_row["stage2_share"]) if regime_row is not None else None,
                    bench_above_rising_sma200=bool(regime_row["bench_ok"]) if regime_row is not None else None,
                    vix=_r(vix, 2)),
        sector=sector, next_results_date=results_date,
        daily_bars=bars(daily), weekly_bars=bars(weekly),
        columns="date, open, high, low, close, volume",
    )


def add_facts(con, market: str, ev: dict, facts: dict) -> None:
    con.execute("INSERT OR IGNORE INTO mt_facts VALUES (?,?,?,?,?,?)",
                (market, ev["symbol"], ev["direction"], ev["trigger_date"],
                 json.dumps(facts, separators=(",", ":")), _now()))
    con.commit()


# ---------------------------------------------------------------------------
# Summary for the page and Telegram
# ---------------------------------------------------------------------------

def summary(con, market: str) -> List[dict]:
    """Per book and direction: picks, closed, average and median R after costs,
    win rate, average excess return. Backfilled picks count; they follow the
    same fixed rules and were logged live as v0.2 signals."""
    d = pd.read_sql_query("SELECT * FROM mt_picks WHERE market=?", con, params=(market,))
    out = []
    for (book, direction), x in d.groupby(["book", "direction"]):
        closed = x[x["status"] == "closed"]
        out.append(dict(
            book=book, direction=direction, picks=len(x), closed=len(closed),
            open=int((x["status"] == "open").sum()), skipped=int((x["status"] == "skipped").sum()),
            avg_r=_r(closed["r"].mean(), 2) if len(closed) else None,
            median_r=_r(closed["r"].median(), 2) if len(closed) else None,
            win_pct=_r((closed["r"] > 0).mean() * 100, 1) if len(closed) else None,
            avg_excess_pct=_r(closed["excess"].mean() * 100, 1) if closed["excess"].notna().any() else None,
        ))
    return out

