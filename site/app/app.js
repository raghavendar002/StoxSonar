// StoxSonar app: reads the same data.json the public page uses, and sets up push alerts.
"use strict";

const REPO = "https://github.com/raghavendar002/StoxSonar";
const DATA_URL = "../data.json";
const view = document.getElementById("view");
let snap = null;

const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (x, d = 1) => (x == null || Number.isNaN(x) ? "–" : Number(x).toFixed(d));
const pct = (x, sign = true) => (x == null || Number.isNaN(x) ? "–" : (sign && x > 0 ? "+" : "") + num(x) + "%");
const rs = (x) => (x == null ? "–" : "₹" + Math.round(x).toLocaleString("en-IN"));
const px = (x) => (x == null ? "–" : "₹" + (x < 1000 ? Number(x).toFixed(2) : Math.round(x).toLocaleString("en-IN")));
const tv = (s) => "https://www.tradingview.com/chart/?symbol=NSE:" + encodeURIComponent(s);
const day = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" });
const standalone = () => window.navigator.standalone === true || matchMedia("(display-mode: standalone)").matches;
const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent);

async function load(force) {
  try {
    const r = await fetch(DATA_URL + (force ? "?t=" + Date.now() : ""), { cache: "no-store" });
    // data.json is written by Python and can hold NaN, which JSON.parse rejects
    snap = JSON.parse((await r.text()).replace(/\bNaN\b/g, "null"));
    document.getElementById("asof").textContent = snap.as_of ? "Close of " + day(snap.as_of) : "";
  } catch (e) {
    if (!snap) view.innerHTML = '<p class="pad">Could not load the data. Check your connection and tap ↻.</p>';
  }
  render();
}

// ---------------------------------------------------------------- Today
function summary(s) {
  const out = [];
  if (s.regime === "Weak" && s.buys_allowed === false)
    out.push("The market is weak, so no new buys are suggested. Breakouts are still logged for the record.");
  else if (s.regime === "Weak") out.push("The market is weak: breakouts fail more often, and every grade is cut one level.");
  else out.push("The market is healthy, which is when breakouts have worked best.");
  const a = s.breakouts.filter((r) => r.grade === "A");
  if (s.buys_allowed !== false) {
    if (a.length) out.push(`${a.length} new Grade A breakout${a.length > 1 ? "s" : ""}: ${a.map((r) => r.symbol).join(", ")}.`);
    else if (s.breakouts.length) out.push("Only Grade B breakouts today: treat them as a watchlist, not buys.");
    else out.push("No new breakouts today.");
  }
  const ups = s.open_signals.filter((r) => r.direction === "up");
  if (ups.length) {
    const act = ups.filter((r) => r.status === "Active").length;
    out.push(`${ups.length} earlier breakouts still open: ${act} Active (near the level), ${ups.length - act} Extended (don't chase).`);
  }
  out.push("Paper-trade only for now: the live record is still too short to trust with money.");
  return out;
}

function breadthBar(b) {
  const colours = { Basing: "var(--s1)", Advancing: "var(--s2)", Topping: "var(--s3)", Declining: "var(--s4)" };
  const parts = Object.keys(colours).map((k) => `<span style="width:${b[k] || 0}%;background:${colours[k]}"></span>`).join("");
  const legend = Object.keys(colours).map((k) => `<span><i style="background:${colours[k]}"></i>${k} ${num(b[k], 0)}%</span>`).join("");
  return `<div class="bar">${parts}</div><div class="legend">${legend}</div>`;
}

function signalCard(r, opts = {}) {
  const dir = r.direction === "up" ? "up" : "down";
  const head = `<div class="row"><span class="grade ${esc(r.grade)}">${esc(r.grade)}</span>
    <a class="sym" href="${tv(r.symbol)}" target="_blank" rel="noopener">${esc(r.symbol)}</a>
    <span class="chip">${dir === "up" ? "Breakout" : "Breakdown"}</span>
    ${opts.status ? `<span class="chip">${esc(r.status)}</span>` : ""}
    <span class="spacer"></span>
    ${r.move_pct != null ? `<span class="${r.move_pct >= 0 ? "up" : "down"}">${pct(r.move_pct)}</span>` : ""}</div>`;
  const facts = `<div class="kv">
    <div>Score<b>${num(r.score, 2)}</b></div><div>RS rank<b>${r.rs_rank ?? "–"}</b></div>
    <div>Stop<b>${pct(r.stop_pct)}</b></div><div>Template<b>${r.template}/8</b></div>
    ${opts.status ? `<div>Sessions<b>${r.sessions}</b></div><div>Signal day<b>${esc(day(r.trigger_date))}</b></div>` :
      `<div>Base<b>${r.base_len}d, ${num(r.depth_pct, 0)}%</b></div><div>Volume<b>${num(r.vol_ratio)}×</b></div>`}
  </div>`;
  let plan = "";
  if (r.plan && opts.plan) {
    const p = r.plan;
    plan = opts.buys === false
      ? `<p class="muted" style="margin:8px 0 0">Logged only: no buys while the market is weak.</p>`
      : `<div class="kv" style="border-top:1px solid var(--line);padding-top:8px">
          <div>Buy<b>${p.qty} sh</b></div><div>Max price<b>${px(p.max_buy)}</b></div>
          <div>Stop<b>${px(p.stop)}</b></div><div>Value<b>${rs(p.value_rs)}</b></div>
          <div>Risk<b>${rs(p.risk_rs)}</b></div><div>Sell by<b>${esc(day(p.exit_by))}</b></div></div>`;
  }
  if (dir === "down" && opts.plan) plan = `<p class="muted" style="margin:8px 0 0">Shadow short: not tradable at ₹1 lakh.</p>`;
  return `<div class="card">${head}${facts}${plan}</div>`;
}

