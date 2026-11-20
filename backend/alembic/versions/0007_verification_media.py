"""Uploaded photos (encrypted), submission and manual-decision columns.

Revision ID: 0007
Revises: 0006
"""
import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None
S = "freda_verify"


def upgrade() -> None:
    op.add_column("verifications", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True), schema=S)
    op.add_column("verifications", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True), schema=S)
    op.add_column("verifications", sa.Column("decided_by", sa.Uuid(), sa.ForeignKey(f"{S}.users.id", ondelete="SET NULL"), nullable=True), schema=S)
    op.add_column("verifications", sa.Column("decision_reason", sa.String(200), nullable=True), schema=S)
    op.create_table(
        "verification_media",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("verification_id", sa.Uuid(), sa.ForeignKey(f"{S}.verifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("doc_type", sa.String(8), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("content_type", sa.String(20), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("verification_id", "kind"),
        schema=S,
    )
    op.create_index("ix_verification_media_verification_id", "verification_media", ["verification_id"], schema=S)
    op.create_index("ix_media_purge", "verification_media", ["purge_after"], schema=S)
    op.execute("ALTER TABLE freda_verify.verification_media ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON freda_verify.verification_media FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    op.drop_table("verification_media", schema=S)
    for c in ("decision_reason", "decided_by", "decided_at", "submitted_at"):
        op.drop_column("verifications", c, schema=S)
