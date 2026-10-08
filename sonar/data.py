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
            df = df[df["Volume"] > 0]
            if len(df):
                df.index = pd.DatetimeIndex(df.index).tz_localize(None)
                out[t] = df[["Open", "High", "Low", "Close", "Volume"]]
        log.info("fetched %d/%d", min(i + batch, len(tickers)), len(tickers))
    return out


def fetch_benchmark(period: str = C.FETCH_PERIOD) -> pd.Series:
    import yfinance as yf
    for t in (C.BENCHMARK, C.BENCHMARK_FALLBACK):
        df = yf.download(t, period=period, interval="1d", auto_adjust=True, progress=False)
        if len(df):
            s = df["Close"]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            s.index = pd.DatetimeIndex(s.index).tz_localize(None)
            s.name = t
            return s.dropna()
    raise RuntimeError("Benchmark unavailable")


def save_cache(path: Path, prices: Dict[str, pd.DataFrame], bench: pd.Series) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as fh:
        pickle.dump({"prices": prices, "bench": bench}, fh)


def load_cache(path: Path):
    """Loads a cache this tool wrote itself. Never point it at a file from elsewhere."""
    with open(path, "rb") as fh:
        d = pickle.load(fh)
    return d["prices"], d["bench"]
