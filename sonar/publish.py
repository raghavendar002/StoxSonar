"""The public page, its JSON, and the evening Telegram post.

Nothing here shows a raw price. The page shows stage labels, grades and
percentage moves, and links each symbol to TradingView for the chart, so the
free beta does not redistribute exchange prices itself.
"""

from __future__ import annotations

import html
import json
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config as C
from .ledger import track_record
from .plan import trade_plan

log = logging.getLogger(__name__)

DISCLAIMER = ("StoxSonar publishes the output of a fixed, published rule set. It is not "
              "investment advice or a recommendation to buy or sell any security, and "
              "StoxSonar is not registered with SEBI as a research analyst. Past signals "
              "do not predict future results.")


def build_snapshot(states: pd.DataFrame, events: pd.DataFrame, regime: pd.DataFrame,
                   as_of: str, site_url: str = "") -> dict:
    day = states[states["date"] == pd.Timestamp(as_of)]
    counts = day["stage"].value_counts().to_dict()
    total = max(len(day), 1)
    reg = regime.loc[pd.Timestamp(as_of)] if pd.Timestamp(as_of) in regime.index else None
    stage_of = day.set_index("symbol")[["stage", "stage_age"]].to_dict("index")
    last_close = day.set_index("symbol")["close"].to_dict()

    def rows(df):
        out = []
        for r in df.itertuples():
            st = stage_of.get(r.symbol, {})
            move = None
            if r.symbol in last_close and r.entry:
                move = round((last_close[r.symbol] / r.entry - 1) * 100, 1)
            out.append(dict(
                symbol=r.symbol.replace(".NS", ""), grade=r.grade, direction=r.direction,
                trigger_date=r.trigger_date, stage=int(r.stage),
                stage_now=st.get("stage"), stage_age=st.get("stage_age"),
                template=int(r.template), rs_rank=None if pd.isna(r.rs_rank) else int(r.rs_rank),
                base_len=int(r.base_len), depth_pct=round(r.depth * 100, 1),
                vol_ratio=round(r.vol_ratio, 1), status=r.status,
                score=None if pd.isna(getattr(r, "score", None)) else round(float(r.score), 2),
                stop_pct=None if pd.isna(getattr(r, "stop", None)) or not r.entry
                else round((r.stop / r.entry - 1) * 100, 1),
                sessions=int(r.sessions or 0), move_pct=move, source=r.source,
                plan=trade_plan(float(r.entry), float(r.stop), r.trigger_date)
                if r.direction == "up" and not pd.isna(getattr(r, "stop", None)) else None))
        return out

    today = events[events["trigger_date"] == as_of]
    is_open = events["status"].isin(["Active", "Extended"]) & (events["trigger_date"] != as_of)
    live_sources = ["live", "late"]
    weak = reg is None or bool(reg["weak"])
    return dict(
        as_of=as_of, engine_version=C.ENGINE_VERSION, site_url=site_url,
        regime="Weak" if weak else "Healthy",
        buys_allowed=not (weak and C.NO_LONGS_WHEN_WEAK),
        benchmark_above_rising_sma200=None if reg is None else bool(reg["bench_ok"]),
        stocks=int(len(day)),
        breadth={C.STAGE_NAMES[s]: round(counts.get(s, 0) / total * 100, 1) for s in (1, 2, 3, 4)},
        breakouts=rows(today[(today["direction"] == "up") & today["grade"].isin(["A", "B"])]),
        breakdowns=rows(today[(today["direction"] == "down") & today["grade"].isin(["A", "B"])]),
        open_signals=rows(events[is_open & events["grade"].isin(["A", "B"])]),
        # Only signals recorded live: replayed history must never read as a live result
        closed_today=rows(events[(events["status_date"] == as_of) & (events["trigger_date"] != as_of)
                                 & (events["source"] != "replay")
                                 & events["status"].isin(["Confirmed", "Failed"])
                                 & events["grade"].isin(["A", "B"])]),
        track_record_live=track_record(events, live_sources).to_dict("records"),
        track_record_replay=track_record(events, ["replay"]).to_dict("records"),
        # Logged-only phase 3 grade on the same live signals; compare with track_record_live
        track_record_live_shadow=track_record(events, live_sources, grade_col="shadow_grade").to_dict("records"),
        live_signals=int(events["source"].isin(live_sources).sum()),
    )


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def _e(x) -> str:
    return html.escape("" if x is None else str(x))


