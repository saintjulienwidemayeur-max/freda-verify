"""Declared customer data (encrypted) on verifications, and the ID-card decision rule on the decision policy.

Revision ID: 0012
Revises: 0011
"""
import sqlalchemy as sa

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.add_column("verifications", sa.Column("expected_enc", sa.LargeBinary(), nullable=True), schema=S)
    op.add_column("decision_policies", sa.Column("id_cards", sa.String(12), nullable=False, server_default="review"), schema=S)


def downgrade() -> None:
    op.drop_column("decision_policies", "id_cards", schema=S)
    op.drop_column("verifications", "expected_enc", schema=S)
