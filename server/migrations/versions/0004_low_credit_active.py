"""Mémorise que la règle « crédit bas » a déjà agi (déclenchement sur franchissement)."""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.execute("ALTER TABLE foyers ADD COLUMN IF NOT EXISTS low_credit_active boolean "
               "NOT NULL DEFAULT false")


def downgrade():
    op.execute("ALTER TABLE foyers DROP COLUMN low_credit_active")