def _tv(sym: str) -> str:
    return f'<a href="https://www.tradingview.com/chart/?symbol=NSE:{_e(sym)}" rel="noopener">{_e(sym)}</a>'


def _grade(g: str) -> str:
    return f'<span class="g g{_e(g)}">{_e(g)}</span>'


COLUMN_HELP = [
    ("Type", "Breakout: the price just rose out of a sideways range. Breakdown: it just fell out of one. "
             "A breakdown is a warning to avoid or exit the stock, not a tip to short it."),
    ("Grade", "How strong the stock's momentum was at the breakout, by its score. A is the top fifth of "
              "past breakouts, B the top half. C and below are not shown. In a Weak market every buy "
              "grade is cut one level, and no buys are suggested at all."),
    ("Score", "Average of four momentum measures: RS rank, 6-month return, distance above the 200-day "
              "average and how far above the base it closed. 0 is a typical past breakout."),
    ("Buy", f"How many shares risk {C.RISK_PCT * 100:g}% of Rs {C.CAPITAL_RS:,} if the stop is hit. Buy at "
            "the next open, and skip it if the open is above the limit shown (1 ATR above the close)."),
    ("Stop", "Sell if it closes below this, measured from the signal close: 2.5 average daily ranges."),
    ("Sell by", f"Time exit: sell at the close {C.HOLD_SESSIONS} trading days after the signal (approximate; "
                "exchange holidays move it later)."),
    ("Fail line", "Same level as the stop: a close beyond it marks the signal Failed."),
    ("Stage at signal", "The stock's trend when the signal fired. Advancing (Stage 2) is the uptrend breakouts "
                        "should come from. Basing is flat after a fall, Topping is flat after a rise, "
                        "Declining is a downtrend."),
    ("Template", "How many of 8 trend checks pass (averages in the right order, near the 52-week high, "
                 "stronger than most stocks). 8/8 is a clean uptrend."),
    ("RS rank", "Relative strength: how this stock moved over the past year compared with all others, "
                "1 to 99. 90 means it beat 90% of NSE stocks."),
    ("Base", "The sideways range it broke out of: how many trading days it lasted and how deep it was "
             "from top to bottom."),
    ("Volume", "Shares traded on the signal day compared with a normal day. 2x or more shows real buying."),
    ("Signal date", "The trading day the signal fired, after that day's close."),
    ("Status", "Active: still near the breakout level, where you risk the least if you are wrong. "
               "Extended: already more than 5% above it, so buying now means chasing. "
               "Confirmed: held above the level for 10 days. Failed: closed beyond its fail line. "
               "Faded: dipped below and never recovered or failed."),
    ("Move since", "How much the stock has moved since the signal day's close."),
]
STATUS_PLAIN = {"Active": "Active · near level", "Extended": "Extended · don't chase"}


