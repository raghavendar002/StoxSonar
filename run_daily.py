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


def _output(**kv) -> None:
    """Tell the GitHub workflow what happened (no-op outside Actions)."""
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as fh:
            fh.writelines(f"{k}={v}\n" for k, v in kv.items())


def latest_session(prices, bench: pd.Series) -> str:
    """The newest date most stocks have a bar for, and the benchmark too."""
    last = pd.Series([df.index.max() for df in prices.values() if len(df)])
    common = last.mode().max() if len(last) else bench.index.max()
    return str(min(common, bench.index.max()).date())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "replay"], default="daily")
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
    today = datetime.now(IST).date().isoformat()
    if a.mode == "daily" and prev == today:
        log.info("%s already published; nothing to do", today)
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

    as_of = latest_session(prices, bench)
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
        publish.send_telegram(publish.telegram_text(snap))
    _output(published="true", as_of=as_of)
    return 0


if __name__ == "__main__":
    sys.exit(main())
