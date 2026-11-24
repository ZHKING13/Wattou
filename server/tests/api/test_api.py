from uuid import UUID

from wattou import repo
from wattou.contract import Meta

from .conftest import T0, feed, register


async def test_register_login(client):
    await register(client)
    r = await client.post("/auth/login", json={"phone": "+2250700000001", "password": "secret1"})
    assert r.status_code == 200 and r.json()["token"]
    bad = await client.post("/auth/login", json={"phone": "+2250700000001", "password": "nope"})
    assert bad.status_code == 401


async def test_register_short_password_rejected(client):
    r = await client.post("/auth/register", json={"phone": "1", "password": "123", "foyer_name": "x"})
    assert r.status_code == 422


async def test_requires_auth(client):
    assert (await client.get("/foyer/summary")).status_code == 401


async def test_summary_without_credit_returns_nulls(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 10, 600)
    s = (await client.get("/foyer/summary", headers=h)).json()
    assert s["credit_kwh"] is None and s["days_left"] is None and s["credit_fcfa"] is None
    assert s["power_w"] == 600 and abs(s["today_kwh"] - 0.1) < 1e-6
    assert s["foyer_name"] == "Chez moi"
    assert s["price_fcfa_kwh"] == 110


async def test_summary_empty_foyer(client):
    h, _ = await register(client)
    s = (await client.get("/foyer/summary", headers=h)).json()
    assert s["power_w"] == 0 and s["today_kwh"] == 0


async def test_credit_reading_and_recharge(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 10, 600)
    r = await client.post("/foyer/credit", headers=h, json={"kind": "reading", "kwh": 50})
    assert r.status_code == 201
    r = await client.post("/foyer/credit", headers=h,
                          json={"kind": "recharge", "kwh": 80, "amount_fcfa": 10000})
    assert r.status_code == 201
    s = (await client.get("/foyer/summary", headers=h)).json()
    assert s["credit_kwh"] == 130 and s["price_fcfa_kwh"] == 125


async def test_credit_reading_increase_rejected_422(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 1, 600)
    await client.post("/foyer/credit", headers=h, json={"kind": "reading", "kwh": 50})
    r = await client.post("/foyer/credit", headers=h, json={"kind": "reading", "kwh": 60})
    assert r.status_code == 422
    assert "plus élevé que le précédent" in r.json()["detail"]


async def test_recharge_requires_amount(client):
    h, _ = await register(client)
    r = await client.post("/foyer/credit", headers=h, json={"kind": "recharge", "kwh": 40})
    assert r.status_code == 422


async def test_appliances_marked_estimated(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 60, 300)
    items = (await client.get("/foyer/appliances?period=day", headers=h)).json()
    ids = {i["id"] for i in items}
    assert {"fond", "autres"} <= ids
    assert all(i["estimated"] is True for i in items)
    assert abs(sum(i["kwh"] for i in items) - 0.3) < 1e-6


async def test_history_hourly(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 60, 1000)
    r = await client.get("/foyer/history", headers=h,
                         params={"from": T0.isoformat(), "to": (T0.replace(hour=20)).isoformat(),
                                 "step": "hour"})
    assert [round(x["kwh"], 6) for x in r.json()] == [1.0]


async def test_absence_and_rules(client, session):
    h, f = await register(client)
    await feed(session, UUID(f), 1, 100)
    assert (await client.put("/foyer/absence", headers=h, json={"enabled": True})).status_code == 200
    foyer = await repo.get_foyer(session, UUID(f))
    assert foyer["absence_mode"] and foyer["absence_since"] is not None
    assert (await client.put("/foyer/rules", headers=h, json={"low_credit_days": 3})).status_code == 200
    assert (await client.put("/foyer/rules", headers=h, json={"low_credit_days": 20})).status_code == 422


async def test_rename_appliance(client, session):
    h, f = await register(client)
    from uuid import uuid4

    from wattou.analysis.types import ApplianceSig
    sig = ApplianceSig(uuid4(), None, 1100, 0.9, 5)
    await repo.save_appliances(session, UUID(f), [sig])
    r = await client.patch(f"/appliances/{sig.id}", headers=h, json={"label": "Clim"})
    assert r.status_code == 200
    assert (await repo.list_appliances(session, UUID(f)))[0].label == "Clim"
    await feed(session, UUID(f), 1, 100)
    items = (await client.get("/foyer/appliances", headers=h)).json()
    clim = next(i for i in items if i["id"] == str(sig.id))
    assert clim["label"] == "Clim" and clim["power_w"] == 1100


async def test_command_published(client, session, pub):
    h, f = await register(client)
    await repo.upsert_device(session, UUID(f), "prise-fer", Meta(kind="plug", name="Fer"))
    r = await client.post("/devices/prise-fer/command", headers=h, json={"on": False})
    assert r.status_code == 202
    assert pub.sent == [(f"wattou/{f}/prise-fer/cmd", {"on": False}, False)]
    assert (await client.post("/devices/inconnu/command", headers=h, json={"on": False})).status_code == 404


async def test_schedule_roundtrip(client, session, pub):
    h, f = await register(client)
    await repo.upsert_device(session, UUID(f), "clim", Meta(kind="ir_ac", name="Clim"))
    sched = {"slots": [{"at": "06:00", "days": [0, 1, 2, 3, 4], "action": {"mode": "off"}}]}
    assert (await client.put("/devices/clim/schedule", headers=h, json=sched)).status_code == 200
    assert (await client.get("/devices/clim/schedule", headers=h)).json()["slots"][0]["at"] == "06:00"
    assert pub.sent[0][2] is True


async def test_foyer_isolation(client, session):
    _, f1 = await register(client, "+2250700000001")
    h2, _ = await register(client, "+2250700000002")
    await repo.add_alert(session, UUID(f1), T0, "outage", "msg", "k")
    [a] = await repo.list_alerts(session, UUID(f1))
    assert (await client.get("/alerts", headers=h2)).json() == []
    assert (await client.post(f"/alerts/{a['id']}/read", headers=h2)).status_code == 404


async def test_push_token(client, session):
    h, f = await register(client)
    r = await client.post("/push-tokens", headers=h, json={"token": "ExponentPushToken[x]"})
    assert r.status_code == 201
    assert await repo.push_tokens(session, UUID(f)) == ["ExponentPushToken[x]"]


async def test_appliance_running_now_counted(client, session):
    from datetime import timedelta
    from uuid import uuid4

    from wattou.analysis.types import Activation, ApplianceSig

    h, f = await register(client)
    sig = ApplianceSig(uuid4(), "Clim", 1100, 0.9, 10)
    await repo.save_appliances(session, UUID(f), [sig])
    await feed(session, UUID(f), 60, 1150)
    running = Activation(T0 + timedelta(minutes=30), None, 1100, 0.9)
    await repo.set_analysis_state(session, UUID(f), T0 + timedelta(minutes=59), [running])
    items = (await client.get("/foyer/appliances?period=day", headers=h)).json()
    clim = next(i for i in items if i["label"] == "Clim")
    assert abs(clim["kwh"] - 0.55) < 0.01
