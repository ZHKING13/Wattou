import json
from uuid import UUID

from wattou.contract import PlugCmd, Schedule
from wattou.control import send_command, set_schedule

F = UUID("00000000-0000-0000-0000-000000000001")


class Pub:
    def __init__(self):
        self.sent = []

    async def publish(self, topic, payload, retain=False):
        self.sent.append((topic, json.loads(payload), retain))


async def test_command_published():
    p = Pub()
    await send_command(p, F, "prise-fer", PlugCmd(on=False))
    assert p.sent == [(f"wattou/{F}/prise-fer/cmd", {"on": False}, False)]


async def test_schedule_published_retained():
    p = Pub()
    s = Schedule(slots=[{"at": "06:00", "days": [0, 1], "action": {"mode": "off"}}])
    await set_schedule(p, F, "clim", s)
    topic, payload, retain = p.sent[0]
    assert topic == f"wattou/{F}/clim/schedule" and retain is True
    assert payload["slots"][0]["at"] == "06:00"
