"""Intraday paper trading, India and US: scan, Bull/Bear/Judge, settle.

  python paper/intraday.py scan   --mkt in     # at open + 15 min: scanner, twin orders, debates, Judge orders
  python paper/intraday.py settle --mkt in     # after the close: play both books on 1-minute bars

One day lives in paper/out/<mkt>/<date>/ (scan.json, debates.json, orders.json,
settle.json), the layout sonar/appfeed.py reads for the app.

Candidates come from a 15-minute opening-range breakout scan. The fixed-rule
twin takes the top signals; the Judge sees the same candidates one stock at a
time, after a Bull (always argues long) and a Bear (always argues short), and
picks LONG, SHORT or NO_TRADE with its own levels. Python sizes every trade.
Paper only; data from yfinance (free, unofficial, a few minutes late).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "paper" / "out"
SPEND = ROOT / "paper" / "spend.json"

US = """AAPL ABBV ABT ACN ADBE AIG AMD AMGN AMT AMZN AVGO AXP BA BAC BKNG BLK BMY BRK-B C CAT
CHTR CL CMCSA COF COP COST CRM CSCO CVS CVX DE DHR DIS DUK EMR F FDX GD GE GILD GM GOOGL GS
HD HON IBM INTC INTU ISRG JNJ JPM KO LIN LLY LMT LOW MA MCD MDLZ MDT MET META MMM MO MRK MS MSFT
NEE NFLX NKE NVDA ORCL PEP PFE PG PLTR PM PYPL QCOM RTX SBUX SCHW SO SPG T TGT TMO TMUS TSLA TXN
UBER UNH UNP UPS USB V VZ WFC WMT XOM""".split()

# Liquid NSE F&O names (Nifty 50 plus active Next-50 F&O stocks)
IN = """RELIANCE HDFCBANK ICICIBANK INFY TCS BHARTIARTL ITC SBIN LT KOTAKBANK AXISBANK HINDUNILVR
BAJFINANCE MARUTI SUNPHARMA M&M HCLTECH NTPC TATAMOTORS TITAN ULTRACEMCO ASIANPAINT POWERGRID ONGC
TATASTEEL ADANIENT ADANIPORTS COALINDIA BAJAJFINSV WIPRO NESTLEIND JSWSTEEL GRASIM TECHM HINDALCO
CIPLA DRREDDY SBILIFE HDFCLIFE BRITANNIA EICHERMOT HEROMOTOCO APOLLOHOSP BAJAJ-AUTO INDUSINDBK
TRENT BEL SHRIRAMFIN DLF VEDL TATAPOWER BANKBARODA PNB CANBK GAIL IOC BPCL HAL INDIGO DIVISLAB
LUPIN GODREJCP PIDILITILND SIEMENS AMBUJACEM CHOLAFIN TVSMOTOR ZYDUSLIFE IRCTC SAIL NMDC
HAVELLS DABUR JINDALSTEL AUROPHARMA BHEL RECLTD PFC LICHSGFIN ICICIPRULI MUTHOOTFIN""".split()

MKT = {
    "us": dict(tickers=US, index="SPY", tz="America/New_York", open="09:30", latest="14:30", cutoff="15:50",
               cash=1000.0, risk=5.0, slip=0.0002, shorts=False, ccy="$", meta_move="spy_move_today",
               name="US"),
    "in": dict(tickers=[t + ".NS" for t in IN], index="^NSEI", tz="Asia/Kolkata", open="09:15", latest="14:00",
               cutoff="15:15", cash=100000.0, risk=500.0, slip=0.0005, shorts=True, ccy="Rs ",
               meta_move="index_move", name="India"),
}
MAX_POS = 2              # open positions per book
MAX_DEBATE = int(__import__("os").environ.get("INTRA_MAX_DEBATE", 4))  # candidates debated per market per day
MONTHLY_CAP_USD = 28.0   # intraday debates; the mid-term debates have their own $6 cap
RESERVE_USD = 0.25       # a candidate is debated only if this much is left this month


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

def bars(tickers, period, interval, tz):
    df = yf.download(tickers, period=period, interval=interval, group_by="ticker", auto_adjust=False,
                     progress=False, threads=False, prepost=False)
    out = {}
    for t in tickers:
        try:
            d = df[t].dropna(how="all") if len(tickers) > 1 else df.dropna(how="all")
        except KeyError:
            continue
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(-1)
        if len(d):
            d.index = d.index.tz_localize(tz) if d.index.tz is None else d.index.tz_convert(tz)
            out[t] = d
    return out


def sym(t):
    return t[:-3] if t.endswith(".NS") else t


def ticker(s, mkt):
    return s + ".NS" if mkt == "in" else s


# ---------------------------------------------------------------------------
# Costs (round trip, in account currency)
# ---------------------------------------------------------------------------

def costs(mkt, entry, exit_, qty):
    if mkt == "us":
        sell = exit_ * qty
        return round(sell * 27.8e-6 + min(0.000166 * qty, 8.30), 4)   # SEC fee + FINRA TAF
    buy, sell = entry * qty, exit_ * qty
    brokerage = min(20, 0.0003 * buy) + min(20, 0.0003 * sell)
    stt = 0.00025 * sell
    exch = 0.0000297 * (buy + sell)
    sebi = 10e-7 * (buy + sell)
    stamp = 0.00003 * buy
    gst = 0.18 * (brokerage + exch + sebi)
    return round(brokerage + stt + exch + sebi + stamp + gst, 2)


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

class NoSession(Exception):
    """The market did not trade on the day asked for (weekend, holiday) or it has not opened yet."""


LATE_AFTER_MIN = 30      # a live scan started later than open + this many minutes replays the open instead
OR_BARS = 3              # the 15-minute opening range, in 5-minute bars


def _cut(d, day, n=OR_BARS):
    """Bars before `day`, plus only the first n bars of `day`: what an on-time scan saw."""
    return pd.concat([d[d.index.date < day], d[d.index.date == day].iloc[:n]])


def late_day(mkt, now=None):
    """Today's date when a scan starting `now` is too late to be live, else None."""
    cfg = MKT[mkt]
    now = (now or pd.Timestamp.now(tz="UTC")).tz_convert(cfg["tz"])
    hh, mm = map(int, cfg["open"].split(":"))
    opened = now.normalize() + pd.Timedelta(hours=hh, minutes=mm)
    return now.date() if now > opened + pd.Timedelta(minutes=LATE_AFTER_MIN) else None


