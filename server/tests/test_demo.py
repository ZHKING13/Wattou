from datetime import datetime, timezone

from sqlalchemy import update

from wattou import models as m
from wattou import repo
from wattou.contract import MeterState
from wattou.demo import foyer_cible


async def test_cible_dernier_foyer_et_par_telephone(session):
    from wattou.api.auth import hash_password

    a = await repo.create_foyer(session, "Ancien")
    # même transaction = même now() : on vieillit le premier foyer pour un ordre sans ambiguïté
    await session.execute(update(m.foyers).where(m.foyers.c.id == a).values(
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    await repo.create_user(session, "+2250700000001", hash_password("secret1"), a)
    b = await repo.create_foyer(session, "Chez Awa")
    await repo.create_user(session, "+2250700000002", hash_password("secret1"), b)
    assert (await foyer_cible(session, "dernier"))[0] == b
    assert (await foyer_cible(session, "+2250700000001"))[0] == a
    assert await foyer_cible(session, "+2259999999999") is None


async def test_donne_la_derniere_mesure_pour_combler_le_trou(session):
    f = await repo.create_foyer(session, "Chez Awa")
    assert (await foyer_cible(session, "dernier")) == (f, None)
    for h in (1, 3):
        t = datetime(2026, 11, 2, h, tzinfo=timezone.utc)
        await repo.insert_meter(session, f, MeterState(ts=t.isoformat(), p_w=1, v=230, i_a=0, pf=1, e_kwh=0))
    assert (await foyer_cible(session, "dernier")) == (f, datetime(2026, 11, 2, 3, tzinfo=timezone.utc))


async def test_reinitialiser_efface_les_mesures_mais_garde_le_compte(session):
    from uuid import uuid4

    from wattou.analysis.types import ApplianceSig
    from wattou.api.auth import hash_password
    from wattou.demo import reinitialiser

    f = await repo.create_foyer(session, "Chez Awa")
    await repo.create_user(session, "+2250700000003", hash_password("secret1"), f)
    t = datetime(2026, 11, 2, tzinfo=timezone.utc)
    await repo.insert_meter(session, f, MeterState(ts=t.isoformat(), p_w=1, v=230, i_a=0, pf=1, e_kwh=0))
    await repo.save_appliances(session, f, [ApplianceSig(uuid4(), None, 100, 0.9, 3)])
    await repo.add_alert(session, f, t, "outage", "x", "k")
    await repo.set_analysis_state(session, f, t, [])
    await repo.add_credit_entry(session, f, t, "reading", 50, None)
    await reinitialiser(session, f)
    assert await repo.latest_ts(session, f) is None
    assert await repo.list_appliances(session, f) == []
    assert await repo.list_alerts(session, f) == []
    assert (await repo.get_analysis_state(session, f))[0] is None
    assert len(await repo.credit_entries(session, f)) == 1
    assert await repo.get_user_by_phone(session, "+2250700000003")
