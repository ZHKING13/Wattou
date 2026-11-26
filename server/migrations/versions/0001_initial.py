"""Schéma initial Wattou."""

from alembic import op

from wattou.models import metadata

revision = "0001"
down_revision = None


def upgrade():
    bind = op.get_bind()
    # TimescaleDB si disponible (docker compose) ; sinon PostgreSQL simple (Railway, hébergeurs gérés).
    timescale = bind.exec_driver_sql(
        "SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb'").first() is not None
    if timescale:
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    metadata.create_all(bind)
    if timescale:
        for table in ("meter_readings", "plug_readings"):
            op.execute(f"SELECT create_hypertable('{table}', 'ts', if_not_exists => TRUE)")


def downgrade():
    metadata.drop_all(op.get_bind())
