"""The wide India intraday pool: Nifty 500 stocks that can be day-traded, built the evening before.

  python paper/intraday.py pool --mkt in   # after the close; writes paper/pool/in/<date>.json

Filters (Raghav, 18 Nov 2026: wide pool, longs only outside F&O):
  - in the Nifty 500, EQ series (trade-to-trade stocks cannot be traded intraday)
  - NSE price band of 10% or more, or no band (F&O): a 2% or 5% circuit can lock a trade in
  - last close at least Rs 50
  - median daily turnover over 20 sessions at least Rs 10 crore
NSE's surveillance lists (ASM/GSM) need a logged-in API, so the band filter stands in for them:
stocks under surveillance are nearly always moved to a 5% band or lower.

Each member carries what the 09:31 scan needs and cannot fetch quickly for 400 stocks:
its normal opening-15-minute volume (mean of the first three 5-minute bars over the last
20 sessions), its 20-day average close, its turnover tier (for slippage) and whether it
is in F&O (shorts are allowed only there).
"""
from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
POOL = ROOT / "paper" / "pool"
UNIVERSE = ROOT / "universe"

NIFTY500_URLS = ["https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
                 "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"]
SECLIST_URL = "https://nsearchives.nseindia.com/content/equities/sec_list.csv"
FO_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

MIN_PRICE = 50.0
MIN_TURNOVER = 10e7          # Rs 10 crore a day
MIN_BAND = 10                # % circuit band; "No Band" (F&O) passes
NORM_DAYS = 20
KEEP_FILES = 15

# Slippage per side by liquidity: F&O names, then turnover tiers
SLIP_FO, SLIP_MID, SLIP_SMALL = 0.0005, 0.0010, 0.0020
MID_TURNOVER = 50e7          # Rs 50 crore a day


def slip_for(fo: bool, turnover: float) -> float:
    if fo:
        return SLIP_FO
    return SLIP_MID if turnover >= MID_TURNOVER else SLIP_SMALL


def _get_csv(urls, keep: Path | None):
    """First URL that answers, saved to `keep`; else the saved copy; else None."""
    import requests
    for u in urls:
        try:
            r = requests.get(u, headers=UA, timeout=30)
            if r.ok and len(r.content) > 200:
                if keep is not None:
                    keep.write_bytes(r.content)
                return pd.read_csv(io.BytesIO(r.content))
            print(f"{u}: HTTP {r.status_code}", flush=True)
        except Exception as e:                       # noqa: BLE001 - any failure falls back to the saved copy
            print(f"{u}: {type(e).__name__} {e}", flush=True)
    if keep is not None and keep.exists():
        print(f"using the saved {keep.name}", flush=True)
        return pd.read_csv(keep)
    return None


def nifty500() -> list[str]:
    df = _get_csv(NIFTY500_URLS, UNIVERSE / "nifty500.csv")
    if df is None:
        raise SystemExit("no Nifty 500 list (NSE unreachable and no saved copy)")
    df.columns = [c.strip() for c in df.columns]
    if "Series" in df:
        df = df[df["Series"].astype(str).str.strip() == "EQ"]
    return sorted(df["Symbol"].astype(str).str.strip().unique())


def bands() -> dict:
    """Symbol -> band in % (None for 'No Band'), EQ series only."""
    df = _get_csv([SECLIST_URL], UNIVERSE / "sec_list_latest.csv")
    if df is None:
        return {}
    df.columns = [c.strip() for c in df.columns]
    df = df[df["Series"].astype(str).str.strip() == "EQ"]
    out = {}
    for s, b in zip(df["Symbol"].astype(str).str.strip(), df["Band"].astype(str).str.strip()):
        out[s] = float(b) if b.replace(".", "", 1).isdigit() else None
    return out


def fo_list(fallback) -> set:
    df = _get_csv([FO_URL], UNIVERSE / "fo_mktlots.csv")
    if df is None:
        return set(fallback)
    df.columns = [c.strip().upper() for c in df.columns]
    col = "SYMBOL" if "SYMBOL" in df else df.columns[1]
    syms = {str(s).strip() for s in df[col]}
    return {s for s in syms if s and s.upper() == s and " " not in s and not s.startswith("NIFTY")}


