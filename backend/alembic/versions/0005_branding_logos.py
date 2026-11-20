"""Logo bytes of the hosted page (one row per organization), locked down like every other table.

Revision ID: 0005
Revises: 0004
"""
import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.create_table(
        "branding_logos",
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey(f"{S}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema=S,
    )
    op.execute("ALTER TABLE freda_verify.branding_logos ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON freda_verify.branding_logos FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("branding_logos", schema=S)
