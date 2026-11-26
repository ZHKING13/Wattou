"""Accès base de données. Seul module qui exécute du SQL."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m
from .analysis.types import Activation, ApplianceSig, CreditEntry, DeviceView, Sample
from .contract import Meta, MeterState, PlugState


def _dt(s: str | datetime) -> datetime:
    return s if isinstance(s, datetime) else datetime.fromisoformat(s)


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
    return [DeviceView(r.id, r.kind, r.essential, dict(r.last_state), r.name) for r in rows]


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


async def first_ts(s: AsyncSession, foyer_id: UUID) -> datetime | None:
    r = m.meter_readings.c
    return (await s.execute(select(func.min(r.ts)).where(r.foyer_id == foyer_id))).scalar_one()


# Énergie = Σ p_w · durée jusqu'à la mesure suivante (plafonnée à MAX_DT_S) : un message
# perdu ne fait pas baisser l'énergie, un vrai trou (coupure) ne compte presque rien.
MAX_DT_S = 10
_WEIGHTED = (
    "SELECT ts, p_w * LEAST(COALESCE(EXTRACT(EPOCH FROM lead(ts) OVER (ORDER BY ts) - ts), 1), "
    f"{MAX_DT_S}) AS ws FROM meter_readings WHERE foyer_id = :f AND ts > :a AND ts <= :z"
)


async def energy_by_bucket(s: AsyncSession, foyer_id: UUID, start: datetime, end: datetime,
                           step: str) -> list[tuple[datetime, float]]:
    """kWh par seau [start, end)."""
    interval = {"minute": timedelta(minutes=1), "hour": timedelta(hours=1), "day": timedelta(days=1)}[step]
    rows = await s.execute(text(
        # date_bin (PostgreSQL ≥ 14) plutôt que time_bucket : marche aussi sans TimescaleDB
        f"SELECT date_bin(:iv, ts, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS b, sum(ws) / 3600000.0 FROM ({_WEIGHTED}) x "
        "WHERE ts >= :a2 AND ts < :z2 GROUP BY b ORDER BY b"),
        {"iv": interval, "f": foyer_id, "a": start - timedelta(seconds=1), "z": end,
         "a2": start, "z2": end})
    return [(b, float(kwh)) for b, kwh in rows]


# --- alertes ---------------------------------------------------------------
async def add_alert(s: AsyncSession, foyer_id: UUID, ts: datetime, kind: str, message: str,
                    dedup_key: str) -> bool:
    res = await s.execute(insert(m.alerts).values(
        foyer_id=foyer_id, ts=ts, kind=kind, message=message, dedup_key=dedup_key)
        .on_conflict_do_nothing().returning(m.alerts.c.id))
    return res.scalar_one_or_none() is not None


async def list_foyer_ids(s: AsyncSession) -> list[UUID]:
    return list((await s.execute(select(m.foyers.c.id))).scalars())


async def get_foyer(s: AsyncSession, foyer_id: UUID) -> dict | None:
    row = (await s.execute(select(m.foyers).where(m.foyers.c.id == foyer_id))).mappings().first()
    return dict(row) if row else None


async def set_absence(s: AsyncSession, foyer_id: UUID, enabled: bool, since: datetime | None) -> None:
    await s.execute(update(m.foyers).where(m.foyers.c.id == foyer_id).values(
        absence_mode=enabled, absence_since=since if enabled else None))


async def set_low_credit_days(s: AsyncSession, foyer_id: UUID, days: float) -> None:
    await s.execute(update(m.foyers).where(m.foyers.c.id == foyer_id).values(low_credit_days=days))


# --- énergie ---------------------------------------------------------------
async def energy_between(s: AsyncSession, foyer_id: UUID, start: datetime, end: datetime) -> float:
    """kWh sur (start, end]."""
    v = (await s.execute(text(f"SELECT COALESCE(sum(ws), 0) FROM ({_WEIGHTED}) x"),
                         {"f": foyer_id, "a": start, "z": end})).scalar_one()
    return float(v) / 3_600_000


async def coverage_between(s: AsyncSession, foyer_id: UUID, start: datetime, end: datetime) -> float:
    """Part des secondes de (start, end] couvertes par une mesure (capteur ≈ 1 mesure/s)."""
    r = m.meter_readings.c
    n = (await s.execute(select(func.count()).where(
        r.foyer_id == foyer_id, r.ts > start, r.ts <= end))).scalar_one()
    seconds = (end - start).total_seconds()
    return n / seconds if seconds > 0 else 0.0


async def plug_energy(s: AsyncSession, foyer_id: UUID, start: datetime,
                      end: datetime) -> dict[str, float]:
    """kWh par prise ; les prises publient toutes les 10 s (et à chaque changement)."""
    rows = await s.execute(text(
        "SELECT device_id, sum(p_w * dt) / 3600000.0 FROM ("
        "  SELECT device_id, p_w, LEAST(EXTRACT(EPOCH FROM (lead(ts) OVER w - ts)), 15) AS dt"
        "  FROM plug_readings WHERE foyer_id = :f AND ts > :a AND ts <= :z"
        "  WINDOW w AS (PARTITION BY device_id ORDER BY ts)) x "
        "WHERE dt IS NOT NULL GROUP BY device_id"), {"f": foyer_id, "a": start, "z": end})
    return {d: float(k) for d, k in rows}


async def baseline_w(s: AsyncSession, foyer_id: UUID, end: datetime) -> float:
    """Consommation de fond : 5e percentile de la puissance nocturne (00h-05h) des 3 derniers jours."""
    v = (await s.execute(text(
        "SELECT percentile_cont(0.05) WITHIN GROUP (ORDER BY p_w) FROM meter_readings "
        "WHERE foyer_id = :f AND ts > :a AND ts <= :z AND extract(hour FROM ts) < 5"),
        {"f": foyer_id, "a": end - timedelta(days=3), "z": end})).scalar_one()
    return float(v or 0.0)


# --- état d'analyse ----------------------------------------------------------
def _act_to_json(a: Activation) -> dict:
    return {"start": a.start.isoformat(), "end": a.end.isoformat() if a.end else None,
            "delta_w": a.delta_w, "pf": a.pf}


def _act_from_json(d: dict) -> Activation:
    return Activation(_dt(d["start"]), _dt(d["end"]) if d["end"] else None, d["delta_w"], d["pf"])


async def get_analysis_state(s: AsyncSession, foyer_id: UUID) -> tuple[datetime | None, list[Activation]]:
    row = (await s.execute(select(m.analysis_state).where(
        m.analysis_state.c.foyer_id == foyer_id))).first()
    if row is None:
        return None, []
    return row.last_ts, [_act_from_json(d) for d in row.open_json]


async def set_analysis_state(s: AsyncSession, foyer_id: UUID, last_ts: datetime,
                             open_: list[Activation]) -> None:
    data = [_act_to_json(a) for a in open_]
    await s.execute(insert(m.analysis_state).values(foyer_id=foyer_id, last_ts=last_ts, open_json=data)
                    .on_conflict_do_update(index_elements=["foyer_id"],
                                           set_={"last_ts": last_ts, "open_json": data}))


# --- appareils reconnus ------------------------------------------------------
async def list_appliances(s: AsyncSession, foyer_id: UUID) -> list[ApplianceSig]:
    rows = await s.execute(select(m.appliances).where(m.appliances.c.foyer_id == foyer_id)
                           .order_by(m.appliances.c.delta_w.desc()))
    return [ApplianceSig(r.id, r.label, r.delta_w, r.pf, r.n_obs, r.device_id, r.essential)
            for r in rows]


async def save_appliances(s: AsyncSession, foyer_id: UUID, sigs: list[ApplianceSig]) -> None:
    for g in sigs:
        vals = dict(label=g.label, delta_w=g.delta_w, pf=g.pf, n_obs=g.n_obs,
                    device_id=g.device_id, essential=g.essential)
        await s.execute(insert(m.appliances).values(id=g.id, foyer_id=foyer_id, **vals)
                        .on_conflict_do_update(index_elements=["id"], set_=vals))


async def update_appliance(s: AsyncSession, foyer_id: UUID, appliance_id: UUID, **vals) -> bool:
    res = await s.execute(update(m.appliances).where(
        m.appliances.c.id == appliance_id, m.appliances.c.foyer_id == foyer_id).values(**vals))
    return res.rowcount > 0


async def add_activations(s: AsyncSession, foyer_id: UUID,
                          assigned: list[tuple[Activation, UUID]]) -> None:
    if assigned:
        await s.execute(m.activations.insert().values([
            dict(foyer_id=foyer_id, appliance_id=sid, start_ts=a.start, end_ts=a.end,
                 delta_w=a.delta_w) for a, sid in assigned]))


async def activations_between(s: AsyncSession, foyer_id: UUID, start: datetime,
                              end: datetime) -> list[tuple[Activation, UUID]]:
    c = m.activations.c
    rows = await s.execute(select(c.start_ts, c.end_ts, c.delta_w, c.appliance_id).where(
        c.foyer_id == foyer_id, c.end_ts > start, c.start_ts < end).order_by(c.start_ts))
    return [(Activation(a, b, d, 0.0), sid) for a, b, d, sid in rows]


# --- crédit -------------------------------------------------------------------
async def add_credit_entry(s: AsyncSession, foyer_id: UUID, ts: datetime, kind: str, kwh: float,
                           amount_fcfa: int | None) -> None:
    await s.execute(m.credit_entries.insert().values(
        foyer_id=foyer_id, ts=ts, kind=kind, kwh=kwh, amount_fcfa=amount_fcfa))


async def credit_entries(s: AsyncSession, foyer_id: UUID) -> list[CreditEntry]:
    c = m.credit_entries.c
    rows = await s.execute(select(c.ts, c.kind, c.kwh, c.amount_fcfa).where(
        c.foyer_id == foyer_id).order_by(c.ts, c.id))
    return [CreditEntry(*r) for r in rows]


# --- alertes et notifications -------------------------------------------------
async def list_alerts(s: AsyncSession, foyer_id: UUID, unread_only: bool = False) -> list[dict]:
    q = select(m.alerts).where(m.alerts.c.foyer_id == foyer_id)
    if unread_only:
        q = q.where(m.alerts.c.read.is_(False))
    rows = await s.execute(q.order_by(m.alerts.c.ts.desc(), m.alerts.c.id.desc()))
    return [dict(r) for r in rows.mappings()]


async def mark_alert_read(s: AsyncSession, foyer_id: UUID, alert_id: int) -> bool:
    res = await s.execute(update(m.alerts).where(
        m.alerts.c.id == alert_id, m.alerts.c.foyer_id == foyer_id).values(read=True))
    return res.rowcount > 0


async def add_push_token(s: AsyncSession, foyer_id: UUID, token: str) -> None:
    await s.execute(insert(m.push_tokens).values(foyer_id=foyer_id, token=token)
                    .on_conflict_do_nothing())


async def push_tokens(s: AsyncSession, foyer_id: UUID) -> list[str]:
    q = select(m.push_tokens.c.token).where(m.push_tokens.c.foyer_id == foyer_id)
    return list((await s.execute(q)).scalars())


# --- utilisateurs et appareils (API) -----------------------------------------
async def create_user(s: AsyncSession, phone: str, password_hash: str, foyer_id: UUID) -> UUID:
    return (await s.execute(m.users.insert().values(
        phone=phone, password_hash=password_hash, foyer_id=foyer_id).returning(m.users.c.id))).scalar_one()


async def get_user_by_phone(s: AsyncSession, phone: str) -> dict | None:
    row = (await s.execute(select(m.users).where(m.users.c.phone == phone))).mappings().first()
    return dict(row) if row else None


async def get_device(s: AsyncSession, foyer_id: UUID, device_id: str) -> dict | None:
    row = (await s.execute(select(m.devices).where(
        m.devices.c.foyer_id == foyer_id, m.devices.c.id == device_id))).mappings().first()
    return dict(row) if row else None


async def list_devices(s: AsyncSession, foyer_id: UUID) -> list[dict]:
    rows = await s.execute(select(m.devices).where(m.devices.c.foyer_id == foyer_id)
                           .order_by(m.devices.c.id))
    return [dict(r) for r in rows.mappings()]


async def set_schedule(s: AsyncSession, foyer_id: UUID, device_id: str, schedule: dict) -> None:
    await s.execute(update(m.devices).where(m.devices.c.foyer_id == foyer_id,
                                            m.devices.c.id == device_id).values(schedule=schedule))


async def plug_series(s: AsyncSession, foyer_id: UUID, device_id: str, start: datetime,
                      end: datetime) -> list[tuple[datetime, float]]:
    c = m.plug_readings.c
    rows = await s.execute(select(c.ts, c.p_w).where(
        c.foyer_id == foyer_id, c.device_id == device_id, c.ts > start, c.ts <= end).order_by(c.ts))
    return [(t, p) for t, p in rows]


async def set_low_credit_active(s: AsyncSession, foyer_id: UUID, active: bool) -> None:
    await s.execute(update(m.foyers).where(m.foyers.c.id == foyer_id).values(low_credit_active=active))
