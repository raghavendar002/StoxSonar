"""The trade plan printed with every bullish signal: how much to buy, where to
stop, and when to get out. Pure arithmetic on the recorded entry and stop."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np

from . import config as C


def trade_plan(entry: float, stop: float, trigger_date: str,
               capital: float = C.CAPITAL_RS, risk_pct: float = C.RISK_PCT) -> Optional[dict]:
    """Size a long so that entry-to-stop loses RISK_PCT of `capital`.

    The buy is at the next open, which is unknown tonight, so the plan gives a
    ceiling: above `max_buy` (MAX_GAP_ATR above the signal close) skip the
    trade. Bought at that ceiling, the loss to the stop is the planned risk
    times (STOP_ATR + MAX_GAP_ATR) / STOP_ATR, 1.4x with the defaults. A gap
    below the stop on a later day can still lose more; a stop is an order,
    not a guarantee.
    """
    per_share = entry - stop
    if not entry or not stop or per_share <= 0:
        return None
    risk = capital * risk_pct
    qty = min(math.floor(risk / per_share), math.floor(capital * C.MAX_POSITION_PCT / entry))
    if qty < 1:
        return None
    max_buy = entry + per_share * C.MAX_GAP_ATR / C.STOP_ATR
    exit_by = np.busday_offset(np.datetime64(trigger_date), C.HOLD_SESSIONS, roll="forward")
    return dict(
        qty=int(qty), max_buy=round(max_buy, 2), stop=round(stop, 2),
        value_rs=round(qty * entry), risk_rs=round(qty * per_share),
        worst_risk_rs=round(qty * (max_buy - stop)),
        max_buy_pct=round((max_buy / entry - 1) * 100, 1),
        stop_pct=round((stop / entry - 1) * 100, 1),
        exit_by=str(exit_by),
    )
