import csv
import json
from datetime import datetime, timedelta, timezone

from wattou_sim.appliances import Constant
from wattou_sim.contract import AcState, MeterState
from wattou_sim.household import Household, NetCut, Outage, abidjan_household
from wattou_sim.runner import ListPublisher, Runner

FOYER = "00000000-0000-0000-0000-000000000001"
T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def meter_msgs(msgs):
    return [json.loads(p) for t, p in msgs if t.endswith("/meter/state")]


async def run(runner, start, seconds):
    for s in range(seconds):
        await runner.step(start + timedelta(seconds=s))


async def test_meter_message_each_second():
    pub = ListPublisher()
    r = Runner(abidjan_household(), FOYER, pub)
    await run(r, T0, 10)
    msgs = meter_msgs(pub.messages)
    assert len(msgs) == 10
    for m in msgs:
        MeterState(**m)


async def test_meta_published_retained_on_start():
    pub = ListPublisher()
    r = Runner(abidjan_household(), FOYER, pub)
    await r.start()
    metas = {t: retain for t, p, retain in pub.raw if t.endswith("/meta")}
    assert f"wattou/{FOYER}/meter/meta" in metas and all(metas.values())
    assert len(metas) == 5


async def test_energy_accumulates():
    pub = ListPublisher()
    r = Runner(Household([Constant("radiateur", 1000, pf=1.0)]), FOYER, pub)
    await run(r, T0, 3601)
    assert abs(meter_msgs(pub.messages)[-1]["e_kwh"] - 1.0) < 0.005


async def test_plug_cmd_off_cuts_power():
    h = abidjan_household()
    pub = ListPublisher()
    r = Runner(h, FOYER, pub)
    fer = h.get("fer")
    t = next(T0 + timedelta(seconds=s) for s in range(86400) if fer.power_w(T0 + timedelta(seconds=s)) > 0)
    before = h.total(t)[0]
    r.handle_command("prise-fer", {"on": False})
    assert abs(before - h.total(t)[0] - 1000) < 1e-6


async def test_schedule_executes_at_sim_time():
    h = abidjan_household()
    pub = ListPublisher()
    r = Runner(h, FOYER, pub)
    r.handle_schedule("clim", {"slots": [{"at": "06:00", "action": {"mode": "off"}}]})
    r.handle_command("clim", {"mode": "cool"})
    await run(r, T0.replace(hour=5, minute=59, second=55), 10)
    states = [json.loads(p) for t, p in pub.messages if t.endswith("/clim/state")]
    AcState(**states[-1])
    assert states[-1]["mode"] == "off"


async def test_outage_publishes_nothing():
    h = abidjan_household()
    h.add_scenario(Outage(T0, T0 + timedelta(minutes=5)))
    pub = ListPublisher()
    await run(Runner(h, FOYER, pub), T0, 60)
    assert pub.messages == []


async def test_netcut_replays_buffer():
    h = abidjan_household()
    h.add_scenario(NetCut(T0, T0 + timedelta(seconds=30)))
    pub = ListPublisher()
    r = Runner(h, FOYER, pub)
    await run(r, T0, 30)
    assert pub.messages == []
    await r.step(T0 + timedelta(seconds=30))
    ts = [m["ts"] for m in meter_msgs(pub.messages)]
    assert len(ts) == 31
    assert ts[0] == T0.isoformat().replace("+00:00", "Z")


async def test_truth_csv_matches_breakdown(tmp_path):
    h = abidjan_household()
    path = tmp_path / "truth.csv"
    r = Runner(h, FOYER, ListPublisher(), truth_path=path)
    start = T0.replace(hour=19, minute=30)
    await run(r, start, 121)
    r.close()
    rows = list(csv.DictReader(open(path)))
    first = start.isoformat().replace("+00:00", "Z")
    minute = [float(x["p_w"]) for x in rows if x["ts"] == first]
    expected = sum(h.total(start + timedelta(seconds=s))[0] for s in range(60)) / 60
    assert abs(sum(minute) - expected) < 0.01
