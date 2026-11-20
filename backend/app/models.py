"""Phase 1 data model. Every tenant-owned row carries organization_id; access is always filtered by it."""
import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, fk


def now() -> datetime:
    return datetime.now(UTC)


class Role(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"
    viewer = "viewer"


class KeyEnv(enum.StrEnum):
    test = "test"
    live = "live"


_PK = dict(primary_key=True, default=uuid.uuid4)
_TS = dict(type_=DateTime(timezone=True))
_JSON = JSON().with_variant(JSONB(), "postgresql")
_BIGPK = BigInteger().with_variant(Integer(), "sqlite")


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)          # stored lower-case
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret_enc: Mapped[str | None] = mapped_column(String(255), nullable=True)   # Fernet-encrypted TOTP secret
    mfa_last_step: Mapped[int | None] = mapped_column(BigInteger, nullable=True)     # blocks TOTP replay
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("users.id"), ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[User] = relationship(back_populates="memberships")
    organization: Mapped[Organization] = relationship(back_populates="memberships")


class RefreshSession(Base):
    """One row per refresh token (rotated on every use; reuse of a rotated token revokes every session of the user)."""
    __tablename__ = "refresh_sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("users.id"), ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("users.id"), ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryCode(Base):
    __tablename__ = "recovery_codes"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("users.id"), ondelete="CASCADE"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKey(Base):
    """Only the SHA-256 of the key is stored. The secret is returned once, at creation."""
    __tablename__ = "api_keys"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    env: Mapped[str] = mapped_column(String(8))                                      # test | live
    prefix: Mapped[str] = mapped_column(String(16))
    last4: Mapped[str] = mapped_column(String(4))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Branding(Base):
    """White-label settings of the hosted verification page (one row per organization). Plain configuration, validated on write.
    The logo is NOT stored yet (no object storage); custom domain and redirect URL are saved but not verified/used yet."""
    __tablename__ = "branding"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), default="")
    color: Mapped[str] = mapped_column(String(7), default="#1E4FE0")
    theme: Mapped[str] = mapped_column(String(5), default="light")
    shape: Mapped[str] = mapped_column(String(7), default="rounded")
    lang: Mapped[str] = mapped_column(String(2), default="en")
    title: Mapped[str] = mapped_column(String(60), default="")
    subtitle: Mapped[str] = mapped_column(String(140), default="")
    support_email: Mapped[str] = mapped_column(String(254), default="")
    docs: Mapped[list] = mapped_column(_JSON, default=lambda: ["id", "passport"])
    redirect_url: Mapped[str] = mapped_column(String(500), default="")
    domain: Mapped[str] = mapped_column(String(253), default="")
    hide_powered: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BrandingLogo(Base):
    """Logo bytes of the hosted page, kept in PostgreSQL (small, validated PNG/JPEG/WebP only, never SVG). Kept apart from `branding` so reading
    the settings never loads image bytes. Served only to authenticated members for now; a public, separate asset origin comes with session tokens."""
    __tablename__ = "branding_logos"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"), primary_key=True)
    content_type: Mapped[str] = mapped_column(String(20))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Verification(Base):
    """A verification session created by a business. The end user opens the hosted page with a one-time-visible session token (only its SHA-256 is stored).
    There is NO verification engine yet: status stays PENDING (EXPIRED is derived from expires_at). No documents, selfies or results are stored."""
    __tablename__ = "verifications"
    __table_args__ = (Index("ix_verifications_org_created", "organization_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    env: Mapped[str] = mapped_column(String(8))                                      # test | live (from the key; dashboard = test)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)        # the business's own identifier for its customer
    session_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_key: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("api_keys.id"), ondelete="SET NULL"), nullable=True)
    created_by_user: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    """Append-only (a PostgreSQL trigger rejects UPDATE/DELETE). Never store secrets, tokens or document data here."""
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_id", "organization_id", "id"),)
    id: Mapped[int] = mapped_column(_BIGPK, primary_key=True, autoincrement=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_api_key_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    meta: Mapped[dict] = mapped_column(_JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class RequestLog(Base):
    """One row per API request. No headers, bodies, query strings or IP addresses are stored."""
    __tablename__ = "request_logs"
    __table_args__ = (Index("ix_reqlog_org_time", "organization_id", "created_at"),)
    id: Mapped[int] = mapped_column(_BIGPK, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(40))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    method: Mapped[str] = mapped_column(String(8))
    path: Mapped[str] = mapped_column(String(200))                                   # route template, e.g. /api/v1/organizations/{org_id}
    status: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
