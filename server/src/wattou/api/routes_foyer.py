from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import repo
from ..analysis.appliances import assign, attribute_totals, visible
from ..analysis.credit import validate_reading
from ..config import get_settings
from ..credit_service import credit_status
from .deps import current_foyer, get_session
from .schemas import (
    AbsenceIn,
    ApplianceOut,
    AppliancePatch,
    CreditIn,
    HistoryPoint,
    PushTokenIn,
    RulesIn,
    Summary,
)

router = APIRouter(tags=["foyer"])
PERIODS = {"day": timedelta(days=1), "week": timedelta(days=7), "month": timedelta(days=30)}


def _midnight(t: datetime) -> datetime:
    return t.replace(hour=0, minute=0, second=0, microsecond=0)


async def _now(s: AsyncSession, foyer: UUID) -> datetime | None:
    """Horloge des données : dernière mesure reçue du foyer."""
    return await repo.latest_ts(s, foyer)


@router.get("/foyer/summary", response_model=Summary)
async def summary(foyer: UUID = Depends(current_foyer), s: AsyncSession = Depends(get_session)):
    f = await repo.get_foyer(s, foyer)
    now = await _now(s, foyer)
    clock = now or datetime.now(UTC)
    st = await credit_status(s, foyer, clock, get_settings().tarif_fcfa_kwh_defaut)
    power = today = month_so_far = 0.0
    if now:
        last = await repo.meter_samples(s, foyer, now - timedelta(seconds=1), now)
        power = last[-1].p_w if last else 0.0
        today = await repo.energy_between(s, foyer, _midnight(now) - timedelta(microseconds=1), now)
        month_so_far = await repo.energy_between(
            s, foyer, _midnight(now).replace(day=1) - timedelta(microseconds=1), now)
    next_month = (_midnight(clock).replace(day=1) + timedelta(days=32)).replace(day=1)
    days_left_month = (next_month - clock).total_seconds() / 86400
    price = st.price_fcfa_kwh
    return Summary(
        power_w=power, today_kwh=today, today_fcfa=round(today * price),
        price_fcfa_kwh=round(price, 2), credit_kwh=st.remaining_kwh,
        credit_fcfa=round(st.remaining_kwh * price) if st.remaining_kwh is not None else None,
        days_left=st.days_left, depletion_at=st.depletion_at,
        month_forecast_fcfa=round((month_so_far + st.daily_kwh * days_left_month) * price),
        absence_mode=f["absence_mode"], low_credit_days=f["low_credit_days"], data_until=now)


@router.get("/foyer/appliances", response_model=list[ApplianceOut])
async def appliances(period: Literal["day", "week", "month"] = "day",
                     foyer: UUID = Depends(current_foyer), s: AsyncSession = Depends(get_session)):
    now = await _now(s, foyer)
    if now is None:
        return []
    start = now - PERIODS[period]
    total = await repo.energy_between(s, foyer, start, now)
    hours = len(await repo.energy_by_bucket(s, foyer, start, now, "minute")) / 60
    sigs = await repo.list_appliances(s, foyer)
    # appareils allumés en ce moment : activations encore ouvertes, rattachées au signal le plus proche
    _, open_ = await repo.get_analysis_state(s, foyer)
    running, _ = assign([replace(a, end=None) for a in open_], sigs)
    known_ids = {g.id for g in sigs}
    running = [(a, sid) for a, sid in running if sid in known_ids]
    parts = attribute_totals(total, hours, await repo.baseline_w(s, foyer, now),
                             await repo.activations_between(s, foyer, start, now) + running, sigs,
                             await repo.plug_energy(s, foyer, start, now), start, now)
    price = (await credit_status(s, foyer, now, get_settings().tarif_fcfa_kwh_defaut)).price_fcfa_kwh
    out = []
    shown = {str(g.id): g for g in visible(sigs)}
    hidden = sum(v for k, v in parts.items() if k not in shown and k not in ("fond", "autres"))
    parts["autres"] = parts.get("autres", 0.0) + hidden
    for key in shown:
        parts.setdefault(key, 0.0)  # un appareil nommé reste listé, même à 0 kWh
    for key, kwh in parts.items():
        g = shown.get(key)
        if g is None and key not in ("fond", "autres"):
            continue
        label = g.label if g else {"fond": "Consommation de fond", "autres": "Autres"}[key]
        power = round(g.delta_w) if g else None
        out.append(ApplianceOut(id=key, label=label, power_w=power, kwh=kwh, fcfa=round(kwh * price),
                                share=kwh / total if total else 0.0,
                                essential=bool(g and g.essential),
                                device_id=g.device_id if g else None))
    return sorted(out, key=lambda a: -a.kwh)


@router.patch("/appliances/{appliance_id}")
async def patch_appliance(appliance_id: UUID, body: AppliancePatch,
                          foyer: UUID = Depends(current_foyer), s: AsyncSession = Depends(get_session)):
    vals = body.model_dump(exclude_none=True)
    if not vals or not await repo.update_appliance(s, foyer, appliance_id, **vals):
        raise HTTPException(404, "Appareil introuvable.")
    await s.commit()
    return {"ok": True}


@router.get("/foyer/history", response_model=list[HistoryPoint])
async def history(from_: datetime = Query(alias="from"), to: datetime = Query(),
                  step: Literal["minute", "hour", "day"] = "hour",
                  foyer: UUID = Depends(current_foyer), s: AsyncSession = Depends(get_session)):
    if to <= from_ or (step == "minute" and to - from_ > timedelta(days=2)):
        raise HTTPException(422, "Période invalide.")
    return [HistoryPoint(ts=b, kwh=k) for b, k in await repo.energy_by_bucket(s, foyer, from_, to, step)]


@router.post("/foyer/credit", status_code=201)
async def add_credit(body: CreditIn, foyer: UUID = Depends(current_foyer),
                     s: AsyncSession = Depends(get_session)):
    now = await _now(s, foyer) or datetime.now(UTC)
    entries = await repo.credit_entries(s, foyer)
    if body.kind == "reading":
        last = [e for e in entries if e.kind == "reading"]
        measured = await repo.energy_between(s, foyer, last[-1].ts, now) if last else 0.0
        if (err := validate_reading(entries, body.kwh, measured)):
            raise HTTPException(422, err)
    if entries and now <= max(e.ts for e in entries):
        now = max(e.ts for e in entries) + timedelta(microseconds=1)
    await repo.add_credit_entry(s, foyer, now, body.kind, body.kwh, body.amount_fcfa)
    await s.commit()
    return {"ok": True}


@router.put("/foyer/absence")
async def absence(body: AbsenceIn, foyer: UUID = Depends(current_foyer),
                  s: AsyncSession = Depends(get_session)):
    await repo.set_absence(s, foyer, body.enabled, await _now(s, foyer) or datetime.now(UTC))
    await s.commit()
    return {"ok": True}


@router.put("/foyer/rules")
async def rules(body: RulesIn, foyer: UUID = Depends(current_foyer),
                s: AsyncSession = Depends(get_session)):
    await repo.set_low_credit_days(s, foyer, body.low_credit_days)
    await s.commit()
    return {"ok": True}


@router.post("/push-tokens", status_code=201)
async def push_token(body: PushTokenIn, foyer: UUID = Depends(current_foyer),
                     s: AsyncSession = Depends(get_session)):
    await repo.add_push_token(s, foyer, body.token)
    await s.commit()
    return {"ok": True}
