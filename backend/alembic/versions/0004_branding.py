"""White-label branding per organization (one row), locked down like every other table.

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.create_table(
        "branding",
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("name", sa.String(40), nullable=False, server_default=""),
        sa.Column("color", sa.String(7), nullable=False, server_default="#1E4FE0"),
        sa.Column("theme", sa.String(5), nullable=False, server_default="light"),
        sa.Column("shape", sa.String(7), nullable=False, server_default="rounded"),
        sa.Column("lang", sa.String(2), nullable=False, server_default="en"),
        sa.Column("title", sa.String(60), nullable=False, server_default=""),
        sa.Column("subtitle", sa.String(140), nullable=False, server_default=""),
        sa.Column("support_email", sa.String(254), nullable=False, server_default=""),
        sa.Column("docs", JSONB(), nullable=False),
        sa.Column("redirect_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("domain", sa.String(253), nullable=False, server_default=""),
        sa.Column("hide_powered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey(f"{S}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema=S,
    )
    op.execute(f"ALTER TABLE {S}.branding ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON freda_verify.branding FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("branding", schema=S)
