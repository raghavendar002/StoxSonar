"""PR 8 study: a ranked momentum core with a crash brake, in one Rs 1 lakh account.

    python research/momentum.py cache/nse_panel.pkl > reports/momentum.md

Why: v0.2's breakouts lose money after costs (reports/simulate.md), and the
mid-term Judge keeps saying Avoid because their base rates are negative. This
tests a different source of candidates instead of a different Judge.

Rules, fixed before the run (research hypotheses H1, H3, H13, H15):
  * Universe each month-end: NSE stocks (survivorship-free daily files) with a
    year of history, trading on 90% of the last 252 sessions, close >= Rs 10,
    median traded value over 126 sessions >= Rs 5 crore, the top 500 of those
    by that value (a stand-in for the Nifty 500; the files carry no share
    counts), minus MQ50-style band hitters (3+ locked-limit days in 126).
  * Score: like NSE's Momentum 30 indices, the cross-sectional z-scores of
    6-month and 12-month return, each divided by 1-year daily volatility,
    averaged.
  * Monthly: on the first session of each month, at the open, sell holdings
    ranked worse than 2N (or out of the universe), then buy the best-ranked
    stocks not held until N are held, each at 1/N of equity. Winners are not
    trimmed.
  * Brakes (one per variant):
      none
      gate      no new buys while the Nifty 500 closes under its 200-day average (H3)
      exit      also sell everything at the next open the first day it closes under it,
                and buy back only at a month start above it
      gate+vix  gate, plus no new buys while India VIX is above its trailing
                1-year 90th percentile (H15)
      exit+vix  exit, plus the same VIX rule on new buys
  * N in {10, 15, 20}. 15 variants in all.
  * Idle cash sits in a liquid ETF, modelled as LIQUID_RATE a year.
  * Costs: the same Indian delivery charges and liquidity slippage as the v0.2
    simulator (sonar/portfolio.py), DP fee included.

The variant is chosen on 2007-2018 only, by Sharpe, and then judged on 2019 on
from a fresh Rs 1 lakh against the bar set on 2026-10-25: CAGR at least the
Nifty 500's + 5 points, max drawdown under 25%, ahead of the index in at least
5 of the 7 full years 2019-2025, deflated Sharpe at least 0.95.

Side check, not a variant: the chosen variant sized by the app's rule of 0.5%
risk per trade (stop taken as 2.5 ATR), to show what that rule does here.
"""

from __future__ import annotations

import math
import pickle
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research"))
from sonar import config as C, nse  # noqa: E402
from sonar.portfolio import buy_cost, sell_cost, slippage  # noqa: E402
from sonar.momentum import month_starts, ranks, wide  # noqa: E402,F401

LIQUID_RATE = 0.055          # liquid ETF, a year, after its fee (overnight rates 2007-2026 ran ~3.5-8.5%)
VIX_PCT = 0.90
NS = (10, 15, 20)
BRAKES = ("none", "gate", "exit", "gate+vix", "exit+vix")
FIT = ("2007-01-01", "2018-12-31")
CHECK_FROM = "2019-01-01"


@dataclass(frozen=True)
class Variant:
    n: int
    brake: str
    risk_pct: Optional[float] = None     # None: 1/N of equity; else size by risk to a 2.5-ATR stop
    vt: Optional[float] = None           # volatility target: scale the month's basket to this yearly vol

    @property
    def name(self) -> str:
        s = f"top {self.n}, brake {self.brake}"
        s += f", vol target {self.vt * 100:.0f}%" if self.vt else ""
        return s + (f", {self.risk_pct * 100:.1f}% risk sizing" if self.risk_pct else "")


def brake_series(bench: pd.Series, vix: Optional[pd.Series], days: pd.DatetimeIndex) -> pd.DataFrame:
    """Per day, at that day's close: is the index under its 200-day average; is VIX in its top decile."""
    b = bench.reindex(days.union(bench.index)).ffill()
    under = (b < b.rolling(200, min_periods=200).mean()).reindex(days).fillna(False)
    hot = pd.Series(False, index=days)
    if vix is not None and len(vix):
        v = vix.reindex(days.union(vix.index)).ffill()
        thr = v.rolling(252, min_periods=200).quantile(VIX_PCT)
        hot = (v > thr).reindex(days).fillna(False)
    return pd.DataFrame({"under": under.astype(bool), "vix_hot": hot.astype(bool)})


# ---------------------------------------------------------------------------
# One account, day by day


