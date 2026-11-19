import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import OrgCtx, Principal, get_current_user, get_principal, org_access
from app.core.errors import AppError, forbidden, not_found
from app.core.security import generate_api_key, new_hex
from app.db.session import get_db
from app.models import ApiKey, AuditLog, Membership, Organization, RequestLog, Role, User, now
from app.schemas import KeyCreatedOut, KeyIn, KeyOut, MemberIn, MemberOut, OrgIn, OrgOut, RoleIn
from app.services import audit

router = APIRouter(tags=["organizations"])


def _org_out(org: Organization, role: str | None) -> OrgOut:
    return OrgOut(id=org.id, name=org.name, slug=org.slug, created_at=org.created_at, role=role)


@router.get("/organizations", response_model=list[OrgOut])
def list_orgs(principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """Dashboard user: every organization they belong to. API key: only the key's own organization."""
    if principal.api_key:
        org = db.get(Organization, principal.api_key.organization_id)
        return [_org_out(org, None)]
    rows = db.execute(select(Organization, Membership.role).join(Membership).where(Membership.user_id == principal.user.id).order_by(Organization.created_at)).all()
    return [_org_out(o, r) for o, r in rows]


@router.post("/organizations", response_model=OrgOut, status_code=201)
def create_org(body: OrgIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    base = "".join(c if c.isalnum() else "-" for c in body.name.lower()).strip("-")[:60] or "org"
    org = Organization(name=body.name, slug=f"{base}-{new_hex(3)}")
    db.add(org)
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role=Role.owner))
    audit.record(db, request, "org.created", org_id=org.id, user_id=user.id, target_type="organization", target_id=org.id)
    db.commit()
    return _org_out(org, Role.owner)


@router.get("/organizations/{org_id}", response_model=OrgOut)
def get_org(ctx: OrgCtx = Depends(org_access("org:read"))):
    return _org_out(ctx.org, ctx.membership.role)


@router.patch("/organizations/{org_id}", response_model=OrgOut)
def rename_org(body: OrgIn, request: Request, ctx: OrgCtx = Depends(org_access("org:update")), db: Session = Depends(get_db)):
    ctx.org.name = body.name
    audit.record(db, request, "org.updated", org_id=ctx.org.id, user_id=ctx.user.id, target_type="organization", target_id=ctx.org.id)
    db.commit()
    return _org_out(ctx.org, ctx.membership.role)


# ───────── members ─────────
@router.get("/organizations/{org_id}/members", response_model=list[MemberOut])
def list_members(ctx: OrgCtx = Depends(org_access("members:read")), db: Session = Depends(get_db)):
    rows = db.execute(select(Membership, User).join(User).where(Membership.organization_id == ctx.org.id).order_by(Membership.created_at)).all()
    return [MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role) for m, u in rows]


@router.post("/organizations/{org_id}/members", response_model=MemberOut, status_code=201)
def add_member(body: MemberIn, request: Request, ctx: OrgCtx = Depends(org_access("members:manage")), db: Session = Depends(get_db)):
    """Phase 1: adds an EXISTING user by e-mail. E-mail invitations come with the e-mail provider."""
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user:
        raise not_found("No user with this e-mail. They must create an account first.")
    if db.scalar(select(Membership.id).where(Membership.organization_id == ctx.org.id, Membership.user_id == user.id)):
        raise AppError(409, "already_member", "This user is already a member")
    db.add(Membership(organization_id=ctx.org.id, user_id=user.id, role=body.role))
    audit.record(db, request, "member.added", org_id=ctx.org.id, user_id=ctx.user.id, target_type="user", target_id=user.id, meta={"role": body.role})
    db.commit()
    return MemberOut(user_id=user.id, email=user.email, full_name=user.full_name, role=body.role)


def _owners(db: Session, org_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(Membership).where(Membership.organization_id == org_id, Membership.role == Role.owner)) or 0


@router.patch("/organizations/{org_id}/members/{user_id}", response_model=MemberOut)
def change_role(user_id: uuid.UUID, body: RoleIn, request: Request, ctx: OrgCtx = Depends(org_access("members:manage")), db: Session = Depends(get_db)):
    m = db.scalar(select(Membership).where(Membership.organization_id == ctx.org.id, Membership.user_id == user_id))
    if not m:
        raise not_found("Member not found")
    if (m.role == Role.owner or body.role == Role.owner) and ctx.membership.role != Role.owner:
        raise forbidden("Only an owner can grant or change the owner role")
    if m.role == Role.owner and body.role != Role.owner and _owners(db, ctx.org.id) <= 1:
        raise AppError(409, "last_owner", "An organization needs at least one owner")
    old, m.role = m.role, body.role
    audit.record(db, request, "member.role_changed", org_id=ctx.org.id, user_id=ctx.user.id, target_type="user", target_id=user_id, meta={"from": old, "to": body.role})
    db.commit()
    u = m.user
    return MemberOut(user_id=u.id, email=u.email, full_name=u.full_name, role=m.role)


