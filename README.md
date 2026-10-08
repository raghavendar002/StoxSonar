# StoxSonar Daily (public beta)

A free daily page and Telegram post listing graded Stage 2 breakouts on NSE, with the outcome of every past signal. It is the smallest version that can tell you two things in about three months: whether the grades work, and whether strangers care.

Start with [docs/GUIDE.md](docs/GUIDE.md) for a plain explanation and setup steps.

The rules follow the StoxSonar Stock Segregation Rules Spec. This is a fresh, standalone build and does not import the old `backend/`.

## What it does every evening
1. Downloads ~3 years of split- and bonus-adjusted daily prices for every NSE EQ stock, plus the Nifty 500 (`sonar/data.py`).
2. Labels each liquid stock (Rs 1 crore/day or more) with its Weinstein stage, its trend template score and its RS rank, and detects base breakouts and breakdowns, graded A/B/C (`sonar/engine.py`).
3. Writes every new signal to an append-only ledger. A signal's grade is never changed afterwards and old signals are never back-inserted; only its status (Active, Extended, Confirmed, Failed, Faded) and its 5/21/63-session returns are updated (`sonar/ledger.py`).
4. Publishes `site/index.html`, `site/data.json` and `site/ledger.csv`, and posts a summary to Telegram (`sonar/publish.py`).

The page shows no raw prices. Charts open on TradingView.

## Run it
```bash
pip install -r requirements.txt
python -m pytest -q tests                 # 8 tests
python run_daily.py --mode replay         # once: fills the ledger from history, marked "replay"
python run_daily.py --telegram            # every trading day after 19:00 IST
```
Use `--limit 100` for a quick trial and `--use-cache` to rerun without downloading again.

## Host it for free (GitHub Actions + Pages)
`.github/workflows/daily.yml` runs the job at 19:00 IST Monday to Friday, commits the ledger and page, and publishes the page on GitHub Pages. Because the ledger is committed every day, the git history is public, timestamped proof that no signal was added or edited later.

1. Put this folder in a **public** GitHub repository.
2. In the repository settings, set Pages to deploy from "GitHub Actions".
3. Create a Telegram bot with @BotFather and a public channel, add the bot as an admin, then add the `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (for example `@stoxsonar`) secrets.
4. Run the workflow once by hand with mode `replay`. After that it runs itself.

## Rules you should not break during the beta
- **Do not change `sonar/config.py`.** The track record is only reported per `ENGINE_VERSION`. Changing a threshold starts a new, empty record.
- **Do not delete or edit ledger rows.** Failures stay in.

## Known limits
- **Data licence:** yfinance and Yahoo are personal-use sources. That is acceptable for a free beta that shows no prices, but they must be replaced with a licensed vendor inside `fetch_prices` before anyone pays.
- **Survivorship:** the replay only sees stocks listed today, so it overstates results. Only the live record counts.
- **Trendline breakouts:** the spec's second breakout type is not included yet. v0.1 has base breakouts only.
- **Lifecycle gap:** the spec does not say what happens when a signal dips below its pivot but never falls 3% under it within 10 sessions. Those signals close as "Faded", which is neither a success nor a failure.
- **Regime:** the regime uses the same day's stage breadth, measured before any breakout shortcut.