def simulate(w: dict, rk: dict, brakes: pd.DataFrame, v: Variant, start: str, end: Optional[str],
             capital: float = C.CAPITAL_RS) -> dict:
    days = w["Close"].index
    days = days[(days >= pd.Timestamp(start)) & ((days <= pd.Timestamp(end)) if end else True)]
    rank_days = sorted(rk)
    starts = set(month_starts(days))
    O, Cl, H, L = w["Open"], w["Close"], w["High"], w["Low"]
    tv = w["value"].rolling(20, min_periods=5).median()
    atr = None
    if v.risk_pct:
        pc = Cl.ffill().shift(1)
        tr = pd.concat([H - L, (H - pc).abs(), (L - pc).abs()]).groupby(level=0).max()
        atr = tr.rolling(14, min_periods=10).mean()
    rets = Cl.ffill().pct_change(fill_method=None) if v.vt else None
    last_seen = w["traded"][::-1].cummax()[::-1]          # False after a stock's final day
    daily_cash = (1 + LIQUID_RATE) ** (1 / 365.25) - 1
    cash, hold, trades, curve = float(capital), {}, [], []   # hold: sym -> dict(qty, cost, entry_day, px)
    last_px: dict = {}
    prev_day = None
    for di, day in enumerate(days):
        if prev_day is not None:
            cash *= (1 + daily_cash) ** (day - prev_day).days
        yb = brakes.loc[prev_day] if prev_day is not None else None
        exit_brake = v.brake.startswith("exit") and yb is not None and bool(yb["under"])

        def sell(sym, why):
            nonlocal cash
            h = hold.pop(sym)
            o = O.at[day, sym]
            px = (o if o == o and o > 0 else last_px.get(sym, h["px"])) * (1 - slippage(tv.at[prev_day, sym] if prev_day is not None else 0))
            proceeds = h["qty"] * px
            c = sell_cost(proceeds)
            cash += proceeds - c
            trades.append(dict(symbol=sym, entry_date=h["entry_day"].date(), exit_date=day.date(), qty=h["qty"],
                               entry=round(h["px"], 2), exit=round(px, 2), reason=why,
                               pnl=round(proceeds - c - h["qty"] * h["px"] - h["cost"], 2),
                               ret=round((proceeds - c) / (h["qty"] * h["px"] + h["cost"]) - 1, 4)))
            last_px.pop(sym, None)

        def trim(sym, keep_qty):
            nonlocal cash
            h = hold[sym]
            q = h["qty"] - keep_qty
            px = O.at[day, sym] * (1 - slippage(tv.at[prev_day, sym]))
            share = q / h["qty"]
            proceeds = q * px
            c = sell_cost(proceeds)
            cash += proceeds - c
            trades.append(dict(symbol=sym, entry_date=h["entry_day"].date(), exit_date=day.date(), qty=q,
                               entry=round(h["px"], 2), exit=round(px, 2), reason="vol trim",
                               pnl=round(proceeds - c - q * h["px"] - h["cost"] * share, 2),
                               ret=round((proceeds - c) / (q * h["px"] + h["cost"] * share) - 1, 4)))
            h["cost"] *= 1 - share
            h["qty"] = keep_qty

        # delisted / merged: out at the last close
        for sym in [s for s in hold if not last_seen.at[day, s]]:
            h = hold.pop(sym)
            px = last_px.get(sym, h["px"])
            proceeds = h["qty"] * px
            c = sell_cost(proceeds)
            cash += proceeds - c
            trades.append(dict(symbol=sym, entry_date=h["entry_day"].date(), exit_date=day.date(), qty=h["qty"],
                               entry=round(h["px"], 2), exit=round(px, 2), reason="delisted",
                               pnl=round(proceeds - c - h["qty"] * h["px"] - h["cost"], 2),
                               ret=round((proceeds - c) / (h["qty"] * h["px"] + h["cost"]) - 1, 4)))
            last_px.pop(sym, None)

        tradable = lambda s: bool(w["traded"].at[day, s]) and O.at[day, s] > 0  # noqa: E731
        if exit_brake:
            for sym in [s for s in hold if tradable(s)]:
                sell(sym, "brake")
        if day in starts and prev_day is not None:
            asof = [d for d in rank_days if d <= prev_day]
            r = rk[asof[-1]] if asof else pd.Series(dtype=float)
            for sym in [s for s in hold if tradable(s) and (r.get(s, np.inf) > 2 * v.n)]:
                sell(sym, "rank")
            blocked = bool(yb["under"]) if v.brake != "none" else False
            if v.brake.endswith("vix"):
                blocked = blocked or bool(yb["vix_hot"])
            if not blocked and len(r):
                equity = cash + sum(h["qty"] * last_px.get(s, h["px"]) for s, h in hold.items())
                expo = 1.0
                if v.vt:
                    basket = list(r.sort_values().index[:v.n])
                    i = Cl.index.get_loc(prev_day)
                    sig = rets.iloc[max(i - 125, 0):i + 1][basket].mean(axis=1).std() * math.sqrt(252)
                    expo = min(1.0, v.vt / sig) if sig and sig == sig else 1.0
                    for sym in [s for s in hold if tradable(s)]:
                        tgt = expo * equity / v.n
                        if hold[sym]["qty"] * O.at[day, sym] > 1.25 * tgt:
                            keep = int(tgt // O.at[day, sym])
                            if keep < 1:
                                sell(sym, "vol trim")
                            elif keep < hold[sym]["qty"]:
                                trim(sym, keep)
                for sym in r.sort_values().index:
                    if len(hold) >= v.n:
                        break
                    if sym in hold or not tradable(sym):
                        continue
                    fill = O.at[day, sym] * (1 + slippage(tv.at[prev_day, sym]))
                    target = expo * equity / v.n
                    if v.risk_pct:
                        a = atr.at[prev_day, sym]
                        if not (a == a and a > 0):
                            continue
                        target = min(target, equity * v.risk_pct / (2.5 * a / Cl.at[prev_day, sym]))
                    qty = int(target // fill)
                    while qty > 0 and qty * fill + buy_cost(qty * fill) > cash:
                        qty -= 1
                    if qty < 1:
                        continue
                    c = buy_cost(qty * fill)
                    cash -= qty * fill + c
                    hold[sym] = dict(qty=qty, cost=c, entry_day=day, px=fill)
        for s in hold:
            c = Cl.at[day, s]
            if c == c:
                last_px[s] = c
        equity = cash + sum(h["qty"] * last_px.get(s, h["px"]) for s, h in hold.items())
        curve.append((day, equity, len(hold), cash))
        prev_day = day
    eq = pd.DataFrame(curve, columns=["date", "equity", "positions", "cash"]).set_index("date")
    return {"equity": eq, "trades": pd.DataFrame(trades)}


# ---------------------------------------------------------------------------
# Scoring against the bar


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_ppf(p: float) -> float:
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _norm_cdf(mid) < p else (lo, mid)
    return (lo + hi) / 2


def deflated_sharpe(x: np.ndarray, sr_trials: list) -> float:
    """Bailey and Lopez de Prado (2014), per period; same formula as research/retune.py."""
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 12 or x.std(ddof=1) == 0:
        return float("nan")
    sr = x.mean() / x.std(ddof=1)
    k = len(sr_trials)
    var_sr = np.var(sr_trials, ddof=1) if k > 1 else 0.0
    g = 0.5772156649
    sr0 = math.sqrt(var_sr) * ((1 - g) * _norm_ppf(1 - 1 / k) + g * _norm_ppf(1 - 1 / (k * math.e))) if k > 1 else 0.0
    skew, kurt = pd.Series(x).skew(), pd.Series(x).kurt() + 3
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-9))
    return float(_norm_cdf((sr - sr0) * math.sqrt(n - 1) / denom))


