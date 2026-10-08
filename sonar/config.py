"""Rule settings for the public StoxSonar list.

Values follow the StoxSonar Stock Segregation Rules Spec. Changing any of them
changes what the engine says, so bump ENGINE_VERSION whenever one changes; the
track record is only reported per engine version.
"""

ENGINE_VERSION = "0.1.0"

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
TRIGGER_CLEARANCE = 0.005    # close beyond pivot by 0.5%
TRIGGER_VOLUME = 1.5         # x 50-day average volume
MAX_WICK = 0.25              # wick against the move, share of day's range

# Lifecycle
LIFECYCLE_SESSIONS = 10
EXTENDED_PCT = 0.05
FAIL_PCT = 0.03

# Outcomes are measured at these horizons (sessions after the trigger close)
HORIZONS = (5, 21, 63)

# Market regime
REGIME_MIN_STAGE2_SHARE = 0.40

# Universe (India)
LIQUIDITY_MIN_VALUE = 1e7    # Rs 1 crore median daily traded value (20 sessions)
BENCHMARK = "^CRSLDX"        # Nifty 500 on Yahoo
BENCHMARK_FALLBACK = "^NSEI"  # Nifty 50

STAGE_NAMES = {1: "Basing", 2: "Advancing", 3: "Topping", 4: "Declining"}
