"""Authentication (JWT for dashboard users, fv_* keys for the API) and role-based access control."""
import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.errors import forbidden, not_found, unauthorized
from app.core.security import decode_jwt, sha256
from app.db.session import get_db
from app.models import ApiKey, Membership, Organization, Role, User, now

PERMS: dict[str, set[str]] = {
    "org:read": {Role.owner, Role.admin, Role.member, Role.viewer},
    "org:update": {Role.owner, Role.admin},
    "members:read": {Role.owner, Role.admin, Role.member, Role.viewer},
    "members:manage": {Role.owner, Role.admin},
    "keys:read": {Role.owner, Role.admin, Role.member},
    "keys:write": {Role.owner, Role.admin},
    "branding:read": {Role.owner, Role.admin, Role.member, Role.viewer},
    "branding:write": {Role.owner, Role.admin},
    "audit:read": {Role.owner, Role.admin},
}


@dataclass
class Principal:
    user: User | None = None
    api_key: ApiKey | None = None

    @property
    def org_id(self) -> uuid.UUID | None:
        return self.api_key.organization_id if self.api_key else None


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized()
    token = authorization[7:].strip()
    if not token:
        raise unauthorized()
    return token


def get_current_user(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    token = _bearer(authorization)
    claims = decode_jwt(token, "access")
    user = db.get(User, uuid.UUID(claims["sub"])) if claims and _is_uuid(claims["sub"]) else None
    if not user or not user.is_active:
        raise unauthorized("Invalid or expired token")
    request.state.user_id = user.id
    return user


def _is_uuid(v: str) -> bool:
    try:
        uuid.UUID(v)
        return True
    except ValueError:
        return False


def get_principal(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Principal:
    token = _bearer(authorization)
    if token.startswith("fv_"):
        key = db.scalar(select(ApiKey).where(ApiKey.key_hash == sha256(token)))
        if not key or key.revoked_at is not None:
            raise unauthorized("Invalid API key")
        ratelimit.enforce(f"key:{key.id}", get_settings().api_rate_limit)
        if key.last_used_at is None or now() - key.last_used_at > timedelta(minutes=1):
            key.last_used_at = now()
            db.commit()
        request.state.org_id, request.state.api_key_id = key.organization_id, key.id
        return Principal(api_key=key)
    return Principal(user=get_current_user(request, authorization, db))


@dataclass
class OrgCtx:
    user: User
    org: Organization
    membership: Membership


def org_access(perm: str):
    """Dependency: the caller must be a member of {org_id} with the permission. Non-members get 404 (organizations cannot be enumerated)."""
    def dep(org_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> OrgCtx:
        m = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id))
        if not m:
            raise not_found("Organization not found")
        if m.role not in PERMS[perm]:
            raise forbidden()
        request.state.org_id = org_id
        return OrgCtx(user, m.organization, m)
    return dep
