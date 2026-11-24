"""Horodatage (horloge des données) du passage en mode absence."""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute("ALTER TABLE foyers ADD COLUMN IF NOT EXISTS absence_since timestamptz")


def downgrade():
    op.execute("ALTER TABLE foyers DROP COLUMN absence_since")
