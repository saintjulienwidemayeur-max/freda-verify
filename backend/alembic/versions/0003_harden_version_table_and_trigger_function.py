"""Fixes reported by the Supabase security advisor after the first deployment.

* alembic_version had row level security disabled (it is created by Alembic itself, outside migration 0002): enable it. The role that runs
  the migrations owns the table, and owners bypass RLS, so Alembic keeps working; nobody else can read or write it.
* the append-only trigger function had a mutable search_path: pin it to pg_catalog (it only calls RAISE).

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE freda_verify.alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER FUNCTION freda_verify.audit_logs_immutable() SET search_path = pg_catalog")


def downgrade() -> None:
    op.execute("ALTER FUNCTION freda_verify.audit_logs_immutable() RESET search_path")
    op.execute("ALTER TABLE freda_verify.alembic_version DISABLE ROW LEVEL SECURITY")
