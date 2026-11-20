# ruff: noqa: E501, S608  (table names are literals defined in this file)
"""Webhook endpoints and deliveries, locked down like every other table.

Revision ID: 0009
Revises: 0008
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret_enc", sa.String(255), nullable=False),
        sa.Column("description", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey(f"{S}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=S,
    )
    op.create_index("ix_webhook_endpoints_org", "webhook_endpoints", ["organization_id"], schema=S)
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("endpoint_id", sa.Uuid(), sa.ForeignKey(f"{S}.webhook_endpoints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.String(120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        schema=S,
    )
    op.create_index("ix_webhook_deliveries_endpoint", "webhook_deliveries", ["endpoint_id", "created_at"], schema=S)
    for t in ("webhook_endpoints", "webhook_deliveries"):
        op.execute(f"ALTER TABLE freda_verify.{t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            DO $$
            DECLARE r text;
            BEGIN
              FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
                  EXECUTE format('REVOKE ALL ON freda_verify.{t} FROM %I', r);
                END IF;
              END LOOP;
            END $$;
        """)


def downgrade() -> None:
    op.drop_table("webhook_deliveries", schema=S)
    op.drop_table("webhook_endpoints", schema=S)