def scan_market(mkt, wait=True, day=None):
    """The 15-minute opening-range scan. With `day`, the scan is replayed from that
    day's 5-minute bars exactly as it stood at the checkpoint (open + 15 min), so a
    run that started late, or a missed day, gets the same facts an on-time run had."""
    cfg = MKT[mkt]
    tz = cfg["tz"]
    if day is not None:
        day = pd.Timestamp(day).date()
        idx = bars([cfg["index"]], "60d", "5m", tz).get(cfg["index"])
        if idx is None or not len(idx):
            raise SystemExit("no index data")
        it = idx[idx.index.date == day].iloc[:OR_BARS]
        if len(it) < OR_BARS:
            raise NoSession(f"{cfg['name']} has no opening range on {day} (holiday, weekend or too old)")
        today = day
    else:
        for attempt in range(15):
            idx = bars([cfg["index"]], "5d", "5m", tz).get(cfg["index"])
            if idx is None or not len(idx):
                raise SystemExit("no index data")
            today = idx.index[-1].date()
            it = idx[idx.index.date == today]
            if len(it) >= 3 or not wait:
                break
            print(f"opening range not complete yet ({len(it)} bars), waiting 60s", flush=True)
            time.sleep(60)
        local_today = pd.Timestamp.now(tz=tz).date()
        if wait and today != local_today:
            # The newest bars are an earlier session: today is a holiday. Never rescan that session.
            raise NoSession(f"{cfg['name']} has not traded today ({local_today}); newest bars are {today}")
    b5 = bars(cfg["tickers"], "60d", "5m", tz)
    if day is not None:
        b5 = {t: _cut(d, day) for t, d in b5.items()}
    daily = bars(cfg["tickers"], "3mo", "1d", tz)
    index_move = it["Close"].iloc[-1] / it["Open"].iloc[0] - 1
    rows, packs = [], {}
    for t, d in b5.items():
        days = sorted(set(d.index.date))
        if days[-1] != today or len(days) < 21:
            continue
        td = d[d.index.date == today]
        if len(td) < 3:
            continue
        orb = td.iloc[:3]
        or_hi, or_lo, or_vol = orb["High"].max(), orb["Low"].min(), orb["Volume"].sum()
        hist = [d[d.index.date == x].iloc[:3]["Volume"].sum() for x in days[-21:-1]]
        relvol = or_vol / max(np.mean(hist), 1)
        last = td["Close"].iloc[-1]
        tr = pd.concat([td["High"] - td["Low"], (td["High"] - td["Close"].shift()).abs(),
                        (td["Low"] - td["Close"].shift()).abs()], axis=1).max(axis=1)
        atr5 = tr.tail(14).mean()
        vwap = (td["Close"] * td["Volume"]).sum() / max(td["Volume"].sum(), 1)
        dd = daily.get(t)
        dd = dd[dd.index.date < today] if dd is not None else None
        prev = dd.iloc[-1] if dd is not None and len(dd) else None
        rows.append(dict(sym=sym(t), last=last, or_hi=or_hi, or_lo=or_lo, relvol=relvol, atr5=atr5, vwap=vwap,
                         gap=(td["Open"].iloc[0] / prev["Close"] - 1) if prev is not None else None,
                         day_hi=td["High"].max(), day_lo=td["Low"].min(), open=td["Open"].iloc[0],
                         prev_close=None if prev is None else prev["Close"],
                         prev_hi=None if prev is None else prev["High"], prev_lo=None if prev is None else prev["Low"],
                         dma20=dd["Close"].tail(20).mean() if dd is not None and len(dd) else None,
                         move_today=last / td["Open"].iloc[0] - 1, dist_or_hi=last / or_hi - 1,
                         dist_or_lo=last / or_lo - 1))
        packs[sym(t)] = td
    df = pd.DataFrame(rows)
    longs = df[(df.relvol >= 1.5) & (df.dist_or_hi >= -0.003)].assign(side="long")
    shorts = df[(df.relvol >= 1.5) & (df.dist_or_lo <= 0.003)].assign(side="short") if cfg["shorts"] else df.iloc[:0]
    sig = pd.concat([longs, shorts]).sort_values("relvol", ascending=False)
    sig = sig.drop_duplicates("sym").head(MAX_DEBATE)
    checkpoint = it.index[-1] + pd.Timedelta(minutes=5)
    meta = {"date": str(today), "market": mkt, "checkpoint_et" if mkt == "us" else "checkpoint": str(checkpoint),
            cfg["meta_move"]: index_move, "universe": len(df), "signals": int(len(longs) + len(shorts)),
            "near_misses": df[(df.relvol >= 1.2)].assign(_d=df.dist_or_hi.abs())
            .sort_values("relvol", ascending=False).head(10)[["sym", "relvol", "dist_or_hi", "move_today"]]
            .round(4).to_dict("records")}
    cands = []
    for _, r in sig.iterrows():
        up = r.side == "long"
        atr = max(r.atr5, 0.0015 * r.last)
        if up:
            trig = max(r.or_hi, r.last) * 1.0005
            stop = max(r.or_lo, trig - 1.5 * atr * 2)
            tgt = trig + 2 * (trig - stop)
        else:
            trig = min(r.or_lo, r.last) * 0.9995
            stop = min(r.or_hi, trig + 1.5 * atr * 2)
            tgt = trig - 2 * (stop - trig)
        b = packs[r.sym][["Open", "High", "Low", "Close", "Volume"]].round(2)
        b.index = b.index.strftime("%H:%M")
        stats = {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.to_dict().items()}
        cands.append(dict(sym=r.sym, side=r.side, stats=stats,
                          mechanical=dict(side=r.side, trigger=round(trig, 2), stop=round(stop, 2),
                                          target=round(tgt, 2), latest_entry=cfg["latest"], cutoff=cfg["cutoff"]),
                          bars_5m=b.reset_index().values.tolist()))
    return dict(meta=meta, candidates=cands)


