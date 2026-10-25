import pandas as pd

from sonar import nse


def _panel():
    d = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"])
    # AAA splits 1:2 on 5 Jan and opens at 50; NSE's prev close is not adjusted
    return pd.DataFrame({
        "date": list(d) * 2, "symbol": ["AAA"] * 4 + ["BBB"] * 4, "isin": ["x"] * 8,
        "open": [99, 100, 50, 51, 10, 10, 10, 10], "high": [101, 101, 51, 52, 11, 11, 11, 11],
        "low": [98, 99, 49, 50, 9, 9, 9, 9], "close": [100, 100, 50, 51, 10, 10.005, 10, 10],
        "prev_close": [99, 100, 100, 50, 10, 10, 10.005, 10],
        "volume": [1000, 1000, 2000, 2000, 5, 5, 5, 5], "value": [0] * 8})


def test_split_is_back_adjusted_and_rounding_ignored():
    adj = nse.adjust(_panel())
    a = adj[adj.symbol == "AAA"].set_index("date")
    assert list(a["close"]) == [50, 50, 50, 51]          # no jump at the split
    assert list(a["volume"]) == [2000, 2000, 2000, 2000]
    b = adj[adj.symbol == "BBB"]
    assert list(b["close"]) == [10, 10.005, 10, 10]      # a 0.05% mismatch is not an action


def test_both_file_formats_parse_to_the_same_columns():
    old = pd.DataFrame({"SYMBOL": ["AAA"], "SERIES": ["EQ"], "OPEN": [1], "HIGH": [2], "LOW": [1],
                        "CLOSE": [2], "LAST": [2], "PREVCLOSE": [1], "TOTTRDQTY": [10],
                        "TOTTRDVAL": [20], "TIMESTAMP": ["02-JAN-2024"], "TOTALTRADES": [1],
                        "ISIN": ["x"]})
    new = pd.DataFrame({"TradDt": ["2026-10-23"], "TckrSymb": ["AAA"], "SctySrs": ["EQ"],
                        "ISIN": ["x"], "OpnPric": [1], "HghPric": [2], "LwPric": [1], "ClsPric": [2],
                        "PrvsClsgPric": [1], "TtlTradgVol": [10], "TtlTrfVal": [20]})
    for raw in (old, new):
        out = nse.parse_bhavcopy(raw)
        assert list(out.columns) == nse.COLUMNS and out.iloc[0]["close"] == 2


def test_urls():
    from datetime import date
    assert nse.bhavcopy_url(date(2026, 10, 23)).endswith("BhavCopy_NSE_CM_0_0_0_20261023_F_0000.csv.zip")
    assert nse.bhavcopy_url(date(2024, 1, 2)).endswith("EQUITIES/2024/JAN/cm02JAN2024bhav.csv.zip")


def test_old_format_two_digit_year():
    old = pd.DataFrame({"SYMBOL": ["AAA"], "SERIES": ["EQ"], "OPEN": [1], "HIGH": [2], "LOW": [1],
                        "CLOSE": [2], "PREVCLOSE": [1], "TOTTRDQTY": [10], "TOTTRDVAL": [20],
                        "TIMESTAMP": ["13-Jul-20"], "ISIN": ["x"]})
    assert nse.parse_bhavcopy(old).iloc[0]["date"] == pd.Timestamp("2020-07-13")


def _one(opens, closes):
    d = pd.bdate_range("2026-01-01", periods=len(closes))
    return pd.DataFrame({"date": d, "symbol": "AAA", "isin": "x", "open": opens, "high": closes,
                         "low": closes, "close": closes, "prev_close": closes, "volume": 1, "value": 0})


def test_bonus_with_a_move_snaps_to_the_exact_ratio():
    # 1:1 bonus, and the stock opens 6% up on the ex-date: factor 0.5, the 6% stays
    f = nse.adjustment_factors(_one([100, 100, 53], [100, 100, 53]))
    assert list(f) == [1.0, 1.0, 0.5]
    assert nse.adjust(_one([100, 100, 53], [100, 100, 53]))["close"].round(2).tolist() == [50, 50, 53]


def test_ordinary_drop_is_not_an_action():
    assert list(nse.adjustment_factors(_one([100, 100, 82], [100, 100, 80]))) == [1.0, 1.0, 1.0]


def test_be_series_kept_and_eq_preferred():
    raw = pd.DataFrame({"TradDt": ["2026-10-23"] * 3, "TckrSymb": ["AAA", "AAA", "BBB"],
                        "SctySrs": ["BE", "EQ", "BE"], "ISIN": ["x"] * 3, "OpnPric": [1, 2, 3],
                        "HghPric": [1, 2, 3], "LwPric": [1, 2, 3], "ClsPric": [1, 2, 3],
                        "PrvsClsgPric": [1, 2, 3], "TtlTradgVol": [1, 1, 1], "TtlTrfVal": [1, 1, 1]})
    out = nse.parse_bhavcopy(raw).set_index("symbol")["close"]
    assert out.to_dict() == {"AAA": 2, "BBB": 3}


def test_old_format_without_isin():
    old = pd.DataFrame({"SYMBOL": ["AAA"], "SERIES": ["EQ"], "OPEN": [1], "HIGH": [2], "LOW": [1],
                        "CLOSE": [2], "PREVCLOSE": [1], "TOTTRDQTY": [10], "TOTTRDVAL": [20],
                        "TIMESTAMP": ["02-JAN-2006"]})
    out = nse.parse_bhavcopy(old)
    assert list(out.columns) == nse.COLUMNS and out.iloc[0]["isin"] == ""
