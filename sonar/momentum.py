"""Ranked momentum with a 200-day exit brake: the shared ranking and a live paper book.

The ranking is the one tested in research/momentum.py (PR 18): NSE stocks
with a year of history, Rs 5 crore a day of median traded value, the top 500
by that value, MQ50-style band hitters dropped, scored like NSE's Momentum 30
(6- and 12-month return over 1-year volatility, z-scored and averaged).

The paper book (Raghav, 2026-11-17) runs the version that passed the bar on
2019 on but was not the pre-registered pick: top 15, monthly, sell at rank
> 30, and sell everything when the Nifty 500 closes under its 200-day average,
buying back only at the next month's rebalance above it. No money, no model
calls. Rs 1 lakh, 1/15 of equity a stock, idle cash at the liquid-ETF rate,
the v0.2 simulator's Indian costs. It never suggests a trade to anyone; it is
a forward record kept by code.

Timing: each evening run decides at that day's close and the orders fill at
the next session's open, read on the following run. The rebalance happens on
the first run of each month (one session later than the backtest, which
traded the month's first open).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from . import config as C
from .portfolio import buy_cost, sell_cost, slippage

MIN_VALUE_RS = 5e7           # Rs 5 crore median daily traded value
UNIVERSE_SIZE = 500
MIN_PRICE = 10.0
BAND_DAYS_MAX = 2            # 3+ locked-limit days in 126 sessions -> out
BOOK_N = 15
BOOK_LIQUID_RATE = 0.055
BOOK_VERSION = "mom-exit-15 v1"




def wide(prices: dict) -> dict:
    """{SYM: OHLCV} -> one date x symbol frame per field, on the union of dates."""
    out = {}
    for k in ("Open", "High", "Low", "Close", "Volume"):
        out[k] = pd.DataFrame({s: f[k] for s, f in prices.items()}).sort_index()
    out["traded"] = out["Close"].notna()
    out["value"] = out["Close"] * out["Volume"]
    return out


def month_starts(days: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(days, index=days)
    return pd.DatetimeIndex(s.groupby([days.year, days.month]).first().values)


def ranks(w: dict, asof: pd.DatetimeIndex) -> dict:
    """{as-of date: Series symbol -> rank (1 = best)} for the eligible universe on each date."""
    close = w["Close"].ffill()
    ret = close.pct_change(fill_method=None)
    vol = ret.rolling(252, min_periods=200).std() * math.sqrt(252)
    r6 = close / close.shift(126) - 1
    r12 = close / close.shift(252) - 1
    seen = w["traded"].rolling(252, min_periods=1).sum()
    med_val = w["value"].rolling(126, min_periods=60).median()
    prev = close.shift(1)
    move = (w["Close"] / prev - 1).abs()
    locked = (w["High"] == w["Low"]) & (move >= 0.019) & (w["Volume"] > 0)
    bands = locked.rolling(126, min_periods=1).sum()
    out = {}
    for d in asof:
        if d not in close.index:
            continue
        ok = (seen.loc[d] >= 0.9 * 252) & (close.loc[d] >= MIN_PRICE) & (med_val.loc[d] >= MIN_VALUE_RS) \
            & (bands.loc[d] <= BAND_DAYS_MAX) & vol.loc[d].gt(0) & r12.loc[d].notna() & r6.loc[d].notna()
        ok = ok & w["traded"].loc[d]
        names = ok[ok].index
        if len(names) < 30:
            out[d] = pd.Series(dtype=float)
            continue
        top = med_val.loc[d, names].nlargest(UNIVERSE_SIZE).index
        a, b = r6.loc[d, top] / vol.loc[d, top], r12.loc[d, top] / vol.loc[d, top]
        z = ((a - a.mean()) / a.std() + (b - b.mean()) / b.std()) / 2
        out[d] = z.rank(ascending=False, method="first")
    return out


# ---------------------------------------------------------------------------
# The live paper book


def empty_book(capital: float = C.CAPITAL_RS) -> dict:
    return dict(version=BOOK_VERSION, n=BOOK_N, capital=capital, cash=float(capital), started=None,
                last_day=None, rebalanced_month=None, holdings={}, pending=None,
                equity=[], trades=[], bench_start=None)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return empty_book()


def save(path: Path, book: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(book, indent=1, default=str), encoding="utf-8")


def _next_bar(f: pd.DataFrame, after: str, upto: str):
    """The first bar after `after`, if it is on or before `upto`."""
    later = f[(f.index > pd.Timestamp(after)) & (f.index <= pd.Timestamp(upto))]
    return (later.index[0], later.iloc[0]) if len(later) else (None, None)


def _tv(f: pd.DataFrame, before) -> float:
    v = (f["Close"] * f["Volume"]).loc[:before]
    v = v[v.index < before].tail(20)
    return float(v.median()) if len(v) else 0.0


def _equity(book: dict, prices: dict) -> float:
    return book["cash"] + sum(h["qty"] * h["last"] for h in book["holdings"].values())


def step(book: dict, prices: dict, bench: pd.Series, as_of: str) -> dict:
    """One evening: fill yesterday's orders at today's open, mark at today's
    close, then queue tomorrow's orders. Safe to call twice for one day."""
    if book.get("last_day") and as_of <= book["last_day"]:
        return book
    log = []
    # 1. Interest on idle cash since the last run
    if book["last_day"]:
        days = (pd.Timestamp(as_of) - pd.Timestamp(book["last_day"])).days
        book["cash"] *= (1 + BOOK_LIQUID_RATE) ** (days / 365.25)
    # 2. Fill the orders queued on the last run at the next session's open
    p = book.get("pending")
    if p:
        keep_sells, keep_buys = [], []
        for sym in p["sells"]:
            h, f = book["holdings"].get(sym), prices.get(sym)
            if h is None:
                continue
            d, bar = _next_bar(f, p["day"], as_of) if f is not None else (None, None)
            if bar is None or not (bar["Open"] > 0):
                keep_sells.append(sym)
                continue
            px = float(bar["Open"]) * (1 - slippage(_tv(f, d)))
            proceeds = h["qty"] * px
            cost = sell_cost(proceeds)
            book["cash"] += proceeds - cost
            pnl = proceeds - cost - h["qty"] * h["entry"] - h["cost"]
            book["trades"].append(dict(symbol=sym, entry_date=h["entry_date"], exit_date=str(d.date()),
                                       qty=h["qty"], entry=round(h["entry"], 2), exit=round(px, 2),
                                       reason=p["why"].get(sym, "rank"), pnl=round(pnl, 2),
                                       ret_pct=round(((proceeds - cost) / (h["qty"] * h["entry"] + h["cost"]) - 1) * 100, 2)))
            del book["holdings"][sym]
            log.append(f"sold {sym}")
        for sym in p["buys"]:
            f = prices.get(sym)
            if f is None or sym in book["holdings"] or len(book["holdings"]) >= book["n"]:
                continue
            d, bar = _next_bar(f, p["day"], as_of)
            if bar is None or not (bar["Open"] > 0):
                continue                       # a missed buy waits for next month, as in the backtest
            fill = float(bar["Open"]) * (1 + slippage(_tv(f, d)))
            qty = int(p["target"] // fill)
            while qty > 0 and qty * fill + buy_cost(qty * fill) > book["cash"]:
                qty -= 1
            if qty < 1:
                continue
            cost = buy_cost(qty * fill)
            book["cash"] -= qty * fill + cost
            book["holdings"][sym] = dict(qty=qty, entry=fill, cost=cost, entry_date=str(d.date()), last=fill)
            log.append(f"bought {sym}")
        book["pending"] = (dict(day=p["day"], sells=keep_sells, buys=[], target=0, why=p["why"])
                           if keep_sells else None)
    # 3. Mark at today's close
    for sym, h in book["holdings"].items():
        f = prices.get(sym)
        if f is not None and len(f.loc[:as_of]):
            h["last"] = float(f["Close"].loc[:as_of].iloc[-1])
    eq = _equity(book, prices)
    b = bench.loc[:as_of]
    sma = b.rolling(200, min_periods=200).mean()
    under = bool(len(b) and sma.notna().iloc[-1] and b.iloc[-1] < sma.iloc[-1])
    if book["started"] is None:
        book["started"], book["bench_start"] = as_of, float(b.iloc[-1])
    book["equity"].append(dict(date=as_of, equity=round(eq, 2), cash=round(book["cash"], 2),
                               positions=len(book["holdings"]), bench=round(float(b.iloc[-1]), 2),
                               under_200dma=under))
    # 4. Queue tomorrow's orders
    month = as_of[:7]
    why, sells, buys, target = {}, [], [], 0.0
    if under:
        sells = list(book["holdings"])
        why = {s: "brake" for s in sells}
        if book["rebalanced_month"] != month:
            book["rebalanced_month"] = month     # under on the month's first run: no buys until next month
    elif book["rebalanced_month"] != month:
        w = wide({s: f.loc[:as_of] for s, f in prices.items() if len(f.loc[:as_of])})
        r = ranks(w, pd.DatetimeIndex([pd.Timestamp(as_of)])).get(pd.Timestamp(as_of), pd.Series(dtype=float))
        if len(r):
            sells = [s for s in book["holdings"] if r.get(s, np.inf) > 2 * book["n"]]
            why = {s: "rank" for s in sells}
            stay = len(book["holdings"]) - len(sells)
            buys = [s for s in r.sort_values().index if s not in book["holdings"]][:max(book["n"] - stay, 0)]
            target = eq / book["n"]
            book["ranks"] = {s: int(v) for s, v in r.sort_values().head(2 * book["n"]).items()}
            book["rebalanced_month"] = month
    if p and book.get("pending"):                # unfilled sells carry over
        sells = sorted(set(sells) | set(book["pending"]["sells"]))
        why = {**book["pending"]["why"], **why}
    book["pending"] = dict(day=as_of, sells=sells, buys=buys, target=round(target, 2), why=why) \
        if (sells or buys) else None
    book["last_day"] = as_of
    book["last_log"] = log
    return book


def summary(book: dict) -> dict:
    """What the app shows: equity against the index since the start, holdings, orders, closed trades."""
    eq = book["equity"]
    out = dict(version=book["version"], n=book["n"], started=book["started"], as_of=book["last_day"],
               capital=book["capital"], equity=eq[-1]["equity"] if eq else book["capital"],
               cash=round(book["cash"], 2), brake_on=bool(eq and eq[-1]["under_200dma"]),
               holdings=[dict(symbol=s.replace(".NS", ""), qty=h["qty"], entry=round(h["entry"], 2),
                              last=round(h["last"], 2), entry_date=h["entry_date"],
                              ret_pct=round((h["last"] / h["entry"] - 1) * 100, 1))
                         for s, h in sorted(book["holdings"].items())],
               pending=book.get("pending"), trades=book["trades"][-30:],
               curve=[dict(date=e["date"], equity=e["equity"], bench=e["bench"]) for e in eq])
    if eq and book.get("bench_start"):
        out["ret_pct"] = round((eq[-1]["equity"] / book["capital"] - 1) * 100, 2)
        out["bench_ret_pct"] = round((eq[-1]["bench"] / book["bench_start"] - 1) * 100, 2)
    return out