def monthly_excess_cash(eq: pd.Series) -> np.ndarray:
    m = eq.resample("ME").last().pct_change().dropna()
    return (m - ((1 + LIQUID_RATE) ** (1 / 12) - 1)).to_numpy()


def metrics(eq: pd.Series, bench: pd.Series, trades: pd.DataFrame) -> dict:
    b = bench.reindex(eq.index).ffill()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    bcagr = (b.iloc[-1] / b.iloc[0]) ** (1 / yrs) - 1
    r = eq.pct_change().dropna() - ((1 + LIQUID_RATE) ** (1 / 252) - 1)
    out = dict(cagr_pct=round(cagr * 100, 1), bench_cagr_pct=round(bcagr * 100, 1),
               edge_pts=round((cagr - bcagr) * 100, 1),
               max_dd_pct=round((eq / eq.cummax() - 1).min() * 100, 1),
               bench_dd_pct=round((b / b.cummax() - 1).min() * 100, 1),
               sharpe=round(r.mean() / r.std() * math.sqrt(252), 2) if r.std() > 0 else float("nan"),
               invested_pct=None, trades=len(trades),
               final_rs=round(float(eq.iloc[-1])))
    return out


def yearly(eq: pd.Series, bench: pd.Series) -> pd.DataFrame:
    b = bench.reindex(eq.index).ffill()
    y = pd.DataFrame({"strategy": eq.resample("YE").last(), "bench": b.resample("YE").last()})
    y = pd.concat([pd.DataFrame({"strategy": [eq.iloc[0]], "bench": [b.iloc[0]]}), y], ignore_index=True)
    out = (y.pct_change().iloc[1:] * 100).round(1)
    out.index = eq.resample("YE").last().index.year
    out["excess"] = (out["strategy"] - out["bench"]).round(1)
    return out


