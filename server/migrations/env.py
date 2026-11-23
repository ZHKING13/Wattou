import asyncio
import os

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from wattou.models import metadata


def do_run(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


async def main():
    engine = create_async_engine(os.environ["WATTOU_DATABASE_URL"])
    async with engine.connect() as conn:
        await conn.run_sync(do_run)
        await conn.commit()
    await engine.dispose()


asyncio.run(main())
