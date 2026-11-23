"""Modèles d'appareils électriques d'un ménage (puissance en fonction du temps)."""

import random
from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta


def _rng(*parts) -> random.Random:
    # str seed => déterministe entre processus (contrairement à hash())
    return random.Random("-".join(str(p) for p in parts))


class Appliance(ABC):
    def __init__(self, name: str, pf: float, essential: bool = False):
        self.name = name
        self.pf = pf
        self.essential = essential
        self.enabled = True  # coupé par une prise connectée si False
        self.scale = 1.0  # ex. clim à consigne élevée
        self.forced_on = False  # scénario « frigo bloqué »

    def power_w(self, t: datetime) -> float:
        if not self.enabled:
            return 0.0
        if self.forced_on:
            return self.nominal_w() * self.scale
        return self._natural_w(t) * self.scale

    @abstractmethod
    def _natural_w(self, t: datetime) -> float: ...

    @abstractmethod
    def nominal_w(self) -> float: ...


class Constant(Appliance):
    def __init__(self, name: str, w: float, pf: float, essential: bool = False):
        super().__init__(name, pf, essential)
        self.w = w

    def nominal_w(self) -> float:
        return self.w

    def _natural_w(self, t: datetime) -> float:
        return self.w


class Cyclic(Appliance):
    def __init__(self, name, on_w, on_s, off_s, pf, essential=True, offset_s=0):
        super().__init__(name, pf, essential)
        self.on_w, self.on_s, self.off_s, self.offset_s = on_w, on_s, off_s, offset_s

    def nominal_w(self) -> float:
        return self.on_w

    def _natural_w(self, t: datetime) -> float:
        phase = (t.timestamp() + self.offset_s) % (self.on_s + self.off_s)
        return self.on_w if phase < self.on_s else 0.0


class Scheduled(Appliance):
    def __init__(self, name, on_w, windows: list[tuple[time, time]], pf,
                 jitter_min: float = 15, seed: int = 0, essential: bool = False):
        super().__init__(name, pf, essential)
        self.on_w, self.windows, self.jitter_min, self.seed = on_w, windows, jitter_min, seed

    def nominal_w(self) -> float:
        return self.on_w

    def _bounds(self, d: date, i: int) -> tuple[datetime, datetime]:
        start, end = self.windows[i]
        r = _rng(self.seed, self.name, d.isoformat(), i)
        js = timedelta(minutes=r.uniform(-self.jitter_min, self.jitter_min))
        je = timedelta(minutes=r.uniform(-self.jitter_min, self.jitter_min))
        s = datetime.combine(d, start, tzinfo=self._tz) + js
        end_day = d if end > start else d + timedelta(days=1)
        e = datetime.combine(end_day, end, tzinfo=self._tz) + je
        return s, e

    def _natural_w(self, t: datetime) -> float:
        self._tz = t.tzinfo
        for d in (t.date(), t.date() - timedelta(days=1)):
            for i in range(len(self.windows)):
                s, e = self._bounds(d, i)
                if s <= t < e:
                    return self.on_w
        return 0.0


class Bursty(Appliance):
    def __init__(self, name, on_w, bursts_per_day, burst_s,
                 active_hours: list[tuple[time, time]], pf, seed: int = 0,
                 essential: bool = False):
        super().__init__(name, pf, essential)
        self.on_w, self.n, self.burst_s = on_w, bursts_per_day, burst_s
        self.active_hours, self.seed = active_hours, seed
        self._cache: dict[date, list[tuple[datetime, datetime]]] = {}

    def nominal_w(self) -> float:
        return self.on_w

    def _bursts(self, d: date, tz) -> list[tuple[datetime, datetime]]:
        if d not in self._cache:
            out = []
            for i in range(self.n):
                start, end = self.active_hours[i % len(self.active_hours)]
                lo = datetime.combine(d, start, tzinfo=tz)
                span = (datetime.combine(d, end, tzinfo=tz) - lo).total_seconds() - self.burst_s
                s = lo + timedelta(seconds=_rng(self.seed, self.name, d, i).uniform(0, span))
                out.append((s, s + timedelta(seconds=self.burst_s)))
            self._cache[d] = out
        return self._cache[d]

    def _natural_w(self, t: datetime) -> float:
        return self.on_w if any(s <= t < e for s, e in self._bursts(t.date(), t.tzinfo)) else 0.0
