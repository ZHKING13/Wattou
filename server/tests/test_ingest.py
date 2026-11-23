import json
import logging
from datetime import datetime, timedelta, timezone

from wattou import repo
from wattou.ingest import handle_message

T0 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def meter(p=500.0, pf=0.9):
    return json.dumps({"ts": "2026-11-02T00:00:00Z", "p_w": p, "v": 228, "i_a": 2.4,
                       "pf": pf, "e_kwh": 1.2}).encode()


async def test_meter_state_stored(session):
    f = await repo.create_foyer(session, "T")
    await handle_message(session, f"wattou/{f}/meter/state", meter())
    [s] = await repo.meter_samples(session, f, T0 - timedelta(1), T0 + timedelta(1))
    assert s.p_w == 500.0


async def test_meta_creates_device(session):
    f = await repo.create_foyer(session, "T")
    meta = {"kind": "plug", "name": "Prise frigo", "essential": True}
    await handle_message(session, f"wattou/{f}/prise-frigo/meta", json.dumps(meta).encode())
    [d] = await repo.device_views(session, f)
    assert (d.id, d.essential) == ("prise-frigo", True)


async def test_plug_state_updates_last_state(session):
    f = await repo.create_foyer(session, "T")
    meta = {"kind": "plug", "name": "Prise fer", "essential": False}
    await handle_message(session, f"wattou/{f}/prise-fer/meta", json.dumps(meta).encode())
    st = {"ts": "2026-11-02T00:00:00Z", "p_w": 1000, "on": True}
    await handle_message(session, f"wattou/{f}/prise-fer/state", json.dumps(st).encode())
    [d] = await repo.device_views(session, f)
    assert d.last_state["on"] is True and d.last_state["p_w"] == 1000


async def test_unknown_foyer_ignored(session, caplog):
    caplog.set_level(logging.WARNING)
    await handle_message(session, "wattou/11111111-1111-1111-1111-111111111111/meter/state", meter())
    assert "inconnu" in caplog.text


async def test_invalid_json_ignored(session, caplog):
    f = await repo.create_foyer(session, "T")
    caplog.set_level(logging.WARNING)
    await handle_message(session, f"wattou/{f}/meter/state", b"{pas du json")
    await handle_message(session, "n/importe/quoi", b"{}")
    assert await repo.latest_ts(session, f) is None
    assert caplog.text.count("ignoré") == 2


async def test_negative_power_made_absolute(session):
    f = await repo.create_foyer(session, "T")
    await handle_message(session, f"wattou/{f}/meter/state", meter(p=-850.0, pf=-0.9))
    [s] = await repo.meter_samples(session, f, T0 - timedelta(1), T0 + timedelta(1))
    assert (s.p_w, s.pf) == (850.0, 0.9)


async def test_batch_buffers_meter_until_flush(session):
    from wattou.ingest import Batch

    f = await repo.create_foyer(session, "T")
    batch = Batch()
    for s in range(5):
        p = json.dumps({"ts": f"2026-11-02T00:00:0{s}Z", "p_w": 100, "v": 228, "i_a": 0.4,
                        "pf": 1, "e_kwh": 0}).encode()
        await handle_message(session, f"wattou/{f}/meter/state", p, batch)
    assert await repo.latest_ts(session, f) is None
    await batch.flush(session)
    assert len(await repo.meter_samples(session, f, T0 - timedelta(1), T0 + timedelta(1))) == 5
    assert len(batch) == 0
