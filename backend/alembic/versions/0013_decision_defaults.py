"""Decision policy defaults: automatic mode, ID cards = printed text must agree with the declared data. Organizations that kept the old default 'review' for ID cards move to the new default.

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards TYPE varchar(16)")      # 'face_and_data' (13 characters) did not fit the 12 of migration 0012
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN mode SET DEFAULT 'auto'")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards SET DEFAULT 'face_and_data'")
    op.execute("UPDATE freda_verify.decision_policies SET id_cards = 'face_and_data' WHERE id_cards = 'review'")


def downgrade() -> None:
    op.execute("UPDATE freda_verify.decision_policies SET id_cards = 'review' WHERE length(id_cards) > 12")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards TYPE varchar(12)")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN mode SET DEFAULT 'manual'")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards SET DEFAULT 'review'")
