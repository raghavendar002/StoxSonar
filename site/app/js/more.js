// More: alerts, simulator access, appearance, the track record and what the app is reading.
import { state, store, REPO_URL, esc, icon, day } from "./core.js";
import { recordTables } from "./views.js";
import { token, checkToken } from "./sim.js";

const S = state.ui;
let rerender = () => {};
export const onChange = (fn) => { rerender = fn; };
const standalone = () => window.navigator.standalone === true || matchMedia("(display-mode: standalone)").matches;
const isIOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent);
const pushable = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

export function applyTheme() {
  const t = store.get("theme", "auto");
  if (t === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.dataset.theme = t;
  const dark = t === "dark" || (t === "auto" && !matchMedia("(prefers-color-scheme: light)").matches);
  document.querySelector('meta[name="theme-color"]').setAttribute("content", dark ? "#05080f" : "#f3f5fa");
}

function b64uToBytes(s) {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
}
async function currentSub() {
  if (!pushable()) return null;
  const reg = await Promise.race([navigator.serviceWorker.ready, new Promise((r) => setTimeout(() => r(null), 2500))]);
  return reg ? reg.pushManager.getSubscription() : null;
}
const subText = (sub, device) => { const j = sub.toJSON(); return JSON.stringify({ device, endpoint: j.endpoint, keys: j.keys }); };

async function refreshAlerts() {
  const sub = await currentSub();
  S.alerts = { checked: true, on: !!sub && Notification.permission === "granted", code: sub ? subText(sub, S.device || guessDevice()) : "" };
  rerender();
}
const guessDevice = () => (isIOS() ? "iPhone" : /Windows/.test(navigator.userAgent) ? "Laptop" : "Device");

function alertsCard() {
  const head = `<div class="row"><span class="grade" style="color:var(--accent);background:var(--accent-soft)">${icon("bell")}</span><div class="grow"><b>Alerts</b>`;
  if (isIOS() && !standalone()) return `<div class="card">${head}<div class="sub">Install the app first</div></div></div>
    <ol class="steps"><li>In Safari, tap the Share button.</li><li>Tap <b>Add to Home Screen</b>, then <b>Add</b>.</li><li>Open StoxSonar from its new icon and come back here.</li></ol></div>`;
  if (!pushable()) return `<div class="card">${head}<div class="sub">This browser cannot receive push alerts</div></div></div>
    <p class="muted" style="margin:10px 0 0">Use Edge or Chrome on Windows, or the home-screen app on iPhone.</p></div>`;
  if (!S.alerts || !S.alerts.checked) { refreshAlerts(); return `<div class="card">${head}<div class="sub">Checking…</div></div></div></div>`; }
  if (!S.alerts.on) return `<div class="card">${head}<div class="sub">Off on this device</div></div><button class="btn small" data-act="alerts-on">Turn on</button></div>
    ${S.alertErr ? `<p style="color:var(--warn);margin:10px 0 0">${esc(S.alertErr)}</p>` : ""}</div>`;
  return `<div class="card">${head}<div class="sub">On for this device</div></div><span class="chip go"><i></i>On</span></div>
    <ol class="steps" style="margin-top:12px">
      <li>Name this device: <input class="text" style="width:130px;display:inline-block;padding:6px 9px" data-in="device" value="${esc(S.device || guessDevice())}"></li>
      <li><button class="btn ghost small" data-act="alerts-copy">Copy code</button> <span class="muted">${esc(S.copied || "")}</span></li>
      <li>Paste it as its own line in the <a href="${REPO_URL}/settings/secrets/actions" target="_blank" rel="noopener">PUSH_SUBS secret</a>, keeping other devices' lines.</li>
      <li>Run <a href="${REPO_URL}/actions/workflows/push-test.yml" target="_blank" rel="noopener">Push test</a>. An alert should arrive within a minute.</li></ol>
    <textarea id="sub-text" readonly aria-label="This device's alert code">${esc(S.alerts.code)}</textarea>
    <div class="row" style="margin-top:10px"><span class="dim grow" style="font-size:12px">Keep this code in the secret, never in a commit.</span>
      <button class="btn ghost small" data-act="alerts-off">Turn off</button></div></div>`;
}

function tokenCard() {
  const has = !!token();
  return `<div class="card"><div class="row"><span class="grade" style="color:var(--judge);background:var(--judge-soft)">${icon("key")}</span>
      <div class="grow"><b>Simulator access</b><div class="sub">${has ? "A GitHub token is saved on this device" : "Lets the app start a replay on GitHub"}</div></div>
      ${has ? `<span class="chip go"><i></i>Saved</span>` : ""}</div>
    ${has ? `<div class="row wrap" style="margin-top:12px"><button class="btn ghost small" data-act="token-test">Test it</button><button class="btn ghost small" data-act="token-clear">Remove</button>
        <span class="muted" style="font-size:13px">${esc(S.tokenMsg || "")}</span></div>`
      : `<ol class="steps" style="margin-top:12px"><li><a href="https://github.com/settings/personal-access-tokens/new" target="_blank" rel="noopener">Create a fine-grained token</a>:
            only the StoxSonar repository, and under Repository permissions set <b>Actions</b> to Read and write. Nothing else.</li>
          <li>Paste it here: <input class="text" type="password" autocomplete="off" placeholder="github_pat_…" data-in="tokenDraft" style="margin-top:6px"></li></ol>
        <div class="row" style="margin-top:8px"><button class="btn small" data-act="token-save">Save on this device</button><span class="muted" style="font-size:13px">${esc(S.tokenMsg || "")}</span></div>`}
    <p class="dim" style="font-size:12px;margin:12px 0 0">The token stays in this browser's storage and is sent only to GitHub. It can start workflows and nothing else.
      The replay refuses to spend beyond the month's leftover API budget, so a lost phone cannot run up a bill. Revoke the token on GitHub if the device is lost.</p></div>`;
}

export function more() {
  const theme = store.get("theme", "auto"), m = state.meta;
  const built = m && m.built_utc ? new Date(m.built_utc).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "–";
  const f = (k) => (m && m.feeds[k]) || {};
  return `<div class="section" style="margin-top:4px"><h2>Settings</h2></div>
    ${alertsCard()}${tokenCard()}
    <div class="card"><div class="row"><span class="grade">${icon("sun")}</span><div class="grow"><b>Appearance</b></div></div>
      <div class="seg" style="margin-top:12px">${[["auto", "Match device"], ["dark", "Dark"], ["light", "Light"]].map(([k, l]) =>
        `<button class="${theme === k ? "on" : ""}" data-act="theme" data-v="${k}">${l}</button>`).join("")}</div></div>
    ${recordTables()}
    <div class="section"><h2>What the app is reading</h2></div>
    <div class="card scroll"><table><thead><tr><th>Feed</th><th>Latest</th><th>Debates</th></tr></thead><tbody>
      ${[["mid-in", "India mid-term"], ["mid-us", "US mid-term"], ["intra-in", "India intraday"], ["intra-us", "US intraday"]].map(([k, l]) =>
        `<tr><td>${l}</td><td>${f(k).as_of ? esc(day(f(k).as_of)) : `<span class="dim">nothing yet</span>`}</td><td>${f(k).cases || 0}</td></tr>`).join("")}</tbody></table></div>
    <p class="foot">Feeds built ${esc(built)}. ${standalone() ? "Running as an installed app." : "Running in a browser tab."}
      Everything shown here is public on GitHub Pages; only the alerts are private to your devices.
      <a href="../">Web page</a> · <a href="../ledger.csv">Ledger (CSV)</a> · <a href="${REPO_URL}" target="_blank" rel="noopener">Repository</a><br>
      Output of fixed rules and an experiment in progress. Not investment advice.</p>`;
}

export const actions = {
  theme: (el) => { store.set("theme", el.dataset.v); applyTheme(); rerender(); },
  "alerts-on": async () => {
    S.alertErr = "";
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { S.alertErr = "Notifications are blocked. Allow them for StoxSonar in your device settings, then try again."; rerender(); return; }
      const reg = await navigator.serviceWorker.ready;
      const { public_key } = await (await fetch("vapid.json")).json();
      if (!(await reg.pushManager.getSubscription())) await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64uToBytes(public_key) });
    } catch (e) { S.alertErr = "Could not turn on alerts: " + (e.message || e); }
    refreshAlerts();
  },
  "alerts-off": async () => { const s = await currentSub(); if (s) await s.unsubscribe(); refreshAlerts(); },
  "alerts-copy": async () => {
    const t = document.getElementById("sub-text");
    try { await navigator.clipboard.writeText(t.value); S.copied = "Copied."; } catch (_) { t.select(); S.copied = "Select all and copy."; }
    rerender();
  },
  "token-save": async () => {
    const v = (S.tokenDraft || "").trim();
    if (!/^(github_pat_|ghp_)[A-Za-z0-9_]{20,}$/.test(v)) { S.tokenMsg = "That does not look like a GitHub token."; rerender(); return; }
    store.set("ghtoken", v); S.tokenDraft = ""; S.tokenMsg = "Checking…"; rerender();
    S.tokenMsg = (await checkToken()).text; rerender();
  },
  "token-test": async () => { S.tokenMsg = "Checking…"; rerender(); S.tokenMsg = (await checkToken()).text; rerender(); },
  "token-clear": () => { store.del("ghtoken"); S.tokenMsg = "Removed from this device."; rerender(); },
};

// Typing a device name updates the code to copy without redrawing the field being typed in
export function onInput(k, v) {
  if (k === "device" && S.alerts && S.alerts.code) {
    try { const j = JSON.parse(S.alerts.code); j.device = v.trim() || "Device"; S.alerts.code = JSON.stringify(j); const t = document.getElementById("sub-text"); if (t) t.value = S.alerts.code; } catch (_) { /* keep the old code */ }
  }
}
