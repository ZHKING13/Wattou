"""Calcul du statut de crédit d'un foyer (partagé par le worker et l'API)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from . import repo
from .analysis.credit import depletion, forecast_daily_kwh, price_per_kwh, remaining_kwh


@dataclass
class CreditStatus:
    price_fcfa_kwh: float
    remaining_kwh: float | None
    daily_kwh: float
    days_left: float | None
    depletion_at: datetime | None


async def hourly_profile(s: AsyncSession, foyer_id: UUID, now: datetime) -> list[float]:
    buckets = await repo.energy_by_bucket(s, foyer_id, now - timedelta(days=7), now, "hour")
    prof = [0.0] * 24
    for b, kwh in buckets:
        prof[b.hour] += kwh
    return prof if sum(prof) > 0 else [1 / 24] * 24


async def daily_forecast(s: AsyncSession, foyer_id: UUID, now: datetime) -> float:
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily = await repo.energy_by_bucket(s, foyer_id, today - timedelta(days=28), today, "day")
    f = forecast_daily_kwh([(b.date(), k) for b, k in daily], today.date())
    if f > 0:
        return f
    # pas encore de journée complète : extrapoler les dernières 24 h mesurées
    start = now - timedelta(hours=24)
    samples = await repo.meter_samples(s, foyer_id, start, now)
    if len(samples) < 600:
        return 0.0
    hours = len(samples) / 3600
    return sum(x.p_w for x in samples) / 1000 / 3600 / hours * 24


async def credit_status(s: AsyncSession, foyer_id: UUID, now: datetime,
                        default_price: float) -> CreditStatus:
    entries = await repo.credit_entries(s, foyer_id)
    price = price_per_kwh(entries, default_price)
    remaining = None
    if entries:
        cache: dict[datetime, float] = {}

        def measured_since(t: datetime) -> float:
            return cache[t]

        for e in entries:
            if e.kind == "reading":
                cache[e.ts] = await repo.energy_between(s, foyer_id, e.ts, now)
        remaining = remaining_kwh(entries, measured_since)
    daily = await daily_forecast(s, foyer_id, now)
    days_left = depletion_at = None
    if remaining is not None:
        res = depletion(remaining, now, daily, await hourly_profile(s, foyer_id, now))
        if res:
            days_left, depletion_at = res
    return CreditStatus(price, remaining, daily, days_left, depletion_at)
