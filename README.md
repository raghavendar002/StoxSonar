# StoxSonar Daily (public beta)

A free daily page and Telegram post listing graded Stage 2 breakouts on NSE, with the outcome of every past signal. It is the smallest version that can tell you two things in about three months: whether the grades work, and whether strangers care.

Start with [docs/GUIDE.md](docs/GUIDE.md) for a plain explanation and setup steps.

The rules follow the StoxSonar Stock Segregation Rules Spec. This is a fresh, standalone build and does not import the old `backend/`.

## What it does every evening
1. Downloads ~3 years of split- and bonus-adjusted daily prices for every NSE EQ stock, plus the Nifty 500 (`sonar/data.py`).
2. Labels each liquid stock (Rs 1 crore/day or more) with its Weinstein stage, its trend template score and its RS rank, and detects base breakouts and breakdowns, graded A/B/C (`sonar/engine.py`).
3. Writes every new signal to an append-only ledger. A signal's grade is never changed afterwards and old signals are never back-inserted; only its status (Active, Extended, Confirmed, Failed, Faded) and its 5/21/63-session returns are updated (`sonar/ledger.py`).
4. Publishes `site/index.html`, `site/data.json` and `site/ledger.csv`, and posts a summary to Telegram (`sonar/publish.py`).
5. Builds the feeds for the installable app in `site/app/` (`sonar/appfeed.py`: mid-term, intraday, debates and books for India and the US) and sends a push alert to the owner's devices (`sonar/push.py`; setup in docs/GUIDE.md).

The page shows no raw prices. Charts open on TradingView.

## Mid-term paper books

Every candidate also becomes a paper trade, scored by fixed rules on daily bars
(`sonar/books.py`): buy at the next open, exit at the stop, a target if one is
set, or the close 21 sessions later, after costs. Results are in R and against
the index, in `mt_picks` in the ledger and `site/books.csv`.

- **Raw v0.2**: Grade A/B breakouts as v0.2 suggests them (none in a Weak market).
- **Twin**: every breakout (C grades too) and every A/B breakdown as a shadow
  short, with no market filter: "take every pick".
- **Debated**: every stock the Judge ruled on, whatever the verdict, at the
  Judge's levels. This is how Go, Wait and Avoid are each scored.
- **Judge**: only what the Judge would trade: Go picks, and Wait picks from the
  day their condition is met.

The numbers each debate reads are frozen on the signal day in `mt_facts`.
A US shadow list (`--market US`, today's S&P 500) runs the same rules and books
in the morning, with no page, no debates and no suggestions; its grade cut-offs
are still NSE's until they are refitted on US data.

## Bull / Bear / Judge (experimental)

After the day's signals have gone out, each Grade A/B breakout or breakdown
(three a day at most) is argued by a Bull and a Bear and ruled on by a Judge
(`sonar/debate.py`): Go, Wait or Avoid, with an entry zone, stop, target and a
description of how the stock is moving. Code checks the Judge's levels and
falls back to v0.2's stop when they break the rules. A Wait carries one
condition that code checks after each close for up to 10 sessions, with no
further model call. Breakdowns are shadow shorts: scored, never traded.

- It runs only when the `ANTHROPIC_API_KEY` repository secret is set.
- Spend is metered from the API's token counts and capped at
  `DEBATE_MONTHLY_CAP_USD` (6) a month; past the cap, debates stop and the
  books keep scoring.
- Debates go out as a second Telegram message and to `site/debates.html`.
- v0.2 has not passed its test, so treat every verdict as a logged experiment.
  The Judge is kept only if, at 100 judged picks, Go beats Avoid after costs.

## The mid-term Brain

`sonar/brain.py` is what the debates learn from. Three of its four jobs are plain code and cost nothing.

- **Track record.** Before each debate it looks up how signals like this one ended: every earlier signal of
  the same side and grade with a finished 21-session result, the same in the same kind of market, and the
  25 most similar on RS rank, Mansfield, base depth, base length and volume. It adds the Judge's own closed
  verdicts and the five closest past cases, without names. Only results finished before the signal day are
  used. What the debate was shown is stored with the debate.
- **Post-mortems.** When a judged paper trade closes, code marks the verdict right or wrong. A Go is right
  if the trade made money. An Avoid, or a Wait that never triggered, is right if the trade lost.
- **Scoreboard.** `site/brain.html` shows progress against the test fixed in advance: at 100 closed judged
  trades, Go must beat Avoid with the whole 90% bootstrap range above zero, the Judge book must beat the
  Twin, and conviction 4-5 must beat 1-2. At 150 without a pass, the Judge is switched off.
- **Lessons.** Once 8 judged trades have closed, and then at most weekly when 4 more have, one Opus call
  reads the anonymised cases and may propose up to three rules of thumb. Code keeps a lesson only if it
  cites 8 real cases and names no stock or date. At most 12 are active, every change is versioned, and
  the cost comes out of the same $6 monthly cap. Kept lessons are given to the next debates.

Eight cases is a low bar, and a lesson built on eight is a hypothesis. Each lesson changes the Judge, so
the versions are counted as extra tries when the results are finally read.

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
- **Lifecycle gap:** the spec does not say what happens when a signal dips below its pivot but never closes below its fail line (entry minus 2.5 ATR) within 10 sessions. Those signals close as "Faded", which is neither a success nor a failure.
- **Regime:** the regime uses the same day's stage breadth, measured before any breakout shortcut.
