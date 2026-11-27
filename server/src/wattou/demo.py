"""Démo hébergée : retrouve le foyer à alimenter avec le simulateur.

`python -m wattou.demo <critère>` affiche « <foyer_id> <0|1> » (1 = le foyer a déjà des mesures),
ou rien si aucun foyer ne correspond. Critère : « dernier » (foyer créé le plus récemment)
ou un numéro de téléphone au format +225XXXXXXXXXX.
"""

import asyncio
import sys
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m
from .db import sessionmaker


async def foyer_cible(s: AsyncSession, critere: str) -> tuple[UUID, bool] | None:
    if critere == "dernier":
        q = select(m.foyers.c.id).order_by(m.foyers.c.created_at.desc()).limit(1)
    else:
        q = select(m.users.c.foyer_id).where(m.users.c.phone == critere)
    foyer = (await s.execute(q)).scalar_one_or_none()
    if foyer is None:
        return None
    r = m.meter_readings.c
    n = (await s.execute(select(func.count()).select_from(
        select(r.ts).where(r.foyer_id == foyer).limit(1).subquery()))).scalar_one()
    return foyer, n > 0


async def _main(critere: str) -> None:
    async with sessionmaker()() as s:
        res = await foyer_cible(s, critere)
    if res:
        print(res[0], int(res[1]))


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1] if len(sys.argv) > 1 else "dernier"))
