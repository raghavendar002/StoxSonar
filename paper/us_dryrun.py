"""One-day US intraday dry run: opening-range scan, then settle on 1-minute bars.

scan   : builds data packs for long candidates at the current time (the checkpoint)
settle : plays out paper/out/<date>/orders.json on today's 1-minute bars

Paper only. Data from yfinance (free, unofficial).
"""
import argparse, json, math, os, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

SP100 = """AAPL ABBV ABT ACN ADBE AIG AMD AMGN AMT AMZN AVGO AXP BA BAC BK BKNG BLK BMY BRK-B C CAT
CHTR CL CMCSA COF COP COST CRM CSCO CVS CVX DE DHR DIS DUK EMR F FDX GD GE GILD GM GOOG GOOGL GS
HD HON IBM INTC INTU ISRG JNJ JPM KO LIN LLY LMT LOW MA MCD MDLZ MDT MET META MMM MO MRK MS MSFT
NEE NFLX NKE NVDA ORCL PEP PFE PG PLTR PM PYPL QCOM RTX SBUX SCHW SO SPG T TGT TMO TMUS TSLA TXN
UBER UNH UNP UPS USB V VZ WFC WMT XOM SPY QQQ""".split()

OUT = Path(__file__).parent / "out"
SLIP = 0.0002          # 0.02% per side
CASH = 1000.0
RISK = 5.0             # 0.5% of $1,000
MAX_POS = 2
CUTOFF = "15:50"       # ET


def bars(tickers, period, interval):
    df = yf.download(tickers, period=period, interval=interval, group_by="ticker",
                     auto_adjust=False, progress=False, threads=True, prepost=False)
    out = {}
    for t in tickers:
        try:
            d = df[t].dropna(how="all")
        except KeyError:
            continue
        if len(d):
            d.index = d.index.tz_convert("America/New_York")
            out[t] = d
    return out


def scan(top=6):
    b5 = bars(SP100, "60d", "5m")
    daily = bars(SP100, "3mo", "1d")
    now = datetime.now(timezone.utc).astimezone(pd.Timestamp.now(tz="America/New_York").tz)
    spy = b5.get("SPY")
    today = spy.index[-1].date()
    spy_t = spy[spy.index.date == today]
    spy_move = spy_t["Close"].iloc[-1] / spy_t["Open"].iloc[0] - 1
    rows, packs = [], {}
    for t, d in b5.items():
        days = sorted(set(d.index.date))
        if days[-1] != today or len(days) < 21:
            continue
        td = d[d.index.date == today]
        if len(td) < 6:
            continue
        orb = td.iloc[:3]                                  # 09:30-09:45
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
        gap = td["Open"].iloc[0] / prev["Close"] - 1 if prev is not None else float("nan")
        d20 = dd["Close"].tail(20).mean() if dd is not None else float("nan")
        rows.append(dict(sym=t, last=last, or_hi=or_hi, or_lo=or_lo, relvol=relvol, atr5=atr5,
                         vwap=vwap, gap=gap, day_hi=td["High"].max(), day_lo=td["Low"].min(),
                         open=td["Open"].iloc[0], prev_close=None if prev is None else prev["Close"],
                         prev_hi=None if prev is None else prev["High"], prev_lo=None if prev is None else prev["Low"],
                         dma20=d20, move_today=last / td["Open"].iloc[0] - 1,
                         dist_or_hi=last / or_hi - 1))
        packs[t] = td
    df = pd.DataFrame(rows)
    if t in ("SPY", "QQQ"):
        pass
    # long signal: strong opening volume and price at/above the opening-range high (within 0.3% below allowed)
    sig = df[(df.relvol >= 1.5) & (df.dist_or_hi >= -0.003) & (~df.sym.isin(["SPY", "QQQ"]))]
    sig = sig.sort_values("relvol", ascending=False).head(top)
    day = str(today)
    od = OUT / day
    od.mkdir(parents=True, exist_ok=True)
    checkpoint = spy.index[-1] + pd.Timedelta(minutes=5)
    meta = dict(date=day, checkpoint_et=str(checkpoint), spy_move_today=spy_move,
                universe=len(df), signals=len(sig),
                near_misses=df[(df.relvol >= 1.2) & (df.dist_or_hi >= -0.01)]
                .sort_values("relvol", ascending=False).head(10)[["sym", "relvol", "dist_or_hi", "move_today"]]
                .round(4).to_dict("records"))
    cands = []
    for _, r in sig.iterrows():
        trig = max(r.or_hi, r.last) * 1.0005
        stop = max(r.or_lo, trig - 1.5 * r.atr5)
        risk_ps = trig - stop
        mech = dict(trigger=round(trig, 2), stop=round(stop, 2), target=round(trig + 2 * risk_ps, 2),
                    latest_entry_et="14:30", cutoff_et=CUTOFF)
        b = packs[r.sym][["Open", "High", "Low", "Close", "Volume"]].round(2)
        b.index = b.index.strftime("%H:%M")
        cands.append(dict(sym=r.sym, stats={k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v)
                                           for k, v in r.to_dict().items()},
                          mechanical=mech, bars_5m=b.reset_index().values.tolist()))
    (od / "scan.json").write_text(json.dumps(dict(meta=meta, candidates=cands), indent=1, default=str))
    print(json.dumps(meta, indent=1, default=str))
    for c in cands:
        print(c["sym"], c["stats"]["relvol"], c["mechanical"])


