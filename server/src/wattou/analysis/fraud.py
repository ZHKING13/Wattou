"""Détection de branchements sauvages (consommation qui ne vient pas du foyer)."""

from collections.abc import Callable
from datetime import datetime, timedelta
from statistics import median
from uuid import UUID

from .types import Activation, Alert, ApplianceSig, CreditEntry, Sample

ABSENCE_MIN_W = 300
ABSENCE_RUN_S = 600
GAP_MIN_KWH = 2.0
GAP_RATIO = 0.10


def _known(a: Activation, sigs: list[ApplianceSig], tol: float = 0.15) -> bool:
    return any((s.label or s.essential or s.device_id) and s.delta_w > 0
               and abs(a.delta_w - s.delta_w) / s.delta_w <= tol for s in sigs)


def check_absence(samples: list[Sample], open_activations: list[Activation],
                  sigs: list[ApplianceSig], baseline_w: float, absence: bool) -> Alert | None:
    """En mode absence : ≥ 300 W inexpliqués en continu pendant 10 min -> alerte."""
    if not absence:
        return None
    known = [a for a in open_activations if _known(a, sigs)]
    run_start, run_vals = None, []
    for s in samples:
        explained = baseline_w + sum(a.delta_w for a in known if a.start <= s.ts)
        extra = s.p_w - explained
        if extra >= ABSENCE_MIN_W:
            if run_start is None:
                run_start, run_vals = s.ts, []
            run_vals.append(extra)
            if (s.ts - run_start).total_seconds() >= ABSENCE_RUN_S:
                w = round(median(run_vals))
                return Alert(
                    "absence_load", s.ts,
                    f"Consommation de {w} W détectée alors que vous êtes absent. Un appareil ou "
                    "un branchement inconnu consomme sur votre compteur.",
                    f"absence_load:{run_start.date().isoformat()}")
        else:
            run_start = None
    return None


def check_meter_gap(entries: list[CreditEntry],
                    measured_between: Callable[[datetime, datetime], float]) -> Alert | None:
    """Le compteur décompte > 10 % de plus que le capteur sur les 2 derniers intervalles."""
    entries = sorted(entries, key=lambda e: e.ts)
    readings = [e for e in entries if e.kind == "reading"][-3:]
    if len(readings) < 3:
        return None
    gaps = []
    for prev, cur in zip(readings, readings[1:]):
        recharged = sum(e.kwh for e in entries
                        if e.kind == "recharge" and prev.ts < e.ts <= cur.ts)
        counted = prev.kwh + recharged - cur.kwh
        measured = measured_between(prev.ts, cur.ts)
        if counted < GAP_MIN_KWH or (counted - measured) / counted <= GAP_RATIO:
            return None
        gaps.append((counted, measured))
    counted, measured = gaps[-1]
    return Alert(
        "meter_gap", readings[-1].ts,
        f"Votre compteur a décompté {counted:.1f} kWh mais Wattou n'en a mesuré que "
        f"{measured:.1f}. Quelque chose consomme entre le compteur et le capteur.",
        f"meter_gap:{readings[-1].ts.isoformat()}")


def _night(t: datetime):
    if t.hour >= 23:
        return t.date()
    if t.hour < 5:
        return (t - timedelta(days=1)).date()
    return None


def check_night_unknown(activations_by_sig: dict[UUID, list[Activation]],
                        sigs: list[ApplianceSig], now: datetime) -> list[Alert]:
    out = []
    since = now - timedelta(days=7)
    for s in sigs:
        if s.label or s.device_id or s.essential:
            continue
        nights = {_night(a.start) for a in activations_by_sig.get(s.id, []) if a.start >= since}
        nights.discard(None)
        if len(nights) >= 3:
            week = now.isocalendar()
            out.append(Alert(
                "night_unknown", now,
                f"Un appareil inconnu d'environ {round(s.delta_w)} W s'allume la nuit depuis "
                "plusieurs jours. Vérifiez qu'aucun branchement n'a été fait sur votre installation.",
                f"night_unknown:{s.id}:{week.year}-{week.week}"))
    return out
