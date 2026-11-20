"""Freda Verify may share a database (e.g. a Supabase project) with other applications: it must stay inside its own schema."""
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import get_engine
from tests.conftest import auth, first_org, register


def test_all_tables_live_in_their_own_schema_and_other_apps_are_untouched():
    with get_engine().connect() as c:
        ours = {r[0] for r in c.execute(text("select table_name from information_schema.tables where table_schema = 'freda_verify'"))}
        public = {r[0] for r in c.execute(text("select table_name from information_schema.tables where table_schema = 'public'"))}
        other_app = c.execute(text("select email from public.users")).scalar()
    assert {"users", "organizations", "api_keys", "audit_logs", "alembic_version"} <= ours
    assert public == {"users"}                      # only the decoy table of the "other application"
    assert other_app == "other-app@example.com"     # its data was not modified by our migrations or tests


def test_row_level_security_is_enabled_on_every_table():
    with get_engine().connect() as c:
        rows = c.execute(text("select tablename, rowsecurity from pg_tables where schemaname = 'freda_verify'")).all()
        cfg = c.execute(text("select proconfig from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'freda_verify' and proname = 'audit_logs_immutable'")).scalar()
    assert len(rows) == 21 and all(rls for _, rls in rows)          # the 20 tables + alembic_version
    assert cfg == ["search_path=pg_catalog"]                         # the trigger function does not depend on the caller's search_path


def test_database_url_is_normalised_like_providers_print_it():
    base = {"app_env": "test"}
    assert Settings(**base, database_url="postgres://u:p@db.x.supabase.co:5432/postgres").database_url == \
        "postgresql+psycopg://u:p@db.x.supabase.co:5432/postgres?sslmode=require"
    assert Settings(**base, database_url="postgresql://u:p@pooler.supabase.com:5432/postgres?sslmode=verify-full").database_url.endswith("sslmode=verify-full")
    assert "sslmode" not in Settings(**base, database_url="postgresql://u:p@localhost:5432/x").database_url       # local / docker hosts stay as they are
    assert "sslmode" not in Settings(**base, database_url="postgresql+psycopg://u:p@postgres:5432/x").database_url


def test_request_logs_endpoint_is_scoped_filterable_and_secret_free(client):
    a = register(client, "a@a.example", "Org A")
    b = register(client, "b@b.example", "Org B")
    org_a, org_b = first_org(client, a), first_org(client, b)
    key = client.post(f"/api/v1/organizations/{org_a['id']}/api-keys", json={"name": "k", "env": "test"}, headers=auth(a)).json()
    client.get("/api/v1/usage", headers={"Authorization": f"Bearer {key['secret']}"})
    client.get("/api/v1/usage", headers={"Authorization": "Bearer fv_test_invalid"})
    rows = client.get(f"/api/v1/organizations/{org_a['id']}/request-logs", headers=auth(a)).json()
    assert any(r["path"] == "/api/v1/usage" and r["api_key_prefix"] == key["prefix"] and r["status"] == 200 for r in rows)
    assert key["secret"] not in str(rows)
    assert all(r["status"] < 400 for r in client.get(f"/api/v1/organizations/{org_a['id']}/request-logs?status_class=2", headers=auth(a)).json())
    assert client.get(f"/api/v1/organizations/{org_b['id']}/request-logs", headers=auth(a)).status_code == 404
