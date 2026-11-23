"""Accès base de données. Seul module qui exécute du SQL."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m
from .analysis.types import DeviceView, Sample
from .contract import Meta, MeterState, PlugState


def _dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


# --- foyers ---------------------------------------------------------------
async def create_foyer(s: AsyncSession, name: str) -> UUID:
    return (await s.execute(m.foyers.insert().values(name=name).returning(m.foyers.c.id))).scalar_one()


async def foyer_exists(s: AsyncSession, foyer_id: UUID) -> bool:
    q = select(func.count()).select_from(m.foyers).where(m.foyers.c.id == foyer_id)
    return (await s.execute(q)).scalar_one() > 0


# --- appareils connectés ---------------------------------------------------
async def upsert_device(s: AsyncSession, foyer_id: UUID, device_id: str, meta: Meta) -> None:
    stmt = insert(m.devices).values(foyer_id=foyer_id, id=device_id, kind=meta.kind,
                                    name=meta.name, essential=meta.essential)
    await s.execute(stmt.on_conflict_do_update(
        index_elements=["foyer_id", "id"],
        set_={"kind": meta.kind, "name": meta.name, "essential": meta.essential}))


async def set_device_state(s: AsyncSession, foyer_id: UUID, device_id: str, state: dict) -> None:
    await s.execute(update(m.devices).where(m.devices.c.foyer_id == foyer_id,
                                            m.devices.c.id == device_id).values(last_state=state))


async def device_views(s: AsyncSession, foyer_id: UUID) -> list[DeviceView]:
    rows = await s.execute(select(m.devices).where(m.devices.c.foyer_id == foyer_id)
                           .order_by(m.devices.c.id))
    return [DeviceView(r.id, r.kind, r.essential, dict(r.last_state)) for r in rows]


# --- mesures ---------------------------------------------------------------
def _meter_row(foyer_id: UUID, st: MeterState) -> dict:
    return {"foyer_id": foyer_id, "ts": _dt(st.ts), "p_w": st.p_w, "v": st.v, "i_a": st.i_a, "pf": st.pf,
                "e_kwh": st.e_kwh}


async def insert_meter_batch(s: AsyncSession, foyer_id: UUID, states: Sequence[MeterState]) -> None:
    if states:
        await s.execute(insert(m.meter_readings).values([_meter_row(foyer_id, x) for x in states])
                        .on_conflict_do_nothing())


async def insert_meter(s: AsyncSession, foyer_id: UUID, st: MeterState) -> None:
    await insert_meter_batch(s, foyer_id, [st])


async def insert_plug(s: AsyncSession, foyer_id: UUID, device_id: str, st: PlugState) -> None:
    await s.execute(insert(m.plug_readings).values(
        foyer_id=foyer_id, device_id=device_id, ts=_dt(st.ts), p_w=st.p_w, on=st.on)
        .on_conflict_do_nothing())


async def meter_samples(s: AsyncSession, foyer_id: UUID, start: datetime, end: datetime) -> list[Sample]:
    r = m.meter_readings.c
    rows = await s.execute(select(r.ts, r.p_w, r.pf, r.v).where(
        r.foyer_id == foyer_id, r.ts > start, r.ts <= end).order_by(r.ts))
    return [Sample(ts, p, pf, v) for ts, p, pf, v in rows]


async def latest_ts(s: AsyncSession, foyer_id: UUID) -> datetime | None:
    r = m.meter_readings.c
    return (await s.execute(select(func.max(r.ts)).where(r.foyer_id == foyer_id))).scalar_one()


async def energy_by_bucket(s: AsyncSession, foyer_id: UUID, start: datetime, end: datetime,
                           step: str) -> list[tuple[datetime, float]]:
    """kWh par seau. Hypothèse : 1 mesure/s ; les trous ne comptent pas d'énergie."""
    interval = {"minute": timedelta(minutes=1), "hour": timedelta(hours=1), "day": timedelta(days=1)}[step]
    rows = await s.execute(text(
        "SELECT time_bucket(:iv, ts) AS b, sum(p_w) / 3600000.0 "
        "FROM meter_readings WHERE foyer_id = :f AND ts >= :a AND ts < :z "
        "GROUP BY b ORDER BY b"), {"iv": interval, "f": foyer_id, "a": start, "z": end})
    return [(b, float(kwh)) for b, kwh in rows]


# --- alertes ---------------------------------------------------------------
async def add_alert(s: AsyncSession, foyer_id: UUID, ts: datetime, kind: str, message: str,
                    dedup_key: str) -> bool:
    res = await s.execute(insert(m.alerts).values(
        foyer_id=foyer_id, ts=ts, kind=kind, message=message, dedup_key=dedup_key)
        .on_conflict_do_nothing().returning(m.alerts.c.id))
    return res.scalar_one_or_none() is not None
