// Shared state, data loading, formatting and icons for the StoxSonar app.

export const REPO = "raghavendar002/StoxSonar";
export const REPO_URL = "https://github.com/" + REPO;

const store = {
  get(k, d) { try { const v = localStorage.getItem("sx." + k); return v == null ? d : JSON.parse(v); } catch (_) { return d; } },
  set(k, v) { try { localStorage.setItem("sx." + k, JSON.stringify(v)); } catch (_) { /* private mode */ } },
  del(k) { try { localStorage.removeItem("sx." + k); } catch (_) { /* private mode */ } },
};
export { store };

export const state = {
  market: store.get("market", "IN"),      // IN | US
  horizon: store.get("horizon", "mid"),   // mid | intra
  tab: "today",
  detail: null,                           // { kind: "case" | "signal", id }
  feeds: {},                              // "mid-in" -> feed
  meta: null,
  ui: {},                                 // per-screen filters and choices
  loading: false,
  offline: false,
};

export const feedKey = (m = state.market, h = state.horizon) => `${h}-${m.toLowerCase()}`;
export const feed = (m, h) => state.feeds[feedKey(m, h)] || null;
export const currency = (m = state.market) => (m === "IN" ? "INR" : "USD");

export async function loadFeeds(force) {
  state.loading = true;
  const bust = force ? "?t=" + Date.now() : "";
  const names = ["mid-in", "mid-us", "intra-in", "intra-us", "meta"];
  const got = await Promise.all(names.map(async (n) => {
    try {
      const r = await fetch(`feed/${n}.json${bust}`, { cache: "no-store" });
      if (!r.ok) return null;
      return JSON.parse((await r.text()).replace(/\bNaN\b/g, "null"));
    } catch (_) { return null; }
  }));
  state.offline = got.every((x) => x == null);
  names.forEach((n, i) => { if (got[i]) { if (n === "meta") state.meta = got[i]; else state.feeds[n] = got[i]; } });
  state.loading = false;
}

// Every case the app knows about, from every feed and from loaded replays
const extraCases = new Map();
export function registerCases(list) { list.forEach((c) => extraCases.set(c.id, c)); }
export function findCase(id) {
  if (extraCases.has(id)) return extraCases.get(id);
  for (const f of Object.values(state.feeds)) {
    for (const c of f.cases || []) if (c.id === id) return c;
    for (const d of f.days || []) for (const c of d.cases || []) if (c.id === id) return c;
  }
  return null;
}

// ---------------------------------------------------------------- formatting
export const esc = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const ok = (x) => x != null && !Number.isNaN(x);
export const num = (x, d = 1) => (ok(x) ? Number(x).toFixed(d) : "–");
export const pct = (x, d = 1) => (ok(x) ? (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(d) + "%" : "–");
export const rfmt = (x) => (ok(x) ? (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(2) + "R" : "–");
export const sign = (x) => (!ok(x) || x === 0 ? "" : x > 0 ? "up" : "down");
export function money(x, cur = "INR", d) {
  if (!ok(x)) return "–";
  const s = cur === "INR" ? "₹" : "$";
  const digits = d != null ? d : (cur === "INR" && Math.abs(x) >= 1000 ? 0 : 2);
  return (x < 0 ? "−" : "") + s + Math.abs(x).toLocaleString(cur === "INR" ? "en-IN" : "en-US",
    { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export const pnl = (x, cur) => (ok(x) ? (x > 0 ? "+" : "") + money(x, cur, 2) : "–");
export const px = (x) => (ok(x) ? (Math.abs(x) >= 1000 ? Math.round(x).toLocaleString("en-IN") : Number(x).toFixed(2)) : "–");
export function day(iso, long) {
  if (!iso) return "–";
  const d = new Date(String(iso).slice(0, 10) + "T00:00:00");
  return d.toLocaleDateString("en-GB", long ? { weekday: "long", day: "numeric", month: "long" } : { weekday: "short", day: "numeric", month: "short" });
}
export const shortDay = (iso) => new Date(String(iso).slice(0, 10) + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
export const tv = (sym, m = state.market) => "https://www.tradingview.com/chart/?symbol=" + (m === "IN" ? "NSE:" : "") + encodeURIComponent(sym);

// ---------------------------------------------------------------- icons
const P = {
  today: "M22 12h-4l-3 9L9 3l-3 9H2",
  trades: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  debates: "M12 3v18M7 21h10M5 7h14M5 7l-3 7a3 3 0 0 0 6 0L5 7zM19 7l-3 7a3 3 0 0 0 6 0l-3-7z",
  sim: "M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2",
  more: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  refresh: "M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5",
  x: "M18 6 6 18M6 6l12 12",
  bull: "M23 6l-9.5 9.5-5-5L1 18M17 6h6v6",
  bear: "M23 18l-9.5-9.5-5 5L1 6M17 18h6v-6",
  judge: "M12 3v18M7 21h10M5 7h14M5 7l-3 7a3 3 0 0 0 6 0L5 7zM19 7l-3 7a3 3 0 0 0 6 0l-3-7z",
  ext: "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3",
  chev: "M9 18l6-6-6-6",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",
  key: "M15 7a4 4 0 1 1-3.9 5H8v3H5v3H2v-3l6.1-6.1A4 4 0 0 1 15 7zM16 8h.01",
  play: "M6 4l14 8-14 8V4z",
  info: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 16v-4M12 8h.01",
  check: "M20 6 9 17l-5-5",
  clock: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
  inbox: "M22 12h-6l-2 3h-4l-2-3H2M5.5 5h13l3.5 7v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6l3.5-7z",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
};
export const icon = (name) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="${P[name] || P.info}"/></svg>`;
export const logo = `<svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="#0b1326"/>
  <path d="M7 19a9 9 0 0 1 18 0" fill="none" stroke="#2fd08a" stroke-width="2.4" stroke-linecap="round" opacity=".45"/>
  <path d="M11 19a5 5 0 0 1 10 0" fill="none" stroke="#2fd08a" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="16" cy="19" r="2" fill="#2fd08a"/><path d="M6 25l6-3 4 1.5 10-7" fill="none" stroke="#6b8cff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

// ---------------------------------------------------------------- small shared pieces
export const note = (text, kind = "") => `<div class="note ${kind}">${icon("info")}<div>${esc(text)}</div></div>`;
export const empty = (title, text, ic = "inbox") =>
  `<div class="card empty"><div class="orb">${icon(ic)}</div><b>${esc(title)}</b>${esc(text || "")}</div>`;
export const rpill = (r) => `<span class="rpill ${sign(r)}">${rfmt(r)}</span>`;
export function verdictChip(j) {
  if (!j || !j.verdict) return `<span class="chip">Not debated</span>`;
  return `<span class="chip ${esc(j.tone)}"><i></i>${esc(j.verdict)}</span>`;
}
export const dots = (n) => `<span class="dots" title="Conviction ${n || 0} of 5">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= (n || 0) ? "on" : ""}"></i>`).join("")}</span>`;

export function tradeLine(t, cur) {
  // One short phrase for what a book did with a candidate
  if (!t) return "No order";
  if (t.status === "passed") return "Passed";
  if (t.status === "not_triggered") return "Never triggered";
  if (t.status === "skipped") return "Skipped";
  if (t.status === "pending") return "Waiting to enter";
  if (t.status === "open") return `Open from ${px(t.entry)}`;
  const why = { stop: "stopped", target: "target hit", time: "time exit", close: "closed at the bell", eod: "closed at the bell" }[t.reason] || t.reason || "closed";
  return `${px(t.entry)} → ${px(t.exit)}, ${why}`;
}