def eligible(symbols, band_of, fo) -> list[str]:
    """The list and band filters (no price data needed)."""
    keep = []
    for s in symbols:
        if band_of and s not in band_of:
            continue                                  # not in EQ series today
        b = band_of.get(s) if band_of else None
        if b is not None and b < MIN_BAND and s not in fo:
            continue
        keep.append(s)
    return keep


def members(daily: dict, b5: dict, fo: set) -> list[dict]:
    """Price, turnover and opening-volume filters on fetched bars; one dict per member."""
    out = []
    for t, d in daily.items():
        s = t[:-3]
        d = d.dropna(subset=["Close", "Volume"])
        if len(d) < NORM_DAYS:
            continue
        close = float(d["Close"].iloc[-1])
        turnover = float((d["Close"] * d["Volume"]).tail(NORM_DAYS).median())
        if close < MIN_PRICE or turnover < MIN_TURNOVER:
            continue
        m5 = b5.get(t)
        if m5 is None or not len(m5):
            continue
        days = sorted(set(m5.index.date))[-NORM_DAYS:]
        opens = [m5[m5.index.date == x].iloc[:3]["Volume"].sum() for x in days]
        opens = [v for v in opens if v > 0]
        if len(opens) < 15:
            continue
        isfo = s in fo
        out.append(dict(sym=s, fo=isfo, close=round(close, 2), turnover_cr=round(turnover / 1e7, 1),
                        or_vol_norm=float(np.mean(opens)), dma20=round(float(d["Close"].tail(20).mean()), 2),
                        slip=slip_for(isfo, turnover)))
    return sorted(out, key=lambda m: -m["turnover_cr"])


def build(bars, tz, fo_fallback, mkt="in"):
    """`bars` is paper/intraday.py's downloader; `fo_fallback` the F&O names to assume if NSE is down."""
    if mkt != "in":
        raise SystemExit("the wide pool is India only")
    t0 = time.time()
    syms = nifty500()
    band_of, fo = bands(), fo_list(fo_fallback)
    keep = eligible(syms, band_of, fo)
    print(f"Nifty 500: {len(syms)}; after series and band filters: {len(keep)}; F&O list: {len(fo)}", flush=True)
    tick = [s + ".NS" for s in keep]
    daily = bars(tick, "3mo", "1d", tz)
    pre = [t for t, d in daily.items() if len(d) and float(d["Close"].dropna().iloc[-1]) >= MIN_PRICE
           and float((d["Close"] * d["Volume"]).tail(NORM_DAYS).median()) >= MIN_TURNOVER]
    b5 = bars(pre, "60d", "5m", tz) if pre else {}
    mem = members({t: daily[t] for t in pre}, b5, fo)
    last = max((d.index[-1].date() for d in daily.values() if len(d)), default=None)
    doc = dict(market=mkt, built_on=str(last), built_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               build_s=round(time.time() - t0), nifty500=len(syms), after_lists=len(keep),
               with_daily=len(daily), after_liquidity=len(pre), members=mem,
               rules=dict(min_price=MIN_PRICE, min_turnover_cr=MIN_TURNOVER / 1e7, min_band_pct=MIN_BAND,
                          slip=dict(fo=SLIP_FO, mid=SLIP_MID, small=SLIP_SMALL, mid_turnover_cr=MID_TURNOVER / 1e7)))
    folder = POOL / mkt
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{last}.json").write_text(json.dumps(doc, indent=1))
    for old in sorted(folder.glob("*.json"))[:-KEEP_FILES]:
        old.unlink()
    print(f"pool for after {last}: {len(mem)} members (F&O {sum(m['fo'] for m in mem)}), "
          f"{doc['build_s']}s", flush=True)
    return doc


def load(mkt, day) -> dict | None:
    """The newest pool built from sessions before `day` (so a replay never sees that day's volume)."""
    folder = POOL / mkt
    files = sorted(p for p in folder.glob("*.json") if p.stem < str(day)) if folder.is_dir() else []
    return json.loads(files[-1].read_text()) if files else None

