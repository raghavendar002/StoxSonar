// Simulator: pick a week and a starting amount, start the replay workflow on GitHub, read its results.
// The replay engine itself lives in the repository (replay.yml). This screen only starts it and shows
// what it publishes under ../replays/. Contract:
//   replays/index.json                      {weeks: [{market, week, clean, debated, capitals, cost_usd, candidates}]}
//   replays/<market>/<week>/quote.json      {candidates, est_usd, fits_budget, budget_left_usd}
//   replays/<market>/<week>/debates.json    [{date, sym, name, headline, stats, bull, bear, judge, mechanical, bars_5m}]
//   replays/<market>/<week>/<capital>.json  {capital, currency, judge: {trades, equity, end_cash, costs}, mechanical: {...}}
import { state, store, REPO, REPO_URL, esc, money, pnl, rfmt, sign, num, shortDay, icon, note, empty, registerCases, verdictChip, rpill, tradeLine } from "./core.js";
import { equityChart } from "./charts.js";

const API = "https://api.github.com/repos/" + REPO;
const WORKFLOW = "replay.yml";
const S = state.ui;
let pollTimer = null, rerender = () => {};
export const onChange = (fn) => { rerender = fn; };

export const token = () => store.get("ghtoken", "");
async function gh(path, opts = {}) {
  return fetch(API + path, { ...opts, headers: { Authorization: "Bearer " + token(), Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28", ...(opts.body ? { "Content-Type": "application/json" } : {}) } });
}
export async function checkToken() {
  if (!token()) return { ok: false, text: "No token saved." };
  try {
    const r = await gh("/actions/workflows?per_page=100");
    if (r.status === 401) return { ok: false, text: "GitHub rejected the token. It may have expired." };
    if (r.status === 403 || r.status === 404) return { ok: false, text: "The token cannot see this repository's Actions. Give it Actions: read and write on StoxSonar only." };
    const j = await r.json();
    const has = (j.workflows || []).some((w) => w.path.endsWith("/" + WORKFLOW));
    return { ok: true, text: has ? "Token works and the replay workflow is there." : "Token works. The replay workflow is not in the repository yet." };
  } catch (_) { return { ok: false, text: "Could not reach GitHub. Check your connection." }; }
}

// The last four finished Monday-to-Friday weeks, newest first
export function lastWeeks(now = new Date()) {
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dow = (d.getDay() + 6) % 7;                 // Monday = 0
  d.setDate(d.getDate() - dow - (dow >= 5 ? 0 : 7)); // this week only counts once Friday is over
  const iso = (x) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`;
  return [0, 1, 2, 3].map((i) => {
    const mon = new Date(d); mon.setDate(d.getDate() - 7 * i);
    const fri = new Date(mon); fri.setDate(mon.getDate() + 4);
    const m = (x) => x.toLocaleDateString("en-GB", { month: "short" });
    const label = mon.getMonth() === fri.getMonth() ? `${mon.getDate()}–${fri.getDate()} ${m(fri)}` : `${mon.getDate()} ${m(mon)} – ${fri.getDate()} ${m(fri)}`;
    return { week: iso(mon), label, ago: i === 0 ? "Last week" : `${i + 1} weeks ago` };
  });
}

async function getJSON(path) {
  try { const r = await fetch(path + "?t=" + Date.now(), { cache: "no-store" }); return r.ok ? await r.json() : null; } catch (_) { return null; }
}
export async function loadIndex() {
  const j = await getJSON("../replays/index.json");
  S.replayIndex = j && Array.isArray(j.weeks) ? j : false;
}
const cached = (m, week) => (S.replayIndex && S.replayIndex.weeks.find((w) => w.market === m && w.week === week)) || null;
const markets = () => (S.simMarket === "both" ? ["in", "us"] : [S.simMarket]);
const cap = (m) => Number(String(m === "in" ? S.simCapIN : S.simCapUS).replace(/[^\d.]/g, "")) || 0;
const cur = (m) => (m === "in" ? "INR" : "USD");

function defaults() {
  if (!S.simMarket) S.simMarket = state.market === "IN" ? "in" : "us";
  if (!S.simWeek) S.simWeek = lastWeeks()[0].week;
  if (S.simCapIN == null) S.simCapIN = "100000";
  if (S.simCapUS == null) S.simCapUS = "1000";
}

// ---------------------------------------------------------------- results
function replayCases(m, week, debates, book) {
  const code = m === "in" ? "IN" : "US";
  const find = (side, d) => ((book && book[side] && book[side].trades) || []).find((t) => t.sym === d.sym && t.date === d.date);
  const hhmm = (x) => { const m = /(\d{2}:\d{2})/.exec(String(x || "").replace(/^\d{4}-\d{2}-\d{2}/, "")); return m ? m[1] : null; };
  const trade = (t) => t && { status: t.status, entry: t.entry, entry_t: hhmm(t.entry_t), exit: t.exit, exit_t: hhmm(t.exit_t),
    reason: t.reason, qty: t.qty, pnl: t.pnl, r: t.r_mult };
  return debates.map((d) => {
    const j = d.judge || {}, took = j.action === "long" || j.action === "short", st = d.stats || {};
    const stats = [["Rel. volume", st.relvol && st.relvol.toFixed(1) + "x"], ["Today", st.move_today != null && (st.move_today * 100).toFixed(1) + "%"],
      ["Last", st.last && st.last.toFixed(2)], ["VWAP", st.vwap && st.vwap.toFixed(2)], ["Prev. close", st.prev_close && st.prev_close.toFixed(2)]].filter((x) => x[1]);
    const lv = (o) => (o && o.trigger ? { entry_low: o.trigger, entry_high: o.trigger, stop: o.stop, target: o.target } : null);
    const jt = find("judge", d);
    return { id: `R-${code}-${week}-${d.date}-${d.sym}`, market: code, horizon: "intra", symbol: d.sym, name: d.name, date: d.date,
      side: j.action === "short" ? "short" : "long", grade: null, headline: d.headline, stats, bull: d.bull, bear: d.bear,
      judge: { verdict: took ? (j.action === "long" ? "Long" : "Short") : j.action === "wait" ? "Wait" : "No trade", tone: took ? "go" : j.action === "wait" ? "wait" : "avoid",
        title: j.title, text: j.text, conviction: j.conviction, leverage: j.leverage, reasons_for: [], reasons_against: [], levels: took ? lv(j) : null },
      twin: lv(d.mechanical) ? { levels: lv(d.mechanical) } : null,
      outcome: { judge: trade(jt) || (took ? null : { status: "passed" }), twin: trade(find("mechanical", d)) || null },
      bars: { tf: "5m", rows: d.bars_5m || [] } };
  });
}

async function openResult(m, week, capital) {
  S.simResult = { m, week, capital, loading: true }; rerender();
  const [debates, book] = await Promise.all([getJSON(`../replays/${m}/${week}/debates.json`), getJSON(`../replays/${m}/${week}/${capital}.json`)]);
  const cases = debates ? replayCases(m, week, debates, book) : [];
  registerCases(cases);
  S.simResult = { m, week, capital, debates, book, cases, loading: false }; rerender();
}

function resultView() {
  const r = S.simResult;
  if (!r) return "";
  if (r.loading) return `<div class="card muted" style="margin-top:12px">Loading the replay…</div>`;
  const c = cur(r.m), wk = lastWeeks().find((w) => w.week === r.week), title = `${r.m === "in" ? "India" : "US"} · ${wk ? wk.label : r.week}`;
  if (!r.debates) return `<div style="margin-top:12px">${empty("No replay for this week yet", "Run it above; the debates are saved, so opening it again is free.", "sim")}</div>`;
  if (!r.book) return `<div style="margin-top:12px">${note(`${title} has been debated, but not yet sized for ${money(r.capital, c, 0)}. Run it above: re-sizing a debated week makes no model calls and costs nothing.`, "info")}</div>`;
  const j = r.book.judge, t = r.book.mechanical, jp = j.end_cash - r.capital, tp = t.end_cash - r.capital, edge = jp - tp;
  const kp = (label, v, s, cls) => `<div class="kpi"><div class="eyebrow">${label}</div><div class="v ${cls || ""}">${v}</div><div class="s">${s}</div></div>`;
  const days = [...new Set(r.cases.map((x) => x.date))].sort();
  return `<div class="section"><h2>${esc(title)}</h2><span class="chip">${money(r.capital, c, 0)} start</span></div>
    <div class="grid k4">${kp("Judge", pnl(jp, c), `ends at ${money(j.end_cash, c, 2)}`, sign(jp))}${kp("Twin", pnl(tp, c), `ends at ${money(t.end_cash, c, 2)}`, sign(tp))}
      ${kp("Judge's edge", pnl(edge, c), edge > 0 ? "the Judge added value" : edge < 0 ? "the Judge cost money" : "no difference", sign(edge))}
      ${kp("Costs paid", money((j.costs || 0), c, 2), "Judge book, fees and taxes")}</div>
    <div style="margin-top:10px">${equityChart(j.equity || [], t.equity || [], r.capital)}</div>
    ${note("One week is 10 to 30 trades. It shows how the three argued, not whether the Judge is any good: that needs about 150.", "info")}
    ${days.map((d) => `<div class="eyebrow" style="margin:16px 2px 8px">${esc(shortDay(d))}</div><div class="list">${r.cases.filter((x) => x.date === d).map((x) => {
      const oj = x.outcome.judge, ot = x.outcome.twin;
      return `<button class="item" data-act="open-case" data-id="${esc(x.id)}"><span class="grow"><span class="row"><span class="sym">${esc(x.symbol)}</span>${verdictChip(x.judge)}</span>
        <span class="sub">Judge: ${esc(tradeLine(oj))} · Twin: ${esc(tradeLine(ot))}</span></span>
        <span class="end stack">${oj && oj.r != null ? rpill(oj.r) : `<span class="rpill">${oj && oj.status === "passed" ? "pass" : "–"}</span>`}<span class="dim" style="font-size:11px">twin ${ot && ot.r != null ? rfmt(ot.r) : "–"}</span></span></button>`;
    }).join("")}</div>`).join("")}`;
}

// ---------------------------------------------------------------- starting a run
function setStatus(text, kind = "info") { S.simStatus = text ? { text, kind } : null; rerender(); }

async function dispatch(mode) {
  if (!token()) { setStatus("Add a GitHub token under More → Simulator access first, or use the “Open on GitHub” link.", ""); return; }
  for (const m of markets()) if (!(cap(m) > 0)) { setStatus("Enter a starting amount above zero.", ""); return; }
  S.simBusy = true; setStatus(mode === "quote" ? "Asking GitHub for a free quote…" : "Starting the replay on GitHub…");
  try {
    for (const m of markets()) {
      const r = await gh(`/actions/workflows/${WORKFLOW}/dispatches`, { method: "POST",
        body: JSON.stringify({ ref: "main", inputs: { market: m === "in" ? "india" : "us", week: S.simWeek, capital: String(cap(m)), mode } }) });
      if (r.status === 404) { S.simBusy = false; setStatus("The replay engine is not in the repository yet, so there is nothing to start. Nothing was spent.", ""); return; }
      if (r.status === 401 || r.status === 403) { S.simBusy = false; setStatus("GitHub refused the token. Check it under More → Simulator access.", ""); return; }
      if (r.status === 422) { S.simBusy = false; setStatus("GitHub rejected the inputs. The workflow may expect different fields.", ""); return; }
      if (!r.ok) { S.simBusy = false; setStatus(`GitHub answered ${r.status}. Nothing was started.`, ""); return; }
    }
  } catch (_) { S.simBusy = false; setStatus("Could not reach GitHub. Check your connection.", ""); return; }
  setStatus("Started. A run usually takes a few minutes; this page checks on it for you.");
  poll(mode);
}

function poll(mode) {
  clearInterval(pollTimer);
  const started = Date.now();
  pollTimer = setInterval(async () => {
    if (Date.now() - started > 15 * 60e3) { clearInterval(pollTimer); S.simBusy = false; setStatus("Still running after 15 minutes. Check the run on GitHub.", ""); return; }
    try {
      const r = await gh(`/actions/workflows/${WORKFLOW}/runs?per_page=1&event=workflow_dispatch`);
      if (!r.ok) return;
      const run = ((await r.json()).workflow_runs || [])[0];
      if (!run || new Date(run.created_at).getTime() < started - 60e3) return;
      if (run.status !== "completed") { setStatus(`GitHub says: ${run.status.replace("_", " ")}…`); return; }
      clearInterval(pollTimer); S.simBusy = false;
      if (run.conclusion !== "success") { setStatus("The run failed on GitHub. Open the run there to see why.", ""); return; }
      setStatus(mode === "quote" ? "Quote ready. Loading it…" : "Finished. Publishing takes about a minute; loading results…");
      setTimeout(async () => { await loadIndex(); const m = markets()[0]; if (mode === "run") await openResult(m, S.simWeek, cap(m)); else await loadQuote(); setStatus(null); }, mode === "run" ? 60e3 : 45e3);
    } catch (_) { /* try again on the next tick */ }
  }, 10e3);
}

async function loadQuote() {
  const out = [];
  for (const m of markets()) { const q = await getJSON(`../replays/${m}/${S.simWeek}/quote.json`); if (q) out.push({ m, ...q }); }
  S.simQuote = out; rerender();
}

// ---------------------------------------------------------------- screen
export function simulator() {
  defaults();
  if (S.replayIndex === undefined) { loadIndex().then(rerender); }
  const weeks = lastWeeks(), engine = S.replayIndex, ms = markets();
  const live = !!engine, has = !!token();
  const moneyField = (m) => `<div class="money"><span>${m === "in" ? "₹" : "$"}</span>
    <input inputmode="decimal" autocomplete="off" aria-label="Starting money, ${m === "in" ? "India" : "US"}" data-in="${m === "in" ? "simCapIN" : "simCapUS"}" value="${esc(m === "in" ? S.simCapIN : S.simCapUS)}"></div>
    <div class="chips">${(m === "in" ? [50000, 100000, 250000, 500000] : [500, 1000, 5000, 10000]).map((v) =>
      `<button class="chip ${cap(m) === v ? "on" : ""}" data-act="sim-cap" data-m="${m}" data-v="${v}">${money(v, cur(m), 0)}</button>`).join("")}</div>`;
  const weekBtn = (w) => {
    const tags = ms.map((m) => cached(m, w.week)).filter(Boolean);
    const tag = tags.length ? (tags.every((t) => t.debated) ? "Debated · free to re-size" : "Quoted") : w.ago;
    return `<button class="${S.simWeek === w.week ? "on" : ""}" data-act="set" data-k="simWeek" data-v="${w.week}"><b>${esc(w.label)}</b><span>${esc(tag)}</span></button>`;
  };
  const quote = (S.simQuote || []).filter((q) => ms.includes(q.m)).map((q) => `<div class="note ${q.fits_budget ? "info" : ""}">${icon("info")}<div><b>${q.m === "in" ? "India" : "US"}:</b>
    ${q.candidates} candidates, about $${num(q.est_usd, 2)}. ${q.fits_budget ? `It fits this month's leftover budget ($${num(q.budget_left_usd, 2)} left).` : `It does not fit this month's leftover budget ($${num(q.budget_left_usd, 2)} left), so the run would refuse to start.`}</div></div>`).join("");
  const ready = live ? engine.weeks.filter((w) => w.debated) : [];
  return `
    <div class="hero" style="--glow:var(--accent)"><div class="status"><span class="pulse"></span>Simulator</div>
      <h1>Replay a week</h1><p>Pick a week and your starting money. Bull, Bear and the Judge trade it day by day, next to the fixed-rule Twin, using only what was known at each decision.</p></div>
    ${engine === false ? `<div style="margin-top:10px">${note("The replay engine is not built yet: its design is waiting for your go in the thread “Simulate Bull/Bear/Judge for a chosen week”. This screen is already wired to it, so these buttons start working the day it merges, with no app update.")}</div>` : ""}
    <div class="card" style="margin-top:10px">
      <div class="field"><label>Market</label><div class="seg">${[["in", "India"], ["us", "US"], ["both", "Both"]].map(([k, l]) =>
        `<button class="${S.simMarket === k ? "on" : ""}" data-act="set" data-k="simMarket" data-v="${k}">${l}</button>`).join("")}</div></div>
      <div class="field"><label>Week</label><div class="week">${weeks.map(weekBtn).join("")}</div></div>
      <div class="field"><label>Starting money</label>${ms.map(moneyField).join('<div style="height:6px"></div>')}</div>
      ${quote}
      <div class="row wrap"><button class="btn ghost" data-act="sim-go" data-mode="quote" ${!live || S.simBusy ? "disabled" : ""}>Free quote</button>
        <button class="btn grow" data-act="sim-go" data-mode="run" ${!live || S.simBusy ? "disabled" : ""}>${icon("play")}Run replay</button></div>
      ${S.simStatus ? `<p class="${S.simStatus.kind === "info" ? "muted" : ""}" style="margin:12px 0 0;${S.simStatus.kind === "info" ? "" : "color:var(--warn)"}">${esc(S.simStatus.text)}</p>` : ""}
      <p class="dim" style="font-size:12.5px;margin:12px 0 0">${has ? "Runs start from here with your saved GitHub token." : `To start runs from here, add a GitHub token under <a href="#/more">More → Simulator access</a>.`}
        ${live ? `Or <a href="${REPO_URL}/actions/workflows/${WORKFLOW}" target="_blank" rel="noopener">open the workflow on GitHub</a>.` : ""}
        Debates cost API money once per week; a new amount on a debated week is free.</p>
    </div>
    ${ready.length ? `<div class="section"><h2>Replays ready</h2></div><div class="list">${ready.map((w) => `<button class="item" data-act="sim-open" data-m="${esc(w.market)}" data-week="${esc(w.week)}" data-cap="${(w.capitals || [])[0] || ""}">
      <span class="grow"><span class="sym">${w.market === "in" ? "India" : "US"} · week of ${esc(shortDay(w.week))}</span>
      <span class="sub">${w.candidates || "?"} candidates · ${w.clean ? "clean: after the models' training cutoff" : "contaminated: the models may know this week"}${(w.capitals || []).length ? " · sized for " + w.capitals.map((x) => money(x, cur(w.market), 0)).join(", ") : ""}</span></span>
      ${icon("chev")}</button>`).join("")}</div>` : ""}
    ${resultView()}`;
}

export const actions = {
  "sim-cap": (el) => { S[el.dataset.m === "in" ? "simCapIN" : "simCapUS"] = el.dataset.v; rerender(); },
  "sim-go": (el) => dispatch(el.dataset.mode),
  "sim-open": (el) => openResult(el.dataset.m, el.dataset.week, Number(el.dataset.cap) || cap(el.dataset.m)),
};
