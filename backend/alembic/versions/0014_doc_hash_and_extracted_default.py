"""Duplicate-document hash on verifications; ID-card rule `face_and_extracted` (identity read from the card itself) becomes the default.

Revision ID: 0014
Revises: 0013
"""
import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.add_column("verifications", sa.Column("doc_hash", sa.String(64), nullable=True), schema=S)
    op.create_index("ix_verifications_doc_hash", "verifications", ["organization_id", "doc_hash"], schema=S)
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards TYPE varchar(24)")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards SET DEFAULT 'face_and_extracted'")
    op.execute("UPDATE freda_verify.decision_policies SET id_cards = 'face_and_extracted' WHERE id_cards IN ('review', 'face_and_data')")


def downgrade() -> None:
    op.execute("UPDATE freda_verify.decision_policies SET id_cards = 'review' WHERE length(id_cards) > 16")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards SET DEFAULT 'face_and_data'")
    op.execute("ALTER TABLE freda_verify.decision_policies ALTER COLUMN id_cards TYPE varchar(16)")
    op.drop_index("ix_verifications_doc_hash", table_name="verifications", schema=S)
    op.drop_column("verifications", "doc_hash", schema=S)
