"""Prix du kWh, crédit restant (kWh affichés par le compteur CIE) et prévision d'épuisement."""

from collections.abc import Callable
from datetime import date, datetime, timedelta

from .types import CreditEntry

MAX_HORIZON_DAYS = 365


def _sorted(entries: list[CreditEntry]) -> list[CreditEntry]:
    return sorted(entries, key=lambda e: e.ts)


def price_per_kwh(entries: list[CreditEntry], default: float) -> float:
    recharges = [e for e in _sorted(entries) if e.kind == "recharge" and e.amount_fcfa and e.kwh > 0]
    last = recharges[-3:]
    if not last:
        return default
    return sum(e.amount_fcfa for e in last) / sum(e.kwh for e in last)


def _last_reading(entries: list[CreditEntry]) -> CreditEntry | None:
    readings = [e for e in _sorted(entries) if e.kind == "reading"]
    return readings[-1] if readings else None


def _recharged_since(entries: list[CreditEntry], since: datetime) -> float:
    return sum(e.kwh for e in entries if e.kind == "recharge" and e.ts > since)


def remaining_kwh(entries: list[CreditEntry],
                  measured_kwh_since: Callable[[datetime], float]) -> float | None:
    last = _last_reading(entries)
    if last is None:
        return None
    left = last.kwh + _recharged_since(entries, last.ts) - measured_kwh_since(last.ts)
    return max(0.0, left)


def validate_reading(entries: list[CreditEntry], new_kwh: float,
                     measured_since_last: float) -> str | None:
    """Message d'erreur si le relevé est plus élevé que possible (faute de frappe probable)."""
    last = _last_reading(entries)
    if last is None:
        return None
    if new_kwh > last.kwh + _recharged_since(entries, last.ts) + 0.5:
        return ("Ce relevé est plus élevé que le précédent sans recharge entre les deux. "
                "Vérifiez le chiffre affiché par le compteur.")
    return None


def forecast_daily_kwh(daily: list[tuple[date, float]], target: date) -> float:
    past = sorted((d, v) for d, v in daily if d < target)
    last7 = [v for d, v in past if (target - d).days <= 7]
    if not last7:
        last7 = [v for _, v in past[-7:]]
    if not last7:
        return 0.0
    base = sum(last7) / len(last7)
    same = [v for d, v in past if (target - d).days <= 28 and d.weekday() == target.weekday()]
    return (base + sum(same) / len(same)) / 2 if len(same) >= 2 else base


def depletion(remaining: float, now: datetime, daily_kwh: float,
              hourly_profile: list[float]) -> tuple[float, datetime] | None:
    """Consomme heure par heure selon le profil (24 parts) ; renvoie (jours, date d'épuisement)."""
    if daily_kwh <= 0 or remaining is None:
        return None
    total = sum(hourly_profile) or 1.0
    t, left = now, remaining
    limit = now + timedelta(days=MAX_HORIZON_DAYS)
    while t < limit:
        next_hour = t.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        portion = (next_hour - t).total_seconds() / 3600
        use = daily_kwh * hourly_profile[t.hour] / total * portion
        if use >= left and use > 0:
            t += timedelta(hours=portion * left / use)
            return (t - now).total_seconds() / 86400, t
        left -= use
        t = next_hour
    return None