# ---------------------------------------------------------------------------
# Bull, Bear, Judge (one stock at a time)
# ---------------------------------------------------------------------------

SYSTEM = (
    "You are one voice in a three-part review of an INTRADAY trade idea for a small paper account "
    "({acct}). Every position is closed the same day by {cutoff} local time; entries are allowed until "
    "{latest}. A rule-based opening-range scanner flagged the stock; it has NOT proved it makes money. "
    "Work only from the fact pack: today's 5-minute bars so far, the opening range, relative volume, "
    "VWAP, yesterday's levels and the index move. No news, no fundamentals, nothing you remember about "
    "later prices. Cite numbers from the pack for every claim. Costs and slippage are about {cost} of a "
    "typical trade's risk, so a marginal edge is a loss."
)
BULL = ("You are the Bull. Make the strongest honest case for going LONG this stock today: where to enter, "
        "where the stop goes, what target is realistic before the close, and what would prove you wrong. "
        "Do not oversell. Under 180 words, plain prose.")
BEAR = ("You are the Bear. First rebut the Bull's points one by one, then make the strongest honest case for "
        "going SHORT or staying out: failed breakout risk, extension from VWAP, fading volume, a weak or strong "
        "index, overhead or underlying levels from yesterday. Give your short trigger, stop and target. "
        "Do not invent problems the numbers do not show. Under 180 words, plain prose.")
