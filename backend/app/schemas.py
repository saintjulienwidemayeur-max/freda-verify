import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RegisterIn(_In):
    email: EmailStr
    password: str = Field(max_length=128)
    full_name: str = Field(min_length=1, max_length=120)
    organization_name: str = Field(min_length=2, max_length=120)


class LoginIn(_In):
    email: EmailStr
    password: str = Field(max_length=128)


class RefreshIn(_In):
    refresh_token: str = Field(max_length=200)


class MfaVerifyIn(_In):
    mfa_token: str = Field(max_length=2000)
    code: str = Field(min_length=6, max_length=16)


class MfaCodeIn(_In):
    code: str = Field(min_length=6, max_length=16)


class MfaDisableIn(_In):
    password: str = Field(max_length=128)
    code: str = Field(min_length=6, max_length=16)


class ForgotIn(_In):
    email: EmailStr


class ResetIn(_In):
    token: str = Field(max_length=200)
    new_password: str = Field(max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: str
    mfa_enabled: bool


class TokensOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (OAuth token type, not a secret)
    expires_in: int
    user: UserOut


class MfaRequiredOut(BaseModel):
    mfa_required: Literal[True] = True
    mfa_token: str


class OrgIn(_In):
    name: str = Field(min_length=2, max_length=120)


class OrgOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    role: str | None = None


class MemberIn(_In):
    email: EmailStr
    role: Literal["admin", "member", "viewer"]


class RoleIn(_In):
    role: Literal["owner", "admin", "member", "viewer"]


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str


class KeyIn(_In):
    name: str = Field(min_length=1, max_length=80)
    env: Literal["test", "live"] = "test"


class KeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    env: str
    prefix: str
    last4: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class KeyCreatedOut(KeyOut):
    secret: str = Field(description="Shown once. Store it in a secret manager; it cannot be retrieved later.")


class MrzIn(_In):
    lines: list[str] = Field(min_length=2, max_length=3)
    fix_ocr: bool = True
