"""Photos are kept until a person deletes them (purge_after becomes optional); table for server-side check results (MRZ reading).

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.alter_column("verification_media", "purge_after", existing_type=sa.DateTime(timezone=True), nullable=True, schema=S)
    op.execute("UPDATE freda_verify.verification_media SET purge_after = NULL")      # decision: photos stay until deleted by a person
    op.create_table(
        "verification_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("verification_id", sa.Uuid(), sa.ForeignKey(f"{S}.verifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("source", sa.String(16), nullable=True),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("verification_id", "kind"),
        schema=S,
    )
    op.create_index("ix_verification_checks_verification_id", "verification_checks", ["verification_id"], schema=S)
    op.execute("ALTER TABLE freda_verify.verification_checks ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON freda_verify.verification_checks FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("verification_checks", schema=S)
    op.execute("UPDATE freda_verify.verification_media SET purge_after = now() WHERE purge_after IS NULL")
    op.alter_column("verification_media", "purge_after", existing_type=sa.DateTime(timezone=True), nullable=False, schema=S)
