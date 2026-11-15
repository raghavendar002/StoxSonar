// Screens: Today, Trades, Debates, and the two detail views (a debate case, a plain signal).
import { state, feed, esc, num, pct, rfmt, sign, money, pnl, px, day, shortDay, tv, icon, note, empty, rpill,
  verdictChip, dots, tradeLine, findCase, currency } from "./core.js";
import { breadthBar, breadthHistory, caseChart, ladder } from "./charts.js";

const ui = (k, d) => (state.ui[k] === undefined ? d : state.ui[k]);
const sigId = (r) => `${r.symbol}|${r.direction}|${r.trigger_date}`;
const section = (title, right = "") => `<div class="section"><h2>${esc(title)}</h2>${right}</div>`;
const kpi = (label, v, s = "", cls = "") => `<div class="kpi"><div class="eyebrow">${esc(label)}</div><div class="v ${cls}">${v}</div><div class="s">${s}</div></div>`;
const notes = (f) => (f && f.notes ? f.notes.map((n) => note(n, "info")).join("") : "");
const marketName = () => (state.market === "IN" ? "India" : "US");

// ---------------------------------------------------------------- shared rows
function signalRow(r) {
  const upDir = r.direction === "up";
  const prog = Math.min(100, ((r.sessions || 0) / 21) * 100);
  return `<button class="item" data-act="open-signal" data-id="${esc(sigId(r))}">
    <span class="grade ${esc(r.grade)}">${esc(r.grade)}</span>
    <span class="grow"><span class="row"><span class="sym">${esc(r.symbol)}</span>
      ${r.status ? `<span class="chip ${r.status === "Active" ? "info" : r.status === "Failed" ? "avoid" : r.status === "Confirmed" ? "go" : ""}">${esc(r.status)}</span>` : ""}</span>
      <span class="sub"><span class="${upDir ? "up" : "down"}">${upDir ? "▲ Breakout" : "▼ Breakdown"}</span> · ${esc(shortDay(r.trigger_date))} · day ${r.sessions || 0} of 21${r.rs_rank != null ? ` · RS ${Math.round(r.rs_rank)}` : ""}</span>
      <span class="meter"><span style="width:${prog}%"></span></span></span>
    <span class="end">${r.move_pct != null ? `<span class="big ${sign(r.move_pct)}">${pct(r.move_pct)}</span>` : r.ret_21_pct != null ? `<span class="big ${sign(r.ret_21_pct)}">${pct(r.ret_21_pct)}</span>` : ""}
      <div class="dim" style="font-size:11.5px">${r.move_pct != null ? "since signal" : ""}</div></span></button>`;
}

function caseRow(c, cur) {
  const oj = c.outcome && c.outcome.judge, ot = c.outcome && c.outcome.twin;
  const sub = c.horizon === "intra"
    ? `Judge: ${esc(tradeLine(oj))} · Twin: ${esc(tradeLine(ot))}`
    : `${esc(c.headline || "")}${c.judge && c.judge.conviction ? ` · conviction ${c.judge.conviction}/5` : ""}`;
  return `<button class="item" data-act="open-case" data-id="${esc(c.id)}">
    ${c.grade ? `<span class="grade ${esc(c.grade)}">${esc(c.grade)}</span>` : `<span class="grade" style="color:var(--judge);background:var(--judge-soft)">${icon("judge")}</span>`}
    <span class="grow"><span class="row"><span class="sym">${esc(c.symbol)}</span>${verdictChip(c.judge)}
      <span class="dim" style="font-size:12px">${esc(shortDay(c.date))}</span></span>
      <span class="sub">${sub}</span></span>
    <span class="end stack">${oj && oj.r != null ? rpill(oj.r) : `<span class="rpill">${oj && oj.status === "passed" ? "pass" : "–"}</span>`}
      <span class="dim" style="font-size:11px">twin ${ot && ot.r != null ? rfmt(ot.r) : "–"}</span></span></button>`;
}

