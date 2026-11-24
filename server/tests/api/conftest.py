import json
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from wattou import repo
from wattou.api.app import create_app
from wattou.api.deps import get_publisher, get_session
from wattou.contract import MeterState

T0 = datetime(2026, 11, 2, 18, tzinfo=timezone.utc)


class Pub:
    def __init__(self):
        self.sent = []

    async def publish(self, topic, payload, retain=False):
        self.sent.append((topic, json.loads(payload), retain))


@pytest.fixture
def pub():
    return Pub()


@pytest.fixture
async def client(session, pub):
    app = create_app(with_mqtt=False)

    async def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_publisher] = lambda: pub
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t/api/v1") as c:
        yield c


async def register(client, phone="+2250700000001"):
    r = await client.post("/auth/register", json={"phone": phone, "password": "secret1",
                                                   "foyer_name": "Chez moi"})
    assert r.status_code == 201, r.text
    body = r.json()
    return {"Authorization": f"Bearer {body['token']}"}, body["foyer_id"]


async def feed(session, foyer_id, minutes, p, start=T0):
    rows = [MeterState(ts=(start + timedelta(seconds=s)).isoformat(), p_w=p, v=228, i_a=1, pf=0.9,
                       e_kwh=0) for s in range(minutes * 60)]
    for i in range(0, len(rows), 2000):
        await repo.insert_meter_batch(session, foyer_id, rows[i:i + 2000])
