"""Lock the schema down for Supabase (and any PostgREST-style API layer).

Supabase exposes tables through an HTTP API using the `anon` / `authenticated` roles. Freda Verify talks to the database ONLY through
its own backend, so those roles must never see these tables: enable row level security (default deny, no policies) and revoke every
privilege. On a plain PostgreSQL without those roles this migration is a harmless no-op for the REVOKE part.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TABLES = ["users", "organizations", "memberships", "refresh_sessions", "password_reset_tokens", "recovery_codes", "api_keys", "audit_logs", "request_logs"]


def upgrade() -> None:
    for t in TABLES:
        op.execute(f"ALTER TABLE freda_verify.{t} ENABLE ROW LEVEL SECURITY")      # no policy = nobody but the table owner / service role
    op.execute("""
        DO $$
        DECLARE r text;
        BEGIN
          FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
              EXECUTE format('REVOKE ALL ON SCHEMA freda_verify FROM %I', r);
              EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA freda_verify FROM %I', r);
              EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA freda_verify FROM %I', r);
              EXECUTE format('REVOKE ALL ON ALL FUNCTIONS IN SCHEMA freda_verify FROM %I', r);
              EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA freda_verify REVOKE ALL ON TABLES FROM %I', r);
            END IF;
          END LOOP;
        END $$;
    """)


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"ALTER TABLE freda_verify.{t} DISABLE ROW LEVEL SECURITY")