function duel(j, t, cur, title) {
  if (!j || !t) return "";
  const jw = (j.pnl || 0) > (t.pnl || 0), tw = (t.pnl || 0) > (j.pnl || 0);
  const side = (who, b, tone, win, ic) => `<div class="side-card ${win ? "win" : ""}">
    <div class="who" style="color:${tone}">${icon(ic)}${who}${win ? `<span class="crown">ahead</span>` : ""}</div>
    <div class="amt ${sign(b.pnl)}">${pnl(b.pnl, cur)}</div>
    <div class="muted num" style="font-size:12.5px">${rfmt(b.r)} · ${b.trades} trade${b.trades === 1 ? "" : "s"}${b.trades ? ` · ${b.wins} won` : ""}</div></div>`;
  return `<div class="card">${title ? `<div class="eyebrow" style="margin-bottom:10px">${esc(title)}</div>` : ""}
    <div class="duel">${side("Judge", j, "var(--judge)", jw, "judge")}<div class="vs">VS</div>${side("Twin", t, "var(--text-2)", tw, "trades")}</div></div>`;
}

const BOOK_NAMES = { raw: "Raw v0.2", twin: "Twin (every pick)", debated: "Debated (every verdict)", judge: "Judge (Go picks)" };
function booksTable(rows) {
  if (!rows || !rows.length) return "";
  const body = rows.map((r) => `<tr><td><b>${esc(BOOK_NAMES[r.book] || r.book)}</b><div class="dim" style="font-size:11.5px">${r.direction === "up" ? "Longs" : "Shadow shorts"}</div></td>
    <td>${r.picks}</td><td>${r.closed}</td><td>${r.open}</td><td class="${sign(r.avg_r)}">${rfmt(r.avg_r)}</td><td>${r.win_pct == null ? "–" : num(r.win_pct, 0) + "%"}</td>
    <td class="${sign(r.avg_excess_pct)}">${pct(r.avg_excess_pct)}</td></tr>`).join("");
  return `<div class="card scroll"><table><thead><tr><th>Book</th><th>Picks</th><th>Closed</th><th>Open</th><th>Avg</th><th>Wins</th><th>Vs index</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

// ---------------------------------------------------------------- Today
function brief(s) {
  const out = [];
  if (s.regime === "Weak" && s.buys_allowed === false) out.push("The market is weak, so no new buys are suggested. Breakouts are still logged so the record stays complete.");
  else if (s.regime === "Weak") out.push("The market is weak: breakouts fail more often, and every grade is cut one level.");
  else out.push("The market is healthy, which is when breakouts have worked best.");
  const ups = s.open_signals.filter((r) => r.direction === "up");
  if (ups.length) {
    const act = ups.filter((r) => r.status === "Active").length;
    out.push(`${ups.length} earlier breakouts are still open: ${act} near their level, ${ups.length - act} already extended (buying those is chasing).`);
  }
  out.push("Paper-trade only for now. The live record is too short to trust with money.");
  return out;
}

function todayMidIN(f) {
  const s = f && f.snapshot;
  if (!s) return empty("No data yet", "The evening run has not published anything this app can read.");
  const weak = s.regime === "Weak", a = s.breakouts.filter((r) => r.grade === "A");
  const head = s.buys_allowed === false ? "No new buys tonight"
    : a.length ? `${a.length} Grade A breakout${a.length > 1 ? "s" : ""}`
    : s.breakouts.length ? "Watchlist only tonight" : "Nothing new tonight";
  const ups = s.open_signals.filter((r) => r.direction === "up").length;
  const movers = s.open_signals.slice().sort((x, y) => Math.abs(y.move_pct || 0) - Math.abs(x.move_pct || 0)).slice(0, 3);
  const live = (s.track_record_live || []).reduce((n, r) => n + (r.signals || 0), 0);
  return `
    <div class="hero" style="--glow:${weak ? "var(--warn)" : "var(--bull)"}">
      <div class="row"><span class="status"><span class="pulse"></span>${esc(s.regime)} market</span>
        <span class="grow"></span><span class="chip">Close of ${esc(day(s.as_of))}</span></div>
      <h1>${esc(head)}</h1>
      <p>${s.stocks.toLocaleString("en-IN")} NSE stocks scanned · ${s.breakouts.length + s.breakdowns.length} new signal${s.breakouts.length + s.breakdowns.length === 1 ? "" : "s"} · ${s.open_signals.length} open</p>
      ${breadthBar(s.breadth)}
    </div>
    <div class="grid k4" style="margin-top:10px">
      ${kpi("New breakouts", s.breakouts.length, a.length ? `${a.length} Grade A` : "A and B grades")}
      ${kpi("New breakdowns", s.breakdowns.length, "shadow shorts")}
      ${kpi("Open signals", s.open_signals.length, `${ups} up · ${s.open_signals.length - ups} down`)}
      ${kpi("Live record", live, "signals logged live")}
    </div>
    ${section("The brief")}
    <div class="card"><ul class="brief">${brief(s).map((t) => `<li>${icon("check")}<span>${esc(t)}</span></li>`).join("")}</ul></div>
    ${section("New breakouts")}
    ${s.breakouts.length ? `<div class="list">${s.breakouts.map(signalRow).join("")}</div>` : empty("Nothing broke out today", "No stock closed above its base on heavy volume with an A or B grade.")}
    ${s.breakdowns.length ? section("New breakdowns") + `<div class="list">${s.breakdowns.map(signalRow).join("")}</div>` : ""}
    ${s.closed_today.length ? section("Closed today") + `<div class="list">${s.closed_today.map(signalRow).join("")}</div>` : ""}
    ${movers.length ? section("Biggest movers among open signals", `<a class="more" href="#/trades">All ${s.open_signals.length}</a>`) + `<div class="list">${movers.map(signalRow).join("")}</div>` : ""}
    ${f.history.length > 1 ? section("Market breadth") + `<div class="card">${breadthHistory(f.history)}</div>` : ""}
    ${f.books.length ? section("Paper books") + booksTable(f.books) : ""}`;
}

function todayMidUS(f) {
  if (!f || !f.signals.length) return notes(f) + empty("No US shadow list yet", "S&P 500 breakouts will be logged and scored here. They are never suggestions.");
  return `${note("Logged and scored only. US grade cut-offs are still India's until refitted, so nothing here is a suggestion.", "info")}
    ${section("US shadow list")}<div class="list">${f.signals.slice(0, 30).map(signalRow).join("")}</div>
    ${f.books.length ? section("Paper books") + booksTable(f.books) : ""}`;
}

function pickDay(f) {
  const days = (f && f.days) || [];
  const i = Math.min(ui("day", 0), Math.max(days.length - 1, 0));
  return { days, i, d: days[i] };
}
const dayChips = (days, i) => (days.length > 1 ? `<div class="chips" style="margin-bottom:12px">${days.map((d, k) =>
  `<button class="chip ${k === i ? "on" : ""}" data-act="set" data-k="day" data-v="${k}">${esc(shortDay(d.date))}</button>`).join("")}</div>` : "");

function todayIntra(f) {
  const { days, i, d } = pickDay(f);
  if (!d) return notes(f) + empty(`No ${marketName()} intraday days yet`, state.market === "IN"
    ? "The India scanner and its fixed-rule twin are the next build step. Days will appear here as they run."
    : "Days will appear here once daily paper trading starts.", "clock");
  const cur = f.currency, b = d.books;
  const head = !b ? "Decisions made, results pending"
    : b.judge.pnl > b.twin.pnl ? "The Judge beat the Twin" : b.judge.pnl < b.twin.pnl ? "The Twin beat the Judge" : "Judge and Twin tied";
  const maxRel = Math.max(...d.near_misses.map((n) => n.relvol), 1.5);
  return `${dayChips(days, i)}
    <div class="hero" style="--glow:var(--judge)">
      <div class="row"><span class="status"><span class="pulse"></span>${d.status === "dry_run" ? "Dry run" : "Paper trading"}</span>
        <span class="grow"></span><span class="chip">${esc(day(d.date))}</span></div>
      <h1>${esc(head)}</h1>
      <p>${d.universe} stocks scanned · ${d.signals} signal${d.signals === 1 ? "" : "s"} · decided ${esc(d.checkpoint || "")} ${esc(d.tz)} ·
        ${esc(d.index.name)} <b class="${sign(d.index.move_pct)}">${pct(d.index.move_pct, 2)}</b></p>
    </div>
    ${d.status === "dry_run" ? `<div style="margin-top:10px">${note("One test day to prove the plumbing: the Judge was played by hand, not by the API. It says nothing about whether the Judge is any good.")}</div>` : ""}
    ${b ? `<div style="margin-top:10px">${duel(b.judge, b.twin, cur, `On ${money(f.capital, cur, 0)} of paper money`)}</div>` : ""}
    ${section("Candidates", `<span class="dim" style="font-size:12.5px">Tap one for the full debate</span>`)}
    <div class="list">${d.cases.map((c) => caseRow(c, cur)).join("")}</div>
    ${section("What the scanner saw")}
    <div class="card scroll"><table><thead><tr><th>Stock</th><th>Rel. vol</th><th>Today</th><th>Vs high</th><th></th></tr></thead><tbody>
      ${d.near_misses.map((n) => `<tr><td><b>${esc(n.symbol)}</b></td>
        <td><div class="row" style="justify-content:flex-end"><span>${num(n.relvol, 1)}×</span><span class="meter" style="width:36px;margin:0"><span style="width:${Math.min(100, (n.relvol / maxRel) * 100)}%;background:${n.relvol >= 1.5 ? "var(--bull)" : "var(--text-3)"}"></span></span></div></td>
        <td class="${sign(n.move_pct)}">${pct(n.move_pct, 2)}</td><td class="${sign(n.dist_pct)}">${pct(n.dist_pct, 2)}</td>
        <td>${n.passed ? `<span class="chip go">Signal</span>` : `<span class="chip">Missed</span>`}</td></tr>`).join("")}</tbody></table></div>
    <p class="foot">A signal needs opening volume of at least 1.5× normal and a price at or above the opening-range high.</p>`;
}

export function today() {
  const f = feed();
  if (state.horizon === "intra") return todayIntra(f);
  return state.market === "IN" ? todayMidIN(f) : todayMidUS(f);
}

// ---------------------------------------------------------------- Trades
function tradesMid(f) {
  const s = f && f.snapshot, rowsAll = s ? s.open_signals : (f && f.signals) || [];
  if (!rowsAll.length) return notes(f) + empty("No open signals", "Signals appear here from the evening they trigger until they close.");
  const mode = ui("tmode", "signals");
  const seg = f.picks && f.picks.length ? `<div class="seg" style="margin-bottom:12px">
      <button class="${mode === "signals" ? "on" : ""}" data-act="set" data-k="tmode" data-v="signals">Signals</button>
      <button class="${mode === "books" ? "on" : ""}" data-act="set" data-k="tmode" data-v="books">Paper books</button></div>` : "";
  if (mode === "books" && f.picks && f.picks.length) {
    const book = ui("book", "twin"), picks = f.picks.filter((p) => p.book === book);
    return `${seg}<div class="chips" style="margin-bottom:12px">${Object.keys(BOOK_NAMES).map((b) =>
      `<button class="chip ${b === book ? "on" : ""}" data-act="set" data-k="book" data-v="${b}">${esc(BOOK_NAMES[b])}</button>`).join("")}</div>
      ${picks.length ? `<div class="list">${picks.map((p) => `<div class="item" style="cursor:default">
        <span class="grade ${esc(p.grade)}">${esc(p.grade || "–")}</span>
        <span class="grow"><span class="row"><span class="sym">${esc(p.symbol)}</span><span class="chip ${p.status === "open" ? "info" : ""}">${esc(p.status)}</span>
          ${p.verdict ? `<span class="chip judge">${esc(p.verdict)}</span>` : ""}</span>
          <span class="sub">${esc(shortDay(p.signal_date))} · ${p.direction === "up" ? "long" : "shadow short"}${p.entry ? ` · in at ${px(p.entry)}` : ""}${p.exit ? ` · out at ${px(p.exit)} (${esc(p.reason || "")})` : ""}</span></span>
        <span class="end stack">${rpill(p.r)}<span class="dim num" style="font-size:11px">${pct(p.ret_pct)}</span></span></div>`).join("")}</div>`
        : empty("Nothing in this book yet", "Picks appear the evening they are logged.")}`;
  }
  const flt = ui("tflt", "all");
  const tests = { all: () => true, up: (r) => r.direction === "up", down: (r) => r.direction !== "up", active: (r) => r.status === "Active", extended: (r) => r.status === "Extended" };
  const rows = rowsAll.filter(tests[flt] || tests.all).sort((a, b) => (b.trigger_date || "").localeCompare(a.trigger_date || ""));
  const chips = [["all", "All"], ["up", "Breakouts"], ["down", "Breakdowns"], ["active", "Active"], ["extended", "Extended"]];
  const avg = rows.length ? rows.reduce((n, r) => n + (r.move_pct || 0), 0) / rows.length : null;
  return `${seg}<div class="grid k2" style="margin-bottom:12px">${kpi("Showing", rows.length, `of ${rowsAll.length} open`)}${kpi("Average move", pct(avg), "since each signal", sign(avg))}</div>
    <div class="chips" style="margin-bottom:12px">${chips.map(([k, l]) => `<button class="chip ${k === flt ? "on" : ""}" data-act="set" data-k="tflt" data-v="${k}">${l}</button>`).join("")}</div>
    ${rows.length ? `<div class="list">${rows.map(signalRow).join("")}</div>` : empty("Nothing matches", "Try another filter.")}
    ${s && s.closed_today.length ? section("Closed today") + `<div class="list">${s.closed_today.map(signalRow).join("")}</div>` : ""}`;
}

function tradesIntra(f) {
  const days = (f && f.days) || [];
  if (!days.length) return notes(f) + empty("No trades yet", `Every paper trade in the ${marketName()} intraday books will be listed here.`, "clock");
  const cur = f.currency, who = ui("who", "all");
  const rows = [];
  days.forEach((d) => d.cases.forEach((c) => [["judge", "Judge"], ["twin", "Twin"]].forEach(([k, name]) => {
    const t = c.outcome[k];
    if (t && t.status !== "passed" && (who === "all" || who === k)) rows.push({ d, c, t, k, name });
  })));
  return `<div class="chips" style="margin-bottom:12px">${[["all", "Both books"], ["judge", "Judge"], ["twin", "Twin"]].map(([k, l]) =>
      `<button class="chip ${k === who ? "on" : ""}" data-act="set" data-k="who" data-v="${k}">${l}</button>`).join("")}</div>
    <div class="list">${rows.map(({ d, c, t, k, name }) => `<button class="item" data-act="open-case" data-id="${esc(c.id)}">
      <span class="grade" style="${k === "judge" ? "color:var(--judge);background:var(--judge-soft)" : ""}">${icon(k === "judge" ? "judge" : "trades")}</span>
      <span class="grow"><span class="row"><span class="sym">${esc(c.symbol)}</span><span class="chip ${k === "judge" ? "judge" : ""}">${name}</span>
        <span class="dim" style="font-size:12px">${esc(shortDay(d.date))}</span></span>
        <span class="sub">${esc(tradeLine(t))}${t.entry_t ? ` · ${esc(t.entry_t)}${t.exit_t ? "–" + esc(t.exit_t) : ""} ${esc(d.tz)}` : ""}</span></span>
      <span class="end stack"><span class="big ${sign(t.pnl)}">${t.pnl != null ? pnl(t.pnl, cur) : "–"}</span>${t.r != null ? rpill(t.r) : ""}</span></button>`).join("")}</div>`;
}

export function trades() { return state.horizon === "intra" ? tradesIntra(feed()) : tradesMid(feed()); }

// ---------------------------------------------------------------- Debates
function allCases(f) {
  if (!f) return [];
  return f.cases && f.cases.length ? f.cases : (f.days || []).flatMap((d) => d.cases);
}

export function debates() {
  const f = feed(), cases = allCases(f);
  if (!cases.length) return notes(f) + empty("No debates yet", "When a Bull, a Bear and the Judge argue over a pick, the whole exchange lands here.", "debates");
  const cur = f.currency, flt = ui("dflt", "all");
  const tests = { all: () => true, go: (c) => c.judge && c.judge.tone === "go", wait: (c) => c.judge && c.judge.tone === "wait", avoid: (c) => c.judge && c.judge.tone === "avoid" };
  const rows = cases.filter(tests[flt]);
  let board = "";
  if (state.horizon === "intra") {
    const sum = (k) => (f.days || []).reduce((a, d) => (d.books ? { pnl: a.pnl + d.books[k].pnl, r: a.r + d.books[k].r, trades: a.trades + d.books[k].trades, wins: a.wins + d.books[k].wins } : a), { pnl: 0, r: 0, trades: 0, wins: 0 });
    board = duel(sum("judge"), sum("twin"), cur, `Scoreboard · ${f.days.length} day${f.days.length === 1 ? "" : "s"}`);
  } else if (f.books.length) board = booksTable(f.books.filter((b) => b.book === "judge" || b.book === "twin" || b.book === "debated"));
  const count = (k) => cases.filter(tests[k]).length;
  const labels = state.horizon === "intra" ? [["all", "All"], ["go", "Took the trade"], ["avoid", "Passed"]] : [["all", "All"], ["go", "Go"], ["wait", "Wait"], ["avoid", "Avoid"]];
  return `${notes(f)}${board}
    <div class="chips" style="margin:14px 0 12px">${labels.map(([k, l]) => `<button class="chip ${k === flt ? "on" : ""}" data-act="set" data-k="dflt" data-v="${k}">${l} · ${count(k)}</button>`).join("")}</div>
    ${rows.length ? `<div class="list">${rows.map((c) => caseRow(c, cur)).join("")}</div>` : empty("Nothing matches", "Try another filter.")}`;
}

// ---------------------------------------------------------------- Detail: a debate case
function takeaway(c) {
  const j = c.outcome && c.outcome.judge, t = c.outcome && c.outcome.twin;
  if (!j && !t) return "";
  if (j && j.status === "passed") {
    if (t && t.r != null) return t.r > 0 ? `The Judge passed on a trade the Twin won (${rfmt(t.r)}).` : `The Judge passed and was right: the Twin lost ${rfmt(t.r)}.`;
    return "The Judge passed; the Twin had no fill to compare.";
  }
  if (j && j.status === "not_triggered") return `The Judge's entry never triggered${t && t.r != null ? `; the Twin made ${rfmt(t.r)} at its own levels.` : "."}`;
  if (j && j.r != null && t && t.r != null) {
    const diff = j.r - t.r;
    return Math.abs(diff) < 0.15 ? `Both books ended about the same: Judge ${rfmt(j.r)}, Twin ${rfmt(t.r)}.`
      : diff > 0 ? `The Judge's levels did better: ${rfmt(j.r)} against the Twin's ${rfmt(t.r)}.` : `The Twin's fixed levels did better: ${rfmt(t.r)} against the Judge's ${rfmt(j.r)}.`;
  }
  if (j && (j.status === "open" || j.status === "pending")) return "Still running: no result yet.";
  return "";
}

