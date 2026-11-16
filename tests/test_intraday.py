import json
import pandas as pd
import importlib.util, pathlib

spec = importlib.util.spec_from_file_location("intraday", pathlib.Path(__file__).parent.parent / "paper" / "intraday.py")
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)

TZ = "Asia/Kolkata"


def mk(rows, start="2026-11-16 09:31"):
    idx = pd.date_range(start, periods=len(rows), freq="1min", tz=TZ)
    return pd.DataFrame(rows, columns=["Open", "High", "Low", "Close"], index=idx)


def order(side, trig, stop, tgt):
    return dict(sym="X", side=side, trigger=trig, stop=stop, target=tgt, latest_entry="14:00", cutoff="15:15")


def test_long_target():
    b = mk([[100, 100.1, 99.9, 100], [100.1, 100.6, 100.2, 100.5], [100.5, 101.6, 100.4, 101.5]])
    r = I.simulate(order("long", 100.5, 100.0, 101.5), b, b.index[0], 0)
    assert r["status"] == "closed" and r["reason"] == "target" and r["entry"] == 100.5


def test_short_stop_same_bar_is_conservative():
    b = mk([[100, 100.2, 99.8, 100], [99.9, 100.6, 99.4, 100.1]])
    r = I.simulate(order("short", 99.5, 100.5, 98.0), b, b.index[0], 0)
    assert r["reason"] == "stop_same_bar"


def test_stale_entry_skipped():
    b = mk([[101.0, 101.2, 100.9, 101.1]])
    assert I.simulate(order("long", 100.5, 100.0, 101.5), b, b.index[0], 0)["status"] == "stale"


def test_not_triggered_and_time_exit():
    b = mk([[100, 100.1, 99.9, 100]] * 3)
    assert I.simulate(order("long", 101, 100, 103), b, b.index[0], 0)["status"] == "not_triggered"
    b = mk([[100.6, 101.1, 100.5, 101]] + [[101, 101.2, 100.8, 101.1]] * 3, start="2026-11-16 15:12")
    r = I.simulate(dict(order("long", 101, 100, 104), latest_entry="15:20"), b, b.index[0], 0)
    assert r["reason"] == "time" and r["exit"] == 101.1


def test_india_costs_about_quarter_r():
    c = I.costs("in", 100.0, 100.0, 625)          # Rs 62,500 position
    assert 55 < c < 80


def test_check_rules():
    v = dict(decision="LONG", trigger=100.2, stop=99.7, target=101.0)
    assert I.check(v, 100.0, "in") == []
    assert I.check(dict(v, target=100.5), 100.0, "in")            # under 1.5R
    assert I.check(dict(v, decision="SHORT", stop=100.7, target=99.0), 100.0, "us")  # US cannot short
    assert I.check(dict(v, trigger=101.5, stop=101.0, target=102.5), 100.0, "in")   # too far


def test_debate_with_fake_caller(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "SPEND", tmp_path / "spend.json")

    class R:
        def __init__(self, text): self.text, self.cost_usd = text, 0.01

    def fake(model, shared, instruction, effort, schema=None, system=None):
        if schema:
            return R(json.dumps(dict(decision="LONG", side_if_traded="long", trigger=100.2, stop=99.7, target=101.0,
                                     conviction=4, headline="h", title="t", text="x")))
        return R("argument")

    scan = dict(meta={"index_move": 0.001}, candidates=[dict(sym="X", side="long", stats={"last": 100.0},
                                                               mechanical={}, bars_5m=[])])
    talks, orders = I.debate("in", scan, caller=fake)
    assert orders[0]["side"] == "long" and orders[0]["leverage"] == 2
    assert json.loads((tmp_path / "spend.json").read_text())


def fake_5m(days, n=75, spike_day=None):
    """n 5-minute bars a day from 09:15; volume spikes and price breaks out on spike_day's open."""
    frames = []
    for d in days:
        idx = pd.date_range(f"{d} 09:15", periods=n, freq="5min", tz=TZ)
        up = 1.0 if d == spike_day else 0.0
        close = [100 + up * (0.2 * min(i, 2) + 5 * (i >= 3)) for i in range(n)]   # big move only after the checkpoint
        frames.append(pd.DataFrame(dict(Open=close, High=[c + 0.05 for c in close], Low=[c - 0.05 for c in close],
                                        Close=close, Volume=[(5000 if up and i < 3 else 1000) for i in range(n)]),
                                   index=idx))
    return pd.concat(frames)


def test_a_replayed_scan_sees_only_what_an_on_time_scan_saw(monkeypatch):
    days = [str(d.date()) for d in pd.bdate_range("2026-10-15", "2026-11-17")]
    data = fake_5m(days, spike_day="2026-11-17")

    def bars(tickers, period, interval, tz):
        if interval == "1d":
            return {}
        return {t: data for t in tickers}
    monkeypatch.setattr(I, "bars", bars)
    monkeypatch.setitem(I.MKT, "in", dict(I.MKT["in"], tickers=["AAA.NS"]))
    s = I.scan_market("in", day="2026-11-17")
    assert s["meta"]["date"] == "2026-11-17" and s["meta"]["checkpoint"].startswith("2026-11-17 09:30")
    c = s["candidates"][0]
    assert [b[0] for b in c["bars_5m"]] == ["09:15", "09:20", "09:25"]      # nothing after the checkpoint
    assert c["stats"]["last"] < 101                                            # the later +5 move is invisible
    # a holiday or a day with no bars is refused, never rescanned from an older session
    try:
        I.scan_market("in", day="2026-11-18")
        assert False
    except I.NoSession:
        pass


def test_late_scans_replay_and_done_days_are_not_redone(tmp_path, monkeypatch):
    early = pd.Timestamp("2026-11-17 09:40", tz=TZ).tz_convert("UTC")
    late = pd.Timestamp("2026-11-17 09:50", tz=TZ).tz_convert("UTC")
    assert I.late_day("in", early) is None and str(I.late_day("in", late)) == "2026-11-17"
    monkeypatch.setattr(I, "OUT", tmp_path)
    (tmp_path / "in" / "2026-11-17").mkdir(parents=True)
    (tmp_path / "in" / "2026-11-17" / "orders.json").write_text("{}")
    monkeypatch.setattr(I, "scan_market", lambda *a, **k: (_ for _ in ()).throw(AssertionError("rescanned")))
    assert I.run_scan("in", day="2026-11-17") is None
