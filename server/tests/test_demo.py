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
