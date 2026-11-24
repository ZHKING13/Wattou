"""Schéma initial Wattou."""

from alembic import op

from wattou.models import metadata

revision = "0001"
down_revision = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    metadata.create_all(op.get_bind())
    for table in ("meter_readings", "plug_readings"):
        op.execute(f"SELECT create_hypertable('{table}', 'ts', if_not_exists => TRUE)")


def downgrade():
    metadata.drop_all(op.get_bind())
