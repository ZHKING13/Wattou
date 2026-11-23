from datetime import UTC, datetime, timedelta

from wattou import repo
from wattou.contract import Meta, MeterState

T0 = datetime(2026, 11, 2, tzinfo=UTC)


def ms(t, p=1000.0):
    return MeterState(ts=t.isoformat(), p_w=p, v=228, i_a=p / 228, pf=1.0, e_kwh=0)


async def test_insert_meter_idempotent(session):
    f = await repo.create_foyer(session, "Test")
    await repo.insert_meter(session, f, ms(T0))
    await repo.insert_meter(session, f, ms(T0))
    assert len(await repo.meter_samples(session, f, T0 - timedelta(1), T0 + timedelta(1))) == 1


async def test_meter_samples_ordered(session):
    f = await repo.create_foyer(session, "Test")
    for s in (3, 1, 2):
        await repo.insert_meter(session, f, ms(T0 + timedelta(seconds=s), p=s))
    samples = await repo.meter_samples(session, f, T0, T0 + timedelta(minutes=1))
    assert [x.p_w for x in samples] == [1, 2, 3]
    assert await repo.latest_ts(session, f) == T0 + timedelta(seconds=3)


async def test_energy_by_bucket_hour(session):
    f = await repo.create_foyer(session, "Test")
    await repo.insert_meter_batch(session, f, [ms(T0 + timedelta(seconds=s)) for s in range(3600)])
    buckets = await repo.energy_by_bucket(session, f, T0, T0 + timedelta(hours=1), "hour")
    assert len(buckets) == 1 and abs(buckets[0][1] - 1.0) < 1e-6


async def test_add_alert_dedup(session):
    f = await repo.create_foyer(session, "Test")
    assert await repo.add_alert(session, f, T0, "credit_low", "msg", "k1") is True
    assert await repo.add_alert(session, f, T0, "credit_low", "msg", "k1") is False


async def test_upsert_device_and_views(session):
    f = await repo.create_foyer(session, "Test")
    await repo.upsert_device(session, f, "prise-frigo", Meta(kind="plug", name="Frigo", essential=True))
    await repo.upsert_device(session, f, "prise-frigo", Meta(kind="plug", name="Frigo 2", essential=True))
    await repo.set_device_state(session, f, "prise-frigo", {"on": True, "p_w": 120})
    [d] = await repo.device_views(session, f)
    assert (d.id, d.kind, d.essential, d.last_state["on"]) == ("prise-frigo", "plug", True, True)


async def test_first_ts(session):
    f = await repo.create_foyer(session, "Test")
    assert await repo.first_ts(session, f) is None
    for s in (5, 2, 9):
        await repo.insert_meter(session, f, ms(T0 + timedelta(seconds=s)))
    assert await repo.first_ts(session, f) == T0 + timedelta(seconds=2)


async def test_energy_is_time_weighted_when_messages_are_lost(session):
    f = await repo.create_foyer(session, "Test")
    await repo.insert_meter_batch(session, f, [ms(T0 + timedelta(seconds=s)) for s in range(0, 3600, 2)])
    assert abs(await repo.energy_between(session, f, T0 - timedelta(seconds=1), T0 + timedelta(hours=1))
               - 1.0) < 0.001
    [(_, kwh)] = await repo.energy_by_bucket(session, f, T0, T0 + timedelta(hours=1), "hour")
    assert abs(kwh - 1.0) < 0.001
    assert abs(await repo.coverage_between(session, f, T0, T0 + timedelta(hours=1)) - 0.5) < 0.01