def md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    rows = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for r in df.itertuples(index=False):
        rows.append("| " + " | ".join("–" if v is None or (isinstance(v, float) and v != v) else str(v) for v in r) + " |")
    return "\n".join(rows) + "\n"


def run(w: dict, bench: pd.Series, vix: Optional[pd.Series], out_dir: Path,
        variants: Optional[list] = None, candidates: Optional[list] = None,
        title: str = "PR 8: ranked momentum with a crash brake") -> str:
    """variants: every trial (all count toward the deflated Sharpe);
    candidates: the ones the 2007-2018 Sharpe may choose from (default: all)."""
    days = w["Close"].index
    pos = {d: i for i, d in enumerate(days)}
    rk = ranks(w, pd.DatetimeIndex([days[pos[d] - 1] for d in month_starts(days) if pos[d] > 0]))
    br = brake_series(bench, vix, days)
    variants = variants or [Variant(n, b) for n in NS for b in BRAKES]
    candidates = candidates or variants
    fit, chk, res_chk = [], [], {}
    for v in variants:
        rf = simulate(w, rk, br, v, *FIT)
        mf = metrics(rf["equity"]["equity"], bench, rf["trades"])
        mf["invested_pct"] = round((1 - rf["equity"]["cash"] / rf["equity"]["equity"]).mean() * 100)
        rc = simulate(w, rk, br, v, CHECK_FROM, None)
        mc = metrics(rc["equity"]["equity"], bench, rc["trades"])
        mc["invested_pct"] = round((1 - rc["equity"]["cash"] / rc["equity"]["equity"]).mean() * 100)
        fit.append({"variant": v.name, **mf})
        chk.append({"variant": v.name, **mc})
        res_chk[v] = rc
        print(f"{v.name}: fit sharpe {mf['sharpe']} cagr {mf['cagr_pct']} | check cagr {mc['cagr_pct']}",
              file=sys.stderr, flush=True)
    fit_df, chk_df = pd.DataFrame(fit), pd.DataFrame(chk)
    pick = fit_df["sharpe"].where([v in candidates for v in variants])
    best_i = int(pick.fillna(-9).idxmax())
    chosen = variants[best_i]
    rc = res_chk[chosen]
    eq = rc["equity"]["equity"]
    m = chk_df.iloc[best_i].to_dict()
    yr = yearly(eq, bench)
    full = yr.loc[[y for y in yr.index if 2019 <= y <= 2025]]
    years_ahead = int((full["excess"] > 0).sum())
    sr_trials = []
    for v in variants:
        x = monthly_excess_cash(res_chk[v]["equity"]["equity"])
        sr_trials.append(x.mean() / x.std(ddof=1) if len(x) > 2 and x.std(ddof=1) > 0 else 0.0)
    dsr = deflated_sharpe(monthly_excess_cash(eq), sr_trials)
    # Each variant against the bar on 2019 on, and its fit-period drawdown (shown, not used to choose)
    ahead, dsrs, fit_dd = [], [], fit_df["max_dd_pct"].tolist()
    for v in variants:
        y = yearly(res_chk[v]["equity"]["equity"], bench)
        y = y.loc[[k for k in y.index if 2019 <= k <= 2025]]
        ahead.append(int((y["excess"] > 0).sum()))
        dsrs.append(round(deflated_sharpe(monthly_excess_cash(res_chk[v]["equity"]["equity"]), sr_trials), 2))
    chk_df["years_ahead_of_7"] = ahead
    chk_df["deflated_sharpe"] = dsrs
    chk_df["fit_max_dd_pct"] = fit_dd
    chk_df["passes_bar_2019_on"] = (chk_df["edge_pts"] >= 5) & (chk_df["max_dd_pct"] > -25) & \
        (chk_df["years_ahead_of_7"] >= 5) & (chk_df["deflated_sharpe"] >= 0.95)
    bar = [("CAGR >= Nifty 500 + 5 pts", f"{m['cagr_pct']}% vs {m['bench_cagr_pct']}% + 5", m["edge_pts"] >= 5),
           ("Max drawdown < 25%", f"{m['max_dd_pct']}%", m["max_dd_pct"] > -25),
           ("Ahead of the index in >= 5 of 7 years (2019-2025)", f"{years_ahead} of {len(full)}", years_ahead >= 5),
           (f"Deflated Sharpe >= 0.95 ({len(variants)} trials)", f"{dsr:.2f}", dsr >= 0.95)]
    passed = all(p for *_, p in bar)
    side = simulate(w, rk, br, replace(chosen, risk_pct=C.RISK_PCT), CHECK_FROM, None)
    ms = metrics(side["equity"]["equity"], bench, side["trades"])
    ms["invested_pct"] = round((1 - side["equity"]["cash"] / side["equity"]["equity"]).mean() * 100)

    out_dir.mkdir(parents=True, exist_ok=True)
    rc["equity"].to_csv(out_dir / "equity_2019.csv")
    rc["trades"].to_csv(out_dir / "trades_2019.csv", index=False)
    fit_df.to_csv(out_dir / "fit_2007_2018.csv", index=False)
    chk_df.to_csv(out_dir / "check_2019_on.csv", index=False)
    tr = rc["trades"]
    why = tr.groupby("reason").agg(trades=("pnl", "size"), avg_ret_pct=("ret", lambda x: round(x.mean() * 100, 1)),
                                   total_pnl_rs=("pnl", lambda x: round(x.sum()))).reset_index() if len(tr) else pd.DataFrame()
    lines = [f"# {title}, Rs {C.CAPITAL_RS:,} account", "",
             f"Data {days[0].date()} to {days[-1].date()}, NSE daily files (delisted stocks included). "
             f"Benchmark: {'; '.join(bench.attrs.get('sources', ['Nifty 500']))} (price index, no dividends). "
             f"India VIX from {vix.index.min().date() if vix is not None and len(vix) else 'n/a'}. "
             f"Idle cash earns {LIQUID_RATE * 100:.1f}% a year (liquid ETF).", "",
             f"## Verdict: **{'PASS' if passed else 'FAIL'}**", "",
             f"Chosen on 2007-2018 by Sharpe from {', '.join(c.name for c in candidates)}: **{chosen.name}**. Judged on {CHECK_FROM} on, fresh Rs 1 lakh.", "",
             md(pd.DataFrame(bar, columns=["test", "result", "pass"])), "",
             "## Every variant, 2007-2018 (the choice is made here)", "", md(fit_df), "",
             "## Every variant, 2019 on (shown for honesty; not used to choose)", "", md(chk_df), "",
             f"## {chosen.name}, 2019 on, year by year (%)", "", md(yr.reset_index().rename(columns={"index": "year"})), "",
             "### How positions ended", "", md(why) if len(why) else "none", "",
             f"## Side check: the same rules sized by {C.RISK_PCT * 100:.1f}% risk per trade (2.5-ATR stop distance), 2019 on", "",
             md(pd.DataFrame([{"variant": replace(chosen, risk_pct=C.RISK_PCT).name, **ms}])), ""]
    return "\n".join(lines)


