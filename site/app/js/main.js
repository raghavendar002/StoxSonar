// Shell: navigation, the India/US and Mid-term/Intraday switches, the detail sheet, and event wiring.
import { state, store, loadFeeds, feed, esc, icon, logo, day } from "./core.js";
import * as views from "./views.js";
import * as sim from "./sim.js";
import * as more from "./more.js";

const TABS = [["today", "Today"], ["trades", "Trades"], ["debates", "Debates"], ["sim", "Simulator"], ["more", "More"]];
const SCREENS = { today: views.today, trades: views.trades, debates: views.debates, sim: sim.simulator, more: more.more };
const $ = (id) => document.getElementById(id);
const desktop = () => matchMedia("(min-width: 980px)").matches;

function parseHash() {
  const [, tab, kind, id] = (location.hash || "#/today").split("/");
  state.tab = SCREENS[tab] ? tab : "today";
  state.detail = kind && id ? { kind, id: decodeURIComponent(id) } : null;
}
const go = (tab, detail) => { location.hash = `#/${tab}` + (detail ? `/${detail.kind}/${encodeURIComponent(detail.id)}` : ""); };

function segs() {
  const seg = (k, opts, accent) => `<div class="seg ${accent ? "accent" : ""}" role="tablist">${opts.map(([v, l]) =>
    `<button role="tab" aria-selected="${state[k] === v}" class="${state[k] === v ? "on" : ""}" data-act="${k}" data-v="${v}">${l}</button>`).join("")}</div>`;
  return seg("market", [["IN", "India"], ["US", "US"]], true) + seg("horizon", [["mid", "Mid-term"], ["intra", "Intraday"]]);
}

function chrome() {
  const f = feed(), asof = f && f.as_of ? `${state.market === "IN" ? "India" : "US"} ${state.horizon === "mid" ? "mid-term" : "intraday"} · ${day(f.as_of)}` : "";
  $("asof").textContent = state.offline ? "Offline: showing nothing new" : asof;
  $("segs-top").innerHTML = segs(); $("segs-side").innerHTML = segs();
  const nav = (cls) => TABS.map(([k, l]) => `<a href="#/${k}" class="${state.tab === k ? "on" : ""}" ${state.tab === k ? 'aria-current="page"' : ""}>${icon(k)}<span>${l}</span></a>`).join("");
  $("tabbar").innerHTML = nav(); $("sidenav").innerHTML = nav();
  $("refresh").classList.toggle("spin", state.loading);
}

function renderMain(resetScroll) {
  chrome();
  const view = $("view");
  view.innerHTML = SCREENS[state.tab]();
  if (resetScroll) { view.style.animation = "none"; void view.offsetWidth; view.style.animation = ""; window.scrollTo(0, 0); }
}

function renderDetail() {
  const d = state.detail, sheet = $("sheet"), on = !!d;
  if (on) {
    const { head, body } = d.kind === "case" ? views.caseDetail(d.id) : views.signalDetail(d.id);
    const keep = sheet.dataset.id === d.id ? $("sheet-body").scrollTop : 0;
    $("sheet-head").innerHTML = head + `<button class="icon-btn" data-act="close" aria-label="Close">${icon("x")}</button>`;
    $("sheet-body").innerHTML = body;
    $("sheet-body").scrollTop = keep;
    sheet.dataset.id = d.id;
  }
  sheet.classList.toggle("on", on); sheet.setAttribute("aria-hidden", String(!on));
  $("scrim").classList.toggle("on", on);
  $("app").classList.toggle("detail", on);
  document.body.style.overflow = on && !desktop() ? "hidden" : "";
}

function render(resetScroll) { renderMain(resetScroll); renderDetail(); }
sim.onChange(() => { if (state.tab === "sim") renderMain(false); });
more.onChange(() => { if (state.tab === "more") renderMain(false); });

async function refresh(force) {
  state.loading = true; chrome();
  await loadFeeds(force);
  render(false);
}

const actions = {
  ...sim.actions, ...more.actions,
  market: (el) => { state.market = el.dataset.v; store.set("market", state.market); state.ui.day = 0; if (state.detail) go(state.tab); render(true); },
  horizon: (el) => { state.horizon = el.dataset.v; store.set("horizon", state.horizon); state.ui.day = 0; if (state.detail) go(state.tab); render(true); },
  set: (el) => {
    const v = el.dataset.v; state.ui[el.dataset.k] = /^\d+$/.test(v) && el.dataset.k === "day" ? Number(v) : v;
    if (el.dataset.k === "role") renderDetail(); else renderMain(false);
  },
  "open-case": (el) => go(state.tab, { kind: "case", id: el.dataset.id }),
  "open-signal": (el) => go(state.tab, { kind: "signal", id: el.dataset.id }),
  close: () => go(state.tab),
  refresh: () => refresh(true),
};

document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-act]");
  if (el && actions[el.dataset.act]) { e.preventDefault(); actions[el.dataset.act](el, e); }
});
document.addEventListener("input", (e) => {
  const k = e.target.dataset && e.target.dataset.in;
  if (k) { state.ui[k] = e.target.value; more.onInput(k, e.target.value); }
});
document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.detail) go(state.tab); });
$("scrim").addEventListener("click", () => go(state.tab));

// Drag the sheet's header down to close it (phones)
let dragY = null;
$("sheet").addEventListener("touchstart", (e) => { dragY = e.target.closest(".head, .grab") ? e.touches[0].clientY : null; }, { passive: true });
$("sheet").addEventListener("touchmove", (e) => {
  if (dragY == null) return;
  const dy = Math.max(0, e.touches[0].clientY - dragY);
  $("sheet").style.transition = "none"; $("sheet").style.transform = `translateY(${dy}px)`;
}, { passive: true });
$("sheet").addEventListener("touchend", (e) => {
  if (dragY == null) return;
  const dy = e.changedTouches[0].clientY - dragY; dragY = null;
  $("sheet").style.transition = ""; $("sheet").style.transform = "";
  if (dy > 110) go(state.tab);
});

let lastTab = null;
window.addEventListener("hashchange", () => { parseHash(); const changed = state.tab !== lastTab; lastTab = state.tab; if (changed) render(true); else { chrome(); renderDetail(); } });
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") refresh(true); });
matchMedia("(min-width: 980px)").addEventListener("change", () => renderDetail());

document.querySelectorAll(".brand-mark").forEach((el) => { el.innerHTML = logo; });
more.applyTheme();
parseHash(); lastTab = state.tab;
chrome();
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js");
refresh(true);
