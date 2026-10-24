"""NSE's own end-of-day files (bhavcopies) as a price source.

Why: the files list every stock that traded that day, including ones later
delisted or merged, so a history built from them has no survivorship bias.
They need no login, and they download from GitHub's runners (checked on
24 Oct 2026).

Adjustment for splits and bonuses comes from the files themselves: on an
ex-date NSE reports an adjusted previous close, so previous close / the
prior day's actual close is that day's adjustment factor.
"""

from __future__ import annotations

import io
import logging
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Iterable, Optional

import pandas as pd

log = logging.getLogger(__name__)

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
NEW_FORMAT_FROM = date(2024, 7, 8)     # NSE switched to the UDiFF file on this date
ADJ_TOLERANCE = 0.001                  # prev-close mismatches below 0.1% are rounding, not actions
COLUMNS = ["date", "symbol", "isin", "open", "high", "low", "close", "prev_close", "volume", "value"]


def bhavcopy_url(d: date) -> str:
    if d >= NEW_FORMAT_FROM:
        return ("https://nsearchives.nseindia.com/content/cm/"
                f"BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
    mon = f"{d:%b}".upper()
    return ("https://nsearchives.nseindia.com/content/historical/EQUITIES/"
            f"{d:%Y}/{mon}/cm{d:%d}{mon}{d:%Y}bhav.csv.zip")


def _old_dates(s: pd.Series) -> pd.Series:
    """Old-format TIMESTAMP is 02-JAN-2024 in most files but 13-Jul-20 in some."""
    s = s.astype(str).str.strip()
    four = pd.to_datetime(s, format="%d-%b-%Y", errors="coerce")
    two = pd.to_datetime(s, format="%d-%b-%y", errors="coerce")
    out = four.fillna(two)
    if out.isna().any():
        raise ValueError(f"unreadable bhavcopy date {s[out.isna()].iloc[0]!r}")
    return out


def parse_bhavcopy(raw: pd.DataFrame) -> pd.DataFrame:
    """Either file format -> one row per EQ-series stock, standard columns."""
    if "TckrSymb" in raw.columns:
        df = raw[raw["SctySrs"].astype(str).str.strip() == "EQ"]
        out = pd.DataFrame({
            "date": pd.to_datetime(df["TradDt"]), "symbol": df["TckrSymb"].str.strip(),
            "isin": df["ISIN"], "open": df["OpnPric"], "high": df["HghPric"], "low": df["LwPric"],
            "close": df["ClsPric"], "prev_close": df["PrvsClsgPric"],
            "volume": df["TtlTradgVol"], "value": df["TtlTrfVal"]})
    else:
        raw = raw.rename(columns=lambda c: c.strip())
        df = raw[raw["SERIES"].astype(str).str.strip() == "EQ"]
        out = pd.DataFrame({
            "date": _old_dates(df["TIMESTAMP"]),
            "symbol": df["SYMBOL"].str.strip(), "isin": df["ISIN"], "open": df["OPEN"],
            "high": df["HIGH"], "low": df["LOW"], "close": df["CLOSE"], "prev_close": df["PREVCLOSE"],
            "volume": df["TOTTRDQTY"], "value": df["TOTTRDVAL"]})
    return out[COLUMNS].reset_index(drop=True)


def fetch_bhavcopy(d: date, session=None) -> Optional[pd.DataFrame]:
    """One day's file, parsed; None on a holiday (NSE answers 404)."""
    import requests
    get = (session or requests).get
    r = get(bhavcopy_url(d), headers=UA, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    return parse_bhavcopy(pd.read_csv(z.open(z.namelist()[0])))


def adjustment_factors(panel: pd.DataFrame) -> pd.Series:
    """Per row, the factor NSE applied to the previous close on that day (1.0 when none).

    A 1:2 split shows as prev_close = half the prior close, factor 0.5.
    """
    p = panel.sort_values(["symbol", "date"])
    prior_close = p.groupby("symbol")["close"].shift(1)
    f = (p["prev_close"] / prior_close).where(prior_close > 0)
    f = f.where((f - 1).abs() > ADJ_TOLERANCE, 1.0).fillna(1.0)
    return f.reindex(panel.index)


def adjust(panel: pd.DataFrame) -> pd.DataFrame:
    """Back-adjust prices (and volumes) so splits and bonuses leave no jump."""
    p = panel.sort_values(["symbol", "date"]).copy()
    f = adjustment_factors(p)
    # The factor on day t applies to every day before t: a reversed cumulative product, shifted
    later = f.groupby(p["symbol"]).transform(lambda s: s[::-1].cumprod()[::-1].shift(-1).fillna(1.0))
    for c in ("open", "high", "low", "close", "prev_close"):
        p[c] = p[c] * later
    p["volume"] = p["volume"] / later
    return p


def _fetch_retrying(d: date, session, tries: int = 4) -> Optional[pd.DataFrame]:
    for k in range(tries):
        try:
            return fetch_bhavcopy(d, session)
        except Exception as e:  # throttling or a dropped connection: back off and retry
            if k == tries - 1:
                log.warning("%s: giving up (%s)", d, e)
                raise
            time.sleep(2 ** k)


def build_panel(days: Iterable[date], workers: int = 4) -> pd.DataFrame:
    """Download and stack the files for `days`, skipping holidays.

    Raises if a weekday's file cannot be fetched at all: a silent gap would
    look like a holiday and quietly corrupt every return across it."""
    import requests
    days = [d for d in days if d.weekday() < 5]
    frames, done = [], 0
    with requests.Session() as session, ThreadPoolExecutor(workers) as pool:
        for df in pool.map(lambda d: _fetch_retrying(d, session), days):
            done += 1
            if df is not None:
                frames.append(df)
            if done % 250 == 0:
                log.info("bhavcopy %d/%d days", done, len(days))
    log.info("bhavcopy: %d trading days out of %d weekdays", len(frames), len(days))
    if not frames:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat(frames, ignore_index=True)


def weekdays(start: date, end: date) -> list:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)
            if (start + timedelta(days=i)).weekday() < 5]


def to_price_dict(panel: pd.DataFrame) -> dict:
    """Adjusted panel -> {SYMBOL.NS: OHLCV frame}, the shape the engine reads."""
    out = {}
    for sym, g in adjust(panel).groupby("symbol"):
        g = g.set_index("date").sort_index()
        df = g[["open", "high", "low", "close", "volume"]].rename(columns=str.capitalize)
        df = df[df["Volume"] > 0]
        if len(df):
            out[f"{sym}.NS"] = df.astype(float)
    return out
