"""Ménage abidjanais type et scénarios injectables."""

from dataclasses import dataclass, field
from datetime import datetime, time

from .appliances import Appliance, Bursty, Constant, Cyclic, Scheduled


@dataclass
class NeighborTap:
    start: datetime
    end: datetime
    w: float = 400.0


@dataclass
class FridgeStuck:
    start: datetime


@dataclass
class Outage:
    start: datetime
    end: datetime


@dataclass
class NetCut:
    start: datetime
    end: datetime


Scenario = NeighborTap | FridgeStuck | Outage | NetCut


@dataclass
class Household:
    appliances: list[Appliance]
    scenarios: list[Scenario] = field(default_factory=list)

    def add_scenario(self, s: Scenario) -> None:
        self.scenarios.append(s)

    def get(self, name: str) -> Appliance:
        return next(a for a in self.appliances if a.name == name)

    def _active(self, kind, t: datetime):
        return [s for s in self.scenarios if isinstance(s, kind)
                and s.start <= t and (not hasattr(s, "end") or t < s.end)]

    def is_outage(self, t: datetime) -> bool:
        return bool(self._active(Outage, t))

    def is_netcut(self, t: datetime) -> bool:
        return bool(self._active(NetCut, t))

    def breakdown(self, t: datetime) -> dict[str, float]:
        stuck = bool(self._active(FridgeStuck, t))
        out = {}
        for a in self.appliances:
            if a.name == "frigo":
                a.forced_on = stuck
            out[a.name] = a.power_w(t)
        taps = self._active(NeighborTap, t)
        if taps:
            out["voisin"] = sum(s.w for s in taps)
        return out

    def total(self, t: datetime) -> tuple[float, float]:
        b = self.breakdown(t)
        p = sum(b.values())
        pfs = {a.name: a.pf for a in self.appliances} | {"voisin": 0.9}
        apparent = sum(w / pfs[n] for n, w in b.items() if w > 0)
        return p, (p / apparent if apparent else 1.0)


def abidjan_household(seed: int = 1) -> Household:
    return Household([
        Scheduled("clim", 1100, [(time(19), time(23, 30)), (time(1), time(5, 30))], pf=0.9, seed=seed),
        Cyclic("frigo", 120, 15 * 60, 25 * 60, pf=0.8, essential=True, offset_s=seed * 97),
        Cyclic("congelateur", 150, 20 * 60, 20 * 60, pf=0.8, essential=True, offset_s=seed * 211),
        Scheduled("ventilateurs", 120, [(time(12), time(16)), (time(21), time(6))], pf=0.95, seed=seed),
        Scheduled("tv", 80, [(time(18, 30), time(23))], pf=0.95, seed=seed),
        Bursty("fer", 1000, 2, 8 * 60, [(time(6), time(8)), (time(18), time(20))], pf=1.0, seed=seed),
        Scheduled("eclairage", 40, [(time(18, 30), time(23, 30))], pf=0.9, seed=seed),
        Constant("fond", 25, pf=0.6),
    ])