JUDGE = ("You are the Judge. Weigh the Bull and the Bear and decide: LONG, SHORT{noshort} or NO_TRADE. "
         "Orders are stop entries: a LONG triggers when price trades at or above `trigger`, a SHORT when it "
         "trades at or below it. Keep the trigger within 0.6% of the last price, the stop 0.15% to 2% from "
         "the trigger on the losing side, and the target at least 1.5x the stop distance on the winning side. "
         "NO_TRADE is a normal verdict; most scanner signals do not pay after costs. Give levels even for "
         "NO_TRADE, for the side you would have taken, so the call can be scored. Conviction 1-5 is how sure "
         "you are; 4-5 lets the account use up to 2x leverage on this trade (risk per trade stays fixed). "
         "headline: one plain line a non-expert understands. text: three or four sentences explaining the "
         "decision, naming the deciding arguments.")
SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["LONG", "SHORT", "NO_TRADE"]},
        "side_if_traded": {"type": "string", "enum": ["long", "short"]},
        "trigger": {"type": "number"}, "stop": {"type": "number"}, "target": {"type": "number"},
        "conviction": {"type": "integer"},
        "headline": {"type": "string"}, "title": {"type": "string"}, "text": {"type": "string"},
    },
    "required": ["decision", "side_if_traded", "trigger", "stop", "target", "conviction", "headline", "title", "text"],
    "additionalProperties": False,
}


def month_spend():
    m = datetime.now(timezone.utc).strftime("%Y-%m")
    d = json.loads(SPEND.read_text()) if SPEND.exists() else {}
    return d, m, float(d.get(m, 0.0))


def add_spend(usd):
    d, m, s = month_spend()
    d[m] = round(s + usd, 4)
    SPEND.write_text(json.dumps(d, indent=1))


def check(v, last, mkt):
    """Why the Judge's order cannot be used; empty when it can."""
    if v["decision"] == "NO_TRADE":
        return []
    bad = []
    up = v["decision"] == "LONG"
    if not MKT[mkt]["shorts"] and not up:
        return ["US account is cash-only: shorts are logged, not traded"]
    trig, stop, tgt = v["trigger"], v["stop"], v["target"]
    if min(trig, stop, tgt) <= 0:
        return ["a level is missing"]
    if abs(trig / last - 1) > 0.006:
        bad.append("trigger more than 0.6% from the last price")
    risk = trig - stop if up else stop - trig
    if risk <= 0:
        bad.append("stop on the wrong side")
    elif not 0.0015 <= risk / trig <= 0.02:
        bad.append("stop not 0.15%-2% from the trigger")
    reward = tgt - trig if up else trig - tgt
    if risk > 0 and reward < 1.5 * risk:
        bad.append("target under 1.5R")
    return bad


def judge_memory(mkt, cand, scan):
    """The Judge's own track record on similar setups, and any lessons; None on day one or on any error."""
    from sonar import intrabrain
    try:
        return intrabrain.memory_block(mkt, dict(cand, index_move=scan["meta"].get(MKT[mkt]["meta_move"])),
                                       scan["meta"]["date"], out=OUT)
    except Exception as e:                                        # memory is a help, never a reason to skip a day
        print(f"no memory for {cand['sym']}: {type(e).__name__} {e}", flush=True)
        return None