def today_summary(s: dict) -> list:
    """Plain sentences for the top of the page: what today's list means for a reader."""
    out = []
    if s["regime"] == "Weak" and not s.get("buys_allowed", True):
        out.append("The market is weak, so no new buys are suggested. Breakouts are still logged below "
                   "so the record stays complete, but in past data most of them lagged the index.")
    elif s["regime"] == "Weak":
        out.append("The market is weak, so breakouts fail more often than usual. Every buy grade is cut "
                   "one level, and fewer good setups appear.")
    else:
        out.append("The market is healthy, which is when breakouts have worked best.")
    a_new = [r for r in s["breakouts"] if r["grade"] == "A"]
    if not s.get("buys_allowed", True):
        pass
    elif a_new:
        out.append(f"{len(a_new)} new Grade A breakout{'s' if len(a_new) > 1 else ''} today: "
                   + ", ".join(r["symbol"] for r in a_new) + ". These are the ones worth a look.")
    elif s["breakouts"]:
        out.append("No Grade A breakouts today, only B. In past data B breakouts beat the Nifty 500 by only "
                   "a fraction of a percent a month on average, so treat them as a watchlist, not buys.")
    else:
        out.append("No new breakouts today. Nothing new to look at.")
    ups = [r for r in s["open_signals"] if r["direction"] == "up"]
    act = sum(r["status"] == "Active" for r in ups)
    ext = sum(r["status"] == "Extended" for r in ups)
    if ups:
        out.append(f"Of {len(ups)} earlier breakouts still open, {act} are Active (near the breakout level, "
                   f"lowest risk) and {ext} are Extended (already more than 5% up; buying now is chasing).")
    out.append("Paper-trade only for now: write down what you would do and check it later. The live "
               "track record is too short to trust with money.")
    return out


def _column_help() -> str:
    items = "".join(f"<dt>{_e(k)}</dt><dd>{_e(v)}</dd>" for k, v in COLUMN_HELP)
    return f'<details class="help"><summary>What the columns mean</summary><dl>{items}</dl></details>'


def _v(x, suffix="") -> str:
    return "–" if x is None or x != x else f"{x}{suffix}"


def _signal_table(rows, empty: str, show_status=False, plan=False) -> str:
    """Most useful columns first, so phones see them without scrolling."""
    if not rows:
        return f'<p class="empty">{_e(empty)}</p>'
    help_of = dict(COLUMN_HELP)

    def cells(r):
        c = [("Stock", _tv(r["symbol"]))]
        if show_status:
            c += [("Type", "Breakout" if r["direction"] == "up" else "Breakdown")]
        c += [("Grade", _grade(r["grade"]))]
        if show_status:
            mv = "" if r["move_pct"] is None else f'{r["move_pct"]:+.1f}%'
            c += [("Status", _e(STATUS_PLAIN.get(r["status"], r["status"]))), ("Move since", mv),
                  ("Signal date", _e(r["trigger_date"]))]
        p = r.get("plan")
        if plan and p:
            c += [("Buy", f"{p['qty']} shares, only if the open is under +{p['max_buy_pct']}%"),
                  ("Stop", f"{p['stop_pct']}%"), ("Sell by", _e(p["exit_by"]))]
        elif plan:
            c += [("Buy", ""), ("Stop", ""), ("Sell by", "")]
        c += [("Score", _v(r.get("score"))), ("Fail line", _v(r.get("stop_pct"), "%"))]
        c += [("RS rank", _e(r["rs_rank"])), ("Stage at signal", _e(C.STAGE_NAMES[r["stage"]])),
              ("Template", f"{r['template']}/8"), ("Volume", f"{r['vol_ratio']}x avg"),
              ("Base", f"{r['base_len']} sessions, {r['depth_pct']}% deep")]
        return c

    cols = [k for k, _ in cells(rows[0])]
    head = "<tr>" + "".join(f'<th title="{_e(help_of.get(c, ""))}">{c}</th>' for c in cols) + "</tr>"
    body = "".join("<tr>" + "".join(f"<td>{v}</td>" for _, v in cells(r)) + "</tr>" for r in rows)
    return f'<div class="scroll"><table>{head}{body}</table></div>'


