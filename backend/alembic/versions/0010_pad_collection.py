# ruff: noqa: E501, S608
"""PAD collection: campaigns (invitation links), volunteers (consent) and donated photos, locked down like every other table.

Revision ID: 0010
Revises: 0009
"""
import sqlalchemy as sa

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None
S = "freda_verify"
TABLES = ("pad_campaigns", "pad_contributions", "pad_samples")


def upgrade() -> None:
    op.create_table(
        "pad_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_enc", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey(f"{S}.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema=S,
    )
    op.create_index("ix_pad_campaigns_org", "pad_campaigns", ["organization_id"], schema=S)
    op.create_table(
        "pad_contributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey(f"{S}.pad_campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(8), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consent_version", sa.String(16), nullable=False),
        sa.Column("skin_label", sa.String(24), nullable=True),
        sa.Column("device", sa.String(80), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("campaign_id", "code"),
        schema=S,
    )
    op.create_index("ix_pad_contributions_campaign", "pad_contributions", ["campaign_id"], schema=S)
    op.create_table(
        "pad_samples",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("contribution_id", sa.Uuid(), sa.ForeignKey(f"{S}.pad_contributions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey(f"{S}.organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("slot", sa.Integer(), nullable=False),
        sa.Column("light", sa.String(16), nullable=True),
        sa.Column("content_type", sa.String(24), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("contribution_id", "kind", "slot"),
        schema=S,
    )
    op.create_index("ix_pad_samples_contribution", "pad_samples", ["contribution_id"], schema=S)
    for t in TABLES:
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
    for t in reversed(TABLES):
        op.drop_table(t, schema=S)
