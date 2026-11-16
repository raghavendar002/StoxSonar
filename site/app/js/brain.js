// The Brain: what the Judge has done so far and what it has learned, for the market and horizon on show.
import { state, feed, esc, num, pct, rfmt, sign, money, shortDay, day, icon, note, empty } from "./core.js";
import { section, kpi, caseRow, skippedList, howItWorks } from "./views.js";

const line = (l, v) => `<div><span>${l}</span><b>${v}</b></div>`;
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const steps = (items) => `<div class="card"><ol class="steps" style="margin:0">${items.map((t) => `<li>${t}</li>`).join("")}</ol></div>`;

// ---------------------------------------------------------------- mid-term: the real Brain
function midBrain(f) {
  const b = f && f.brain, sb = b && b.scoreboard;
  if (!b || !sb) return empty("The Brain has nothing to show yet", "It starts with the first debate in the evening run.", "brain");
  const cases = f.cases || [], v = sb.verdicts || {}, need = b.min_cases || 8, sw = b.switch, bud = b.budget;
  const debated = cases.length, first = cases.length ? cases[cases.length - 1].date : null;
  const calls = {};
  (b.outcomes || []).forEach((o) => { calls[`${o.symbol}|${o.date}`] = o; });
  const lessons = b.lessons || [];
  const head = lessons.length ? `${plural(lessons.length, "lesson")} learned so far`
    : sb.judged_closed >= need ? "Enough trades for a first review" : `Still learning: ${sb.judged_closed} of ${need} trades finished`;
  const r2 = (x) => (x == null ? "–" : rfmt(x));

  const history = cases.map((c) => {
    const t = c.outcome && c.outcome.judge, o = calls[`${c.symbol}|${c.date}`];
    const what = !t ? "no paper trade"
      : t.status === "closed" ? `closed ${rfmt(t.r)}${o && o.call ? ` · the verdict was ${o.call}` : ""}`
      : t.status === "open" ? `open, day ${t.sessions || 0} of ${t.horizon || 21}${t.ret_pct != null ? ` · ${pct(t.ret_pct)} so far` : ""}`
      : t.status === "pending" ? "enters at the next open" : String(t.status).replace(/_/g, " ");
    const cls = o && o.call ? (o.call === "right" ? "up" : "down") : "";
    return `<button class="item" data-act="open-case" data-id="${esc(c.id)}">
      <span class="grade ${esc(c.grade)}">${esc(c.grade || "–")}</span>
      <span class="grow"><span class="row"><span class="sym">${esc(c.symbol)}</span><span class="chip ${esc(c.judge.tone)}"><i></i>${esc(c.judge.verdict)}</span>
        <span class="dim" style="font-size:12px">${esc(shortDay(c.date))}</span></span>
        <span class="sub">${c.side === "long" ? "Breakout" : "Breakdown"} · conviction ${c.judge.conviction || "–"}/5 · <span class="${cls}">${esc(what)}</span></span></span>
      <span class="end">${icon("chev")}</span></button>`;
  }).join("");

  return `
    <div class="hero" style="--glow:var(--judge)">
      <div class="row"><span class="status"><span class="pulse"></span>The Brain · India mid-term</span></div>
      <h1>${esc(head)}</h1>
      <p>${debated ? `${plural(debated, "debate")} held${first ? ` since ${esc(shortDay(first))}` : ""}` : "No debates held yet"} · a lesson needs ${need} finished trades behind it · the pass-or-fail test is read at ${sb.needed}</p>
      <span class="meter" style="margin-top:14px"><span style="width:${Math.min(100, (sb.judged_closed / need) * 100)}%;background:var(--judge)"></span></span>
    </div>
    <div class="grid k4" style="margin-top:10px">
      ${kpi("Debates held", debated, `at most ${bud ? bud.per_day : 3} a day`)}
      ${kpi("Verdicts", `${v.Go || 0} · ${v.Wait || 0} · ${v.Avoid || 0}`, "Go · Wait · Avoid")}
      ${kpi("Trades finished", sb.judged_closed, `of ${sb.needed} for the test`)}
      ${kpi("API spend", bud ? "$" + num(bud.spent_usd, 2) : "–", bud ? `of $${num(bud.cap_usd, 0)} this month` : "")}
    </div>

    ${section("What it has learned")}
    ${lessons.length ? `<div class="card"><ol class="steps" style="margin:0">${lessons.map((x) => `<li>${esc(x.text)} <span class="dim">(${x.n_cases} trades behind it, added ${esc(shortDay(x.added))})</span></li>`).join("")}</ol></div>`
      : `<div class="card"><b>Nothing yet, and that is the honest answer.</b>
          <p class="muted" style="margin:8px 0 0;font-size:14px;line-height:1.55">A lesson is only kept when at least ${need} finished trades back it, so the Judge cannot learn from one lucky or unlucky pick. ${sb.judged_closed} ${sb.judged_closed === 1 ? "has" : "have"} finished. A mid-term trade runs up to 21 sessions, so the first review is weeks away.</p></div>`}
    ${b.last_review ? `<div class="card" style="margin-top:10px"><div class="eyebrow">Last review · ${esc(shortDay(b.last_review.date))}</div><p style="margin:6px 0 0">${esc(b.last_review.summary || "")}</p>
        <p class="dim" style="margin:8px 0 0;font-size:12px">${b.last_review.n_cases} trades read · ${b.last_review.added || 0} lessons added · ${b.last_review.dropped || 0} dropped</p></div>` : ""}

    ${section("What it has done so far", debated ? `<a class="more" href="#/debates">All debates</a>` : "")}
    ${debated ? `<div class="list">${history}</div>` : empty("No verdicts yet", "Each new Grade A or B signal is debated in the evening run, one stock at a time.", "debates")}
    ${skippedList(f)}

    ${section("Is the Judge earning its keep?")}
    <div class="card"><b>${esc(sb.state || "")}</b>
      <p class="muted" style="margin:6px 0 12px;font-size:13.5px">It passes only if Go picks beat Avoid picks, the Judge's book beats the Twin's, and high conviction beats low. For Avoid, the result is the trade as if it had been taken, so a loss there means the Judge was right.</p>
      <div class="facts">
        ${line(`Go · ${sb.go.n} finished`, `<span class="${sign(sb.go.avg_r)}">${r2(sb.go.avg_r)}</span>`)}
        ${line(`Avoid, as if taken · ${sb.avoid.n}`, `<span class="${sign(sb.avoid.avg_r)}">${r2(sb.avoid.avg_r)}</span>`)}
        ${line(`Judge book · ${sb.judge_book.n} finished`, `<span class="${sign(sb.judge_book.avg_r)}">${r2(sb.judge_book.avg_r)}</span>`)}
        ${line(`Twin book · ${sb.twin_book.n} finished`, `<span class="${sign(sb.twin_book.avg_r)}">${r2(sb.twin_book.avg_r)}</span>`)}
        ${line("Verdicts that were right", sb.right_pct == null ? "–" : num(sb.right_pct, 0) + "%")}
        ${sw ? line(`Debates in a ${esc(sw.regime || "")} market`, sw.off ? `<span class="down">Switched off</span>` : `<span class="up">On</span>`) : ""}
      </div>
      ${sw && sw.off ? `<p class="muted" style="margin:10px 0 0;font-size:13px">Off because ${esc(sw.why)}. The books keep scoring every signal.</p>`
        : sw ? `<p class="dim" style="margin:10px 0 0;font-size:12px">Debates stop in a market type if under ${sw.min_share_pct}% of the Judge's first ${sw.after} verdicts there are Go or Wait, because a Judge that only says Avoid is not worth paying for.</p>` : ""}
    </div>

    ${section("How it learns")}
    ${steps([
      "<b>Before each debate</b> code looks up how similar past signals ended and how the Judge's own earlier verdicts turned out. Bull, Bear and Judge all read it.",
      "<b>When a judged trade finishes</b> code marks the verdict right or wrong. No model is involved, so it cannot flatter itself.",
      `<b>Once ${need} trades have finished</b> a weekly review may propose short rules of thumb. Code keeps one only if it cites ${need} real trades and names no stock or date. At most 12 are held.`,
      `<b>At ${sb.needed} finished trades</b> the pass-or-fail test is read. If the Judge is still failing at ${sb.kill_at}, the debates stop for good.`,
    ])}
    <p class="foot"><a href="../brain.html" target="_blank" rel="noopener">The same record as a plain web page</a></p>`;
}

// ---------------------------------------------------------------- intraday: the record the Judge reads, and its lessons
function intraBrain(f) {
  const days = ((f && f.days) || []).filter((d) => d.status !== "dry_run");
  const name = state.market === "IN" ? "India" : "US", cur = f ? f.currency : "INR";
  if (!days.length) return empty(`No ${name} intraday record yet`, "The Judge's calls are collected here from the first live paper session.", "brain")
    + `<div style="margin-top:10px">${howItWorks(true)}</div>`;
  const cases = days.flatMap((d) => d.cases), judged = cases.filter((c) => c.judge);
  const took = judged.filter((c) => c.judge.tone === "go"), passed = judged.filter((c) => c.judge.tone !== "go");
  const longs = took.filter((c) => c.side !== "short").length, shorts = took.length - longs;
  const settled = days.filter((d) => d.books);
  const sum = (k) => settled.reduce((a, d) => a + (d.books[k].pnl || 0), 0);
  const cost = days.reduce((a, d) => a + (d.cost_usd || 0), 0);
  // Each call is scored by code after the close. A pass is scored against the rule plan's trade on the
  // same stock (the Twin's trade), even when the Twin's two slots were full. Older days without that
  // shadow score fall back to the Twin book's own trade.
  const callOf = (c) => {
    const o = c.outcome || {};
    if (o.call) return o.call;
    if (c.judge.tone === "go") { const t = o.judge; return t && t.r != null ? (t.r > 0 ? "right" : "wrong") : null; }
    const t = o.twin; if (!t || t.r == null) return null;
    return t.r <= -0.1 ? "right" : t.r >= 0.1 ? "wrong" : "flat";
  };
  const passCalls = passed.map(callOf).filter((x) => x && x !== "no fill");
  const passRight = passCalls.filter((x) => x === "right").length, passWrong = passCalls.filter((x) => x === "wrong").length, passFlat = passCalls.length - passRight - passWrong;
  const tkCalls = took.map(callOf).filter((x) => x === "right" || x === "wrong");
  const tkWon = tkCalls.filter((x) => x === "right").length;
  const ib = (f && f.brain) || {}, rec = ib.record || {}, lessons = ib.lessons || [];
  const need = ib.review_at || 20, scored = rec.scored || 0, perLesson = ib.min_cases || 8;
  const head = !took.length ? `${plural(judged.length, "call")} so far, no trade taken yet`
    : `${plural(judged.length, "call")}, ${plural(took.length, "trade")} taken`;
  const allPass = judged.length >= 4 && !took.length;
  return `
    <div class="hero" style="--glow:var(--judge)">
      <div class="row"><span class="status"><span class="pulse"></span>The Judge's record · ${name} intraday</span></div>
      <h1>${esc(head)}</h1>
      <p>${plural(days.length, "live day")} since ${esc(day(days[days.length - 1].date))} · paper money only</p>
    </div>
    ${allPass ? `<div style="margin-top:10px">${note(`The Judge has said No trade on every candidate so far. That can be discipline or it can be a Judge that never acts. The passes below show which: each one is scored against what the rule trade made on the same stock.`, "warn")}</div>` : ""}
    <div class="grid k4" style="margin-top:10px">
      ${kpi("Calls", judged.length, `${longs} long · ${shorts} short · ${passed.length} no trade`)}
      ${kpi("Judge book", settled.length ? (sum("judge") > 0 ? "+" : "") + money(sum("judge"), cur, cur === "INR" ? 0 : 2) : "–", plural(settled.length, "settled day"), settled.length ? sign(sum("judge")) : "")}
      ${kpi("Twin book", settled.length ? (sum("twin") > 0 ? "+" : "") + money(sum("twin"), cur, cur === "INR" ? 0 : 2) : "–", "same candidates, fixed rules", settled.length ? sign(sum("twin")) : "")}
      ${kpi("API spend", "$" + num(cost, 2), "on these debates")}
    </div>

    ${section("Were its calls right?")}
    <div class="card"><div class="facts">
      ${line("Trades it took", tkCalls.length ? `${tkWon} won · ${tkCalls.length - tkWon} lost` : took.length ? "not settled yet" : "none")}
      ${line("No-trade calls", passCalls.length ? `<span class="${passRight >= passWrong ? "up" : "down"}">${passRight} right · ${passWrong} wrong</span>${passFlat ? ` · ${passFlat} flat` : ""}` : "none scored yet")}
      ${rec.passed && rec.passed.rule_avg_r != null ? line("Rule trades it refused, on average", `<span class="${sign(rec.passed.rule_avg_r)}">${rfmt(rec.passed.rule_avg_r)}</span>`) : ""}
      ${rec.rule_plan && rec.rule_plan.n ? line(`Rule plan on every candidate · ${rec.rule_plan.n}`, `<span class="${sign(rec.rule_plan.avg_r)}">${rfmt(rec.rule_plan.avg_r)}</span> · ${rec.rule_plan.win_pct}% won`) : ""}
    </div>
    <p class="dim" style="margin:10px 0 0;font-size:12px">After each close, code plays the scanner's rule trade on every candidate, whether or not the Twin had room for it. A No trade is right when that trade lost, wrong when it made money, and flat when it ended within a tenth of its risk. A trade the Judge took is right when its own levels made money.</p></div>

    ${section("What it has learned")}
    ${lessons.length ? `<div class="card"><ol class="steps" style="margin:0">${lessons.map((x) => `<li>${esc(x.text)} <span class="dim">(${x.n_cases} calls behind it, added ${esc(shortDay(x.added))})</span></li>`).join("")}</ol></div>`
      : `<div class="card"><b>No lessons yet: ${scored} of ${need} calls scored.</b>
          <p class="muted" style="margin:8px 0 0;font-size:14px;line-height:1.55">Before every call the Judge now reads its own record: how its calls and the rule plan did so far, and the five most similar past setups with what happened in each. Lessons come later. Once ${need} calls are scored, a weekly review may add a rule of thumb, and code keeps it only if ${perLesson} real calls back it and it names no stock or date.</p></div>`}
    ${ib.last_review ? `<div class="card" style="margin-top:10px"><div class="eyebrow">Last review · ${esc(shortDay(String(ib.last_review.created_utc).slice(0, 10)))}</div><p style="margin:6px 0 0">${esc(ib.last_review.summary || "")}</p>
        <p class="dim" style="margin:8px 0 0;font-size:12px">${ib.last_review.n_scored} calls read · ${ib.last_review.added || 0} lessons added · ${ib.last_review.dropped || 0} dropped</p></div>` : ""}

    ${section("Every call so far", `<a class="more" href="#/debates">Debates</a>`)}
    ${judged.length ? `<div class="list">${days.flatMap((d) => d.cases.filter((c) => c.judge).map((c) => caseRow(c, cur))).join("")}</div>` : empty("No calls yet", "", "debates")}
    <div style="margin-top:10px">${howItWorks(true)}</div>`;
}

export function brain() {
  const f = feed();
  if (state.horizon === "intra") return intraBrain(f);
  if (state.market === "US") return empty("No Brain for US mid-term", "US mid-term signals are only logged and scored. No Bull, Bear or Judge runs on them, so there is nothing to learn from yet. Switch to India, or to Intraday, at the top.", "brain");
  return midBrain(f);
}
