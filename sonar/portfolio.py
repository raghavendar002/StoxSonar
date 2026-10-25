"""Day-by-day replay of one account trading the signals, with Indian costs.

The yardstick until now was "signal plus 21 sessions". This answers the
question a trader asks instead: starting with CAPITAL_RS, buying what the app
suggests the way the trade plan says, how much would the account be worth,
and how deep were the falls along the way?

Rules as the app trades today (v0.2), each a parameter so PR 6 can vary them:
  * a buy is a Grade A or B up signal in a Healthy market (no buys when Weak)
  * sized by trade_plan on the account's equity at the signal close
  * bought at the next open, skipped if that open is above the plan's max_buy
    or at or below the stop, or if cash or the position cap does not allow it;
    several signals on one day are taken in order of score
  * stop: a low at or below the stop sells at the stop, or at the open when
    the stock opens below it (a gap through the stop fills worse)
  * time exit: the close HOLD_SESSIONS sessions after the signal
Equity is marked at each close. Idle cash earns nothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from . import config as C
from .plan import trade_plan

# Delivery (CNC) equity charges, NSE, discount broker, as of 2026
STT = 0.001                 # securities transaction tax, buy and sell
EXCHANGE = 0.0000297        # NSE transaction charge
SEBI = 0.000001             # SEBI turnover fee
STAMP_BUY = 0.00015         # stamp duty, buy only
GST = 0.18                  # on brokerage + exchange + SEBI charges
BROKERAGE = 0.0             # zero for delivery at most discount brokers
DP_SELL_RS = 15.93          # depository charge per stock sold (Rs 13.5 + GST)
# One-way slippage by median daily traded value (Rs): thinner stocks cost more
SLIPPAGE = ((50e7, 0.0005), (10e7, 0.0010), (1e7, 0.0025), (0, 0.0050))


def slippage(traded_value: float) -> float:
    for floor, s in SLIPPAGE:
        if traded_value >= floor:
            return s
    return SLIPPAGE[-1][1]


def buy_cost(value: float) -> float:
    fees = value * (EXCHANGE + SEBI) + value * BROKERAGE
    return value * (STT + STAMP_BUY) + fees * (1 + GST)


def sell_cost(value: float) -> float:
    fees = value * (EXCHANGE + SEBI) + value * BROKERAGE
    return value * STT + fees * (1 + GST) + DP_SELL_RS


@dataclass
class Position:
    symbol: str
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    qty: int
    entry: float               # fill price incl. slippage
    stop: float
    exit_due: int              # bar index in the stock's frame of the time exit
    cost_in: float
    grade: str
    peak: float = 0.0
    state: dict = field(default_factory=dict)


ExitRule = Callable[[Position, pd.DataFrame, int], Optional[tuple]]


def v02_exit(pos: Position, f: pd.DataFrame, i: int) -> Optional[tuple]:
    """Stop (gap-aware), else the time exit. Returns (price, reason) or None."""
    o, lo, c = f["Open"].iat[i], f["Low"].iat[i], f["Close"].iat[i]
    if o <= pos.stop:
        return o, "gap below stop"
    if lo <= pos.stop:
        return pos.stop, "stop"
    if i >= pos.exit_due:
        return c, "time"
    return None


def default_entry_filter(sig) -> bool:
    return sig.direction == "up" and sig.grade in ("A", "B") and \
        not (C.NO_LONGS_WHEN_WEAK and sig.regime == "Weak")


def simulate(signals: pd.DataFrame, prices: Dict[str, pd.DataFrame], bench: pd.Series,
             capital: float = C.CAPITAL_RS, max_positions: Optional[int] = None,
             exit_rule: ExitRule = v02_exit, entry_filter=default_entry_filter,
             start: Optional[str] = None, end: Optional[str] = None) -> dict:
    sig = signals[signals.apply(entry_filter, axis=1)].copy()
    sig["date"] = pd.to_datetime(sig["trigger_date"])
    if start:
        sig = sig[sig["date"] >= pd.Timestamp(start)]
    if end:
        sig = sig[sig["date"] <= pd.Timestamp(end)]
    sig = sig[sig["symbol"].isin(prices)].sort_values(["date", "score"], ascending=[True, False])
    by_day = {d: g for d, g in sig.groupby("date")}
    frames = {s: prices[s].assign(tv=(prices[s]["Close"] * prices[s]["Volume"]).rolling(20, min_periods=5).median())
              for s in sig["symbol"].unique()}
    pos_idx = {s: {d: i for i, d in enumerate(f.index)} for s, f in frames.items()}

    days = bench.index[(bench.index >= sig["date"].min())] if len(sig) else bench.index[:0]
    if end:
        days = days[days <= pd.Timestamp(end)]
    cash, open_pos, trades, curve = float(capital), [], [], []
    pending = []                                       # signals waiting for the next open
    last_close: Dict[str, float] = {}
    for day in days:
        # 1. Buys at today's open from yesterday's signals
        for s in pending:
            f, ix = frames[s.symbol], pos_idx[s.symbol]
            i = ix.get(day)
            if i is None or any(p.symbol == s.symbol for p in open_pos):
                continue
            if max_positions is not None and len(open_pos) >= max_positions:
                break
            equity = cash + sum(p.qty * last_close.get(p.symbol, p.entry) for p in open_pos)
            plan = trade_plan(s.entry, s.stop, s.trigger_date, capital=equity)
            o = f["Open"].iat[i]
            if plan is None or o > plan["max_buy"] or o <= s.stop:
                continue
            fill = o * (1 + slippage(f["tv"].iat[i - 1] if i else 0))
            qty = plan["qty"]
            while qty > 0 and qty * fill + buy_cost(qty * fill) > cash:
                qty -= 1
            if qty < 1:
                continue
            cost = buy_cost(qty * fill)
            cash -= qty * fill + cost
            sig_i = ix.get(s.date)
            due = (sig_i if sig_i is not None else i - 1) + C.HOLD_SESSIONS
            open_pos.append(Position(s.symbol, s.date, day, qty, fill, s.stop, due, cost, s.grade,
                                     peak=fill))
        pending = []
        # 2. Exits during today's session
        still = []
        for p in open_pos:
            f, i = frames[p.symbol], pos_idx[p.symbol].get(day)
            if i is None:
                if day > f.index[-1]:                  # delisted or merged: out at the last close
                    i, out = len(f) - 1, (f["Close"].iat[-1], "delisted")
                else:                                  # not traded today (suspension)
                    still.append(p)
                    continue
            else:
                p.peak = max(p.peak, f["High"].iat[i])
                out = exit_rule(p, f, i) if day > p.entry_date or i >= p.exit_due else None
                if day == p.entry_date and out is None and f["Low"].iat[i] <= p.stop:
                    out = (p.stop, "stop")             # stopped out on the day of entry
            if out is None:
                still.append(p)
                continue
            px, why = out
            px *= 1 - slippage(f["tv"].iat[i - 1] if i else 0)
            proceeds = p.qty * px
            cost = sell_cost(proceeds)
            cash += proceeds - cost
            trades.append(dict(symbol=p.symbol, grade=p.grade, signal=p.signal_date.date(),
                               entry_date=p.entry_date.date(), exit_date=day.date(), qty=p.qty,
                               entry=round(p.entry, 2), exit=round(px, 2), reason=why,
                               pnl=round(proceeds - cost - p.qty * p.entry - p.cost_in, 2),
                               ret=round((proceeds - cost) / (p.qty * p.entry + p.cost_in) - 1, 4),
                               sessions=i - pos_idx[p.symbol][p.entry_date]))
            last_close.pop(p.symbol, None)
        open_pos = still
        # 3. Mark to market at the close; queue today's signals for tomorrow's open
        for p in open_pos:
            i = pos_idx[p.symbol].get(day)
            if i is not None:
                last_close[p.symbol] = frames[p.symbol]["Close"].iat[i]
        equity = cash + sum(p.qty * last_close.get(p.symbol, p.entry) for p in open_pos)
        curve.append((day, equity, len(open_pos), cash))
        if day in by_day:
            pending = list(by_day[day].itertuples(index=False))
    eq = pd.DataFrame(curve, columns=["date", "equity", "positions", "cash"]).set_index("date")
    return {"equity": eq, "trades": pd.DataFrame(trades), "bench": bench.reindex(eq.index).ffill()}


def metrics(eq: pd.Series, bench: pd.Series, trades: pd.DataFrame) -> dict:
    """Headline numbers for one equity curve against the benchmark over the same days."""
    if len(eq) < 2:
        return {}
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")
    bcagr = (bench.iloc[-1] / bench.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")
    r = eq.pct_change().dropna()
    dd = eq / eq.cummax() - 1
    bdd = bench / bench.cummax() - 1
    out = dict(start=str(eq.index[0].date()), end=str(eq.index[-1].date()),
               cagr_pct=round(cagr * 100, 2), bench_cagr_pct=round(bcagr * 100, 2),
               max_drawdown_pct=round(dd.min() * 100, 1), bench_max_drawdown_pct=round(bdd.min() * 100, 1),
               sharpe=round(r.mean() / r.std() * math.sqrt(252), 2) if r.std() > 0 else None,
               final_rs=round(float(eq.iloc[-1])))
    if len(trades):
        w, l = trades[trades["pnl"] > 0], trades[trades["pnl"] <= 0]
        out.update(trades=len(trades), win_pct=round(len(w) / len(trades) * 100, 1),
                   avg_win_pct=round(w["ret"].mean() * 100, 2) if len(w) else None,
                   avg_loss_pct=round(l["ret"].mean() * 100, 2) if len(l) else None,
                   profit_factor=round(w["pnl"].sum() / -l["pnl"].sum(), 2) if len(l) and l["pnl"].sum() < 0 else None,
                   avg_sessions=round(trades["sessions"].mean(), 1))
    return out


def yearly(eq: pd.Series, bench: pd.Series) -> pd.DataFrame:
    y = pd.DataFrame({"strategy": eq.resample("YE").last(), "bench": bench.resample("YE").last()})
    first = pd.DataFrame({"strategy": [eq.iloc[0]], "bench": [bench.iloc[0]]})
    y = pd.concat([first, y], ignore_index=True)
    out = (y.pct_change().iloc[1:] * 100).round(1)
    out.index = eq.resample("YE").last().index.year
    out["excess"] = (out["strategy"] - out["bench"]).round(1)
    return out
