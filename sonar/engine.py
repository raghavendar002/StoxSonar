"""Stage, trend template and graded breakout engine.

The engine is a pure replay: give it each stock's full daily history and it
walks forward one session at a time, using only data up to that session. A
daily run and a historical replay therefore produce the same labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------------------
# Per-stock features
# ---------------------------------------------------------------------------

def compute_features(df: pd.DataFrame, bench_close: pd.Series) -> pd.DataFrame:
    """Indicators for one stock. `df` has Open/High/Low/Close/Volume on a DatetimeIndex."""
    f = df[["Open", "High", "Low", "Close", "Volume"]].astype(float).copy()
    c = f["Close"]
    f["sma50"] = c.rolling(50).mean()
    f["sma150"] = c.rolling(150).mean()
    f["sma200"] = c.rolling(200).mean()
    f["slope150"] = f["sma150"] / f["sma150"].shift(C.SLOPE_LOOKBACK) - 1
    f["sma200_up"] = f["sma200"] > f["sma200"].shift(C.SMA200_LOOKBACK)
    f["hi52"] = f["High"].rolling(252, min_periods=200).max()
    f["lo52"] = f["Low"].rolling(252, min_periods=200).min()
    # Average volume of the 50 sessions before today, so a breakout day's own
    # volume does not inflate its baseline.
    f["vol50"] = f["Volume"].rolling(50).mean().shift(1)
    prev_close = c.shift(1)
    tr = pd.concat([f["High"] - f["Low"], (f["High"] - prev_close).abs(),
                    (f["Low"] - prev_close).abs()], axis=1).max(axis=1)
    f["atr_pct"] = tr.rolling(14).mean() / c
    f["traded_value"] = (c * f["Volume"]).rolling(20).median()
    # Bad prints: a huge one-day move without the volume a real move brings
    f["spike"] = ((c / prev_close - 1).abs() > C.SPIKE_MAX_MOVE) & \
        ~(f["Volume"] >= C.SPIKE_MAX_VOLUME * f["vol50"])
    f["prior_126"] = c / c.shift(126) - 1
    f["rs_score"] = (0.4 * (c / c.shift(63) - 1) + 0.2 * (c / c.shift(126) - 1)
                     + 0.2 * (c / c.shift(189) - 1) + 0.2 * (c / c.shift(252) - 1))
    f["mansfield"] = mansfield_rs(c, bench_close)
    f["bench"] = bench_close.reindex(f.index).ffill()
    f["n"] = np.arange(1, len(f) + 1)
    return f


def mansfield_rs(close: pd.Series, bench_close: pd.Series) -> pd.Series:
    """(RS line / its 52-week average - 1) x 100 on weekly closes, carried to daily.

    A week's value is labelled with its last session, so mid-week days see the
    previous completed week only.
    """
    bench = bench_close.reindex(close.index).ffill()
    rsl = (close / bench).dropna()
    if rsl.empty:
        return pd.Series(np.nan, index=close.index)
    weekly = rsl.groupby(rsl.index.to_period("W-FRI")).agg(lambda s: s.iloc[-1])
    last_day = rsl.groupby(rsl.index.to_period("W-FRI")).apply(lambda s: s.index[-1])
    m = (weekly / weekly.rolling(52).mean() - 1) * 100
    m.index = pd.DatetimeIndex(last_day.values)
    return m.reindex(close.index).ffill()


def rs_rank_matrix(features: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """RS percentile (1-99) per date among liquid stocks with a full RS score."""
    scores = {}
    for sym, f in features.items():
        s = f["rs_score"].where(f["traded_value"] >= C.LIQUIDITY_MIN_VALUE)
        scores[sym] = s
    m = pd.DataFrame(scores)
    ranks = m.rank(axis=1, pct=True)
    return (ranks * 98 + 1).round()


def template_checks(row, rs_rank: float) -> List[bool]:
    c = row.Close
    return [
        c > row.sma150 and c > row.sma200,
        row.sma150 > row.sma200,
        bool(row.sma200_up),
        row.sma50 > row.sma150 and row.sma50 > row.sma200,
        c > row.sma50,
        c >= C.TEMPLATE_LOW_MULT * row.lo52,
        c >= C.TEMPLATE_HIGH_MULT * row.hi52,
        (rs_rank if rs_rank == rs_rank else 0) >= C.TEMPLATE_RS_MIN,
    ]


TEMPLATE_LABELS = [
    "Close above SMA150 and SMA200",
    "SMA150 above SMA200",
    "SMA200 rising for a month",
    "SMA50 above SMA150 and SMA200",
    "Close above SMA50",
    "30%+ above 52-week low",
    "Within 25% of 52-week high",
    f"RS rank {C.TEMPLATE_RS_MIN}+",
]


# ---------------------------------------------------------------------------
# Stage rules
# ---------------------------------------------------------------------------

def raw_stage(row, prev_confirmed: Optional[int]) -> Optional[int]:
    """The stage today's numbers fit, or None when they fit no row."""
    c, s50, s150, slope = row.Close, row.sma50, row.sma150, row.slope150
    if c > s150 and slope > C.SLOPE_BAND and s50 > s150:
        return 2
    if c < s150 and slope < -C.SLOPE_BAND and s50 < s150:
        return 4
    if -C.SLOPE_BAND <= slope <= C.SLOPE_BAND:
        if prev_confirmed in (4, 1):
            return 1
        if prev_confirmed in (2, 3):
            return 3
        mid = (row.hi52 + row.lo52) / 2
        return 1 if c < mid else 3
    return None


