"""Evening run: fetch prices, label every stock, log signals, publish.

First time, bootstrap the ledger from history (signals are marked "replay"):
    python run_daily.py --mode replay
Every trading day after the close (19:00 IST):
    python run_daily.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from sonar import config as C
from sonar import data, engine, ledger, publish

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("stoxsonar")


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

    as_of = str(bench.index.max().date())
    stale = [s for s, df in prices.items() if len(df) and str(df.index.max().date()) != as_of]
    if len(stale) > 0.2 * len(prices):
        log.error("%d of %d symbols lack data for %s; refusing to publish a partial day",
                  len(stale), len(prices), as_of)
        return 2

    res = engine.run_market(prices, bench)
    con = ledger.connect(a.db)
    prev = ledger.last_run(con, "NSE")
    if a.mode == "daily" and prev is None:
        log.error("Ledger is empty. Run once with --mode replay to bootstrap it.")
        return 2
    if a.mode == "daily" and prev == as_of:
        log.info("%s already recorded; refreshing outcomes and page only", as_of)

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
