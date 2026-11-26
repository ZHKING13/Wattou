import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from wattou.config import Settings
from wattou.models import metadata


def _url() -> str:
    # même normalisation que l'application (Railway fournit postgresql://)
    return Settings._pilote_async(os.environ["WATTOU_DATABASE_URL"])


def do_run(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


async def main():
    engine = create_async_engine(_url())
    async with engine.connect() as conn:
        await conn.run_sync(do_run)
        await conn.commit()
    await engine.dispose()


asyncio.run(main())