def _valid(row) -> bool:
    return row.n >= C.MIN_HISTORY and not any(
        pd.isna(v) for v in (row.sma50, row.sma150, row.sma200, row.slope150, row.hi52, row.lo52))


# ---------------------------------------------------------------------------
# Base detection and triggers
# ---------------------------------------------------------------------------

def _max_depth(atr_pct: float) -> float:
    return C.BASE_MAX_DEPTH_VOLATILE if atr_pct > C.VOLATILE_ATR_PCT else C.BASE_MAX_DEPTH


def detect_trigger(H, L, O, Cl, V, vol50, atr_pct, t, spike=None) -> Optional[dict]:
    """A base breakout or breakdown that triggers on session t, if any."""
    s = max(0, t - C.BASE_LOOKBACK)
    if t - s < C.BASE_MIN_LEN:
        return None
    if spike is not None and spike[s:t + 1].any():
        return None
    rng = H[t] - L[t]
    if rng <= 0 or not vol50[t] or np.isnan(vol50[t]):
        return None
    vol_ratio = V[t] / vol50[t]
    if vol_ratio < C.TRIGGER_VOLUME:
        return None
    pos = (Cl[t] - L[t]) / rng
    max_depth = _max_depth(atr_pct[t])

    # Breakout: pivot is the highest high of the lookback, set >= 15 sessions ago
    k = s + int(np.argmax(H[s:t]))
    pivot = H[k]
    base_len = t - k
    if base_len >= C.BASE_MIN_LEN:
        base_low = L[k:t].min()
        depth = pivot / base_low - 1
        upper_wick = (H[t] - max(O[t], Cl[t])) / rng
        if (C.BASE_MIN_DEPTH <= depth <= max_depth and Cl[t] > pivot * (1 + C.TRIGGER_CLEARANCE_UP)
                and pos >= 0.5 and upper_wick <= C.MAX_WICK):
            return dict(direction="up", pivot=pivot, base_len=base_len, depth=depth,
                        vol_ratio=vol_ratio)

    # Breakdown: mirror image around the lowest low
    k = s + int(np.argmin(L[s:t]))
    trough = L[k]
    base_len = t - k
    if base_len >= C.BASE_MIN_LEN:
        base_high = H[k:t].max()
        depth = base_high / trough - 1
        lower_wick = (min(O[t], Cl[t]) - L[t]) / rng
        if (C.BASE_MIN_DEPTH <= depth <= max_depth and Cl[t] < trough * (1 - C.TRIGGER_CLEARANCE_DOWN)
                and pos <= 0.5 and lower_wick <= C.MAX_WICK):
            return dict(direction="down", pivot=trough, base_len=base_len, depth=depth,
                        vol_ratio=vol_ratio)
    return None


def momentum_score(values: Dict[str, float]) -> float:
    """Average z-score of the SCORE_FEATURES, each clipped to its 2006-2018 range."""
    zs = []
    for name, (lo, hi, mean, std) in C.SCORE_FEATURES.items():
        x = values.get(name)
        x = lo if x is None or x != x else min(max(x, lo), hi)
        zs.append((x - mean) / std)
    return float(np.mean(zs))