@router.delete("/organizations/{org_id}/members/{user_id}", status_code=204)
def remove_member(user_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("members:manage")), db: Session = Depends(get_db)):
    m = db.scalar(select(Membership).where(Membership.organization_id == ctx.org.id, Membership.user_id == user_id))
    if not m:
        raise not_found("Member not found")
    if m.role == Role.owner and ctx.membership.role != Role.owner:
        raise forbidden("Only an owner can remove an owner")
    if m.role == Role.owner and _owners(db, ctx.org.id) <= 1:
        raise AppError(409, "last_owner", "An organization needs at least one owner")
    db.delete(m)
    audit.record(db, request, "member.removed", org_id=ctx.org.id, user_id=ctx.user.id, target_type="user", target_id=user_id)
    db.commit()


# ───────── API keys ─────────
@router.get("/organizations/{org_id}/api-keys", response_model=list[KeyOut])
def list_keys(ctx: OrgCtx = Depends(org_access("keys:read")), db: Session = Depends(get_db)):
    return db.scalars(select(ApiKey).where(ApiKey.organization_id == ctx.org.id).order_by(ApiKey.created_at.desc())).all()


@router.post("/organizations/{org_id}/api-keys", response_model=KeyCreatedOut, status_code=201)
def create_key(body: KeyIn, request: Request, ctx: OrgCtx = Depends(org_access("keys:write")), db: Session = Depends(get_db)):
    secret, prefix, last4, digest = generate_api_key(body.env)
    key = ApiKey(organization_id=ctx.org.id, name=body.name, env=body.env, prefix=prefix, last4=last4, key_hash=digest, created_by=ctx.user.id)
    db.add(key)
    db.flush()
    audit.record(db, request, "api_key.created", org_id=ctx.org.id, user_id=ctx.user.id, target_type="api_key", target_id=key.id, meta={"env": body.env, "prefix": prefix})
    db.commit()
    return KeyCreatedOut.model_validate({**KeyOut.model_validate(key).model_dump(), "secret": secret})


@router.delete("/organizations/{org_id}/api-keys/{key_id}", status_code=204)
def revoke_key(key_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("keys:write")), db: Session = Depends(get_db)):
    key = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.organization_id == ctx.org.id))   # scoped by org: other tenants' ids are "not found"
    if not key:
        raise not_found("API key not found")
    if key.revoked_at is None:
        key.revoked_at = now()
        audit.record(db, request, "api_key.revoked", org_id=ctx.org.id, user_id=ctx.user.id, target_type="api_key", target_id=key.id, meta={"prefix": key.prefix})
        db.commit()


# ───────── audit log + usage ─────────
@router.get("/organizations/{org_id}/audit-logs")
def audit_logs(limit: int = 50, before_id: int | None = None, ctx: OrgCtx = Depends(org_access("audit:read")), db: Session = Depends(get_db)):
    q = select(AuditLog).where(AuditLog.organization_id == ctx.org.id)
    if before_id:
        q = q.where(AuditLog.id < before_id)
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(max(1, min(limit, 200)))).all()
    return [{"id": r.id, "action": r.action, "actor_user_id": r.actor_user_id, "actor_api_key_id": r.actor_api_key_id, "target_type": r.target_type,
             "target_id": r.target_id, "ip": r.ip, "meta": r.meta, "created_at": r.created_at} for r in rows]


@router.get("/organizations/{org_id}/request-logs")
def request_logs(limit: int = 50, before_id: int | None = None, status_class: int | None = None, ctx: OrgCtx = Depends(org_access("keys:read")), db: Session = Depends(get_db)):
    """Newest API requests of the organization (route template, status, latency, key prefix). No bodies, headers or IPs are ever stored."""
    q = select(RequestLog, ApiKey.prefix).join(ApiKey, ApiKey.id == RequestLog.api_key_id, isouter=True).where(RequestLog.organization_id == ctx.org.id)
    if before_id:
        q = q.where(RequestLog.id < before_id)
    if status_class in (2, 3, 4, 5):
        q = q.where(RequestLog.status >= status_class * 100, RequestLog.status < status_class * 100 + 100)
    rows = db.execute(q.order_by(RequestLog.id.desc()).limit(max(1, min(limit, 200)))).all()
    return [{"id": r.id, "created_at": r.created_at, "method": r.method, "path": r.path, "status": r.status, "latency_ms": r.latency_ms,
             "api_key_prefix": prefix, "request_id": r.request_id} for r, prefix in rows]


@router.get("/usage")
def usage(organization_id: uuid.UUID | None = None, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """Requests of the last 30 days for one organization (API key: its own; dashboard user: ?organization_id=, must be a member)."""
    if principal.api_key:
        org_id = principal.api_key.organization_id
    else:
        if not organization_id:
            raise AppError(422, "validation_error", "organization_id is required for dashboard users")
        if not db.scalar(select(Membership.id).where(Membership.organization_id == organization_id, Membership.user_id == principal.user.id)):
            raise not_found("Organization not found")
        org_id = organization_id
    from datetime import timedelta
    since = now() - timedelta(days=30)
    base = (RequestLog.organization_id == org_id, RequestLog.created_at >= since)
    total = db.scalar(select(func.count()).select_from(RequestLog).where(*base)) or 0
    errors = db.scalar(select(func.count()).select_from(RequestLog).where(*base, RequestLog.status >= 400)) or 0
    day = func.date_trunc("day", RequestLog.created_at)
    by_day = db.execute(select(day, func.count()).where(*base).group_by(day).order_by(day)).all()
    return {"organization_id": org_id, "period_days": 30, "requests": total, "errors": errors, "by_day": [{"day": d.date().isoformat(), "requests": n} for d, n in by_day]}
