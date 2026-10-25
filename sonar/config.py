"""Rule settings for the public StoxSonar list.

Values follow the StoxSonar Stock Segregation Rules Spec. Changing any of them
changes what the engine says, so bump ENGINE_VERSION whenever one changes; the
track record is only reported per engine version.
"""

ENGINE_VERSION = "0.2.0"

# History
MIN_HISTORY = 252            # sessions before a stock gets a stage
FETCH_PERIOD = "3y"

# Stage rules (Weinstein, daily data)
SLOPE_LOOKBACK = 21          # SMA150 slope = SMA150 / SMA150[21 sessions ago] - 1
SLOPE_BAND = 0.01            # +/-1% counts as flat
CONFIRM_SESSIONS = 5         # hysteresis

# Trend template
TEMPLATE_RS_MIN = 70
TEMPLATE_LOW_MULT = 1.30     # close >= 30% above 52-week low
TEMPLATE_HIGH_MULT = 0.75    # close within 25% of 52-week high
SMA200_LOOKBACK = 22

# Base and trigger
BASE_LOOKBACK = 65
BASE_MIN_LEN = 15
BASE_MIN_DEPTH = 0.08
BASE_MAX_DEPTH = 0.35
BASE_MAX_DEPTH_VOLATILE = 0.50
VOLATILE_ATR_PCT = 0.05
TRIGGER_CLEARANCE_UP = 0.02  # breakout close at least 2% above pivot (v0.2; 0.5% failed 42-45%)
TRIGGER_CLEARANCE_DOWN = 0.005  # breakdown close 0.5% below the trough (not yet re-tested)
TRIGGER_VOLUME = 1.5         # x 50-day average volume
MAX_WICK = 0.25              # wick against the move, share of day's range

# Lifecycle
LIFECYCLE_SESSIONS = 10
EXTENDED_PCT = 0.05
STOP_ATR = 2.5               # Failed = close beyond entry -/+ 2.5 x ATR (v0.2; was pivot -3%)
SPIKE_MAX_MOVE = 0.50        # a one-day move this big ...
SPIKE_MAX_VOLUME = 2.0       # ... on under 2x average volume is treated as a bad print

# Bullish grade (v0.2): a momentum score, the plain average of four z-scores.
# Means, spreads and clip bounds were fixed on 2006-2018 breakouts only; the
# grade cut-offs are that period's 80th (A) and 50th (B) percentiles.
SCORE_FEATURES = {           # name: (clip low, clip high, mean, std)
    "rs_rank": (8.0, 99.0, 63.4461, 23.9557),
    "prior_126": (-0.2279, 2.6572, 0.4515, 0.5162),       # 6-month return
    "dist_sma200": (-0.0953, 1.2511, 0.3207, 0.2600),     # close / SMA200 - 1
    "ext_pivot": (0.0054, 0.1441, 0.0342, 0.0296),        # close / pivot - 1
}
SCORE_A = 0.565
SCORE_B = -0.118

# Shadow grade (logged only, v0.2.x): the 'selected' score from the phase 3
# walk-forward study (research/retune.py, reports/retune.md), fitted on NSE
# breakouts 2007-2026. It beat v0.2 out of sample but missed the 0.95 deflated
# Sharpe bar, so it changes no grade, suggestion or message: it is recorded next
# to each live signal so the two can be compared on trades neither has seen.
# Changing it does not need an ENGINE_VERSION bump, since nothing shown depends on it.
SHADOW_FEATURES = {          # name: (clip low, clip high, mean, std, sign; +1 = higher is better)
    "dist_sma50": (0.079275, 0.45759, 0.19464, 0.0778215, -1),
    "depth": (0.0856332, 0.457155, 0.215812, 0.0818601, -1),
    "atr_pct": (0.020335, 0.070465, 0.0409662, 0.0106329, -1),
    "from_hi52": (-0.450175, 0, -0.0705391, 0.100666, +1),
    "tight10": (0.006435, 0.062495, 0.0253653, 0.012328, -1),
    "template": (3, 8, 6.64347, 1.61661, +1),
}
SHADOW_A = 0.5217
SHADOW_B = 0.0833

# Trade plan on every bullish signal (v0.2). Sizing is for one account: change
# CAPITAL_RS to yours. These only shape what is suggested, not what is recorded.
CAPITAL_RS = 100_000         # account size
RISK_PCT = 0.005             # risk 0.5% of the account per trade, from entry to stop
MAX_POSITION_PCT = 0.25      # never more than a quarter of the account in one stock
MAX_GAP_ATR = 1.0            # skip the buy if the next open is more than 1 ATR above the signal close
HOLD_SESSIONS = 21           # time exit: sell at the close 21 sessions after the signal
NO_LONGS_WHEN_WEAK = True    # in a Weak market, log breakouts but suggest no buys

# Outcomes are measured at these horizons (sessions after the trigger close)
HORIZONS = (5, 21, 63)

# Market regime
REGIME_MIN_STAGE2_SHARE = 0.40

# Universe (India)
LIQUIDITY_MIN_VALUE = 1e7    # Rs 1 crore median daily traded value (20 sessions)
BENCHMARK = "^CRSLDX"        # Nifty 500 on Yahoo
BENCHMARK_FALLBACK = "^NSEI"  # Nifty 50

STAGE_NAMES = {1: "Basing", 2: "Advancing", 3: "Topping", 4: "Declining"}
