import os

import pytest

# The suite needs a real PostgreSQL (same as production): FV_TEST_DATABASE_URL must point to a database whose name ends in "_test".
TEST_URL = os.environ.get("FV_TEST_DATABASE_URL")
if not TEST_URL or not TEST_URL.split("?")[0].endswith("_test"):
    pytest.exit("Set FV_TEST_DATABASE_URL to a PostgreSQL database named *_test (it is wiped on every run)", returncode=2)

os.environ.update({"FV_APP_ENV": "test", "FV_DATABASE_URL": TEST_URL, "FV_CORS_ORIGINS": '["https://app.example.test"]', "FV_AUTH_RATE_LIMIT": "10"})
os.environ.pop("FV_REDIS_URL", None)

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.core import ratelimit  # noqa: E402
from app.db.session import get_engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "correct horse battery"


@pytest.fixture(scope="session", autouse=True)
def _schema():
    with get_engine().begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS freda_verify CASCADE"))
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))
        # decoy table of ANOTHER application that shares the database (see test_schema_and_config.py)
        c.execute(text("CREATE TABLE public.users (id int primary key, email text)"))
        c.execute(text("INSERT INTO public.users VALUES (1, 'other-app@example.com')"))
    command.upgrade(Config("alembic.ini"), "head")        # the tests exercise the real migrations, not create_all()


@pytest.fixture(autouse=True)
def _clean():
    ratelimit.reset_memory()
    with get_engine().begin() as c:
        c.execute(text("TRUNCATE " + ", ".join(f"freda_verify.{t}" for t in ("users", "organizations", "memberships", "refresh_sessions", "password_reset_tokens", "recovery_codes", "api_keys", "audit_logs", "request_logs")) + " RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def register(client, email="owner@example.com", org="Acme Bank", password=PASSWORD, name="Test User"):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": name, "organization_name": org})
    assert r.status_code == 201, r.text
    return r.json()


def auth(tokens) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def first_org(client, tokens) -> dict:
    return client.get("/api/v1/organizations", headers=auth(tokens)).json()[0]
