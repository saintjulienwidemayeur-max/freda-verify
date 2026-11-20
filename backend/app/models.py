"""Phase 1 data model. Every tenant-owned row carries organization_id; access is always filtered by it."""
import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, Uuid
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
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class VerificationMedia(Base):
    """A photo uploaded by the end user. `data` is Fernet-encrypted; photos are deleted at `purge_after` (retention) or on request.
    There is no automated analysis of these images: a human reviews them in the dashboard."""
    __tablename__ = "verification_media"
    __table_args__ = (UniqueConstraint("verification_id", "kind"), Index("ix_media_purge", "purge_after"), Index("ix_verification_media_verification_id", "verification_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    verification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("verifications.id"), ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16))                      # document_front | document_back | selfie
    doc_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    content_type: Mapped[str] = mapped_column(String(20))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))                    # of the plain image (integrity / duplicate detection later)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)      # None = keep until deleted


class VerificationCheck(Base):
    """Result of a server-side check on the uploaded photos. `data` is Fernet-encrypted JSON (it contains names, birth date and document number)."""
    __tablename__ = "verification_checks"
    __table_args__ = (UniqueConstraint("verification_id", "kind"), Index("ix_verification_checks_verification_id", "verification_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    verification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("verifications.id"), ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16))                      # mrz
    status: Mapped[str] = mapped_column(String(12))                    # read | unreadable | unavailable
    source: Mapped[str | None] = mapped_column(String(16), nullable=True)   # which photo the text came from
    data: Mapped[bytes] = mapped_column(LargeBinary)
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


class WebhookEndpoint(Base):
    """A URL of the business that receives signed events. The signing secret is stored Fernet-encrypted (it is needed to sign) and shown once at creation."""
    __tablename__ = "webhook_endpoints"
    __table_args__ = (Index("ix_webhook_endpoints_org", "organization_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(500))
    secret_enc: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WebhookDelivery(Base):
    """One attempt series to deliver one event to one endpoint. The payload holds NO personal data (ids, reference, status only)."""
    __tablename__ = "webhook_deliveries"
    __table_args__ = (Index("ix_webhook_deliveries_endpoint", "endpoint_id", "created_at"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    endpoint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("webhook_endpoints.id"), ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    event: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict] = mapped_column(_JSON, default=dict)
    status: Mapped[str] = mapped_column(String(10), default="pending")        # pending | delivered | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PadCampaign(Base):
    """A reusable invitation link for volunteers who donate photos for presentation-attack (PAD) testing. The token lives in the URL fragment; it is stored encrypted so the owner can copy the link again."""
    __tablename__ = "pad_campaigns"
    __table_args__ = (Index("ix_pad_campaigns_org", "organization_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    token_enc: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey(fk("users.id"), ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PadContribution(Base):
    """One volunteer. `code` (p001, p002, ...) is the only identifier in exported file names. Consent is recorded before anything can be uploaded."""
    __tablename__ = "pad_contributions"
    __table_args__ = (UniqueConstraint("campaign_id", "code"), Index("ix_pad_contributions_campaign", "campaign_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("pad_campaigns.id"), ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(8))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    consent_version: Mapped[str] = mapped_column(String(16))
    skin_label: Mapped[str | None] = mapped_column(String(24), nullable=True)      # optional, self-described
    device: Mapped[str | None] = mapped_column(String(80), nullable=True)           # coarse user-agent summary only
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PadSample(Base):
    """A donated photo (Fernet-encrypted). kind: live | print | replay | mask."""
    __tablename__ = "pad_samples"
    __table_args__ = (UniqueConstraint("contribution_id", "kind", "slot"), Index("ix_pad_samples_contribution", "contribution_id"))
    id: Mapped[uuid.UUID] = mapped_column(Uuid, **_PK)
    contribution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("pad_contributions.id"), ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(8))
    slot: Mapped[int] = mapped_column(Integer)
    light: Mapped[str | None] = mapped_column(String(16), nullable=True)           # lighting label chosen from a fixed list
    content_type: Mapped[str] = mapped_column(String(24))
    size: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class DecisionPolicy(Base):
    """Per-organization decision mode. `manual` (default): only a person decides. `auto`: the system approves when every configured check is strong and rejects only for objective
    failures; what is left is `uncertain` and goes to a person (`review`) or is rejected (`reject`, the organization's explicit choice)."""
    __tablename__ = "decision_policies"
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(fk("organizations.id"), ondelete="CASCADE"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(8), default="manual")
    uncertain: Mapped[str] = mapped_column(String(8), default="review")
    face_min: Mapped[float] = mapped_column(Float, default=0.363)
    require_pad: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
