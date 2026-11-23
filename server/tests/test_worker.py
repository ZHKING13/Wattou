import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from wattou import models as m
from wattou import repo
from wattou.contract import Meta, MeterState, PlugState
from wattou.notify import LogNotifier
from wattou.worker import analyze_foyer

T0 = datetime(2026, 11, 2, 18, tzinfo=timezone.utc)


class Pub:
    def __init__(self):
        self.sent = []

    async def publish(self, topic, payload, retain=False):
        self.sent.append((topic, json.loads(payload)))


def ms(t, p):
    return MeterState(ts=t.isoformat(), p_w=p, v=228, i_a=p / 228, pf=0.9, e_kwh=0)


async def insert_profile(session, f, minutes_power: list[tuple[int, float]], start=T0):
    rows, t = [], start
    for minutes, p in minutes_power:
        for _ in range(minutes * 60):
            rows.append(ms(t, p))
            t += timedelta(seconds=1)
    for i in range(0, len(rows), 2000):
        await repo.insert_meter_batch(session, f, rows[i:i + 2000])
    return t


async def test_clim_three_times_one_appliance(session):
    f = await repo.create_foyer(session, "T")
    profile = []
    for _ in range(3):
        profile += [(20, 50), (20, 1150)]
    profile += [(20, 50)]
    await insert_profile(session, f, profile)
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    sigs = await repo.list_appliances(session, f)
    assert len(sigs) == 1 and sigs[0].n_obs == 3 and abs(sigs[0].delta_w - 1100) < 5
    acts = (await session.execute(select(m.activations).where(m.activations.c.foyer_id == f))).all()
    assert len(acts) == 3
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    acts2 = (await session.execute(select(m.activations).where(m.activations.c.foyer_id == f))).all()
    assert len(acts2) == 3


async def test_steps_at_window_boundary_not_lost(session):
    f = await repo.create_foyer(session, "T")
    await insert_profile(session, f, [(10, 50)])
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    await insert_profile(session, f, [(10, 1150), (10, 50)], start=T0 + timedelta(minutes=10))
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    [sig] = await repo.list_appliances(session, f)
    assert sig.n_obs == 1


async def test_low_credit_triggers_command(session):
    f = await repo.create_foyer(session, "T")
    for dev, essential in (("prise-fer", False), ("prise-frigo", True)):
        await repo.upsert_device(session, f, dev, Meta(kind="plug", name=dev, essential=essential))
        state = PlugState(ts=T0.isoformat(), p_w=100, on=True).model_dump()
        await repo.set_device_state(session, f, dev, state)
    await repo.add_credit_entry(session, f, T0, "reading", 1.0, None)
    await insert_profile(session, f, [(120, 333)])
    pub, notifier = Pub(), LogNotifier()
    await repo.add_push_token(session, f, "ExponentPushToken[x]")
    await analyze_foyer(session, pub, notifier, f)
    assert (f"wattou/{f}/prise-fer/cmd", {"on": False}) in pub.sent
    assert not any("prise-frigo" in t for t, _ in pub.sent)
    assert any("crédit" in body for _, _, body in notifier.sent)


async def test_outage_alert_from_gap(session):
    f = await repo.create_foyer(session, "T")
    end = await insert_profile(session, f, [(5, 100)])
    await insert_profile(session, f, [(5, 100)], start=end + timedelta(minutes=30))
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    alerts = await repo.list_alerts(session, f)
    assert [a["kind"] for a in alerts] == ["outage"]


async def test_no_peak_alert_without_history(session):
    f = await repo.create_foyer(session, "T")
    await insert_profile(session, f, [(60, 50), (60, 1500), (30, 50)], start=T0.replace(hour=1))
    await analyze_foyer(session, Pub(), LogNotifier(), f)
    assert [a["kind"] for a in await repo.list_alerts(session, f) if a["kind"] == "peak"] == []