def _record_table(rows, note: str) -> str:
    def v(x, suffix=""):
        return "–" if x is None or x != x else f"{x}{suffix}"
    body = "".join(
        f"<tr><td>{_grade(r['grade'])}</td><td>{r['signals']}</td><td>{v(r['confirmed_pct'], '%')}</td>"
        f"<td>{v(r['failed_pct'], '%')}</td><td>{r['measured_21']}</td>"
        f"<td>{v(r['avg_excess_21_pct'], '%')}</td><td>{v(r['win_pct_21'], '%')}</td>"
        f"<td>{v(r['avg_r_21'], 'R')}</td></tr>" for r in rows)
    return (f'<p class="note">{_e(note)}</p><div class="scroll"><table>'
            "<tr><th>Grade</th><th>Signals</th><th>Confirmed</th><th>Failed</th>"
            "<th>Measured at 21 sessions</th><th>Avg vs Nifty 500</th><th>Beat Nifty 500</th>"
            f"<th>Avg R</th></tr>{body}</table></div>")


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1c1a;--mute:#6b6862;--line:#e4e1da;--card:#fff;--accent:#0f766e;
--a:#0f766e;--b:#b45309;--c:#6b7280;--w:#b91c1c;--s1:#94a3b8;--s2:#16a34a;--s3:#f59e0b;--s4:#dc2626}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#141413;--fg:#ecebe7;--mute:#a19e97;
--line:#2c2b29;--card:#1c1c1a;--accent:#2dd4bf;--a:#2dd4bf;--b:#fbbf24;--c:#9ca3af;--w:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:980px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0}h2{font-size:18px;margin:36px 0 8px}
.sub{color:var(--mute);margin:4px 0 20px}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-weight:600;font-size:13px}
.Healthy{background:color-mix(in srgb,var(--s2) 18%,transparent);color:var(--s2)}
.Weak{background:color-mix(in srgb,var(--s4) 18%,transparent);color:var(--s4)}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;margin:10px 0 4px}
.bar span{display:block}.legend{display:flex;flex-wrap:wrap;gap:14px;color:var(--mute);font-size:13px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}
th,td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line)}
th{color:var(--mute);font-weight:500;font-size:12px}tr:last-child td{border-bottom:0}
a{color:var(--accent);text-decoration:none;font-weight:600}
.g{display:inline-block;min-width:22px;text-align:center;border-radius:5px;font-weight:700;color:#fff;padding:0 6px}
.gA{background:var(--a)}.gB{background:var(--b)}.gC{background:var(--c)}.gW{background:var(--w)}
.today{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:10px;padding:12px 16px;margin:16px 0}.today p{margin:6px 0}
.help{margin:10px 0;color:var(--mute);font-size:14px}.help summary{cursor:pointer;color:var(--accent);font-weight:600}
.help dt{font-weight:600;color:var(--fg);margin-top:8px}.help dd{margin:2px 0 0}
.empty,.note{color:var(--mute)}.foot{margin-top:40px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);padding-top:16px}
"""


BOOK_NAMES = {"raw": "Raw v0.2", "twin": "Twin (every pick)", "debated": "Debated (every verdict)",
              "judge": "Judge (Go picks)"}


def _books_section(rows) -> str:
    if not rows:
        return ""
    body = "".join(
        f"<tr><td>{_e(BOOK_NAMES.get(r['book'], r['book']))}</td>"
        f"<td>{'Long' if r['direction'] == 'up' else 'Shadow short'}</td><td>{r['picks']}</td>"
        f"<td>{r['closed']}</td><td>{r['open']}</td><td>{_v(r['avg_r'], 'R')}</td><td>{_v(r['median_r'], 'R')}</td>"
        f"<td>{_v(r['win_pct'], '%')}</td><td>{_v(r['avg_excess_pct'], '%')}</td></tr>" for r in rows)
    return (
        "<h2>Mid-term books (paper)</h2>"
        "<p class=\"note\">Every candidate is turned into a paper trade with fixed rules: buy at the next open, "
        "exit at the stop, the target or the close 21 sessions later, after costs. <b>Raw</b> trades as v0.2 "
        "suggests today; <b>Twin</b> takes every breakout (C grades too) and every A/B breakdown as a shadow "
        "short, with no market filter. <b>Debated</b> is every stock the Judge ruled on, at the Judge's levels; "
        "<b>Judge</b> is only its Go picks. <a href=\"books.csv\">Every pick</a> · "
        "<a href=\"debates.html\">every debate</a>.</p>"
        "<table><thead><tr><th>Book</th><th>Side</th><th>Picks</th><th>Closed</th><th>Open</th><th>Avg R</th>"
        f"<th>Median R</th><th>Wins</th><th>Vs index</th></tr></thead><tbody>{body}</tbody></table>")


def render_html(s: dict) -> str:
    colors = {"Basing": "var(--s1)", "Advancing": "var(--s2)", "Topping": "var(--s3)", "Declining": "var(--s4)"}
    bar = "".join(f'<span style="width:{v}%;background:{colors[k]}" title="{k} {v}%"></span>'
                  for k, v in s["breadth"].items())
    legend = "".join(f'<span><i style="background:{colors[k]}"></i>{k} {v}%</span>'
                     for k, v in s["breadth"].items())
    live_note = (f"{s['live_signals']} signals recorded live so far. Every signal is logged the evening "
                 "it fires and never edited; failures stay in.")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>StoxSonar Daily</title><meta name="description" content="Daily Weinstein stage and graded breakout screen for NSE stocks, with every past signal's outcome.">
<style>{CSS}</style></head><body><main>
<h1>StoxSonar Daily</h1>
<p class="sub">NSE · close of {_e(s['as_of'])} · {s['stocks']} liquid stocks · rules v{_e(s['engine_version'])}</p>
<p>Market regime <span class="pill {_e(s['regime'])}">{_e(s['regime'])}</span>
{'' if s['regime'] == 'Healthy' else ' Bullish grades are cut one level in a weak market.'}</p>
<div class="bar">{bar}</div><div class="legend">{legend}</div>
<div class="today"><b>What this means today</b>{''.join(f"<p>{_e(x)}</p>" for x in today_summary(s))}</div>

<h2>{'New buys today' if s.get('buys_allowed', True) else 'New breakouts today (logged, not suggested: market weak)'}</h2>
{_signal_table(s['breakouts'], 'No Grade A or B breakouts today.', plan=s.get('buys_allowed', True))}

<h2>New breakdowns today (avoid or exit; not shorts)</h2>
{_signal_table(s['breakdowns'], 'No Grade A or B breakdowns today.')}

<h2>Signals still in play</h2>
{_signal_table(s['open_signals'], 'Nothing open.', show_status=True)}
{_column_help()}

<h2>Track record (live)</h2>
{_record_table(s['track_record_live'], live_note)}

{_books_section(s.get('books') or [])}

<h2>Backtest replay</h2>
{_record_table(s['track_record_replay'], 'The same rules replayed over past data before the live record began. Treat it as a hint, not proof.')}

<h2>How it works</h2>
<p><b>Stage</b> follows Weinstein: the 150-day average and its one-month slope decide Basing, Advancing,
Topping or Declining, and a change counts only after 5 sessions. <b>Template</b> is Minervini's 8-point
trend template, shown for context. <b>Breakout</b> is a close at least 2% above a base of 15+ sessions
and 8–35% depth, on 1.5x average volume, closing in the upper half of the day with a small upper wick.
<b>Score</b> averages four measures of momentum: RS rank, the 6-month return, distance above the
200-day average and how far above the base the stock closed. Only breakouts above the 200-day average
can grade A or B: <b>A</b> is a score in the top fifth of 2006–2018 breakouts, <b>B</b> the top half.
A signal is <b>Confirmed</b> if it holds above the base for 10 sessions and <b>Failed</b> if it closes
below its fail line, 2.5 average daily ranges under the breakout close. Results are measured from the
next day's open, the first price anyone could buy at. R is the 21-session move divided by the distance
to the fail line.</p>
<p class="foot">{_e(DISCLAIMER)} Charts open on TradingView.</p>
</main></body></html>"""


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _rs(x: float) -> str:
    return f"Rs {x:,.2f}" if x < 1000 else f"Rs {x:,.0f}"