def debate(mkt, scan, caller=None):
    from sonar import debate as D
    from sonar import config as C
    cfg = MKT[mkt]
    caller = caller or D.api_call
    acct = (f"Rs 1,00,000, risk Rs 500 per trade, long and short (intraday MIS)" if mkt == "in"
            else "$1,000 cash account, risk $5 per trade, long only; a SHORT verdict is logged but not traded")
    system = SYSTEM.format(acct=acct, cutoff=cfg["cutoff"], latest=cfg["latest"],
                           cost="a quarter" if mkt == "in" else "a tenth")
    talks, judge_orders = [], []
    for c in scan["candidates"]:
        _, _, spent = month_spend()
        if MONTHLY_CAP_USD - spent < RESERVE_USD:
            talks.append(dict(sym=c["sym"], skipped="monthly intraday debate cap reached"))
            continue
        pack = json.dumps(dict(market=cfg["name"], symbol=c["sym"], scanner_side=c["side"], stats=c["stats"],
                               rule_based_plan=c["mechanical"], index_move_today=scan["meta"].get(cfg["meta_move"]),
                               bars_5m_today=c["bars_5m"]), default=str)
        memory = judge_memory(mkt, c, scan)
        try:
            bull = caller(C.DEBATE_MODEL_ARGUE, pack, BULL, "low", system=system)
            bear = caller(C.DEBATE_MODEL_ARGUE, pack, BEAR + "\n\nThe Bull said:\n" + bull.text, "low", system=system)
            judge = caller(C.DEBATE_MODEL_JUDGE, pack,
                           JUDGE.format(noshort="" if cfg["shorts"] else " (logged only: this account cannot short)")
                           + (f"\n\n{memory}" if memory else "")
                           + "\n\nBULL:\n" + bull.text + "\n\nBEAR:\n" + bear.text, "medium",
                           schema=SCHEMA, system=system)
        except Exception as e:                                    # one stock failing never stops the day
            talks.append(dict(sym=c["sym"], error=str(e)[:300]))
            continue
        v = json.loads(judge.text)
        cost = bull.cost_usd + bear.cost_usd + judge.cost_usd
        add_spend(cost)
        problems = check(v, c["stats"]["last"], mkt)
        traded = v["decision"] != "NO_TRADE" and not problems
        lev = 2 if (mkt == "in" and int(v["conviction"]) >= 4) else 1
        if traded:
            judge_orders.append(dict(sym=c["sym"], side="long" if v["decision"] == "LONG" else "short",
                                     trigger=round(v["trigger"], 2), stop=round(v["stop"], 2),
                                     target=round(v["target"], 2), conviction=int(v["conviction"]), leverage=lev,
                                     latest_entry=cfg["latest"], cutoff=cfg["cutoff"]))
        talks.append(dict(sym=c["sym"], name=None, headline=v["headline"], bull=bull.text, bear=bear.text,
                          judge_title=v["title"] if traded else f"No trade: {v['title']}",
                          judge_text=v["text"] + (f" (Order not placed: {'; '.join(problems)}.)" if problems else ""),
                          verdict=v, problems=problems, cost_usd=round(cost, 4), memory=memory,
                          decided_utc=datetime.now(timezone.utc).isoformat(timespec="seconds")))
        print(c["sym"], v["decision"], problems, f"${cost:.3f}", flush=True)
    return talks, judge_orders


# ---------------------------------------------------------------------------
# Settle
# ---------------------------------------------------------------------------

def simulate(o, b1, start, slip):
    up = o.get("side", "long") == "long"
    b = b1[(b1.index >= start) & (b1.index.strftime("%H:%M") <= o["cutoff"])]
    trig, stop, tgt = o["trigger"], o["stop"], o["target"]
    entry = entry_t = None
    for ts, r in b.iterrows():
        if entry is None:
            if ts.strftime("%H:%M") > o["latest_entry"]:
                return dict(status="not_triggered")
            hit = r.High >= trig if up else r.Low <= trig
            if not hit:
                continue
            first = ts == b.index[0]
            gap_px = r.Open if (r.Open > trig if up else r.Open < trig) else trig
            if first and abs(gap_px / trig - 1) > 0.003:
                return dict(status="stale", note="price was already past the trigger when the order went in")
            entry = gap_px * (1 + slip if up else 1 - slip)
            entry_t = ts
            if (r.Low <= stop) if up else (r.High >= stop):
                return dict(status="closed", entry=entry, entry_t=str(ts), exit=stop * (1 - slip if up else 1 + slip),
                            exit_t=str(ts), reason="stop_same_bar")
            continue
        if (r.Low <= stop) if up else (r.High >= stop):
            px = (min(stop, r.Open) * (1 - slip)) if up else (max(stop, r.Open) * (1 + slip))
            return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=px, exit_t=str(ts), reason="stop")
        if (r.High >= tgt) if up else (r.Low <= tgt):
            px = tgt * (1 - slip if up else 1 + slip)
            return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=px, exit_t=str(ts), reason="target")
    if entry is None:
        return dict(status="not_triggered")
    last = b.iloc[-1].Close
    return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=last * (1 - slip if up else 1 + slip),
                exit_t=str(b.index[-1]), reason="time")