function renderToday(s) {
  const reg = `<div class="card"><div class="regime"><span class="pill ${esc(s.regime)}">${esc(s.regime)}</span>
      <span>${s.buys_allowed === false ? "No new buys" : "Buys allowed"}</span><span class="spacer"></span>
      <span class="muted">${s.stocks} stocks</span></div>${breadthBar(s.breadth || {})}
      <ul class="notes">${summary(s).map((t) => `<li>${esc(t)}</li>`).join("")}</ul></div>`;
  const ups = s.breakouts.length ? s.breakouts.map((r) => signalCard(r, { plan: true, buys: s.buys_allowed })).join("")
    : '<p class="muted">None today.</p>';
  const downs = s.breakdowns.length ? s.breakdowns.map((r) => signalCard(r, { plan: true })).join("")
    : '<p class="muted">None today.</p>';
  return reg + `<h2>New breakouts</h2>${ups}<h2>New breakdowns</h2>${downs}`;
}

// ---------------------------------------------------------------- Signals
function renderSignals(s) {
  const by = (a, b) => (b.trigger_date || "").localeCompare(a.trigger_date || "");
  const ups = s.open_signals.filter((r) => r.direction === "up").sort(by);
  const downs = s.open_signals.filter((r) => r.direction !== "up").sort(by);
  const list = (rows) => rows.length ? rows.map((r) => signalCard(r, { status: true })).join("") : '<p class="muted">None.</p>';
  return `<h2>Closed today</h2>${list(s.closed_today)}
    <h2>Open breakouts (${ups.length})</h2>${list(ups)}
    <h2>Open breakdowns (${downs.length})</h2>${list(downs)}`;
}

