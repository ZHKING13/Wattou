"""Détection de branchements sauvages (consommation qui ne vient pas du foyer)."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from .types import Activation, Alert, ApplianceSig, CreditEntry

ABSENCE_MIN_W = 300
ABSENCE_RUN_S = 600
GAP_MIN_KWH = 2.0
GAP_RATIO = 0.10


def _known(a: Activation, sigs: list[ApplianceSig], tol: float = 0.15) -> bool:
    return any((s.label or s.essential or s.device_id) and s.delta_w > 0
               and abs(a.delta_w - s.delta_w) / s.delta_w <= tol for s in sigs)


def check_absence(activations: list[Activation], sigs: list[ApplianceSig],
                  absence_since: datetime | None, now: datetime) -> Alert | None:
    """En mode absence : une charge inconnue ≥ 300 W allumée après le départ et restée
    allumée 10 min -> alerte (horodatée à début + 10 min).

    Fondé sur les paliers plutôt que sur la consommation de fond : celle-ci inclut déjà les
    appareils qui tournent toute la nuit, ce qui masquait la charge du voisin.
    """
    if absence_since is None:
        return None
    for a in sorted(activations, key=lambda x: x.start):
        if a.delta_w < ABSENCE_MIN_W or a.start < absence_since or _known(a, sigs):
            continue
        alert_at = a.start + timedelta(seconds=ABSENCE_RUN_S)
        if (a.end or now) >= alert_at and now >= alert_at:
            return Alert(
                "absence_load", alert_at,
                f"Consommation de {round(a.delta_w)} W détectée alors que vous êtes absent. Un "
                "appareil ou un branchement inconnu consomme sur votre compteur.",
                f"absence_load:{a.start.date().isoformat()}")
    return None


def check_meter_gap(entries: list[CreditEntry],
                    measured_between: Callable[[datetime, datetime], float],
                    coverage_between: Callable[[datetime, datetime], float] | None = None,
                    min_coverage: float = 0.95) -> Alert | None:
    """Le compteur décompte > 10 % de plus que le capteur sur les 2 derniers intervalles."""
    entries = sorted(entries, key=lambda e: e.ts)
    readings = [e for e in entries if e.kind == "reading"][-3:]
    if len(readings) < 3:
        return None
    gaps = []
    for prev, cur in zip(readings, readings[1:], strict=False):
        recharged = sum(e.kwh for e in entries
                        if e.kind == "recharge" and prev.ts < e.ts <= cur.ts)
        if coverage_between and coverage_between(prev.ts, cur.ts) < min_coverage:
            return None  # données du capteur incomplètes : on n'accuse personne
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
                        sigs: list[ApplianceSig], now: datetime,
                        history_start: datetime) -> list[Alert]:
    """Charge inconnue *nouvelle* qui revient la nuit (≥ 3 nuits sur 7 jours).

    « Nouvelle » : jamais vue avant les 7 derniers jours alors qu'on observait déjà le foyer
    depuis au moins une semaine. Une habitude présente dès l'installation (clim, congélateur
    pas encore nommés) n'est pas un branchement suspect.
    """
    out = []
    since = now - timedelta(days=7)
    for s in sigs:
        if s.label or s.device_id or s.essential:
            continue
        acts = activations_by_sig.get(s.id, [])
        if not acts:
            continue
        first_seen = min(a.start for a in acts)
        # nouvelle = apparue dans les 7 derniers jours, après au moins 7 jours d'observation sans elle
        if first_seen < since or first_seen - history_start < timedelta(days=7):
            continue
        nights = {_night(a.start) for a in acts}
        nights.discard(None)
        if len(nights) >= 3:
            week = now.isocalendar()
            out.append(Alert(
                "night_unknown", now,
                f"Un nouvel appareil inconnu d'environ {round(s.delta_w)} W s'allume la nuit depuis "
                "plusieurs jours. Vérifiez qu'aucun branchement n'a été fait sur votre installation.",
                f"night_unknown:{s.id}:{week.year}-{week.week}"))
    return out
