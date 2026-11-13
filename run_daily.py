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
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from sonar import books
from sonar import config as C
from sonar import data, engine, ledger, publish

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("stoxsonar")
IST = timezone(timedelta(hours=5, minutes=30))
SESSION_FINAL = (16, 0)      # IST; NSE closes 15:30, a bar dated today is partial before this
US_SESSION_FINAL = (16, 30)  # New York time; the US close is 16:00


def last_complete_day(now: datetime, market: str = "NSE") -> str:
    """The newest date whose session has finished, by the market's own clock."""
    tz, final = (IST, SESSION_FINAL) if market == "NSE" else (ZoneInfo("America/New_York"), US_SESSION_FINAL)
    now = now.astimezone(tz)
    day = now.date() if (now.hour, now.minute) >= final else now.date() - timedelta(days=1)
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


def run_books(con, market: str, prices, bench: pd.Series, regime: pd.DataFrame,
              as_of: str) -> list:
    """Mid-term books: turn today's candidates into picks, freeze their fact
    packs, and re-score every pick still open. No model is called here."""
    books.init(con)
    first = con.execute("SELECT COUNT(*) FROM mt_picks WHERE market=?", (market,)).fetchone()[0] == 0
    events = ledger.events_frame(con, market)
    picks = books.new_picks(events, market, ["live", "late"])
    if first:
        # First run: v0.2's earlier live signals join under the same fixed rules, marked as such
        books.add_picks(con, [p for p in picks if p["signal_date"] < as_of], source_override="backfill")
    today = [p for p in picks if p["signal_date"] == as_of]
    added = books.add_picks(con, today)
    need = set(books.open_symbols(con, market)) | {p["symbol"] for p in picks if p["signal_date"] == as_of}
    frames = {s: engine.compute_features(prices[s], bench) for s in need if s in prices}
    vix = data.latest_vix(market)
    for ev in events[(events["trigger_date"] == as_of) & events["source"].isin(["live", "late"])].to_dict("records"):
        if ev["symbol"] in frames and (books.in_raw(ev) or books.in_twin(ev)):
            reg = regime.loc[pd.Timestamp(as_of)] if pd.Timestamp(as_of) in regime.index else None
            books.add_facts(con, market, ev, books.fact_pack(ev, frames[ev["symbol"]], reg, vix))
    done = books.update(con, market, frames)
    log.info("%s books: %d new picks, %d finished on this pass", market, added, done)
    return books.summary(con, market)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "replay", "check", "page"], default="daily")
    ap.add_argument("--market", choices=["NSE", "US"], default="NSE",
                    help="US = the S&P 500 shadow list: logged and scored, no page")
    ap.add_argument("--db", type=Path, default=ROOT / "ledger" / "stoxsonar.db")
    ap.add_argument("--site", type=Path, default=ROOT / "site")
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--use-cache", action="store_true", help="skip fetching; use --cache")
    ap.add_argument("--universe-csv", type=Path, default=None)
    ap.add_argument("--limit", type=int, default=0, help="first N symbols only (testing)")
    ap.add_argument("--site-url", default="")
    ap.add_argument("--telegram", action="store_true", help="post the summary to Telegram")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    us = a.market == "US"
    a.cache = a.cache or ROOT / "cache" / ("prices_us.pkl" if us else "prices_india.pkl")
    a.universe_csv = a.universe_csv or ROOT / "universe" / ("sp500.csv" if us else "nse_sec_list.csv")
    if us and a.mode in ("page", "replay"):
        ap.error("the US shadow list has no page and bootstraps itself on its first daily run")

    _output(published="false")
    if a.mode == "page":        # redraw the page from the last published data, nothing else
        snap = json.loads((a.site / "data.json").read_text(encoding="utf-8"))
        (a.site / "index.html").write_text(publish.render_html(snap), encoding="utf-8")
        _output(published="true", as_of=snap["as_of"] + " (page redrawn)")
        return 0
    con = ledger.connect(a.db)
    market = a.market
    prev = ledger.last_run(con, market)
    done = last_complete_day(datetime.now(timezone.utc), market)
    if a.mode == "daily" and prev is not None and prev >= done:
        log.info("%s is the newest finished session and is already published", prev)
        return 0

    if a.use_cache:
        prices, bench = data.load_cache(a.cache)
    else:
        tickers = data.load_us_universe(a.universe_csv) if us else data.load_universe(a.universe_csv)
        if a.limit:
            tickers = tickers[:a.limit]
        log.info("fetching %d symbols", len(tickers))
        bench = data.fetch_benchmark(market=market)
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
        bench = data.extend_benchmark(bench, pd.Timestamp(as_of), market=market)
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
        return 2 if datetime.now(IST).hour >= 22 and not us else 0

    # A new engine version starts with no record: replay its history once, then go live
    record_mode = "bootstrap" if a.mode == "daily" and prev is None else a.mode
    if record_mode == "bootstrap":
        log.info("no %s record yet; replaying history before today's live signals", C.ENGINE_VERSION)
    prices = {s: df.loc[:as_of] for s, df in prices.items()}
    bench = bench.loc[:as_of]
    res = engine.run_market(prices, bench)

    new = ledger.record_events(con, res.events, market, as_of, record_mode, after=prev)
    reg = res.regime.loc[pd.Timestamp(as_of)]
    ledger.record_day(con, res.states, market, as_of, "Weak" if reg["weak"] else "Healthy",
                      float(reg["stage2_share"]) if pd.notna(reg["stage2_share"]) else None, new)
    book_rows = []
    if a.mode == "daily":
        try:
            book_rows = run_books(con, market, prices, bench, res.regime, as_of)
        except Exception:  # the books must never stop the day's signals going out
            log.exception("mid-term books failed; signals publish without them")
    if us:
        log.info("US shadow %s: %d new signals", as_of, new)
        if a.telegram:
            publish.send_telegram(publish.us_telegram_text(ledger.events_frame(con, market), as_of, book_rows))
        _output(published="true", as_of=f"US {as_of}")
        return 0
    events = ledger.events_frame(con, "NSE")

    snap = publish.build_snapshot(res.states, events, res.regime, as_of, a.site_url)
    snap["books"] = book_rows
    publish.write_site(snap, a.site)
    events.to_csv(a.site / "ledger.csv", index=False)
    if book_rows:
        pd.read_sql_query("SELECT * FROM mt_picks WHERE market='NSE' ORDER BY signal_date DESC, book, symbol",
                          con).to_csv(a.site / "books.csv", index=False)
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
