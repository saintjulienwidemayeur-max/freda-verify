# ruff: noqa: E501, S608
"""Decision policy per organization (manual / automatic), locked down like every other table.

Revision ID: 0011
Revises: 0010
"""
import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.create_table(
        "decision_policies",
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mode", sa.String(8), nullable=False, server_default="manual"),
        sa.Column("uncertain", sa.String(8), nullable=False, server_default="review"),
        sa.Column("face_min", sa.Float(), nullable=False, server_default="0.363"),
        sa.Column("require_pad", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        schema=S,
    )
    op.execute("ALTER TABLE freda_verify.decision_policies ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON freda_verify.decision_policies FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("decision_policies", schema=S)
