"""Exit rules for the phase 6 study, fixed before any of them was run.

Every rule keeps the same initial stop (STOP_ATR x ATR under the signal close,
gap-aware, as v0.2), so position sizes and entries are identical and only the
way out differs. Signals read at a close act at the next open, the first price
anyone could trade on. Rules that trail hold at most MAX_HOLD sessions.

  v02          stop, or the close 21 sessions after the signal (today's rule)
  time63       stop, or the close 63 sessions after the signal
  sma50        stop, or the next open after a close below the 50-day average
  chandelier   stop, or the next open after a close below the highest high since
               entry minus 3 ATR
  breakeven    stop; after a close 10% above entry the stop moves up to entry;
               then the sma50 exit
  half20       stop; sell half at +20% (a limit, filled at that price, or the open
               if it opens above); the rest by the sma50 exit
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from . import config as C
from .portfolio import Position, v02_exit

MAX_HOLD = 252
CHANDELIER_ATR = 3.0
BREAKEVEN_GAIN = 0.10
PARTIAL_GAIN = 0.20


def _stop(pos: Position, f: pd.DataFrame, i: int) -> Optional[tuple]:
    o, lo = f["Open"].iat[i], f["Low"].iat[i]
    if o <= pos.stop:
        return o, "gap below stop"
    if lo <= pos.stop:
        return pos.stop, "stop"
    return None


def _pending(pos: Position, f: pd.DataFrame, i: int) -> Optional[tuple]:
    """A sell decided at yesterday's close, done at today's open."""
    why = pos.state.pop("sell_open", None)
    return (f["Open"].iat[i], why) if why else None


def _held(pos: Position, i: int) -> int:
    return i - (pos.exit_due - C.HOLD_SESSIONS)       # sessions since the signal


def _trail(pos: Position, f: pd.DataFrame, i: int, line: float, why: str) -> Optional[tuple]:
    if _held(pos, i) >= MAX_HOLD:
        return f["Close"].iat[i], "max hold"
    if line == line and f["Close"].iat[i] < line:
        pos.state["sell_open"] = why
    return None


def time63(pos, f, i):
    out = _stop(pos, f, i)
    if out:
        return out
    return (f["Close"].iat[i], "time") if _held(pos, i) >= 63 else None


def sma50(pos, f, i):
    out = _pending(pos, f, i) or _stop(pos, f, i)
    return out or _trail(pos, f, i, f["sma50"].iat[i], "below 50-day")


def chandelier(pos, f, i):
    out = _pending(pos, f, i) or _stop(pos, f, i)
    if out:
        return out
    line = pos.peak - CHANDELIER_ATR * f["atr"].iat[i]
    return _trail(pos, f, i, line, "chandelier")


def breakeven(pos, f, i):
    out = _pending(pos, f, i) or _stop(pos, f, i)
    if out:
        return out
    if f["Close"].iat[i] >= pos.entry * (1 + BREAKEVEN_GAIN):
        pos.stop = max(pos.stop, pos.entry)
    return _trail(pos, f, i, f["sma50"].iat[i], "below 50-day")


def half20(pos, f, i):
    out = _pending(pos, f, i) or _stop(pos, f, i)
    if out:
        return out
    target = pos.entry * (1 + PARTIAL_GAIN)
    if not pos.state.get("half_sold") and f["High"].iat[i] >= target:
        pos.state["half_sold"] = True
        return max(target, f["Open"].iat[i]), "half at +20%", 0.5
    return _trail(pos, f, i, f["sma50"].iat[i], "below 50-day")


RULES = {"v02": v02_exit, "time63": time63, "sma50": sma50, "chandelier": chandelier,
         "breakeven": breakeven, "half20": half20}