def telegram_text(s: dict) -> str:
    lines = [("Delayed · " if s.get("delayed") else "") + f"StoxSonar · NSE close {s['as_of']}",
             f"Regime: {s['regime']} · Advancing {s['breadth']['Advancing']}% of {s['stocks']} stocks", ""]
    if s["breakouts"] and not s.get("buys_allowed", True):
        lines.append(f"Market is Weak: no new buys today. {len(s['breakouts'])} breakout(s) logged for "
                     "the record only: " + ", ".join(r["symbol"] for r in s["breakouts"]))
    elif s["breakouts"]:
        lines.append(f"New buys (risk {C.RISK_PCT * 100:g}% of Rs {C.CAPITAL_RS:,} each)")
        for r in s["breakouts"]:
            lines.append(f"{r['grade']} · {r['symbol']} · score {_v(r['score'])}"
                         + (f" · RS {r['rs_rank']}" if r['rs_rank'] is not None else ""))
            p = r.get("plan")
            if p:
                lines.append(f"   Buy {p['qty']} at the open, only if under {_rs(p['max_buy'])} · "
                             f"stop {_rs(p['stop'])} ({p['stop_pct']}%) · sell by close {p['exit_by']}"
                             f" · ~Rs {p['value_rs']:,}, risk Rs {p['risk_rs']:,}")
    else:
        lines.append("No Grade A or B breakouts today.")
    if s["breakdowns"]:
        lines += ["", "Breakdowns (avoid or exit; not shorts)"] + [
            f"{r['grade']} · {r['symbol']} · {C.STAGE_NAMES[r['stage']]}" for r in s["breakdowns"]]
    if s["closed_today"]:
        lines += ["", "Closed today"] + [f"{r['grade']} · {r['symbol']} {r['status']} ({r['move_pct']:+.1f}%)"
                                         for r in s["closed_today"]]
    book_lines = books_lines(s.get("books") or [])
    if book_lines:
        lines += ["", "Mid-term paper books (after costs)"] + book_lines
    if s.get("site_url"):
        lines += ["", f"Full list and track record: {s['site_url']}"]
    lines += ["", "Rule-based screen output, not investment advice."]
    return "\n".join(lines)


