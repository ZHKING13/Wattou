"""Programmation enregistrée par appareil."""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade():
    op.execute("ALTER TABLE devices ADD COLUMN IF NOT EXISTS schedule jsonb NOT NULL "
               "DEFAULT '{\"slots\": []}'")


def downgrade():
    op.execute("ALTER TABLE devices DROP COLUMN schedule")