function outcomeCard(name, t, cur, tone, ic, intra) {
  if (!t) return `<div class="outcome"><div class="row" style="color:${tone};font-weight:700">${icon(ic)}${name}</div><div class="muted" style="margin-top:6px">No order placed.</div></div>`;
  const res = t.pnl != null ? `<span class="big ${sign(t.pnl)}" style="font:700 20px var(--display)">${pnl(t.pnl, cur)}</span>` : t.ret_pct != null ? `<span class="${sign(t.ret_pct)}" style="font:700 20px var(--display)">${pct(t.ret_pct)}</span>` : "";
  const line = (l, v) => (v ? `<div class="line"><span>${l}</span><b>${v}</b></div>` : "");
  return `<div class="outcome"><div class="row"><span class="row" style="color:${tone};font-weight:700">${icon(ic)}${name}</span><span class="grow"></span>${t.r != null ? rpill(t.r) : ""}</div>
    <div class="row" style="margin-top:8px;align-items:baseline">${res}<span class="muted" style="font-size:13px">${esc(tradeLine(t))}</span></div>
    ${line("Entry", t.entry ? `${px(t.entry)}${t.entry_t ? " · " + esc(intra ? t.entry_t : shortDay(t.entry_t)) : ""}` : "")}
    ${line("Exit", t.exit ? `${px(t.exit)}${t.exit_t ? " · " + esc(intra ? t.exit_t : shortDay(t.exit_t)) : ""}` : "")}
    ${line("Size", t.qty ? `${num(t.qty, 2)} shares` : "")}${line("Vs index", t.excess_pct != null ? pct(t.excess_pct) : "")}</div>`;
}

