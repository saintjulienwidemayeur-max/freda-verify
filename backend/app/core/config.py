"""Settings come from environment variables (prefix FV_). Nothing secret is hard-coded."""
import secrets
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FV_", env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    database_url: str                       # required: no default DSN (no credentials in code)
    secret_key: str | None = None           # JWT signing key. Required in prod; generated per process in dev/test
    encryption_key: str | None = None       # Fernet key protecting TOTP secrets at rest
    cors_origins: list[str] = []
    redis_url: str | None = None
    auto_migrate: bool = True               # run `alembic upgrade head` when the container starts (see docker-entrypoint.sh)
    trust_proxy: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    login_max_failures: int = 5
    login_lock_minutes: int = 15
    auth_rate_limit: int = 10               # requests / minute / IP on credential endpoints
    api_rate_limit: int = 120               # requests / minute / API key
    issuer: str = "freda-verify"
    hosted_url: str = "https://freda-verify.onrender.com"   # origin of the static site that serves /verify (used to build session links)
    session_ttl_minutes: int = 1440         # default lifetime of a verification session link
    media_retention_days: int = 30          # uploaded photos are deleted this many days after upload (the decision record stays)
    media_max_bytes: int = 2 * 1024 * 1024  # per photo
    session_rate_limit: int = 120           # requests / minute / session token

    @field_validator("database_url")
    @classmethod
    def _dsn(cls, v: str) -> str:
        """Accepts the URL as providers print it (postgres:// or postgresql://) and makes it use the psycopg 3 driver.
        Remote hosts (Supabase, RDS...) get sslmode=require unless the URL already says otherwise; localhost / docker hosts are left alone."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg://" + v[len("postgresql://"):]
        host = (urlsplit(v).hostname or "").lower()
        if v.startswith("postgresql+psycopg://") and "sslmode=" not in v and host not in ("localhost", "127.0.0.1", "::1", "postgres", "db"):
            v += ("&" if "?" in v else "?") + "sslmode=require"
        return v

    @model_validator(mode="after")
    def _secrets(self) -> "Settings":
        if self.app_env == "prod":
            if not self.secret_key or len(self.secret_key) < 32:
                raise ValueError("FV_SECRET_KEY (>= 32 chars) is required in prod")
            if not self.encryption_key or len(self.encryption_key) < 32:
                raise ValueError("FV_ENCRYPTION_KEY (>= 32 chars) is required in prod")
            if "*" in self.cors_origins:
                raise ValueError("wildcard CORS is not allowed in prod")
        else:
            # dev/test only: ephemeral per-process secrets (tokens do not survive a restart)
            self.secret_key = self.secret_key or secrets.token_urlsafe(48)
            self.encryption_key = self.encryption_key or self.secret_key
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
