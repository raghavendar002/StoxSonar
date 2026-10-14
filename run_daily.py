"""Evening run: fetch prices, label every stock, log signals, publish.

First time, bootstrap the ledger from history (signals are marked "replay"):
    python run_daily.py --mode replay
Every trading day after the close:
    python run_daily.py

The daily job is scheduled several times each evening because GitHub often
starts scheduled jobs hours late. Each attempt publishes only a session that
is newer than the last one recorded; if the data source has not posted today's
close yet, it does nothing and a later attempt picks it up.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from sonar import config as C
from sonar import data, engine, ledger, publish

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("stoxsonar")
IST = timezone(timedelta(hours=5, minutes=30))
SESSION_FINAL = (16, 0)      # IST; NSE closes 15:30, a bar dated today is partial before this


def last_complete_day(now: datetime) -> str:
    """The newest date whose session has finished, by the clock in India."""
    now = now.astimezone(IST)
    day = now.date() if (now.hour, now.minute) >= SESSION_FINAL else now.date() - timedelta(days=1)
    return day.isoformat()


def _output(**kv) -> None:
    """Tell the GitHub workflow what happened (no-op outside Actions)."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as fh:
            fh.writelines(f"{k}={v}\n" for k, v in kv.items())


def _log_freshness(prices, bench: pd.Series) -> None:
    """Which dates the data source actually has, so late data is easy to spot."""
    last = pd.Series([str(df.index.max().date()) for df in prices.values() if len(df)])
    log.info("benchmark %s last date %s; stocks by last date: %s", bench.name,
             bench.index.max().date(), last.value_counts().head(4).to_dict())


def latest_session(prices) -> str:
    """The newest date most stocks have a bar for."""
    last = pd.Series([df.index.max() for df in prices.values() if len(df)])
    return str(last.mode().max().date())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "replay", "check"], default="daily")
    ap.add_argument("--db", type=Path, default=ROOT / "ledger" / "stoxsonar.db")
    ap.add_argument("--site", type=Path, default=ROOT / "site")
    ap.add_argument("--cache", type=Path, default=ROOT / "cache" / "prices_india.pkl")
    ap.add_argument("--use-cache", action="store_true", help="skip fetching; use --cache")
    ap.add_argument("--universe-csv", type=Path, default=ROOT / "universe" / "nse_sec_list.csv")
    ap.add_argument("--limit", type=int, default=0, help="first N symbols only (testing)")
    ap.add_argument("--site-url", default="")
    ap.add_argument("--telegram", action="store_true", help="post the summary to Telegram")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    _output(published="false")
    con = ledger.connect(a.db)
    prev = ledger.last_run(con, "NSE")
    done = last_complete_day(datetime.now(timezone.utc))
    if a.mode == "daily" and prev is not None and prev >= done:
        log.info("%s is the newest finished session and is already published", prev)
        return 0

    if a.use_cache:
        prices, bench = data.load_cache(a.cache)
    else:
        tickers = data.load_universe(a.universe_csv)
        if a.limit:
            tickers = tickers[:a.limit]
        log.info("fetching %d symbols", len(tickers))
        bench = data.fetch_benchmark()
        prices = data.fetch_prices(tickers)
        data.save_cache(a.cache, prices, bench)
    if a.limit:
        prices = dict(list(prices.items())[:a.limit])

    _log_freshness(prices, bench)
    if a.mode == "check":       # report how fresh the data is, publish nothing
        return 0
    # A run during market hours sees today's half-finished bar; never use it
    prices = {s: df.loc[:done] for s, df in prices.items()}
    bench = bench.loc[:done]
    as_of = latest_session(prices)
    if a.mode != "replay" and bench.index.max() < pd.Timestamp(as_of):
        # The index sometimes updates later than the stocks; don't let it hold the day back
        bench = data.extend_benchmark(bench, pd.Timestamp(as_of))
    if a.mode == "daily" and prev is not None and as_of <= prev:
        # The data source has not posted a newer close yet (or it is a market
        # holiday). Publishing now would repeat the last session, so wait.
        log.warning("Newest data is for %s, already published on the last run. "
                    "Nothing new to publish; a later attempt will retry.", as_of)
        return 0
    stale = [s for s, df in prices.items() if len(df) and str(df.index.max().date()) < as_of]
    if len(stale) > 0.2 * len(prices):
        log.warning("%d of %d symbols lack data for %s; refusing to publish a partial day",
                    len(stale), len(prices), as_of)
        # Earlier attempts wait for a later one; the last one fails loudly
        return 2 if datetime.now(IST).hour >= 22 else 0

    if a.mode == "daily" and prev is None:
        log.error("Ledger is empty. Run once with --mode replay to bootstrap it.")
        return 2
    prices = {s: df.loc[:as_of] for s, df in prices.items()}
    bench = bench.loc[:as_of]
    res = engine.run_market(prices, bench)

    new = ledger.record_events(con, res.events, "NSE", as_of, a.mode, after=prev)
    reg = res.regime.loc[pd.Timestamp(as_of)]
    ledger.record_day(con, res.states, "NSE", as_of, "Weak" if reg["weak"] else "Healthy",
                      float(reg["stage2_share"]) if pd.notna(reg["stage2_share"]) else None, new)
    events = ledger.events_frame(con, "NSE")

    snap = publish.build_snapshot(res.states, events, res.regime, as_of, a.site_url)
    publish.write_site(snap, a.site)
    events.to_csv(a.site / "ledger.csv", index=False)
    log.info("%s: %d stocks, regime %s, %d new signals, %d breakouts A/B",
             as_of, snap["stocks"], snap["regime"], new, len(snap["breakouts"]))
    if a.telegram:
        # Posted after the next session opened: say so rather than look current
        now = datetime.now(IST)
        snap["delayed"] = now.date().isoformat() > as_of and (now.hour, now.minute) >= (9, 15)
        publish.send_telegram(publish.telegram_text(snap))
    _output(published="true", as_of=as_of)
    return 0


if __name__ == "__main__":
    sys.exit(main())