function speech(c, role) {
  const j = c.judge;
  if (role === "bull") return `<div class="speech" style="--tone:var(--bull)"><div class="who">The Bull's case</div><p>${esc(c.bull || "No Bull case was recorded.")}</p></div>`;
  if (role === "bear") return `<div class="speech" style="--tone:var(--bear)"><div class="who">The Bear's case</div><p>${esc(c.bear || "No Bear case was recorded.")}</p></div>`;
  if (!j) return `<div class="speech" style="--tone:var(--judge)"><div class="who">The Judge</div><p>This candidate was not debated.</p></div>`;
  const list = (title, arr) => (arr && arr.length ? `<div class="eyebrow" style="margin-top:12px">${title}</div><ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` : "");
  return `<div class="speech" style="--tone:var(--judge)"><div class="who">The Judge's ruling</div>
    <div class="verdict">${esc(j.title || j.verdict)}</div>
    <div class="row wrap" style="margin-bottom:10px">${verdictChip(j)}${j.conviction ? `<span class="chip">Conviction ${dots(j.conviction)}</span>` : ""}
      ${j.leverage ? `<span class="chip">Leverage ${j.leverage}×</span>` : ""}${j.horizon_sessions ? `<span class="chip">Hold up to ${j.horizon_sessions} sessions</span>` : ""}</div>
    ${j.text ? `<p>${esc(j.text)}</p>` : ""}${list("For", j.reasons_for)}${list("Against", j.reasons_against)}
    ${j.wait ? `<p><b>Waiting for:</b> ${esc(j.wait)}${j.wait_status ? ` <span class="chip warn">${esc(j.wait_status)}</span>` : ""}</p>` : ""}
    ${j.invalidation ? `<p><b>Wrong if:</b> ${esc(j.invalidation)}</p>` : ""}
    ${ladder(j.levels, c.side)}
    ${c.problems ? `<p class="dim" style="margin-top:10px">Level check: ${esc(c.problems)}</p>` : ""}</div>`;
}

