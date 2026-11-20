"""Verification sessions (no engine yet) and the public hosted-page endpoints.

Business side (API key or dashboard user): create / list / read verifications.
End-user side (session token `fvs_…`, nothing else): read the branding of the organization, download its logo, record consent.
Documents, selfies, results and webhooks are NOT implemented: a verification stays PENDING until it expires.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import PERMS, Principal, get_principal
from app.core.errors import AppError, forbidden, not_found, unauthorized
from app.core.security import new_token, sha256
from app.db.session import get_db
from app.models import Branding, BrandingLogo, Membership, Verification, now
from app.schemas import BrandingOut, SessionBranding, SessionOut, VerificationCreatedOut, VerificationIn, VerificationOut
from app.services import audit

router = APIRouter(tags=["verifications"])
SESSION_PREFIX = "fvs_"


def _status(v: Verification) -> str:
    return "EXPIRED" if v.status == "PENDING" and v.expires_at <= now() else v.status


def _out(v: Verification) -> dict:
    return {"id": v.id, "status": _status(v), "env": v.env, "reference": v.reference, "consent_given": v.consent_at is not None,
            "created_at": v.created_at, "expires_at": v.expires_at}


def _org_for(principal: Principal, organization_id: uuid.UUID | None, perm: str, request: Request, db: Session) -> uuid.UUID:
    """API keys act inside their own organization (read and create). Dashboard users must be members with the permission."""
    if principal.api_key:
        return principal.api_key.organization_id
    if not organization_id:
        raise AppError(422, "validation_error", "organization_id is required for dashboard users")
    m = db.scalar(select(Membership).where(Membership.organization_id == organization_id, Membership.user_id == principal.user.id))
    if not m:
        raise not_found("Organization not found")
    if m.role not in PERMS[perm]:
        raise forbidden()
    request.state.org_id = organization_id
    return organization_id


@router.post("/verifications", response_model=VerificationCreatedOut, status_code=201)
def create_verification(body: VerificationIn, request: Request, principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    org_id = _org_for(principal, body.organization_id, "verifications:write", request, db)
    s = get_settings()
    token = SESSION_PREFIX + new_token(32)
    v = Verification(organization_id=org_id, env=principal.api_key.env if principal.api_key else "test", reference=(body.reference or None),
                     session_hash=sha256(token), expires_at=now() + timedelta(minutes=body.expires_in_minutes or s.session_ttl_minutes),
                     created_by_key=principal.api_key.id if principal.api_key else None, created_by_user=principal.user.id if principal.user else None)
    db.add(v)
    db.flush()
    audit.record(db, request, "verification.created", org_id=org_id, user_id=principal.user.id if principal.user else None,
                 api_key_id=principal.api_key.id if principal.api_key else None, target_type="verification", target_id=v.id, meta={"env": v.env})
    db.commit()
    return {**_out(v), "session_token": token, "url": f"{s.hosted_url.rstrip('/')}/verify#s={token}"}


@router.get("/verifications", response_model=list[VerificationOut])
def list_verifications(request: Request, organization_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0,
                       principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    org_id = _org_for(principal, organization_id, "verifications:read", request, db)
    rows = db.scalars(select(Verification).where(Verification.organization_id == org_id).order_by(Verification.created_at.desc())
                      .limit(max(1, min(limit, 100))).offset(max(0, offset))).all()
    return [_out(v) for v in rows]


@router.get("/verifications/{verification_id}", response_model=VerificationOut)
def get_verification(verification_id: uuid.UUID, request: Request, organization_id: uuid.UUID | None = None,
                     principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    org_id = _org_for(principal, organization_id, "verifications:read", request, db)
    v = db.scalar(select(Verification).where(Verification.id == verification_id, Verification.organization_id == org_id))
    if not v:
        raise not_found("Verification not found")          # also for another tenant's id
    return _out(v)


# ───────── end-user side: authenticated by the session token only ─────────
def get_session(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Verification:
    tok = (authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else "")
    if not tok.startswith(SESSION_PREFIX) or len(tok) > 120:
        raise unauthorized("Invalid session")
    h = sha256(tok)
    ratelimit.enforce(f"sess:{h[:16]}", get_settings().session_rate_limit)
    v = db.scalar(select(Verification).where(Verification.session_hash == h))
    if not v:
        raise unauthorized("Invalid session")
    request.state.org_id = v.organization_id
    if v.expires_at <= now():
        raise AppError(410, "session_expired", "This verification link has expired")
    return v


@router.get("/session", response_model=SessionOut)
def read_session(v: Verification = Depends(get_session), db: Session = Depends(get_db)):
    """What the hosted page needs: the organization's public branding (never its redirect URL or domain, never any key) and the session state."""
    b = db.get(Branding, v.organization_id)
    d = BrandingOut() if not b else BrandingOut(name=b.name, color=b.color, theme=b.theme, shape=b.shape, lang=b.lang, title=b.title, subtitle=b.subtitle,
                                                 support_email=b.support_email, docs=list(dict.fromkeys(b.docs)), hide_powered=b.hide_powered)
    branding = SessionBranding(name=d.name, color=d.color, theme=d.theme, shape=d.shape, lang=d.lang, title=d.title, subtitle=d.subtitle,
                               support_email=d.support_email, docs=list(d.docs), hide_powered=d.hide_powered,
                               has_logo=db.get(BrandingLogo, v.organization_id) is not None)
    return SessionOut(verification_id=v.id, status=_status(v), expires_at=v.expires_at, consent_given=v.consent_at is not None, branding=branding)


@router.get("/session/logo")
def session_logo(v: Verification = Depends(get_session), db: Session = Depends(get_db)):
    row = db.get(BrandingLogo, v.organization_id)
    if not row:
        raise not_found("No logo")
    return Response(row.data, media_type=row.content_type, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300",
                                                                    "Content-Security-Policy": "default-src 'none'; sandbox"})


@router.post("/session/consent", status_code=204)
def give_consent(request: Request, v: Verification = Depends(get_session), db: Session = Depends(get_db)):
    if v.consent_at is None:
        v.consent_at = now()
        audit.record(db, request, "verification.consent_given", org_id=v.organization_id, target_type="verification", target_id=v.id)
        db.commit()
    return Response(status_code=204)