def books_lines(rows) -> list:
    out = []
    for r in rows:
        if not r["closed"]:
            continue
        side = "longs" if r["direction"] == "up" else "shadow shorts"
        out.append(f"{BOOK_NAMES.get(r['book'], r['book'])} {side}: {r['closed']} closed, "
                   f"avg {r['avg_r']:+.2f}R, wins {r['win_pct']:.0f}% · {r['open']} open")
    return out


def us_telegram_text(events: pd.DataFrame, as_of: str, book_rows) -> str:
    """One short message for the US shadow list: logged and scored, never suggested."""
    today = events[(events["trigger_date"] == as_of) & (events["source"] == "live")]
    ups = today[(today["direction"] == "up") & today["grade"].isin(["A", "B"])]
    downs = today[(today["direction"] == "down") & today["grade"].isin(["A", "B"])]
    lines = [f"StoxSonar · US shadow list (S&P 500) · close {as_of}",
             "Logged and scored only. No suggestions: grade cut-offs are still NSE's until refitted.", ""]
    lines.append(f"Breakouts A/B: {', '.join(f'{r.grade} {r.symbol}' for r in ups.itertuples()) or 'none'}")
    lines.append(f"Breakdowns A/B (shadow shorts): {', '.join(f'{r.grade} {r.symbol}' for r in downs.itertuples()) or 'none'}")
    bl = books_lines(book_rows or [])
    if bl:
        lines += ["", "Paper books (after costs)"] + bl
    return "\n".join(lines)