export function caseDetail(id) {
  const c = findCase(id);
  if (!c) return { head: `<h1>Not found</h1>`, body: empty("This debate is no longer in the feed", "") };
  const cur = currency(c.market), role = ui("role", "judge"), intra = c.horizon === "intra";
  const roleBtn = (k, label) => `<button class="role ${k} ${role === k ? "on" : ""}" data-act="set" data-k="role" data-v="${k}"><span class="av">${icon(k)}</span>${label}</button>`;
  const take = takeaway(c);
  const head = `<div class="grow"><div class="eyebrow">${esc(c.market === "IN" ? "India" : "US")} · ${intra ? "Intraday" : "Mid-term"} · ${esc(day(c.date))}</div>
      <h1>${esc(c.symbol)}</h1><div class="muted">${esc([c.name, c.headline].filter(Boolean).join(" · "))}</div>
      <div class="row wrap" style="margin-top:8px">${verdictChip(c.judge)}${intra ? "" : `<span class="chip">${c.side === "long" ? "Long" : "Shadow short"}</span>`}${c.grade ? `<span class="chip">Grade ${esc(c.grade)}</span>` : ""}</div></div>`;
  const body = `${caseChart(c)}
    <div class="roles">${roleBtn("bull", "Bull")}${roleBtn("bear", "Bear")}${roleBtn("judge", "Judge")}</div>
    ${speech(c, role)}
    ${section("What happened")}
    ${take ? `<div class="note info">${icon("info")}<div>${esc(take)}</div></div>` : ""}
    <div class="grid k2 stackm">${outcomeCard("Judge", c.outcome.judge, cur, "var(--judge)", "judge", intra)}${outcomeCard("Twin", c.outcome.twin, cur, "var(--text-2)", "trades", intra)}</div>
    ${c.twin && c.twin.levels ? `<div class="card" style="margin-top:10px"><div class="eyebrow">The Twin's fixed levels</div>${ladder(c.twin.levels, c.side)}</div>` : ""}
    ${c.stats && c.stats.length ? section("The numbers they argued over") + `<div class="facts">${c.stats.map(([k, v]) => `<div><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}</div>` : ""}
    <div class="row" style="margin-top:16px"><a class="btn ghost small" href="${tv(c.symbol, c.market)}" target="_blank" rel="noopener">${icon("ext")}Chart on TradingView</a>
      ${c.cost_usd ? `<span class="dim" style="font-size:12px">This debate cost $${num(c.cost_usd, 2)}</span>` : ""}</div>`;
  return { head, body };
}

