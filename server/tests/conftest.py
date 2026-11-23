import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

TEST_DB = os.environ.setdefault(
    "WATTOU_TEST_DATABASE_URL", "postgresql+asyncpg://wattou:wattou@localhost:5432/wattou_test"
)
os.environ.setdefault("WATTOU_DATABASE_URL", TEST_DB)
os.environ.setdefault("WATTOU_MQTT_HOST", "localhost")
os.environ.setdefault("WATTOU_JWT_SECRET", "test-secret")


@pytest.fixture(scope="session")
def migrated():
    subprocess.run(["uv", "run", "alembic", "upgrade", "head"], check=True,
                   cwd=Path(__file__).parents[1], env={**os.environ, "WATTOU_DATABASE_URL": TEST_DB})


@pytest.fixture
async def engine(migrated):
    eng = create_async_engine(TEST_DB)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    async with engine.connect() as conn:
        trans = await conn.begin()
        s = AsyncSession(bind=conn, join_transaction_mode="create_savepoint",
                         expire_on_commit=False)
        try:
            yield s
        finally:
            await s.close()
            await trans.rollback()
