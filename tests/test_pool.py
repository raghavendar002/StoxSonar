import json
import importlib.util
import pathlib

import pandas as pd

_here = pathlib.Path(__file__).parent.parent / "paper"
spec = importlib.util.spec_from_file_location("intraday", _here / "intraday.py")
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
P = I.pool

from test_intraday import fake_5m, TZ  # noqa: E402

DAYS = [str(d.date()) for d in pd.bdate_range("2026-10-15", "2026-11-17")]


def daily(close, vol, n=40):
    idx = pd.date_range("2026-09-20", periods=n, freq="B", tz=TZ)
    return pd.DataFrame(dict(Open=close, High=close, Low=close, Close=close, Volume=vol), index=idx)


def test_list_and_band_filters():
    band = {"AAA": 20.0, "BBB": 5.0, "CCC": None, "FOO": 5.0}       # CCC: no band (F&O); DDD: not EQ today
    assert P.eligible(["AAA", "BBB", "CCC", "DDD", "FOO"], band, fo={"FOO", "CCC"}) == ["AAA", "CCC", "FOO"]


def test_price_turnover_and_slippage_tiers():
    b5 = {t: fake_5m(DAYS[-22:]) for t in ("BIG.NS", "MID.NS", "THIN.NS", "PENNY.NS", "FNO.NS")}
    d = {"BIG.NS": daily(1000, 1_000_000),        # Rs 100 cr a day
         "MID.NS": daily(200, 1_000_000),         # Rs 20 cr
         "THIN.NS": daily(100, 500_000),          # Rs 5 cr: out
         "PENNY.NS": daily(20, 50_000_000),       # under Rs 50: out
         "FNO.NS": daily(500, 1_000_000)}
    m = {x["sym"]: x for x in P.members(d, b5, fo={"FNO"})}
    assert set(m) == {"BIG", "MID", "FNO"}
    assert m["FNO"]["slip"] == P.SLIP_FO and m["BIG"]["slip"] == P.SLIP_MID and m["MID"]["slip"] == P.SLIP_SMALL
    assert m["BIG"]["or_vol_norm"] == 3000      # three 1,000-share opening bars


def test_pool_for_a_day_is_built_from_earlier_sessions_only(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "POOL", tmp_path)
    (tmp_path / "in").mkdir()
    for d in ("2026-11-14", "2026-11-16", "2026-11-17"):
        (tmp_path / "in" / f"{d}.json").write_text(json.dumps(dict(built_on=d, members=[])))
    assert P.load("in", "2026-11-17")["built_on"] == "2026-11-16"


def _wide_setup(monkeypatch, members):
    data = fake_5m(DAYS, spike_day="2026-11-17")
    monkeypatch.setattr(I, "bars", lambda tickers, period, interval, tz: {t: data for t in tickers})
    monkeypatch.setattr(I.pool, "load", lambda mkt, day: dict(built_on="2026-11-16", members=members))


def test_wide_scan_sees_only_the_checkpoint_and_charges_its_slippage(monkeypatch):
    _wide_setup(monkeypatch, [dict(sym="SMALL", fo=False, or_vol_norm=3000, dma20=100, slip=0.002, turnover_cr=12)])
    w = I.scan_wide("in", "2026-11-17")
    c = w["candidates"][0]
    assert w["meta"]["scanned"] == 1 and c["side"] == "long"
    assert [b[0] for b in c["bars_5m"]] == ["09:15", "09:20", "09:25"]       # nothing after 09:30
    assert c["stats"]["last"] < 101 and round(c["stats"]["relvol"], 1) == 5.0
    assert c["mechanical"]["slip"] == 0.002 and c["pool"]["fo"] is False


def test_no_shorts_outside_fo():
    v = dict(decision="SHORT", trigger=99.8, stop=100.3, target=99.0)
    assert I.check(v, 100.0, "in", fo=True) == []
    assert I.check(v, 100.0, "in", fo=False)


def test_settle_uses_each_orders_slippage():
    b = pd.DataFrame([[100, 100.1, 99.9, 100], [100.1, 100.6, 100.2, 100.5], [100.5, 101.6, 100.4, 101.5]],
                     columns=["Open", "High", "Low", "Close"],
                     index=pd.date_range("2026-11-17 09:31", periods=3, freq="1min", tz=TZ))
    o = dict(sym="X", side="long", trigger=100.5, stop=100.0, target=101.5, latest_entry="14:00", cutoff="15:15")
    cheap = I.settle_book("in", [o], {"X.NS": b}, b.index[0])["trades"][0]
    dear = I.settle_book("in", [dict(o, slip=0.002)], {"X.NS": b}, b.index[0])["trades"][0]
    assert dear["pnl"] < cheap["pnl"]


def test_shadow_mode_logs_both_pool_twins_and_debates_the_80(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "OUT", tmp_path)
    monkeypatch.setattr(I, "WIDE", "shadow")
    f80 = dict(sym="SBIN", side="long", stats={"last": 100}, bars_5m=[],
               mechanical=dict(side="long", trigger=100.1, stop=99.5, target=101.3, latest_entry="14:00", cutoff="15:15"))
    monkeypatch.setattr(I, "scan_market", lambda mkt, day=None: dict(
        meta={"date": "2026-11-17", "checkpoint": "2026-11-17 09:30:00+05:30", "index_move": 0}, candidates=[f80]))
    _wide_setup(monkeypatch, [dict(sym="SMALL", fo=False, or_vol_norm=3000, dma20=100, slip=0.002, turnover_cr=12)])
    debated = []
    monkeypatch.setattr(I, "debate", lambda mkt, s: (debated.extend(c["sym"] for c in s["candidates"]) or ([], [])))
    I.run_scan("in", day="2026-11-17")
    o = json.loads((tmp_path / "in" / "2026-11-17" / "orders.json").read_text())
    assert debated == ["SBIN"] and [x["sym"] for x in o["mechanical"]] == ["SBIN"]
    assert [x["sym"] for x in o["pools"]["f80"]] == ["SBIN"] and [x["sym"] for x in o["pools"]["wide"]] == ["SMALL"]


def test_live_mode_debates_the_wide_pool(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "OUT", tmp_path)
    monkeypatch.setattr(I, "WIDE", "live")
    monkeypatch.setattr(I, "scan_market", lambda mkt, day=None: dict(
        meta={"date": "2026-11-17", "checkpoint": "2026-11-17 09:30:00+05:30", "index_move": 0}, candidates=[]))
    _wide_setup(monkeypatch, [dict(sym="SMALL", fo=False, or_vol_norm=3000, dma20=100, slip=0.002, turnover_cr=12)])
    debated = []
    monkeypatch.setattr(I, "debate", lambda mkt, s: (debated.extend(c["sym"] for c in s["candidates"]) or ([], [])))
    I.run_scan("in", day="2026-11-17")
    assert debated == ["SMALL"]


def test_a_wide_failure_never_stops_the_day(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "OUT", tmp_path)
    monkeypatch.setattr(I, "WIDE", "shadow")
    monkeypatch.setattr(I, "scan_market", lambda mkt, day=None: dict(
        meta={"date": "2026-11-17", "checkpoint": "2026-11-17 09:30:00+05:30", "index_move": 0}, candidates=[]))
    monkeypatch.setattr(I, "scan_wide", lambda mkt, day: 1 / 0)
    monkeypatch.setattr(I, "debate", lambda mkt, s: ([], []))
    I.run_scan("in", day="2026-11-17")
    s = json.loads((tmp_path / "in" / "2026-11-17" / "scan.json").read_text())
    assert "ZeroDivisionError" in s["wide"]["meta"]["error"]