// ---------------------------------------------------------------- Detail: a plain signal
export function signalDetail(id) {
  const f = feed(state.market, "mid"), s = f && f.snapshot;
  const pool = s ? [...s.breakouts, ...s.breakdowns, ...s.open_signals, ...s.closed_today] : (f && f.signals) || [];
  const r = pool.find((x) => sigId(x) === id);
  if (!r) return { head: `<h1>Not found</h1>`, body: empty("This signal is no longer open", "") };
  const upDir = r.direction === "up", p = r.plan;
  const debated = (f.cases || []).find((c) => c.symbol === r.symbol && c.date === r.trigger_date);
  const fact = (k, v) => `<div><span>${k}</span><b>${v}</b></div>`;
  const head = `<div class="grow"><div class="eyebrow">${state.market === "IN" ? "India" : "US"} · Mid-term · ${esc(day(r.trigger_date))}</div>
    <h1>${esc(r.symbol)}</h1>
    <div class="row wrap" style="margin-top:8px"><span class="chip ${upDir ? "go" : "avoid"}">${upDir ? "Breakout" : "Breakdown"}</span><span class="chip">Grade ${esc(r.grade)}</span>
      ${r.status ? `<span class="chip info">${esc(r.status)}</span>` : ""}</div></div>`;
  const buys = s ? s.buys_allowed !== false : false;
  const plan = !upDir ? `<div class="card"><div class="eyebrow">Shadow short</div><p class="muted" style="margin:6px 0 0">Logged and scored, never traded: stock futures are too large for a ₹1 lakh account.</p></div>`
    : !p ? ""
    : `<div class="card"><div class="eyebrow">Plan for a ₹1 lakh account</div>${buys ? "" : `<div style="margin-top:8px"><span class="chip warn">No buys while the market is weak</span></div>`}
        <div class="facts" style="margin-top:10px">${fact("Buy", `${p.qty} shares`)}${fact("Only below", "₹" + px(p.max_buy))}${fact("Stop", "₹" + px(p.stop))}${fact("Sell by", esc(shortDay(p.exit_by)))}
          ${fact("Position", money(p.value_rs, "INR", 0))}${fact("Risk", money(p.risk_rs, "INR", 0))}${fact("Worst case", money(p.worst_risk_rs, "INR", 0))}${fact("Stop distance", pct(p.stop_pct))}</div></div>`;
  const body = `
    <div class="grid k2">${kpi("Since the signal", pct(r.move_pct), `day ${r.sessions || 0} of 21`, sign(r.move_pct))}${kpi("Momentum score", num(r.score, 2), r.rs_rank != null ? `RS rank ${Math.round(r.rs_rank)}` : "")}</div>
    <div style="margin-top:10px">${plan}</div>
    ${section("Why it was flagged")}
    <div class="facts">${fact("Stage", r.stage_now != null ? `${r.stage_now}${r.stage_age != null ? ` · ${r.stage_age}d` : ""}` : r.stage ?? "–")}${fact("Trend template", r.template != null ? `${r.template}/8` : "–")}
      ${fact("Base", r.base_len ? `${r.base_len} days` : "–")}${fact("Base depth", r.depth_pct != null ? num(r.depth_pct, 0) + "%" : "–")}
      ${fact("Breakout volume", r.vol_ratio != null ? num(r.vol_ratio, 1) + "×" : "–")}${fact("Fail line", pct(r.stop_pct))}${fact("Source", esc(r.source || "live"))}${fact("Signal day", esc(shortDay(r.trigger_date)))}</div>
    ${debated ? section("The debate") + `<div class="list">${caseRow(debated, "INR")}</div>`
      : `<div style="margin-top:14px">${note("No Bull, Bear or Judge debate exists for this signal.", "info")}</div>`}
    <div class="row" style="margin-top:16px"><a class="btn ghost small" href="${tv(r.symbol)}" target="_blank" rel="noopener">${icon("ext")}Chart on TradingView</a></div>`;
  return { head, body };
}