// ---------------------------------------------------------------- Record
function recordTable(rows) {
  if (!rows || !rows.length) return '<p class="muted">No signals yet.</p>';
  const body = rows.map((r) => `<tr><td><span class="grade ${esc(r.grade)}">${esc(r.grade)}</span></td>
    <td>${r.signals}</td><td>${r.closed}</td><td>${pct(r.confirmed_pct, false)}</td><td>${pct(r.failed_pct, false)}</td>
    <td>${r.measured_21}</td><td>${pct(r.avg_excess_21_pct)}</td><td>${pct(r.win_pct_21, false)}</td>
    <td>${r.avg_r_21 == null ? "–" : num(r.avg_r_21, 2) + "R"}</td></tr>`).join("");
  return `<div class="card scroll"><table><thead><tr><th>Grade</th><th>Signals</th><th>Closed</th><th>Held</th>
    <th>Failed</th><th>21d</th><th>Vs index</th><th>Wins</th><th>Avg</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderRecord(s) {
  return `<p class="muted">Held / Failed: share of closed signals confirmed or failed within 10 sessions.
      21d columns: signals old enough to measure 21 sessions after entry, against the Nifty 500.</p>
    <h2>Live record (${s.live_signals} signals)</h2>${recordTable(s.track_record_live)}
    <h2>Shadow grade on the same live signals</h2>${recordTable(s.track_record_live_shadow)}
    <h2>Replay of history (not live)</h2>${recordTable(s.track_record_replay)}
    <p class="muted">Engine ${esc(s.engine_version)}. <a href="../ledger.csv">Every signal (CSV)</a> ·
      <a href="../">Full web page</a></p>`;
}

// ---------------------------------------------------------------- Settings and alerts
function b64uToBytes(s) {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
}

async function currentSub() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

function subText(sub, device) {
  const j = sub.toJSON();
  return JSON.stringify({ device, endpoint: j.endpoint, keys: j.keys });
}

async function turnOnAlerts() {
  const out = document.getElementById("alert-out");
  try {
    const perm = await Notification.requestPermission();
    if (perm !== "granted") { out.innerHTML = '<p class="warn">Notifications are blocked. Allow them in Settings → Notifications → StoxSonar, then try again.</p>'; return; }
    const reg = await navigator.serviceWorker.ready;
    const { public_key } = await (await fetch("vapid.json")).json();
    let sub = await reg.pushManager.getSubscription();
    if (!sub) sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64uToBytes(public_key) });
    renderSettingsInto();
  } catch (e) {
    out.innerHTML = `<p class="warn">Could not turn on alerts: ${esc(e.message || e)}</p>`;
  }
}

async function copySub() {
  const t = document.getElementById("sub-text");
  try { await navigator.clipboard.writeText(t.value); document.getElementById("copied").textContent = "Copied."; }
  catch (_) { t.select(); document.getElementById("copied").textContent = "Select all and copy."; }
}

function renderSettings() {
  setTimeout(renderSettingsInto, 0);
  return '<div id="settings"><p class="muted pad">Checking alerts…</p></div>';
}

async function renderSettingsInto() {
  const box = document.getElementById("settings");
  if (!box) return;
  const parts = [];
  if (isIOS() && !standalone()) {
    parts.push(`<div class="card"><b>Install the app first.</b> iPhone only allows alerts from the home-screen app.
      <ol class="steps"><li>In Safari, tap the Share button.</li><li>Tap <b>Add to Home Screen</b>, then <b>Add</b>.</li>
      <li>Open StoxSonar from its new icon and come back to Settings.</li></ol></div>`);
  } else if (!("PushManager" in window) || !("serviceWorker" in navigator)) {
    parts.push('<div class="card warn">This browser cannot receive push alerts. Use Edge or Chrome on Windows, or the home-screen app on iPhone.</div>');
  } else {
    const sub = await currentSub();
    const perm = window.Notification ? Notification.permission : "default";
    if (!sub || perm !== "granted") {
      parts.push(`<div class="card"><p>Alerts are <b>off</b> on this device.</p>
        <button class="primary" id="on">Turn on alerts</button><div id="alert-out"></div></div>`);
    } else {
      const guess = isIOS() ? "iPhone" : /Windows/.test(navigator.userAgent) ? "Laptop" : "Device";
      parts.push(`<div class="card"><p>Alerts are <b class="up">on</b> here. One last step on each device:</p>
        <ol class="steps">
          <li>Name this device: <input id="dev" value="${guess}" style="width:110px"> then tap Copy.</li>
          <li><button class="ghost" id="copy">Copy code</button> <span id="copied" class="muted"></span></li>
          <li>Open <a href="${REPO}/settings/secrets/actions" target="_blank" rel="noopener">the repository's Actions secrets</a>
            and edit <b>PUSH_SUBS</b> (create it the first time). Paste the code as its own line; keep other devices' lines.</li>
          <li>Run <a href="${REPO}/actions/workflows/push-test.yml" target="_blank" rel="noopener">Push test</a>
            (Run workflow). A test alert should arrive within a minute.</li>
        </ol>
        <textarea id="sub-text" readonly>${esc(subText(sub, guess))}</textarea>
        <p class="muted">This code lets the evening run reach this device. Keep it in the secret, never in a commit.</p>
        <button class="ghost" id="off">Turn off alerts</button></div>`);
    }
  }
  parts.push(`<div class="card"><b>What you get</b><ul class="notes">
      <li>One alert each evening after the NSE run: market mood, new A/B breakouts, closed signals.</li>
      <li>Telegram keeps posting as a backup for now. If this device stops accepting alerts, Telegram tells you.</li>
      <li>Debates, paper books and the US list arrive here once they go live.</li></ul></div>
    <p class="muted">Data last published for ${snap ? esc(snap.as_of) : "–"}.
    ${standalone() ? "Running as an installed app." : "Running in a browser tab."}</p>`);
  box.innerHTML = parts.join("");
  const on = document.getElementById("on"); if (on) on.onclick = turnOnAlerts;
  const copy = document.getElementById("copy"); if (copy) copy.onclick = copySub;
  const dev = document.getElementById("dev");
  if (dev) dev.oninput = async () => { document.getElementById("sub-text").value = subText(await currentSub(), dev.value.trim() || "Device"); };
  const off = document.getElementById("off");
  if (off) off.onclick = async () => { const s = await currentSub(); if (s) await s.unsubscribe(); renderSettingsInto(); };
}

// ---------------------------------------------------------------- Router
const SCREENS = { today: renderToday, signals: renderSignals, record: renderRecord, settings: renderSettings };

function render() {
  const tab = (location.hash || "#today").slice(1);
  const fn = SCREENS[tab] || renderToday;
  document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("on", a.dataset.tab === (SCREENS[tab] ? tab : "today")));
  if (fn !== renderSettings && !snap) return;
  view.innerHTML = fn(snap) + (fn !== renderSettings ? '<p class="disclaimer">Output of a fixed rule set. Not investment advice.</p>' : "");
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", render);
document.getElementById("refresh").onclick = () => load(true);
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") load(true); });
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
load(true);
