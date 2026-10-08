# StoxSonar Daily: how it works and how to switch it on

## What people get every evening

At about 7:15 pm IST on every trading day, two things update:

1. **A web page** at `https://raghavendar002.github.io/StoxSonar/` showing:
   - **Market mood:** Healthy or Weak, plus a coloured bar showing what share of NSE stocks are in each stage (Basing, Advancing, Topping, Declining).
   - **New breakouts today:** stocks that just broke out of a base on heavy volume, each graded A or B, with its momentum score, RS rank, fail line, stage, trend template, base and volume.
   - **New breakdowns today:** the bearish mirror image.
   - **Signals still in play:** earlier signals and how they are doing now (Active, Extended, and so on).
   - **Track record:** for every grade, how many signals were confirmed or failed, and how they did against the Nifty 500 after 21 trading days.
2. **A Telegram post** in your channel with the same short list and a link to the page.

The page never shows a stock price. Clicking a stock opens its chart on TradingView.

## How it decides (plain version)

For each of the ~1,300 NSE stocks that trade at least Rs 1 crore a day:

1. **Stage:** is the 150-day average rising, flat or falling, and is the price above or below it? That puts the stock in Stage 1 (Basing), 2 (Advancing), 3 (Topping) or 4 (Declining). A change only counts after it holds for 5 days, so labels don't flicker.
2. **Trend template:** 8 yes/no checks from Mark Minervini (averages stacked in the right order, near the 52-week high, stronger than 70% of stocks, and so on). The score runs from 0 to 8.
3. **Breakout:** the stock went sideways for at least 15 days in a range 8–35% deep, then closed at least 2% above the top of that range on at least 1.5x normal volume.
4. **Grade:**
   - The **score** averages four momentum measures: RS rank, the 6-month return, how far the price is above its 200-day average, and how far above the range it closed. Testing on 2006–2026 showed these, not the shape of the range, decide how breakouts do.
   - **A:** above the 200-day average with a score in the top fifth of 2006–2018 breakouts.
   - **B:** above the 200-day average with a score in the top half.
   - **C:** everything else (not posted).
   - In a Weak market, every grade drops one level.
5. **Follow-up:** each breakout is watched for 10 days.
   - **Confirmed:** it held above the breakout level for those 10 days.
   - **Failed:** it closed below its fail line, 2.5 average daily ranges under the breakout close. A jumpy stock gets a wider line than a calm one.
   - Results are measured from the next morning's open, the first price you could actually buy at.

## How it runs on its own

- The code lives in a GitHub repository. GitHub gives every public repository free computers that can run a job on a schedule (GitHub Actions).
- At 7:00 pm IST, Monday to Friday, GitHub starts a fresh computer. It downloads 3 years of prices, runs the steps above, saves new signals to the ledger file, rebuilds the page and posts to Telegram. It takes about 5–10 minutes and costs nothing.
- Every evening's ledger is saved into the repository's history with a date stamp. Anyone can check that no signal was added or changed afterwards. That public proof is what will make people trust the track record later.
- You don't need your laptop on. If a run fails, GitHub emails you.

## Step 1: the repository

Done: the code lives at https://github.com/raghavendar002/StoxSonar.

## Step 2: create the Telegram bot and channel (5 minutes, on your phone)

**Make the bot**
1. In Telegram, search for **@BotFather** (the one with the blue tick) and open it.
2. Tap **Start**, then send `/newbot`.
3. When it asks for a name, send `StoxSonar Daily`.
4. When it asks for a username, send something ending in `bot`, for example `stoxsonar_daily_bot`. If it's taken, try another.
5. BotFather replies with a long **token** that looks like `7012345678:AAH...`. Copy it and keep it private, because anyone who has it can post as your bot.

**Make the channel**
6. In Telegram, tap the pencil (new message), then **New Channel**.
7. Name it `StoxSonar Daily` and add a short description, for example "Daily graded Stage 2 breakouts on NSE, with every past signal's result. Not investment advice."
8. Choose **Public** and pick a link, for example `t.me/stoxsonar`. The part after `t.me/` is your **channel name**.
9. Open the channel, tap its name, then **Administrators**, then **Add Admin**. Search for your bot's username, add it, and keep **Post Messages** switched on.

**Give both to GitHub**
10. Open `https://github.com/raghavendar002/StoxSonar/settings/secrets/actions`.
11. Click **New repository secret**. For Name, type `TELEGRAM_BOT_TOKEN`; for Secret, paste the token. Save.
12. Click **New repository secret** again. For Name, type `TELEGRAM_CHAT_ID`; for Secret, type your channel name with an @, for example `@stoxsonar`. Save.

Don't paste the token into this chat. Secrets stored in GitHub are encrypted and never shown in logs.

## Step 3: switch on the web page (30 seconds)

1. Open `https://github.com/raghavendar002/StoxSonar/settings/pages`
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.

That's everything. After that, I start the first run, which fills the history (marked "replay" so it's never mixed with the live record). From the next evening it runs on its own.

## Rules for the next 3 months

- Don't change the rules (`sonar/config.py`). Any change starts a new, empty track record.
- Don't delete failed signals.
- Each week, check two numbers:
  - Grade A/B results against Nifty on the page.
  - Your channel's subscriber count and how many people view each post.
