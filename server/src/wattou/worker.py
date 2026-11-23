"""Worker d'analyse : toutes les 60 s, analyse chaque foyer. `python -m wattou.worker`."""

import asyncio
import logging
from collections import defaultdict
from datetime import timedelta
from uuid import UUID, uuid4

import aiomqtt
from sqlalchemy.ext.asyncio import AsyncSession

from . import repo
from .analysis import alerts as al
from .analysis import fraud
from .analysis.appliances import assign
from .analysis.rules import low_credit_actions
from .analysis.steps import track
from .analysis.types import Alert, ApplianceSig
from .config import Settings, get_settings
from .control import MqttPublisher, Publisher, send_command
from .credit_service import credit_status
from .db import sessionmaker
from .notify import ExpoNotifier, LogNotifier, Notifier

log = logging.getLogger("wattou.worker")
SETTLE_S = 5          # paliers trop proches de la fin de fenêtre : traités au passage suivant
CONTEXT_S = 600       # contexte relu avant la fenêtre (paliers, absence sur 10 min)
MAX_WINDOW = timedelta(hours=6)


async def _plug_sigs(s: AsyncSession, foyer_id: UUID, sigs: list[ApplianceSig]) -> list[ApplianceSig]:
    """Un signal par prise connectée ; sa puissance suit la dernière mesure de la prise."""
    by_dev = {g.device_id: g for g in sigs if g.device_id}
    for d in await repo.device_views(s, foyer_id):
        if d.kind != "plug":
            continue
        g = by_dev.get(d.id)
        if g is None:
            g = ApplianceSig(uuid4(), d.id, 0.0, 0.9, 0, d.id, d.essential)
            sigs.append(g)
        g.essential = d.essential
        p = float(d.last_state.get("p_w") or 0)
        if p > 5 and g.n_obs == 0:
            g.delta_w = p
    return sigs


async def _emit(s: AsyncSession, notifier: Notifier, foyer_id: UUID, alerts: list[Alert]) -> None:
    tokens = None
    for a in alerts:
        if await repo.add_alert(s, foyer_id, a.ts, a.kind, a.message, a.dedup_key):
            tokens = tokens if tokens is not None else await repo.push_tokens(s, foyer_id)
            await notifier.send(tokens, "Wattou", a.message)


async def analyze_foyer(s: AsyncSession, pub: Publisher, notifier: Notifier, foyer_id: UUID,
                        default_price: float = 110.0) -> None:
    latest = await repo.latest_ts(s, foyer_id)
    if latest is None:
        return
    last_ts, open_ = await repo.get_analysis_state(s, foyer_id)
    if last_ts is None:
        last_ts = await repo.first_ts(s, foyer_id) - timedelta(seconds=1)
    window_end = min(latest, last_ts + MAX_WINDOW)
    boundary = max(last_ts, window_end - timedelta(seconds=SETTLE_S))
    caught_up = window_end == latest
    samples = await repo.meter_samples(s, foyer_id, last_ts - timedelta(seconds=CONTEXT_S), window_end)
    window = [x for x in samples if x.ts > last_ts]

    closed, open_ = track(samples, open_, last_ts, boundary)
    sigs = await _plug_sigs(s, foyer_id, await repo.list_appliances(s, foyer_id))
    assigned, sigs = assign(closed, sigs)
    await repo.save_appliances(s, foyer_id, sigs)
    await repo.add_activations(s, foyer_id, assigned)

    foyer = await repo.get_foyer(s, foyer_id)
    found: list[Alert] = []
    found += al.check_outage(window)
    if (v := al.check_voltage(window)):
        found.append(v)
    found += al.check_stuck(open_, sigs, window_end)
    if foyer["absence_mode"] and foyer["absence_since"]:
        recent = [a for a, _ in await repo.activations_between(
            s, foyer_id, last_ts - timedelta(seconds=CONTEXT_S), window_end)]
        if (a := fraud.check_absence(recent + open_, sigs, foyer["absence_since"], window_end)):
            found.append(a)
    for d in await repo.device_views(s, foyer_id):
        if d.kind == "plug" and d.essential and any(k in d.id for k in al.STUCK_LABELS):
            series = await repo.plug_series(s, foyer_id, d.id,
                                            window_end - timedelta(hours=al.STUCK_H, minutes=1), window_end)
            found += al.check_plug_stuck(d.id, d.id, series, window_end)
    if caught_up:
        entries = await repo.credit_entries(s, foyer_id)

        async def measured(a, b):
            return await repo.energy_between(s, foyer_id, a, b)

        readings = [e for e in entries if e.kind == "reading"][-3:]
        pairs = zip(readings, readings[1:], strict=False)
        cache = {(p.ts, c.ts): await measured(p.ts, c.ts) for p, c in pairs}
        if (g := fraud.check_meter_gap(entries, lambda a, b: cache[(a, b)])):
            found.append(g)
        two_weeks = await repo.activations_between(s, foyer_id, window_end - timedelta(days=14),
                                                   window_end)
        by_sig: dict[UUID, list] = defaultdict(list)
        for a, sid in two_weeks:
            by_sig[sid].append(a)
        found += fraud.check_night_unknown(by_sig, sigs, window_end, await repo.first_ts(s, foyer_id))
        status = await credit_status(s, foyer_id, window_end, default_price)
        if (c := al.check_credit(status.days_left, foyer["low_credit_days"], status.depletion_at,
                                 window_end)):
            found.append(c)
        today = window_end.replace(hour=0, minute=0, second=0, microsecond=0)
        hours = await repo.energy_by_bucket(s, foyer_id, today - timedelta(days=7), window_end, "hour")
        today_h, past = [0.0] * 24, [0.0] * 24
        past_days = set()
        for b, kwh in hours:
            (today_h if b >= today else past)[b.hour] += kwh
            if b < today:
                past_days.add(b.date())
        if len(past_days) >= 3:  # pas de « pic » sans historique pour comparer
            n = len(past_days)
            if (p := al.check_peak(today_h, [x / n for x in past], window_end)):
                found.append(p)
        for device_id, cmd in low_credit_actions(status.days_left, foyer["low_credit_days"],
                                                 await repo.device_views(s, foyer_id)):
            await send_command(pub, foyer_id, device_id, cmd)
    await _emit(s, notifier, foyer_id, found)
    await repo.set_analysis_state(s, foyer_id, boundary, open_)


async def run_worker(settings: Settings, interval_s: float = 60) -> None:
    maker = sessionmaker()
    notifier: Notifier = ExpoNotifier() if settings.expo_push_enabled else LogNotifier()
    async with aiomqtt.Client(settings.mqtt_host, settings.mqtt_port, username=settings.mqtt_user,
                              password=settings.mqtt_password) as client:
        pub = MqttPublisher(client)
        while True:
            busy = False
            async with maker() as s:
                for f in await repo.list_foyer_ids(s):
                    try:
                        before = (await repo.get_analysis_state(s, f))[0]
                        await analyze_foyer(s, pub, notifier, f, settings.tarif_fcfa_kwh_defaut)
                        await s.commit()
                        after = (await repo.get_analysis_state(s, f))[0]
                        latest = await repo.latest_ts(s, f)
                        busy = busy or (latest is not None and after is not None
                                        and after != before
                                        and latest - after > timedelta(seconds=SETTLE_S + 1))
                    except Exception:
                        log.exception("analyse du foyer %s en échec", f)
                        await s.rollback()
            await asyncio.sleep(0 if busy else interval_s)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    st = get_settings()
    asyncio.run(run_worker(st, st.worker_interval_s))