def settle_book(mkt, orders, b1, start):
    cfg = MKT[mkt]
    cash, out = cfg["cash"], []
    for o in orders[:MAX_POS]:
        d = b1.get(ticker(o["sym"], mkt))
        if d is None:
            out.append(dict(sym=o["sym"], status="no_data"))
            continue
        d = d[d.index.date == start.date()]
        r = simulate(o, d, start, cfg["slip"])
        up = o.get("side", "long") == "long"
        rps = abs(o["trigger"] - o["stop"])
        cap = cfg["cash"] / MAX_POS * o.get("leverage", 1)
        qty = min(cfg["risk"] / rps, cap / o["trigger"])
        if mkt == "in":
            qty = float(int(qty))                       # whole shares on NSE
        r.update(sym=o["sym"], side=o.get("side", "long"), qty=round(qty, 4))
        if r["status"] == "closed" and qty > 0:
            gross = (r["exit"] - r["entry"]) * qty * (1 if up else -1)
            fee = costs(mkt, r["entry"], r["exit"], qty)
            pnl = gross - fee
            r.update(costs=fee, pnl=round(pnl, 2), r_mult=round(pnl / (rps * qty), 2))
            cash += pnl
        out.append(r)
    return dict(trades=out, end_cash=round(cash, 2))


def shadow(mkt, scan, talks, b1, start):
    """Score every candidate twice, whatever the books did: the scanner's rule plan
    (the Twin's trade) and the Judge's own levels (a No trade still names them).
    One position each, so a full book never hides a result. sonar/intrabrain.py
    turns these into the Judge's track record."""
    cfg = MKT[mkt]
    out = []
    for c in scan.get("candidates") or []:
        rule = dict(sym=c["sym"], **c["mechanical"])
        row = dict(sym=c["sym"], side=c["side"], rule=settle_book(mkt, [rule], b1, start)["trades"][0])
        v = (talks.get(c["sym"]) or {}).get("verdict") or {}
        if v.get("trigger") and v.get("stop") and v.get("target"):
            side = {"LONG": "long", "SHORT": "short"}.get(v.get("decision"), v.get("side_if_traded") or c["side"])
            o = dict(sym=c["sym"], side=side, trigger=v["trigger"], stop=v["stop"], target=v["target"],
                     latest_entry=cfg["latest"], cutoff=cfg["cutoff"])
            risk = (o["trigger"] - o["stop"]) * (1 if side == "long" else -1)
            if risk > 0 and (o["target"] - o["trigger"]) * (1 if side == "long" else -1) > 0:
                row["judge_levels"] = settle_book(mkt, [o], b1, start)["trades"][0]
            else:
                row["judge_levels"] = dict(status="bad_levels", side=side)
        out.append(row)
    return out