// ---------------------------------------------------------------- Record (inside More)
export function recordTables() {
  const f = feed("IN", "mid"), s = f && f.snapshot;
  if (!s) return "";
  const table = (rows) => (!rows || !rows.length ? `<div class="card muted">No signals yet.</div>` : `<div class="card scroll"><table><thead><tr><th>Grade</th><th>Signals</th><th>Closed</th><th>Held</th><th>Failed</th><th>21d</th><th>Vs index</th><th>Wins</th><th>Avg</th></tr></thead><tbody>
    ${rows.map((r) => `<tr><td><span class="grade ${esc(r.grade)}" style="width:26px;height:26px;font-size:12px">${esc(r.grade)}</span></td><td>${r.signals}</td><td>${r.closed}</td>
      <td>${r.confirmed_pct == null ? "–" : num(r.confirmed_pct, 0) + "%"}</td><td>${r.failed_pct == null ? "–" : num(r.failed_pct, 0) + "%"}</td><td>${r.measured_21}</td>
      <td class="${sign(r.avg_excess_21_pct)}">${pct(r.avg_excess_21_pct)}</td><td>${r.win_pct_21 == null ? "–" : num(r.win_pct_21, 0) + "%"}</td><td class="${sign(r.avg_r_21)}">${rfmt(r.avg_r_21)}</td></tr>`).join("")}</tbody></table></div>`);
  return `${section("Track record · India mid-term")}
    <p class="muted" style="margin:0 2px 10px;font-size:13px">Held and Failed are shares of closed signals within 10 sessions. The 21d columns measure 21 sessions after entry against the Nifty 500.</p>
    <div class="eyebrow" style="margin:0 2px 8px">Live</div>${table(s.track_record_live)}
    <div class="eyebrow" style="margin:14px 2px 8px">Shadow grade, same live signals</div>${table(s.track_record_live_shadow)}
    <div class="eyebrow" style="margin:14px 2px 8px">Replay of history (not live)</div>${table(s.track_record_replay)}`;
}