def grade_event(direction: str, stage: int, score: float, above_sma200: bool,
                weak_regime: bool) -> str:
    """Bullish: graded by momentum score, only above the 200-day average, cut one
    level in a weak market. Bearish: the spec's stage table, no regime cut."""
    if direction == "up":
        if not above_sma200:
            return "C"
        g = "A" if score >= C.SCORE_A else "B" if score >= C.SCORE_B else "C"
        if weak_regime:
            g = {"A": "B", "B": "C"}.get(g, g)
        return g
    return {3: "A", 4: "B", 2: "W", 1: "C"}[stage]


# ---------------------------------------------------------------------------
# Per-stock replay
# ---------------------------------------------------------------------------

@dataclass
class Event:
    symbol: str
    direction: str
    trigger_date: str
    grade: str
    stage: int
    template: int
    rs_rank: float
    mansfield: float
    regime: str
    pivot: float
    entry: float
    base_len: int
    depth: float
    vol_ratio: float
    stop: float = 0.0
    score: Optional[float] = None
    status: str = "Active"
    status_date: str = ""
    sessions: int = 0
    outcomes: Dict[str, Optional[float]] = field(default_factory=dict)
    # Research-only measurements (backtest analysis). Not stored in the ledger
    # and not used for grading.
    features: Dict[str, Optional[float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(d.pop("outcomes"))
        d.update(d.pop("features"))
        return d


def _lifecycle(ev: Event, close: float, day: int, closed_beyond_pivot: bool) -> str:
    """Status after `day` sessions (day 0 = trigger day)."""
    up = ev.direction == "up"
    move = close / ev.pivot - 1 if up else 1 - close / ev.pivot
    if day > 0 and (close < ev.stop if up else close > ev.stop):
        return "Failed"
    if day >= C.LIFECYCLE_SESSIONS:
        return "Faded" if closed_beyond_pivot else "Confirmed"
    return "Extended" if move > C.EXTENDED_PCT else "Active"


def replay_symbol(symbol: str, f: pd.DataFrame, rs_rank: pd.Series,
                  weak_regime: Optional[pd.Series], with_events: bool = True):
    """Walk one stock forward. Returns (daily state DataFrame, list of Events)."""
    rs_rank = rs_rank.reindex(f.index)
    weak = (weak_regime.reindex(f.index).fillna(False) if weak_regime is not None
            else pd.Series(False, index=f.index))
    H, L, O, Cl, V = (f[k].to_numpy(float) for k in ("High", "Low", "Open", "Close", "Volume"))
    vol50, atr = f["vol50"].to_numpy(float), f["atr_pct"].to_numpy(float)
    spike = f["spike"].to_numpy(bool)
    dates = f.index

    confirmed: Optional[int] = None
    since: Optional[int] = None
    cand, cand_days = None, 0
    open_ev: Optional[Event] = None
    open_idx, below = 0, False
    events: List[Event] = []
    rows = []

    for t, row in enumerate(f.itertuples()):
        if not _valid(row):
            continue
        rr = rs_rank.iloc[t]
        raw = raw_stage(row, confirmed)
        if confirmed is None:
            if raw is not None:
                confirmed, since = raw, t
        elif raw is not None and raw != confirmed:
            if raw == cand:
                cand_days += 1
            else:
                cand, cand_days = raw, 1
            if cand_days >= C.CONFIRM_SESSIONS:
                confirmed, since, cand, cand_days = cand, t, None, 0
        else:
            cand, cand_days = None, 0
        if confirmed is None:
            continue

        checks = template_checks(row, rr)
        template = int(sum(checks))
        new_event = None

        if with_events:
            if open_ev is not None:
                day = t - open_idx
                if (open_ev.direction == "up" and Cl[t] < open_ev.pivot) or \
                   (open_ev.direction == "down" and Cl[t] > open_ev.pivot):
                    below = True
                open_ev.status = _lifecycle(open_ev, Cl[t], day, below)
                open_ev.status_date = str(dates[t].date())
                open_ev.sessions = day
                if open_ev.status in ("Failed", "Confirmed", "Faded"):
                    open_ev = None
            if open_ev is None:
                trig = detect_trigger(H, L, O, Cl, V, vol50, atr, t, spike)
                if trig:
                    score = momentum_score(dict(
                        rs_rank=rr, prior_126=row.prior_126, dist_sma200=Cl[t] / row.sma200 - 1,
                        ext_pivot=Cl[t] / trig["pivot"] - 1))
                    g = grade_event(trig["direction"], confirmed, score, Cl[t] > row.sma200,
                                    bool(weak.iloc[t]))
                    sign = 1 if trig["direction"] == "up" else -1
                    trig["stop"] = float(Cl[t] * (1 - sign * C.STOP_ATR * atr[t]))
                    trig["score"] = round(score, 3) if trig["direction"] == "up" else None
                    ev = Event(symbol=symbol, trigger_date=str(dates[t].date()), grade=g,
                               stage=confirmed, template=template,
                               rs_rank=None if pd.isna(rr) else float(rr),
                               mansfield=None if pd.isna(row.mansfield) else round(float(row.mansfield), 2),
                               regime="Weak" if weak.iloc[t] else "Healthy",
                               entry=float(Cl[t]), **trig)
                    ev.status = _lifecycle(ev, Cl[t], 0, False)
                    ev.status_date = ev.trigger_date
                    ev.features["stage_age"] = t - since
                    events.append(ev)
                    open_ev, open_idx, below, new_event = ev, t, False, ev
                    # Shortcut: a Grade A breakout out of a base confirms Stage 2 now
                    if ev.direction == "up" and g == "A" and confirmed == 1 and (raw == 2 or cand == 2):
                        confirmed, since, cand, cand_days = 2, t, None, 0

        rows.append(dict(
            date=dates[t], symbol=symbol, stage=confirmed,
            transition_to=cand, transition_day=cand_days if cand else 0,
            stage_age=t - since, template=template,
            template_failed=[TEMPLATE_LABELS[i] for i, ok in enumerate(checks) if not ok],
            rs_rank=rr, mansfield=row.mansfield, liquid=row.traded_value >= C.LIQUIDITY_MIN_VALUE,
            close=row.Close, event=new_event.direction if new_event else None,
        ))

    for ev in events:
        _fill_outcomes(ev, f)
        _research_features(ev, f)
    return pd.DataFrame(rows), events


def _fill_outcomes(ev: Event, f: pd.DataFrame) -> None:
    """Return after each horizon, the benchmark's return, and R at 21 sessions.

    Returns run from the next session's open, the first price anyone could act
    on, to the close h sessions after the trigger. A bad print inside that
    window leaves the outcome unmeasured rather than wrong."""
    i = f.index.get_loc(pd.Timestamp(ev.trigger_date))
    sign = 1 if ev.direction == "up" else -1
    risk = abs(1 - ev.stop / ev.entry)
    spike = f["spike"].to_numpy(bool)
    for h in C.HORIZONS:
        j = i + h
        if j < len(f) and not spike[i + 1:j + 1].any():
            r = f["Close"].iloc[j] / f["Open"].iloc[i + 1] - 1
            b = f["bench"].iloc[j] / f["bench"].iloc[i] - 1
            ev.outcomes[f"ret_{h}"] = round(float(r), 4)
            ev.outcomes[f"bench_{h}"] = round(float(b), 4)
            if h == 21 and risk > 0:
                ev.outcomes["r_21"] = round(float(sign * r / risk), 2)
        else:
            ev.outcomes.setdefault(f"ret_{h}", None)
            ev.outcomes.setdefault(f"bench_{h}", None)
    ev.outcomes.setdefault("r_21", None)


def _research_features(ev: Event, f: pd.DataFrame) -> None:
    """Extra context at the trigger, and how the trade path looked afterwards."""
    i = f.index.get_loc(pd.Timestamp(ev.trigger_date))
    c, o, h, l, v = (f[k].to_numpy(float) for k in ("Close", "Open", "High", "Low", "Volume"))
    row = f.iloc[i]

    def r(x):
        return None if x is None or not np.isfinite(x) else round(float(x), 4)

    fe = ev.features
    fe["ext_pivot"] = r(c[i] / ev.pivot - 1)
    fe["atr_pct"] = r(row.atr_pct)
    fe["fail_dist_atr"] = r(abs(1 - ev.pivot / c[i]) / row.atr_pct) if row.atr_pct else None
    fe["from_hi52"] = r(c[i] / row.hi52 - 1)
    fe["from_lo52"] = r(c[i] / row.lo52 - 1)
    fe["dist_sma50"] = r(c[i] / row.sma50 - 1)
    fe["dist_sma200"] = r(c[i] / row.sma200 - 1)
    fe["slope150"] = r(row.slope150)
    fe["prior_63"] = r(c[i] / c[i - 63] - 1) if i >= 63 else None
    fe["prior_126"] = r(c[i] / c[i - 126] - 1) if i >= 126 else None
    fe["day_ret"] = r(c[i] / c[i - 1] - 1)
    fe["gap"] = r(o[i] / c[i - 1] - 1)
    fe["tight10"] = r(np.std(c[i - 10:i]) / ev.pivot) if i >= 10 else None
    fe["dry_vol10"] = r(np.mean(v[i - 10:i]) / row.vol50) if row.vol50 else None
    fe["traded_value"] = r(row.traded_value)
    fe["price"] = r(c[i])
    fe["bench_prior_63"] = r(row.bench / f["bench"].iloc[i - 63] - 1) if i >= 63 else None
    # Path after the trigger, for entry and stop research
    if i + 1 < len(f):
        fe["next_open_gap"] = r(o[i + 1] / c[i] - 1)
    for n in (10, 21):
        if i + n < len(f):
            fe[f"mfe_{n}"] = r(h[i + 1:i + n + 1].max() / c[i] - 1)
            fe[f"mae_{n}"] = r(l[i + 1:i + n + 1].min() / c[i] - 1)
            fe[f"ret_{n}_from_open"] = r(c[i + n] / o[i + 1] - 1)


# ---------------------------------------------------------------------------
# Whole market
# ---------------------------------------------------------------------------

@dataclass
class MarketResult:
    states: pd.DataFrame          # one row per liquid stock per session
    events: List[Event]
    regime: pd.DataFrame          # per session: bench_ok, stage2_share, weak


def run_market(prices: Dict[str, pd.DataFrame], bench_close: pd.Series,
               state_sink=None) -> MarketResult:
    """Replay a whole market. With `state_sink`, each stock's daily states are
    handed to sink(symbol, states, features) instead of being kept, so long
    histories fit in memory."""
    feats = {s: compute_features(df, bench_close) for s, df in prices.items() if len(df) >= 60}
    ranks = rs_rank_matrix(feats)

    # Pass 1: stages only, to measure breadth for the regime
    stage2, counted = None, None
    for s, f in feats.items():
        st, _ = replay_symbol(s, f, ranks[s], None, with_events=False)
        if st.empty:
            continue
        st = st[st["liquid"]].set_index("date")
        is2 = (st["stage"] == 2).astype(int)
        one = pd.Series(1, index=st.index)
        stage2 = is2 if stage2 is None else stage2.add(is2, fill_value=0)
        counted = one if counted is None else counted.add(one, fill_value=0)

    b = bench_close.astype(float)
    sma200 = b.rolling(200).mean()
    regime = pd.DataFrame({"bench_ok": (b > sma200) & (sma200 > sma200.shift(21))})
    share = (stage2 / counted) if counted is not None else pd.Series(dtype=float)
    regime["stage2_share"] = share.reindex(regime.index)
    regime["weak"] = ~(regime["bench_ok"] & (regime["stage2_share"] >= C.REGIME_MIN_STAGE2_SHARE))

    # Pass 2: stages plus events, graded under the regime
    states, events = [], []
    for s, f in feats.items():
        st, ev = replay_symbol(s, f, ranks[s], regime["weak"])
        if not st.empty:
            if state_sink is not None:
                state_sink(s, st[st["liquid"]], f)
            else:
                states.append(st[st["liquid"]])
        # Only stocks that pass the liquidity floor on the trigger day count
        liquid_days = set(f.index[f["traded_value"] >= C.LIQUIDITY_MIN_VALUE].strftime("%Y-%m-%d"))
        events.extend(e for e in ev if e.trigger_date in liquid_days)
    states_df = pd.concat(states, ignore_index=True) if states else pd.DataFrame()
    return MarketResult(states=states_df, events=events, regime=regime)
