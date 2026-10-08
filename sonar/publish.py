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
                sessions=int(r.sessions or 0), move_pct=move, source=r.source))
        return out

    today = events[events["trigger_date"] == as_of]
    is_open = events["status"].isin(["Active", "Extended"]) & (events["trigger_date"] != as_of)
    live_sources = ["live", "late"]
    return dict(
        as_of=as_of, engine_version=C.ENGINE_VERSION, site_url=site_url,
        regime="Weak" if reg is None or bool(reg["weak"]) else "Healthy",
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


def _v(x, suffix="") -> str:
    return "–" if x is None or x != x else f"{x}{suffix}"


def _signal_table(rows, empty: str, show_status=False) -> str:
    if not rows:
        return f'<p class="empty">{_e(empty)}</p>'
    head = ("<tr><th>Stock</th>" + ("<th>Type</th>" if show_status else "") + "<th>Grade</th><th>Score</th><th>Stage at signal</th><th>Template</th>"
            "<th>RS rank</th><th>Fail line</th><th>Base</th><th>Volume</th>"
            + ("<th>Signal date</th><th>Status</th><th>Move since</th>" if show_status else "")
            + "</tr>")
    body = []
    for r in rows:
        mv = "" if r["move_pct"] is None else f'{r["move_pct"]:+.1f}%'
        body.append(
            f"<tr><td>{_tv(r['symbol'])}</td>"
            + (f"<td>{'Breakout' if r['direction'] == 'up' else 'Breakdown'}</td>" if show_status else "")
            + f"<td>{_grade(r['grade'])}</td><td>{_v(r['score'])}</td>"
            f"<td>{_e(C.STAGE_NAMES[r['stage']])}</td><td>{r['template']}/8</td>"
            f"<td>{_e(r['rs_rank'])}</td><td>{_v(r['stop_pct'], '%')}</td>"
            f"<td>{r['base_len']} sessions, {r['depth_pct']}% deep</td>"
            f"<td>{r['vol_ratio']}x avg</td>"
            + (f"<td>{_e(r['trigger_date'])}</td><td>{_e(r['status'])}</td><td>{mv}</td>" if show_status else "")
            + "</tr>")
    return f'<div class="scroll"><table>{head}{"".join(body)}</table></div>'


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
.empty,.note{color:var(--mute)}.foot{margin-top:40px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);padding-top:16px}
"""


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

<h2>New breakouts today</h2>
{_signal_table(s['breakouts'], 'No Grade A or B breakouts today.')}

<h2>New breakdowns today</h2>
{_signal_table(s['breakdowns'], 'No Grade A or B breakdowns today.')}

<h2>Signals still in play</h2>
{_signal_table(s['open_signals'], 'Nothing open.', show_status=True)}

<h2>Track record (live)</h2>
{_record_table(s['track_record_live'], live_note)}

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

def telegram_text(s: dict) -> str:
    lines = [f"StoxSonar · NSE close {s['as_of']}",
             f"Regime: {s['regime']} · Advancing {s['breadth']['Advancing']}% of {s['stocks']} stocks", ""]
    if s["breakouts"]:
        lines.append("New breakouts")
        for r in s["breakouts"]:
            lines.append(f"{r['grade']} · {r['symbol']} · score {_v(r['score'])}"
                         + (f" · RS {r['rs_rank']}" if r['rs_rank'] is not None else "")
                         + (f" · fail line {r['stop_pct']}%" if r['stop_pct'] is not None else ""))
    else:
        lines.append("No Grade A or B breakouts today.")
    if s["breakdowns"]:
        lines += ["", "New breakdowns"] + [f"{r['grade']} · {r['symbol']} · {C.STAGE_NAMES[r['stage']]}"
                                           for r in s["breakdowns"]]
    if s["closed_today"]:
        lines += ["", "Closed today"] + [f"{r['grade']} · {r['symbol']} {r['status']} ({r['move_pct']:+.1f}%)"
                                         for r in s["closed_today"]]
    if s.get("site_url"):
        lines += ["", f"Full list and track record: {s['site_url']}"]
    lines += ["", "Rule-based screen output, not investment advice."]
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
    r.raise_for_status()
    return True


def write_site(s: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(render_html(s), encoding="utf-8")
    (out_dir / "data.json").write_text(json.dumps(s, indent=1, default=str), encoding="utf-8")
    (out_dir / f"{s['as_of']}.json").write_text(json.dumps(s, default=str), encoding="utf-8")
