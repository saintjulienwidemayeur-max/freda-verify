"""Settings come from environment variables (prefix FV_). Nothing secret is hard-coded."""
import base64
import hashlib
import secrets
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FV_", env_file=".env", extra="ignore")

    app_env: Literal["dev", "test", "prod"] = "dev"
    database_url: str                       # required: no default DSN (no credentials in code)
    secret_key: str | None = None           # JWT signing key. Required in prod; generated per process in dev/test
    encryption_key: str | None = None       # Fernet key protecting TOTP secrets at rest
    cors_origins: list[str] = []
    redis_url: str | None = None
    trust_proxy: bool = False
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    login_max_failures: int = 5
    login_lock_minutes: int = 15
    auth_rate_limit: int = 10               # requests / minute / IP on credential endpoints
    api_rate_limit: int = 120               # requests / minute / API key
    issuer: str = "freda-verify"

    @model_validator(mode="after")
    def _secrets(self) -> "Settings":
        if self.app_env == "prod":
            if not self.secret_key or len(self.secret_key) < 32:
                raise ValueError("FV_SECRET_KEY (>= 32 chars) is required in prod")
            if not self.encryption_key:
                raise ValueError("FV_ENCRYPTION_KEY is required in prod")
            if "*" in self.cors_origins:
                raise ValueError("wildcard CORS is not allowed in prod")
        else:
            # dev/test only: ephemeral per-process secrets (tokens do not survive a restart)
            self.secret_key = self.secret_key or secrets.token_urlsafe(48)
            self.encryption_key = self.encryption_key or base64.urlsafe_b64encode(
                hashlib.sha256(self.secret_key.encode()).digest()
            ).decode()
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
