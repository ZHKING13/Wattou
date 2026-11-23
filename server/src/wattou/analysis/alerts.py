"""Alertes hors fraude : crédit, pic, appareil bloqué, coupure, tension."""

from datetime import datetime

from .steps import segments
from .types import Activation, Alert, ApplianceSig, Sample

STUCK_LABELS = ("frigo", "congel")
STUCK_H = 3
V_MIN, V_MAX, V_RUN_S = 180, 250, 10


def _fr(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def check_credit(days_left: float | None, threshold: float, depletion_at: datetime | None,
                 now: datetime) -> Alert | None:
    if days_left is None or days_left >= threshold:
        return None
    when = f" (épuisement prévu le {depletion_at:%d/%m} vers {depletion_at:%H}h)" if depletion_at else ""
    return Alert("credit_low", now, f"Il vous reste environ {_fr(days_left)} jours de crédit{when}.",
                 f"credit_low:{now.date().isoformat()}")


def check_peak(hourly_today: list[float], hourly_7d_avg: list[float], now: datetime) -> Alert | None:
    h = now.hour - 1
    if h < 0:
        return None
    used, usual = hourly_today[h], hourly_7d_avg[h]
    if used > 0.5 and used > 1.5 * usual:
        return Alert("peak", now,
                     f"Consommation inhabituelle entre {h}h et {h + 1}h : {_fr(used)} kWh "
                     f"au lieu de {_fr(usual)} kWh d'habitude.",
                     f"peak:{now.date().isoformat()}:{h}")
    return None


def check_stuck(open_activations: list[Activation], sigs: list[ApplianceSig],
                now: datetime) -> list[Alert]:
    out = []
    watched = [s for s in sigs if s.label and any(k in s.label.lower() for k in STUCK_LABELS)]
    for a in open_activations:
        if (now - a.start).total_seconds() < STUCK_H * 3600:
            continue
        for s in watched:
            if abs(a.delta_w - s.delta_w) <= 0.15 * s.delta_w:
                out.append(Alert("stuck", now,
                                 f"Votre {s.label} ne s'arrête plus depuis {STUCK_H} h : "
                                 "il est peut-être en panne.",
                                 f"stuck:{s.id}:{a.start.isoformat()}"))
                break
    return out


def check_outage(samples: list[Sample], max_gap_s: int = 120) -> list[Alert]:
    segs = segments(samples, max_gap_s)
    out = []
    for prev, nxt in zip(segs, segs[1:]):
        a, b = prev[-1].ts, nxt[0].ts
        minutes = round((b - a).total_seconds() / 60)
        out.append(Alert("outage", b,
                         f"Coupure de courant de {minutes} min (de {a:%H:%M} à {b:%H:%M}).",
                         f"outage:{a.isoformat()}"))
    return out


def check_voltage(samples: list[Sample]) -> Alert | None:
    run: list[Sample] = []
    for s in samples:
        if s.v < V_MIN or s.v > V_MAX:
            run.append(s)
            if (run[-1].ts - run[0].ts).total_seconds() >= V_RUN_S - 1:
                worst = min(run, key=lambda x: x.v) if s.v < V_MIN else max(run, key=lambda x: x.v)
                return Alert("voltage", s.ts,
                             f"Tension dangereuse de {round(worst.v)} V : débranchez les appareils "
                             "fragiles (TV, ordinateur, frigo).",
                             f"voltage:{run[0].ts.isoformat()[:13]}")
        else:
            run = []
    return None
