// Hand-drawn SVG charts: no library, so the app works offline and stays small.
import { esc, px, shortDay } from "./core.js";

const STAGES = [["Basing", "var(--s1)"], ["Advancing", "var(--s2)"], ["Topping", "var(--s3)"], ["Declining", "var(--s4)"]];

export function breadthBar(b = {}) {
  const parts = STAGES.map(([k, c]) => `<span style="width:${b[k] || 0}%;background:${c}"></span>`).join("");
  const legend = STAGES.map(([k, c]) => `<span><i style="background:${c}"></i>${k} <b class="num">${Math.round(b[k] || 0)}%</b></span>`).join("");
  return `<div class="bar">${parts}</div><div class="legend">${legend}</div>`;
}

// Stacked columns, one per session: how the four stages shifted, with the regime under each
export function breadthHistory(hist) {
  if (!hist || hist.length < 2) return "";
  const W = 640, H = 120, pad = 2, n = hist.length, bw = (W - pad * (n - 1)) / n;
  let cols = "";
  hist.forEach((h, i) => {
    const x = i * (bw + pad);
    let y = 0;
    STAGES.slice().reverse().forEach(([k, c]) => {
      const hh = ((h.breadth[k] || 0) / 100) * (H - 14);
      cols += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(hh - 1, 0).toFixed(1)}" rx="2" fill="${c}" opacity="${i === n - 1 ? 1 : .7}"/>`;
      y += hh;
    });
    cols += `<rect x="${x.toFixed(1)}" y="${H - 6}" width="${bw.toFixed(1)}" height="4" rx="2" fill="${h.regime === "Healthy" ? "var(--bull)" : "var(--warn)"}"/>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%;height:96px;display:block" role="img"
    aria-label="Stage mix for the last ${n} sessions">${cols}</svg>
    <div class="row" style="justify-content:space-between;font-size:11.5px;color:var(--text-3);margin-top:6px">
      <span>${esc(shortDay(hist[0].date))}</span><span>Stage mix, last ${n} sessions · strip below: market mood</span><span>${esc(shortDay(hist[n - 1].date))}</span></div>`;
}

export function spark(values, { w = 120, h = 34, color = "var(--accent)" } = {}) {
  const v = values.filter((x) => x != null);
  if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((x, i) => [(i / (v.length - 1)) * w, h - 3 - ((x - lo) / span) * (h - 6)]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const id = "g" + Math.random().toString(36).slice(2, 8);
  return `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    <path d="${d} L ${w} ${h} L 0 ${h} Z" fill="url(#${id})"/><path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="${pts[pts.length - 1][0].toFixed(1)}" cy="${pts[pts.length - 1][1].toFixed(1)}" r="3" fill="${color}"/></svg>`;
}

const mins = (t) => { const [h, m] = String(t).split(":").map(Number); return h * 60 + m; };

/* Candles with the levels each book set and what then happened.
   c: a case. Intraday bars stop at the decision; the axis runs on to the close so
   entries and exits made later can be placed in time. */
export function caseChart(c) {
  const rows = (c.bars && c.bars.rows) || [];
  if (rows.length < 3) return "";
  const intra = c.bars.tf !== "1d";
  const narrow = true;   // the detail view is a phone-width column everywhere, so few units across keep labels readable
  const W = 420, H = 290, L = 6, R = 62, T = 12, B = 24;
  const jl = c.judge && c.judge.levels, tl = c.twin && c.twin.levels;
  const oj = c.outcome && c.outcome.judge, ot = c.outcome && c.outcome.twin;
  const prices = [];
  rows.forEach((r) => prices.push(r[2], r[3]));
  [jl, tl].forEach((l) => l && ["entry_low", "entry_high", "stop", "target"].forEach((k) => l[k] && prices.push(l[k])));
  [oj, ot].forEach((t) => t && [t.entry, t.exit].forEach((v) => v && prices.push(v)));
  let lo = Math.min(...prices), hi = Math.max(...prices);
  const padY = (hi - lo) * 0.06 || 1; lo -= padY; hi += padY;
  const y = (p) => T + ((hi - p) / (hi - lo)) * (H - T - B);

  let x, bw, xt = null, decisionX = null, ticks = "";
  if (intra) {
    const t0 = mins(rows[0][0]), step = rows.length > 1 ? mins(rows[1][0]) - t0 : 5;
    const lastBar = mins(rows[rows.length - 1][0]) + step;
    const ends = [lastBar + 30];
    [oj, ot].forEach((t) => t && [t.entry_t, t.exit_t].forEach((v) => v && ends.push(mins(v) + 20)));
    const hasAfter = ends.length > 1;
    const t1 = hasAfter ? Math.max(...ends, t0 + 390) : lastBar;
    xt = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
    x = (i) => xt(t0 + i * step + step / 2);
    bw = Math.max(((W - L - R) / ((t1 - t0) / step)) * 0.62, 1.5);
    if (hasAfter) decisionX = xt(lastBar);
    for (let t = Math.ceil(t0 / 60) * 60; t <= t1; t += narrow ? 120 : 60) {
      ticks += `<text x="${xt(t).toFixed(1)}" y="${H - 6}" text-anchor="middle" class="ax">${String(Math.floor(t / 60)).padStart(2, "0")}:00</text>`;
    }
  } else {
    const n = rows.length + 6;
    x = (i) => L + ((i + 0.5) / n) * (W - L - R);
    bw = Math.max(((W - L - R) / n) * 0.62, 1.5);
    [0, Math.floor(rows.length / 2), rows.length - 1].forEach((i) => {
      ticks += `<text x="${x(i).toFixed(1)}" y="${H - 6}" text-anchor="middle" class="ax">${esc(shortDay(rows[i][0]))}</text>`;
    });
    const at = (d) => { const i = rows.findIndex((r) => r[0] >= d); return i < 0 ? null : x(i); };
    xt = at;
  }

  let grid = "";
  for (let i = 0; i <= 3; i++) {
    const p = lo + ((hi - lo) * i) / 3;
    grid += `<line x1="${L}" x2="${W - R}" y1="${y(p).toFixed(1)}" y2="${y(p).toFixed(1)}" class="gr"/>
      <text x="${W - R + 6}" y="${(y(p) + 3.5).toFixed(1)}" class="ax">${px(p)}</text>`;
  }
  let candles = "";
  rows.forEach((r, i) => {
    const [, o, h, l, cl] = r, upc = cl >= o, col = upc ? "var(--bull)" : "var(--bear)", cx = x(i);
    candles += `<line x1="${cx.toFixed(1)}" x2="${cx.toFixed(1)}" y1="${y(h).toFixed(1)}" y2="${y(l).toFixed(1)}" stroke="${col}" stroke-width="1"/>
      <rect x="${(cx - bw / 2).toFixed(1)}" y="${y(Math.max(o, cl)).toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(Math.abs(y(o) - y(cl)), 1).toFixed(1)}" fill="${col}" rx=".6"/>`;
  });

  const lines = [], used = [];
  const level = (p, label, color, dash) => {
    if (!p) return;
    let ly = y(p);
    while (used.some((u) => Math.abs(u - ly) < 11)) ly += 11;    // keep the tags readable when levels crowd
    used.push(ly);
    lines.push(`<line x1="${L}" x2="${W - R}" y1="${y(p).toFixed(1)}" y2="${y(p).toFixed(1)}" stroke="${color}" stroke-width="1.2" ${dash ? 'stroke-dasharray="5 4"' : ""} opacity=".9"/>
      <rect x="${W - R + 2}" y="${(ly - 8).toFixed(1)}" width="${R - 4}" height="15" rx="4" fill="${color}"/>
      <text x="${W - R + 5}" y="${(ly + 3).toFixed(1)}" class="tag">${label} ${px(p)}</text>`);
  };
  if (jl) { level(jl.target, "T", "var(--bull)"); level(jl.entry_high, "E", "var(--judge)"); level(jl.stop, "S", "var(--bear)"); }
  if (tl) { level(tl.target, "T", "var(--bull)", true); level(tl.entry_high, "E", "var(--text-3)", true); level(tl.stop, "S", "var(--bear)", true); }

  let marks = "";
  const trade = (t, color, name, above) => {
    if (!t || !t.entry || !xt) return;
    const x1 = intra ? xt(mins(t.entry_t)) : xt(t.entry_t), x2 = t.exit ? (intra ? xt(mins(t.exit_t)) : xt(t.exit_t)) : null;
    if (x1 == null) return;
    if (x2 != null) marks += `<line x1="${x1.toFixed(1)}" y1="${y(t.entry).toFixed(1)}" x2="${x2.toFixed(1)}" y2="${y(t.exit).toFixed(1)}" stroke="${color}" stroke-width="2" stroke-dasharray="2 3"/>`;
    marks += `<circle cx="${x1.toFixed(1)}" cy="${y(t.entry).toFixed(1)}" r="5" fill="var(--card)" stroke="${color}" stroke-width="2.2"/>`;
    if (x2 != null) marks += `<circle cx="${x2.toFixed(1)}" cy="${y(t.exit).toFixed(1)}" r="5" fill="${color}"/>
      <text x="${x2.toFixed(1)}" y="${(y(t.exit) + (above ? -10 : 18)).toFixed(1)}" text-anchor="middle" class="mk" fill="${color}">${name}</text>`;
  };
  trade(ot, "var(--text-2)", "Twin", true);
  trade(oj, "var(--judge)", "Judge", false);

  const after = decisionX == null ? "" : `<rect x="${decisionX.toFixed(1)}" y="${T}" width="${(W - R - decisionX).toFixed(1)}" height="${H - T - B}" fill="var(--raise)" opacity=".35"/>
    <line x1="${decisionX.toFixed(1)}" x2="${decisionX.toFixed(1)}" y1="${T}" y2="${H - B}" stroke="var(--line-2)" stroke-dasharray="3 3"/>
    <text x="${(decisionX + 6).toFixed(1)}" y="${H - B - 7}" class="ax">after the decision</text>`;

  const cap = [
    jl ? `<span><i style="border-color:var(--judge)"></i>Judge's levels</span>` : "",
    tl ? `<span><i class="dash" style="border-color:var(--text-3)"></i>Twin's levels</span>` : "",
    (oj && oj.entry) || (ot && ot.entry) ? `<span>○ entry · ● exit</span>` : "",
    `<span>E entry · S stop · T target</span>`,
  ].join("");
  return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Price chart with entry, stop and target levels">
    <style>.ax{font:10.5px var(--mono);fill:var(--text-3)}.gr{stroke:var(--line);stroke-width:1}.tag{font:700 9.5px var(--mono);fill:#05080f}.mk{font:700 10.5px var(--font)}</style>
    ${grid}${after}${candles}${lines.join("")}${marks}${ticks}</svg><div class="cap">${cap}</div></div>`;
}

// Stop / entry / target on one line, with the reward-to-risk it implies
export function ladder(l, side = "long") {
  if (!l || !l.stop || !l.entry_high) return "";
  const e = (l.entry_low + l.entry_high) / 2 || l.entry_high, risk = Math.abs(e - l.stop);
  const rr = l.target && risk ? Math.abs(l.target - e) / risk : null;
  const cell = (label, v, color, extra = "") => `<div style="flex:1;min-width:0"><span class="dim" style="font-size:11.5px">${label}</span>
    <div class="mono" style="font-weight:700;font-size:15px;color:${color}">${v}</div><div class="dim" style="font-size:11.5px">${extra}</div></div>`;
  const zone = l.entry_low && l.entry_low !== l.entry_high ? `${px(l.entry_low)}–${px(l.entry_high)}` : px(l.entry_high);
  const riskPct = e ? (risk / e) * 100 : null;
  return `<div style="margin-top:12px"><div style="display:flex;height:6px;border-radius:3px;overflow:hidden;gap:2px">
      <span style="flex:1;background:var(--bear);opacity:.8"></span><span style="flex:${rr ? rr.toFixed(2) : 1};background:var(--bull);opacity:.8"></span></div>
    <div class="row" style="margin-top:8px;align-items:flex-start">
      ${cell("Stop", px(l.stop), "var(--bear)", riskPct ? `${riskPct.toFixed(1)}% risk` : "")}
      ${cell(side === "short" ? "Short at" : "Entry", zone, "var(--text)")}
      ${cell("Target", l.target ? px(l.target) : "–", "var(--bull)", rr ? `${rr.toFixed(1)}R` : "")}
      ${l.target_2 ? cell("Then", px(l.target_2), "var(--bull)") : ""}</div></div>`;
}

// Two equity lines (Judge and Twin) from [{date, value}]
export function equityChart(a, b, start) {
  const narrow = typeof innerWidth === "number" && innerWidth < 760;
  const W = narrow ? 400 : 680, H = narrow ? 230 : 220, L = 8, R = 58, T = 10, B = 22;
  const all = [...a, ...b].map((p) => p.value).concat(start);
  if (all.length < 3) return "";
  let lo = Math.min(...all), hi = Math.max(...all);
  const pad = (hi - lo) * 0.15 || start * 0.002; lo -= pad; hi += pad;
  const n = Math.max(a.length, b.length);
  const x = (i) => L + ((i + 1) / n) * (W - L - R), y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const path = (s) => `M ${L} ${y(start).toFixed(1)} ` + s.map((p, i) => `L ${x(i).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");
  const end = (s, color, name) => s.length ? `<circle cx="${x(s.length - 1).toFixed(1)}" cy="${y(s[s.length - 1].value).toFixed(1)}" r="4" fill="${color}"/>
    <text x="${W - R + 6}" y="${(y(s[s.length - 1].value) + 4).toFixed(1)}" style="font:700 11px var(--font)" fill="${color}">${name}</text>` : "";
  const ticks = (a.length >= b.length ? a : b).map((p, i) => `<text x="${x(i).toFixed(1)}" y="${H - 5}" text-anchor="middle" style="font:10.5px var(--mono);fill:var(--text-3)">${esc(shortDay(p.date))}</text>`).join("");
  return `<div class="chart"><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Account value by day, Judge against Twin">
    <line x1="${L}" x2="${W - R}" y1="${y(start).toFixed(1)}" y2="${y(start).toFixed(1)}" stroke="var(--line-2)" stroke-dasharray="4 4"/>
    <path d="${path(b)}" fill="none" stroke="var(--text-2)" stroke-width="2.2" stroke-linejoin="round" stroke-dasharray="6 4"/>
    <path d="${path(a)}" fill="none" stroke="var(--judge)" stroke-width="2.6" stroke-linejoin="round"/>
    ${end(b, "var(--text-2)", "Twin")}${end(a, "var(--judge)", "Judge")}${ticks}</svg></div>`;
}
