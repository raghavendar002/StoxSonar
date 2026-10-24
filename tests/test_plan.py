from sonar import config as C
from sonar.plan import trade_plan


def test_risk_is_half_a_percent_and_capped_at_the_ceiling():
    # ATR 3% of 1000: stop 2.5 ATR = 925, ceiling 1 ATR = 1030
    p = trade_plan(1000.0, 925.0, "2026-10-23")
    assert p["qty"] == 6                       # Rs 500 / Rs 75 a share
    assert p["risk_rs"] <= C.CAPITAL_RS * C.RISK_PCT
    assert p["max_buy"] == 1030.0
    assert p["worst_risk_rs"] <= C.CAPITAL_RS * 0.0075
    assert p["exit_by"] == "2026-11-23"        # 21 weekdays later


def test_position_cap_and_bad_inputs():
    p = trade_plan(1000.0, 995.0, "2026-10-23")   # tight stop would mean 100 shares
    assert p["qty"] * 1000 <= C.CAPITAL_RS * C.MAX_POSITION_PCT
    assert trade_plan(1000.0, 1000.0, "2026-10-23") is None
    assert trade_plan(100000.0, 90000.0, "2026-10-23") is None    # one share is over the cap
