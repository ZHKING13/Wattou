"""Démo hébergée : retrouve le foyer à alimenter avec le simulateur.

`python -m wattou.demo <critère>` affiche « <foyer_id> <dernière mesure ISO ou -> », ou rien si aucun
foyer ne correspond : le simulateur reprend à la dernière mesure pour combler un éventuel trou.
Critère : « dernier » (foyer créé le plus récemment)
ou un numéro de téléphone au format +225XXXXXXXXXX.
"""

import asyncio
import sys
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models as m
from .db import sessionmaker


async def foyer_cible(s: AsyncSession, critere: str) -> tuple[UUID, datetime | None] | None:
    if critere == "dernier":
        q = select(m.foyers.c.id).order_by(m.foyers.c.created_at.desc()).limit(1)
    else:
        q = select(m.users.c.foyer_id).where(m.users.c.phone == critere)
    foyer = (await s.execute(q)).scalar_one_or_none()
    if foyer is None:
        return None
    r = m.meter_readings.c
    derniere = (await s.execute(select(func.max(r.ts)).where(r.foyer_id == foyer))).scalar_one()
    return foyer, derniere


async def reinitialiser(s: AsyncSession, foyer: UUID) -> None:
    """Efface les mesures simulées d'un foyer et tout ce qui en découle (appareils reconnus,
    activations, alertes, état d'analyse). Garde le compte, les appareils connectés et le crédit."""
    for table in (m.activations, m.appliances, m.alerts, m.analysis_state, m.meter_readings, m.plug_readings):
        await s.execute(delete(table).where(table.c.foyer_id == foyer))


async def _main(args: list[str]) -> None:
    reinit = "--reinitialiser" in args
    critere = next((a for a in args if not a.startswith("--")), "dernier")
    async with sessionmaker()() as s:
        res = await foyer_cible(s, critere)
        if res and reinit:
            await reinitialiser(s, res[0])
            await s.commit()
            res = (res[0], None)
    if res:
        print(res[0], res[1].isoformat() if res[1] else "-")


if __name__ == "__main__":
    asyncio.run(_main(sys.argv[1:]))