def settle(mkt, day, caller=None):
    cfg = MKT[mkt]
    od = OUT / mkt / day
    orders = json.loads((od / "orders.json").read_text())
    scan = json.loads((od / "scan.json").read_text()) if (od / "scan.json").exists() else {}
    talks = {t["sym"]: t for t in json.loads((od / "debates.json").read_text())} if (od / "debates.json").exists() else {}
    syms = sorted({ticker(o["sym"], mkt) for o in orders["mechanical"] + orders["judge"]}
                  | {ticker(c["sym"], mkt) for c in scan.get("candidates") or []})
    b1 = bars(syms, "7d", "1m", cfg["tz"]) if syms else {}    # Yahoo keeps 1-minute bars about a week
    start = pd.Timestamp(orders["decided"]).tz_convert(cfg["tz"])
    res = {book: settle_book(mkt, orders[book], b1, start) for book in ("mechanical", "judge")}
    res["shadow"] = shadow(mkt, scan, talks, b1, start)
    (od / "settle.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))
    lessons_review(mkt, caller)


def lessons_review(mkt, caller=None):
    """At most weekly, once enough calls are scored: one Opus call that may add or drop lessons."""
    from sonar import intrabrain
    import os
    if not os.environ.get("ANTHROPIC_API_KEY") and caller is None:
        return
    try:
        _, _, spent = month_spend()
        row = intrabrain.review(mkt, MONTHLY_CAP_USD - spent, call=caller)
    except Exception as e:                                        # never fails the settle
        print(f"lessons review skipped: {type(e).__name__} {e}", flush=True)
        return
    if row:
        add_spend(row.get("cost_usd") or 0)
        print("lessons review:", json.dumps(row, default=str), flush=True)


# ---------------------------------------------------------------------------

def run_scan(mkt, no_debate=False, day=None, force=False):
    """One scan. A live scan that starts late, or `day` given, replays the open
    as it stood at the checkpoint. A day that already has orders is never redone
    (no double spend when two schedulers fire) unless `force`."""
    cfg = MKT[mkt]
    replay = day or late_day(mkt)
    if replay and not force and (OUT / mkt / str(replay) / "orders.json").exists():
        print(f"{cfg['name']} {replay} already scanned; nothing to do", flush=True)
        return None
    try:
        s = scan_market(mkt, day=replay)
    except NoSession as e:
        print(str(e), flush=True)
        return None
    day = s["meta"]["date"]
    od = OUT / mkt / day
    if not force and (od / "orders.json").exists():
        print(f"{cfg['name']} {day} already scanned; nothing to do", flush=True)
        return None
    if replay:
        s["meta"]["replayed"] = True
        s["meta"]["ran_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    od.mkdir(parents=True, exist_ok=True)
    (od / "scan.json").write_text(json.dumps(s, indent=1, default=str))
    print(json.dumps(s["meta"], indent=1, default=str), flush=True)
    mech = [dict(sym=c["sym"], **c["mechanical"]) for c in s["candidates"]
            if cfg["shorts"] or c["side"] == "long"][:MAX_POS]
    talks, judge_orders = ([], []) if no_debate else debate(mkt, s)
    if talks:
        (od / "debates.json").write_text(json.dumps(talks, indent=1, default=str))
    decided = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cp = s["meta"].get("checkpoint_et") or s["meta"].get("checkpoint")
    if __import__("os").environ.get("INTRA_TEST_REPLAY"):      # tests on a past session: decide 10 min after the checkpoint
        decided = (pd.Timestamp(cp) + pd.Timedelta(minutes=10)).isoformat()
    elif replay:
        # Orders go in when an on-time run's would have: two minutes after the checkpoint
        decided = (pd.Timestamp(cp) + pd.Timedelta(minutes=2)).tz_convert("UTC").isoformat()
    note = ("Late run: the open was replayed from the day's 5-minute bars as it stood at the checkpoint, "
            "and orders start two minutes after it." if replay else "Live paper day.")
    orders = dict(decided=decided,
                  note=note + ("" if talks else " No debates ran (no candidates, cap or no key)."),
                  mechanical=mech, judge=judge_orders, replayed=bool(replay))
    (od / "orders.json").write_text(json.dumps(orders, indent=1))
    print(json.dumps(orders, indent=1))
    return day


def last_day(mkt):
    days = sorted(p.name for p in (OUT / mkt).glob("20*") if (p / "orders.json").exists())
    return days[-1] if days else None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["scan", "settle"])
    ap.add_argument("--mkt", choices=["in", "us"], required=True)
    ap.add_argument("--day")
    ap.add_argument("--no-debate", action="store_true")
    ap.add_argument("--force", action="store_true", help="redo a day that already has orders")
    a = ap.parse_args()
    if a.mode == "scan":
        run_scan(a.mkt, a.no_debate, day=a.day, force=a.force)
    else:
        d = a.day or last_day(a.mkt)
        if not d:
            raise SystemExit("nothing to settle")
        settle(a.mkt, d)
