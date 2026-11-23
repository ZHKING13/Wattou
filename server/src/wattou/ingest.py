"""Worker d'ingestion : MQTT -> base. `python -m wattou.ingest`."""

import asyncio
import json
import logging
from uuid import UUID

import aiomqtt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from . import repo
from .config import Settings, get_settings
from .contract import AcState, Meta, MeterState, PlugState, parse_topic
from .db import sessionmaker

log = logging.getLogger("wattou.ingest")


class Batch:
    """Tampon d'insertions de mesures, vidé par lots (débit du rattrapage)."""

    def __init__(self):
        self.meter: dict[UUID, list[MeterState]] = {}
        self.plug: list[tuple[UUID, str, PlugState]] = []

    def __len__(self) -> int:
        return sum(len(v) for v in self.meter.values()) + len(self.plug)

    async def flush(self, session: AsyncSession) -> None:
        for foyer_id, states in self.meter.items():
            for i in range(0, len(states), 2000):
                await repo.insert_meter_batch(session, foyer_id, states[i:i + 2000])
        for foyer_id, device_id, st in self.plug:
            await repo.insert_plug(session, foyer_id, device_id, st)
        self.meter, self.plug = {}, []
_known: set[UUID] = set()


async def _foyer_ok(session: AsyncSession, foyer_id: UUID) -> bool:
    if foyer_id in _known:
        return True
    if await repo.foyer_exists(session, foyer_id):
        _known.add(foyer_id)
        return True
    return False


async def handle_message(session: AsyncSession, topic: str, payload: bytes,
                         batch: Batch | None = None) -> None:
    try:
        foyer_id, device_id, leaf = parse_topic(topic)
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("payload non objet")
    except (ValueError, UnicodeDecodeError) as e:
        log.warning("message ignoré (%s): %s", e, topic)
        return
    if not await _foyer_ok(session, foyer_id):
        log.warning("foyer inconnu %s, message ignoré", foyer_id)
        return
    try:
        if leaf == "meta":
            await repo.upsert_device(session, foyer_id, device_id, Meta(**data))
        elif leaf == "state" and "e_kwh" in data:
            st = MeterState(**data)
            st = st.model_copy(update={"p_w": abs(st.p_w), "pf": abs(st.pf)})
            if batch is None:
                await repo.insert_meter(session, foyer_id, st)
            else:
                batch.meter.setdefault(foyer_id, []).append(st)
        elif leaf == "state" and "on" in data:
            st = PlugState(**data)
            st = st.model_copy(update={"p_w": abs(st.p_w)})
            if batch is None:
                await repo.insert_plug(session, foyer_id, device_id, st)
            else:
                batch.plug.append((foyer_id, device_id, st))
            await repo.set_device_state(session, foyer_id, device_id, st.model_dump(mode="json"))
        elif leaf == "state" and "mode" in data:
            await repo.set_device_state(session, foyer_id, device_id,
                                         AcState(**data).model_dump(mode="json"))
    except ValidationError as e:
        log.warning("message ignoré (invalide): %s %s", topic, e.errors(include_url=False)[:1])


async def run_ingest(settings: Settings) -> None:
    maker = sessionmaker()
    async with aiomqtt.Client(settings.mqtt_host, settings.mqtt_port, username=settings.mqtt_user,
                              password=settings.mqtt_password) as client:
        await client.subscribe("wattou/+/+/meta", qos=1)
        await client.subscribe("wattou/+/+/state", qos=1)
        log.info("ingestion démarrée")
        batch = Batch()
        queue: asyncio.Queue = asyncio.Queue()

        async def reader():
            async for msg in client.messages:
                await queue.put((str(msg.topic), msg.payload))

        task = asyncio.create_task(reader())
        try:
            while True:
                topic, payload = await queue.get()
                async with maker() as session:
                    await handle_message(session, topic, payload, batch)
                    while not queue.empty() and len(batch) < 5000:
                        await handle_message(session, *queue.get_nowait(), batch)
                    try:
                        await batch.flush(session)
                        await session.commit()
                    except Exception:  # un lot en échec ne doit pas arrêter l'ingestion
                        log.exception("lot d'insertion en échec, ignoré")
                        await session.rollback()
                        batch = Batch()
        finally:
            task.cancel()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(run_ingest(get_settings()))
