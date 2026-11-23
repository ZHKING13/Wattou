"""Publication des commandes et programmations vers les appareils (MQTT)."""

from typing import Protocol
from uuid import UUID

import aiomqtt

from .contract import AcCmd, PlugCmd, Schedule, topic


class Publisher(Protocol):
    async def publish(self, topic: str, payload: str, retain: bool = False) -> None: ...


class MqttPublisher:
    def __init__(self, client: aiomqtt.Client):
        self.client = client

    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        await self.client.publish(topic, payload, qos=1, retain=retain)


async def send_command(pub: Publisher, foyer_id: UUID, device_id: str, cmd: PlugCmd | AcCmd) -> None:
    await pub.publish(topic(str(foyer_id), device_id, "cmd"), cmd.model_dump_json(exclude_none=True))


async def set_schedule(pub: Publisher, foyer_id: UUID, device_id: str, schedule: Schedule) -> None:
    await pub.publish(topic(str(foyer_id), device_id, "schedule"), schedule.model_dump_json(),
                      retain=True)
