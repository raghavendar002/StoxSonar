"""Price data for the daily run.

Uses Yahoo Finance through yfinance because its NSE history is already split-
and bonus-adjusted, which the spec makes a launch blocker. yfinance is a
personal-use source: fine for a free beta, and it must be swapped for a
licensed vendor behind `fetch_prices` before StoxSonar charges anyone.
"""

from __future__ import annotations

import io
import logging
import pickle
from pathlib import Path
from typing import Dict, List

import pandas as pd

from . import config as C

log = logging.getLogger(__name__)

NSE_EQUITY_LIST = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"


def load_universe(local_csv: Path | None = None) -> List[str]:
    """NSE EQ-series symbols, ETFs removed, as Yahoo tickers (SYMBOL.NS)."""
    df = None
    try:
        import requests
        r = requests.get(NSE_EQUITY_LIST, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip() for c in df.columns]
        df = df.rename(columns={"SYMBOL": "Symbol", "SERIES": "Series", "NAME OF COMPANY": "Security Name"})
    except Exception as e:  # network blocked or NSE format change: fall back to the local list
        log.warning("NSE equity list unavailable (%s); using local list", e)
    if df is None:
        if local_csv is None or not Path(local_csv).exists():
            raise RuntimeError("No universe source: NSE list unreachable and no local CSV given")
        df = pd.read_csv(local_csv)
    df = df[df["Series"].astype(str).str.strip() == "EQ"]
    name = df["Security Name"].astype(str).str.upper()
    sym = df["Symbol"].astype(str).str.strip()
    df = df[~name.str.contains("ETF") & ~sym.str.contains("BEES|ETF")]
    return sorted(s + ".NS" for s in df["Symbol"].astype(str).str.strip())


SP500_LIST = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def load_us_universe(local_csv: Path | None = None) -> List[str]:
    """Today's S&P 500 members as Yahoo tickers (BRK.B -> BRK-B). The list is
    saved to `local_csv` whenever it loads, so a later failed fetch falls back
    to the last good copy. Today's members only: firms that left the index are
    missing, which flatters any look back, so only the forward record counts."""
    syms = None
    try:
        import requests
        r = requests.get(SP500_LIST, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        t = pd.read_html(io.StringIO(r.text))[0]
        syms = sorted(t["Symbol"].astype(str).str.strip().str.replace(".", "-", regex=False))
        if len(syms) < 450:
            raise ValueError(f"only {len(syms)} symbols")
        if local_csv is not None:
            pd.DataFrame({"Symbol": syms}).to_csv(local_csv, index=False)
    except Exception as e:
        log.warning("S&P 500 list unavailable (%s); using local list", e)
        syms = None
    if syms is None:
        if local_csv is None or not Path(local_csv).exists():
            raise RuntimeError("No US universe: list unreachable and no local CSV given")
        syms = sorted(pd.read_csv(local_csv)["Symbol"].astype(str).str.strip())
    return syms


def next_results_date(ticker: str, after: str):
    """The next results (earnings) date on or after `after`, as YYYY-MM-DD, or
    None. Best effort from Yahoo, which often has nothing for NSE stocks."""
    try:
        import yfinance as yf
        cal = yf.Ticker(ticker).calendar or {}
        dates = cal.get("Earnings Date") or []
        ok = sorted(str(d) for d in dates if str(d) >= after)
        return ok[0] if ok else None
    except Exception as e:
        log.info("no results date for %s (%s)", ticker, type(e).__name__)
        return None


def load_sectors(path: Path) -> Dict[str, str]:
    """Bare symbol -> sector name, from universe/sectors_nse.json."""
    import json
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("sector list unavailable (%s)", e)
        return {}


def latest_vix(market: str = "NSE"):
    """The last close of the market's volatility index, or None."""
    try:
        s = fetch_benchmark_symbol(C.VIX[market], period="1mo")
        return float(s.iloc[-1]) if len(s) else None
    except Exception as e:
        log.warning("VIX unavailable (%s)", e)
        return None


def fetch_prices(tickers: List[str], period: str = C.FETCH_PERIOD,
                 batch: int = 200) -> Dict[str, pd.DataFrame]:
    """Adjusted daily OHLCV per ticker."""
    import yfinance as yf
    out: Dict[str, pd.DataFrame] = {}
    for i in range(0, len(tickers), batch):
        chunk = tickers[i:i + batch]
        raw = yf.download(chunk, period=period, interval="1d", auto_adjust=True,
                          group_by="ticker", threads=True, progress=False)
        for t in chunk:
            try:
                df = raw[t] if len(chunk) > 1 else raw
            except KeyError:
                continue
            df = df.dropna(subset=["Close"])
            zero = df["Volume"] <= 0
            if len(df) and zero.iloc[-1]:
                log.debug("%s: newest bar %s has no volume", t, df.index[-1])
            df = df[~zero]
            if len(df):
                df.index = pd.DatetimeIndex(df.index).tz_localize(None)
                out[t] = df[["Open", "High", "Low", "Close", "Volume"]]
        log.info("fetched %d/%d", min(i + batch, len(tickers)), len(tickers))
    return out


def fetch_benchmark_symbol(t: str, period: str = C.FETCH_PERIOD) -> pd.Series:
    import yfinance as yf
    df = yf.download(t, period=period, interval="1d", auto_adjust=True, progress=False)
    if not len(df):
        return pd.Series(dtype=float, name=t)
    s = df["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    s.index = pd.DatetimeIndex(s.index).tz_localize(None)
    s.name = t
    return s.dropna()


def _bench_symbols(market: str):
    return (C.US_BENCHMARK, C.US_BENCHMARK_FALLBACK) if market == "US" else (C.BENCHMARK, C.BENCHMARK_FALLBACK)


def fetch_benchmark(period: str = C.FETCH_PERIOD, market: str = "NSE") -> pd.Series:
    for t in _bench_symbols(market):
        s = fetch_benchmark_symbol(t, period)
        if len(s):
            return s
    raise RuntimeError("Benchmark unavailable")


def extend_benchmark(bench: pd.Series, to: pd.Timestamp, market: str = "NSE") -> pd.Series:
    """Carry the benchmark forward to `to` using the fallback index's daily
    returns, or flat if that is missing too. Logged, since it is an estimate."""
    missing_from = bench.index.max()
    try:
        fallback = _bench_symbols(market)[1]
        alt = fetch_benchmark_symbol(fallback)
    except Exception:
        alt = pd.Series(dtype=float)
    ext = bench.copy()
    if len(alt) and missing_from in alt.index and to in alt.index:
        rel = alt.loc[missing_from:to] / alt.loc[missing_from]
        ext = pd.concat([bench, rel.iloc[1:] * bench.iloc[-1]])
        how = fallback + " returns"
    else:
        ext.loc[to] = bench.iloc[-1]
        how = "the last value"
    log.warning("benchmark %s ends %s; extended to %s with %s", bench.name,
                missing_from.date(), to.date(), how)
    ext.name = bench.name
    return ext


def save_cache(path: Path, prices: Dict[str, pd.DataFrame], bench: pd.Series) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump({"prices": prices, "bench": bench}, fh)


def load_cache(path: Path):
    """Loads a cache this tool wrote itself. Never point it at a file from elsewhere."""
    with open(path, "rb") as fh:
        d = pickle.load(fh)
    return d["prices"], d["bench"]