def simulate(order, b1, start):
    """Play one long stop-entry order on 1-minute bars after `start`."""
    b = b1[b1.index >= start]
    cut = b[b.index.strftime("%H:%M") <= order.get("cutoff_et", CUTOFF)]
    latest = order.get("latest_entry_et", "14:30")
    trig, stop, tgt = order["trigger"], order["stop"], order["target"]
    entry_t = entry = None
    for ts, r in cut.iterrows():
        if entry is None:
            if ts.strftime("%H:%M") > latest:
                return dict(status="not_triggered")
            if r.High >= trig:
                entry = max(trig, r.Open) * (1 + SLIP)
                entry_t = ts
                # same-bar stop check (conservative)
                if r.Low <= stop:
                    return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=stop * (1 - SLIP),
                                exit_t=str(ts), reason="stop_same_bar")
            continue
        if r.Low <= stop:
            px = min(stop, r.Open) * (1 - SLIP)
            return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=px, exit_t=str(ts), reason="stop")
        if r.High >= tgt:
            px = max(tgt, r.Open) * (1 - SLIP) if r.Open > tgt else tgt * (1 - SLIP)
            return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=px, exit_t=str(ts), reason="target")
    if entry is None:
        return dict(status="not_triggered")
    last = cut.iloc[-1]
    return dict(status="closed", entry=entry, entry_t=str(entry_t), exit=last.Close * (1 - SLIP),
                exit_t=str(cut.index[-1]), reason="time")


def settle(day):
    od = OUT / day
    orders = json.loads((od / "orders.json").read_text())
    syms = sorted({o["sym"] for o in orders["mechanical"] + orders["judge"]})
    b1 = bars(syms, "5d", "1m")
    start = pd.Timestamp(orders["decided_et"])
    res = {}
    for book in ("mechanical", "judge"):
        cash, out = CASH, []
        for o in orders[book]:
            d = b1[o["sym"]]
            d = d[d.index.date == start.date()]
            r = simulate(o, d, start)
            rps = o["trigger"] - o["stop"]
            qty = min(RISK / rps, (CASH / MAX_POS) / o["trigger"])
            r.update(sym=o["sym"], qty=round(qty, 4))
            if r["status"] == "closed":
                pnl = (r["exit"] - r["entry"]) * qty
                r.update(pnl=round(pnl, 2), r_mult=round(pnl / (rps * qty), 2))
                cash += pnl
            out.append(r)
        res[book] = dict(trades=out, end_cash=round(cash, 2))
    (od / "settle.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["scan", "settle"])
    ap.add_argument("--day")
    a = ap.parse_args()
    scan() if a.mode == "scan" else settle(a.day)