def send_telegram(text: str, token: Optional[str] = None, chat_id: Optional[str] = None) -> bool:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        log.info("Telegram not configured; skipping post")
        return False
    import requests
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
                      timeout=30)
    if not r.ok:
        # raise_for_status() would put the URL, and with it the bot token, in the public log
        raise RuntimeError(f"Telegram post failed with HTTP {r.status_code}")
    return True


def write_site(s: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_html(s), encoding="utf-8")
    (out_dir / "data.json").write_text(json.dumps(s, indent=1, default=str), encoding="utf-8")
    (out_dir / f"{s['as_of']}.json").write_text(json.dumps(s, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Bull / Bear / Judge: the second message and the debates page
# ---------------------------------------------------------------------------

DEBATE_NOTE = ("An experiment, not advice: the screen under these calls has not passed its test, and the "
               "Judge has no track record yet. Every call is logged and scored.")
SKIPPED = {"not_debated_daily_limit": "not debated (daily limit of 3)",
           "not_debated_budget": "not debated (monthly API budget reached)",
           "no_fact_pack": "not debated (no data pack)", "error": "debate failed", "refused": "debate failed"}


def _px(x) -> str:
    return f"{x:,.2f}" if x < 1000 else f"{x:,.0f}"


def _levels_line(v: dict, up: bool) -> str:
    t2 = f" then {_px(v['target_2'])}" if v.get("target_2") else ""
    side = "Buy" if up else "Short"
    return (f"{side} {_px(v['entry_low'])}–{_px(v['entry_high'])} · stop {_px(v['stop'])} · "
            f"target {_px(v['target'])}{t2} · hold up to {v['horizon_sessions']} sessions")


def _wait_line(v: dict) -> str:
    vol = f" on volume ≥ {v['wait_min_volume_ratio']:g}x average" if v.get("wait_min_volume_ratio") else ""
    word = "above" if v["wait_kind"] == "close_above" else "below"
    return f"Wait for a close {word} {_px(v['wait_level'])}{vol} within {v['wait_within_sessions']} sessions"


def debate_telegram_text(as_of: str, rows: list, waits: list, record: list, spent_usd: float) -> str:
    lines = [f"StoxSonar · Bull/Bear/Judge · NSE close {as_of}", ""]
    for r in rows:
        name = r["symbol"].replace(".NS", "")
        up = r["direction"] == "up"
        kind = "breakout" if up else "breakdown, SHADOW SHORT (logged, not traded)"
        if r["status"] != "done":
            lines += [f"{name} · {r['grade']} {kind}: {SKIPPED.get(r['status'], r['status'])}", ""]
            continue
        v = r["v"]
        lines.append(f"{v['verdict'].upper()} · {name} · {r['grade']} {kind} · conviction {v['conviction']}/5")
        if not r["levels_ok"]:
            lines.append("   The Judge's levels broke the rules (" + "; ".join(r["problems"])
                         + "), so the paper trade uses v0.2's stop.")
        elif v["verdict"] == "Wait":
            lines.append("   " + _wait_line(v) + ". Then: " + _levels_line(v, up))
        else:
            lines.append("   " + ("" if v["verdict"] == "Go" else "If taken anyway: ") + _levels_line(v, up))
        if up and v["verdict"] == "Go" and r.get("regime") == "Weak":
            lines.append("   Market is Weak: v0.2 itself suggests no buys today.")
        lines.append("   " + v["how_its_moving"])
        if v["reasons_for"]:
            lines.append("   For: " + " | ".join(v["reasons_for"][:3]))
        if v["reasons_against"]:
            lines.append("   Against: " + " | ".join(v["reasons_against"][:3]))
        lines.append("   Wrong if: " + v["invalidation"])
        lines.append("")
    for w in waits:
        name = w["symbol"].replace(".NS", "")
        if w["status"] == "triggered":
            lines += [f"WAIT MET · {name} (signal {w['signal_date']}): now a Go for the paper book. "
                      + _levels_line(w["v"], w["direction"] == "up"), ""]
        else:
            lines += [f"Wait expired · {name} (signal {w['signal_date']}): condition not met in time.", ""]
    closed = [r for r in record if r["closed"]]
    if closed:
        lines.append("How past verdicts turned out (after costs): " + " · ".join(
            f"{r['verdict']} {r['closed']} closed, avg {r['avg_r']:+.2f}R" for r in closed))
    lines.append(f"API spend this month: ${spent_usd:.2f} of ${C.DEBATE_MONTHLY_CAP_USD:.0f}")
    lines += ["", DEBATE_NOTE]
    text = "\n".join(lines)
    return text if len(text) <= 4000 else text[:3990] + "\n(cut)"     # Telegram's limit is 4096


def write_debates(con, market: str, out_dir: Path) -> None:
    """site/debates.html: every debate in full, newest first, with how it ended."""
    import json as _json
    d = pd.read_sql_query("SELECT * FROM mt_debates WHERE market=? AND status='done' "
                          "ORDER BY signal_date DESC, symbol", con, params=(market,))
    picks = pd.read_sql_query("SELECT symbol, direction, signal_date, status, exit_reason, r, ret FROM mt_picks "
                              "WHERE market=? AND book='debated'", con, params=(market,))
    ended = {(p.symbol, p.direction, p.signal_date): p for p in picks.itertuples()}
    parts = []
    for r in d.itertuples():
        v = _json.loads(r.judge)
        up = r.direction == "up"
        p = ended.get((r.symbol, r.direction, r.signal_date))
        if p is None or p.status in ("pending", "open"):
            how = "Still running." if p is not None and p.status == "open" else "Not started yet."
        elif p.status == "skipped":
            how = f"No paper trade: {p.exit_reason}."
        else:
            how = f"Paper trade closed by {p.exit_reason}: {p.r:+.2f}R ({p.ret * 100:+.1f}%) after costs."
        wait = ""
        if v["verdict"] == "Wait" and r.wait_status:
            wait = f"<p>{_e(_wait_line(v))}. Status: {_e(r.wait_status)}{' on ' + _e(r.wait_date) if r.wait_date else ''}.</p>"
        flag = f"<p class=\"note\">Levels rejected by the rule check: {_e(r.level_problems)}.</p>" if r.level_problems else ""
        lst = lambda xs: "".join(f"<li>{_e(x)}</li>" for x in xs)  # noqa: E731
        parts.append(
            f"<h2>{_e(r.symbol.replace('.NS', ''))} · {_e(r.signal_date)} · "
            f"{'breakout' if up else 'breakdown (shadow short)'} · grade {_e(r.grade)}</h2>"
            f"<p><b>{_e(v['verdict'])}</b>, conviction {v['conviction']}/5. {_e(_levels_line(v, up))}.</p>"
            f"{wait}{flag}<p>{_e(v['how_its_moving'])}</p>"
            f"<p><b>For</b></p><ul>{lst(v['reasons_for'])}</ul><p><b>Against</b></p><ul>{lst(v['reasons_against'])}</ul>"
            f"<p><b>Wrong if:</b> {_e(v['invalidation'])}</p><p><b>How it turned out:</b> {_e(how)}</p>"
            f"<details><summary>Bull's case</summary><p>{_e(r.bull)}</p></details>"
            f"<details><summary>Bear's case</summary><p>{_e(r.bear)}</p></details>")
    body = "".join(parts) or "<p class=\"empty\">No debates yet.</p>"
    page = (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>StoxSonar debates</title><style>{CSS}details{{margin:8px 0}}summary{{cursor:pointer}}</style>"
            f"</head><body><main><h1>Bull / Bear / Judge</h1><p class=\"sub\">{_e(DEBATE_NOTE)} "
            f"<a href=\"index.html\">Back to the daily page</a></p>{body}"
            f"<p class=\"foot\">{_e(DISCLAIMER)}</p></main></body></html>")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "debates.html").write_text(page, encoding="utf-8")