def load_vix() -> Optional[pd.Series]:
    try:
        import yfinance as yf
        df = yf.download(C.VIX["NSE"], period="max", interval="1d", auto_adjust=False, progress=False)
        s = df["Close"]
        s = s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
        s.index = pd.DatetimeIndex(s.index).tz_localize(None)
        return s.dropna()
    except Exception as e:  # the VIX rule then never fires, and the report says n/a
        print(f"India VIX unavailable: {e}", file=sys.stderr)
        return None


def vt_study() -> dict:
    """Pre-registered 2026-11-17: does a 15% volatility target fix the 2008 drawdown
    of the exit-brake book? Candidates: exit brake, N 15 or 20, with or without it."""
    base = [Variant(n, b) for n in NS for b in BRAKES]
    new = [Variant(n, "exit", vt=0.15) for n in (15, 20)]
    cands = [Variant(15, "exit"), Variant(20, "exit")] + new
    return dict(variants=base + new, candidates=cands,
                title="PR 8b: the exit-brake momentum book with a 15% volatility target")


def main(cache_path: str, study: str = "base") -> int:
    from backtest import spliced_benchmark
    with open(cache_path, "rb") as fh:          # written by backtest.py on this runner
        prices = nse.to_price_dict(pickle.load(fh))
    w = wide(prices)
    bench = spliced_benchmark()
    if study == "vt":
        print(run(w, bench, load_vix(), ROOT / "reports" / "momentum_vt", **vt_study()))
    else:
        print(run(w, bench, load_vix(), ROOT / "reports" / "momentum"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
