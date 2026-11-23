import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from wattou.config import get_settings
from wattou.models import metadata


def do_run(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


async def main():
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as conn:
        await conn.run_sync(do_run)
        await conn.commit()
    await engine.dispose()


asyncio.run(main())
