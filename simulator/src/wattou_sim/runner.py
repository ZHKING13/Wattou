"""Fait « vivre » un ménage simulé : mesures MQTT, commandes, programmations, vérité terrain."""

import csv
import json
import random
import time as _time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from .contract import Schedule, topic
from .household import Household

PLUGS = {"prise-tv": "tv", "prise-fer": "fer", "prise-frigo": "frigo"}
PLUG_NAMES = {"prise-tv": "Prise TV", "prise-fer": "Prise fer à repasser",
              "prise-frigo": "Prise frigo"}
STATE_EVERY_S = 10


def iso(t: datetime) -> str:
    return t.isoformat().replace("+00:00", "Z")


class Publisher(Protocol):
    async def publish(self, topic: str, payload: str, retain: bool = False) -> None: ...


class ListPublisher:
    def __init__(self):
        self.raw: list[tuple[str, str, bool]] = []

    async def publish(self, topic: str, payload: str, retain: bool = False) -> None:
        self.raw.append((topic, payload, retain))

    @property
    def messages(self) -> list[tuple[str, str]]:
        return [(t, p) for t, p, _ in self.raw if not t.endswith("/meta")]


class SimClock:
    def __init__(self, start: datetime, speed: float):
        self.start, self.speed, self._t0 = start, speed, _time.monotonic()

    def now(self) -> datetime:
        return self.start + timedelta(seconds=(_time.monotonic() - self._t0) * self.speed)


class Runner:
    def __init__(self, household: Household, foyer_id: str, publisher: Publisher,
                 truth_path: Path | str | None = None, seed: int = 1):
        self.h, self.foyer, self.pub = household, foyer_id, publisher
        names = {a.name for a in household.appliances}
        self.plugs = {d: a for d, a in PLUGS.items() if a in names}
        self.has_ac = "clim" in names
        self.plug_on = {d: True for d in self.plugs}
        self.ac_override: str | None = None
        self.ac_setpoint = 24
        self._ac_natural_prev = False
        self.schedules: dict[str, Schedule] = {}
        self._sched_done: set[tuple[str, int, str]] = set()
        self.e_kwh = 0.0
        self.last_t: datetime | None = None
        self._last_state: dict[str, tuple] = {}
        self._buffer: list[tuple[str, str]] = []
        self._rng = random.Random(f"volt-{seed}")
        self._truth = open(truth_path, "w", newline="") if truth_path else None
        if self._truth:
            self._truth_w = csv.writer(self._truth)
            self._truth_w.writerow(["ts", "appareil", "p_w"])
        self._minute: datetime | None = None
        self._acc: dict[str, float] = {}
        self._n = 0

    # --- commandes -------------------------------------------------------
    def handle_command(self, device_id: str, payload: dict) -> None:
        if device_id in self.plugs and "on" in payload:
            self.plug_on[device_id] = bool(payload["on"])
            self.h.get(self.plugs[device_id]).enabled = self.plug_on[device_id]
        elif device_id == "clim" and self.has_ac:
            if payload.get("mode"):
                self.ac_override = payload["mode"]
            if payload.get("setpoint_c") is not None:
                self.ac_setpoint = int(payload["setpoint_c"])
            self._apply_ac()

    def handle_schedule(self, device_id: str, payload: dict) -> None:
        self.schedules[device_id] = Schedule(**payload)

    def _apply_ac(self) -> None:
        clim = self.h.get("clim")
        clim.enabled = self.ac_override != "off"
        clim.forced_on = self.ac_override in ("cool", "fan")
        scale = 0.7 if self.ac_setpoint >= 27 else 1.0
        clim.scale = scale * (60 / 1100 if self.ac_override == "fan" else 1.0)

    def _ac_mode(self, t: datetime) -> str:
        if self.ac_override:
            return self.ac_override
        return "cool" if self.h.get("clim")._natural_w(t) > 0 else "off"

    def _run_schedules(self, t: datetime) -> None:
        hhmm = t.strftime("%H:%M")
        for dev, sched in self.schedules.items():
            for i, slot in enumerate(sched.slots):
                key = (dev, i, t.strftime("%Y-%m-%dT%H:%M"))
                if slot.at == hhmm and t.weekday() in slot.days and key not in self._sched_done:
                    self._sched_done.add(key)
                    self.handle_command(dev, slot.action)

    # --- simulation ------------------------------------------------------
    async def start(self) -> None:
        metas = {"meter": {"kind": "meter", "name": "Compteur", "essential": False}}
        for d, a in self.plugs.items():
            metas[d] = {"kind": "plug", "name": PLUG_NAMES[d],
                        "essential": self.h.get(a).essential}
        if self.has_ac:
            metas["clim"] = {"kind": "ir_ac", "name": "Clim salon", "essential": False}
        for d, m in metas.items():
            await self.pub.publish(topic(self.foyer, d, "meta"), json.dumps(m), retain=True)

    def _emit(self, out: list, device: str, payload: dict) -> None:
        out.append((topic(self.foyer, device, "state"), json.dumps(payload)))

    async def step(self, t: datetime) -> list[tuple[str, str]]:
        self._run_schedules(t)
        if self.has_ac:
            nat = self.h.get("clim")._natural_w(t) > 0
            if nat and not self._ac_natural_prev and self.ac_override == "off":
                self.ac_override = None
                self._apply_ac()
            self._ac_natural_prev = nat
        dt = (t - self.last_t).total_seconds() if self.last_t else 0.0
        self.last_t = t
        if self.h.is_outage(t):
            return []
        p, pf = self.h.total(t)
        self.e_kwh += p * min(dt, 60) / 3_600_000
        self._truth_add(t)
        v = 228 + max(-4.0, min(4.0, self._rng.gauss(0, 1.5)))
        out: list[tuple[str, str]] = []
        self._emit(out, "meter", {"ts": iso(t), "p_w": round(p, 1), "v": round(v, 1),
                                  "i_a": round(p / (v * pf), 3), "pf": round(pf, 3),
                                  "e_kwh": round(self.e_kwh, 5)})
        periodic = int(t.timestamp()) % STATE_EVERY_S == 0
        for d, a in self.plugs.items():
            state = (round(self.h.get(a).power_w(t), 1), self.plug_on[d])
            if periodic or self._last_state.get(d) != state:
                self._last_state[d] = state
                self._emit(out, d, {"ts": iso(t), "p_w": state[0], "on": state[1]})
        if self.has_ac:
            state = (self._ac_mode(t), self.ac_setpoint)
            if periodic or self._last_state.get("clim") != state:
                self._last_state["clim"] = state
                self._emit(out, "clim", {"ts": iso(t), "mode": state[0], "setpoint_c": state[1]})
        if self.h.is_netcut(t):
            self._buffer.extend(out)
            return []
        out, self._buffer = self._buffer + out, []
        for tp, payload in out:
            await self.pub.publish(tp, payload)
        return out

    # --- vérité terrain --------------------------------------------------
    def _truth_add(self, t: datetime) -> None:
        if not self._truth:
            return
        minute = t.replace(second=0, microsecond=0)
        if self._minute and minute != self._minute:
            self._truth_flush()
        self._minute = minute
        for name, w in self.h.breakdown(t).items():
            self._acc[name] = self._acc.get(name, 0.0) + w
        self._n += 1

    def _truth_flush(self) -> None:
        if self._n:
            for name, w in self._acc.items():
                self._truth_w.writerow([iso(self._minute), name, round(w / self._n, 3)])
        self._acc, self._n = {}, 0

    def close(self) -> None:
        if self._truth:
            self._truth_flush()
            self._truth.close()
            self._truth = None
