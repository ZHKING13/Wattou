"""CLI : python -m wattou_sim --foyer <uuid> [--speed 60] [--backfill-days 14] ..."""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import aiomqtt

from .household import FridgeStuck, NeighborTap, NetCut, Outage, abidjan_household
from .runner import Runner, SimClock

log = logging.getLogger("wattou_sim")
SCENARIOS = {"neighbor_tap": NeighborTap, "outage": Outage, "netcut": NetCut}


def parse_dt(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_scenario(spec: str):
    name, _, when = spec.partition("@")
    if name == "fridge_stuck":
        return FridgeStuck(parse_dt(when))
    start, _, end = when.partition("/")
    return SCENARIOS[name](parse_dt(start), parse_dt(end))


class BatchingPublisher:
    """Publie en QoS 1 sans attendre chaque accusé : envois groupés par lots concurrents."""

    def __init__(self, client, batch: int = 500):
        self.client, self.batch = client, batch
        self._pending: list = []

    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self._pending.append(self.client.publish(topic, payload, qos=1, retain=retain))
        if len(self._pending) >= self.batch:
            await self.flush()

    async def flush(self) -> None:
        pending, self._pending = self._pending, []
        if pending:
            await asyncio.gather(*pending)


async def listen(client: aiomqtt.Client, runner: Runner, foyer: str) -> None:
    await client.subscribe(f"wattou/{foyer}/+/cmd")
    await client.subscribe(f"wattou/{foyer}/+/schedule")
    async for msg in client.messages:
        parts = str(msg.topic).split("/")
        try:
            payload = json.loads(msg.payload)
        except ValueError:
            continue
        if parts[3] == "cmd":
            runner.handle_command(parts[2], payload)
        else:
            runner.handle_schedule(parts[2], payload)
        log.info("%s %s %s", parts[2], parts[3], payload)


async def main(args) -> None:
    h = abidjan_household(seed=args.seed)
    for s in args.scenario:
        h.add_scenario(parse_scenario(s))
    async with aiomqtt.Client(args.host, args.port, username=args.user,
                              password=args.password, max_queued_outgoing_messages=0,
                              max_inflight_messages=1000) as client:
        pub = BatchingPublisher(client)
        runner = Runner(h, args.foyer, pub, truth_path=args.truth,
                        seed=args.seed)
        await runner.start()
        await pub.flush()
        listener = asyncio.create_task(listen(client, runner, args.foyer))
        t = parse_dt(args.start)
        try:
            end_backfill = t + timedelta(days=args.backfill_days)
            while t < end_backfill:
                await runner.step(t)
                t += timedelta(seconds=1)
                if int(t.timestamp()) % 3600 == 0:
                    log.info("backfill %s", t.isoformat())
            await pub.flush()
            clock = SimClock(t, args.speed)
            while args.until is None or t < parse_dt(args.until):
                while t < clock.now():
                    await runner.step(t)
                    t += timedelta(seconds=1)
                await pub.flush()
                await asyncio.sleep(0.05)
            await pub.flush()
        finally:
            listener.cancel()
            runner.close()


def cli() -> None:
    p = argparse.ArgumentParser(prog="wattou_sim")
    p.add_argument("--foyer", required=True)
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=1883)
    p.add_argument("--user", default="device")
    p.add_argument("--password", default="device")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--start", default=datetime.now(timezone.utc).replace(
        microsecond=0).isoformat())
    p.add_argument("--backfill-days", type=float, default=0)
    p.add_argument("--until", default=None)
    p.add_argument("--scenario", action="append", default=[])
    p.add_argument("--truth", default=None)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    asyncio.run(main(args))


if __name__ == "__main__":
    cli()
