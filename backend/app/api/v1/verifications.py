"""Verification sessions (no engine yet) and the public hosted-page endpoints.

Business side (API key or dashboard user): create / list / read verifications.
End-user side (session token `fvs_…`, nothing else): read the branding of the organization, download its logo, record consent.
Photos: the end user uploads a document (front, back) and a selfie with the session token; they are stored ENCRYPTED, deleted after the retention
period, and reviewed by a human in the dashboard (status MANUAL_REVIEW → APPROVED / REJECTED). There is NO automated analysis (no OCR, face match,
liveness or AML), no results API and no webhooks.

MRZ reading: after submission, a background task reads the machine-readable zone from the document photos with Tesseract and validates it with the
ICAO 9303 check digits (app.services.mrz). The result is stored encrypted and shown to reviewers as advice; it never decides anything.
"""
import json
import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import PERMS, OrgCtx, Principal, get_principal, org_access
from app.core.errors import AppError, forbidden, not_found, unauthorized
from app.core.security import decrypt_bytes, encrypt_bytes, new_token, sha256
from app.db.session import SessionLocal, get_db
from app.models import Branding, BrandingLogo, Membership, Verification, VerificationCheck, VerificationMedia, now
from app.schemas import BrandingOut, DecisionIn, MediaOut, SessionBranding, SessionOut, VerificationCreatedOut, VerificationIn, VerificationOut
from app.services import audit, ocr
from app.services.images import read_limited, sniff_ok

router = APIRouter(tags=["verifications"])
SESSION_PREFIX = "fvs_"


def _status(v: Verification) -> str:
    return "EXPIRED" if v.status == "PENDING" and v.expires_at <= now() else v.status


def _out(v: Verification, media_count: int = 0) -> dict:
    return {"id": v.id, "status": _status(v), "env": v.env, "reference": v.reference, "consent_given": v.consent_at is not None,
            "created_at": v.created_at, "expires_at": v.expires_at, "submitted_at": v.submitted_at, "decided_at": v.decided_at,
            "decision_reason": v.decision_reason, "media_count": media_count}


def _counts(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    return dict(db.execute(select(VerificationMedia.verification_id, func.count()).where(VerificationMedia.verification_id.in_(ids))
                           .group_by(VerificationMedia.verification_id)).all())


def purge_expired_media(db: Session) -> int:
    """Optional retention (FV_MEDIA_RETENTION_DAYS > 0): photos are deleted once `purge_after` has passed. With the default (0) nothing is ever purged automatically.
    Called on every upload and at startup; the verification record itself stays."""
    n = db.execute(delete(VerificationMedia).where(VerificationMedia.purge_after.is_not(None), VerificationMedia.purge_after <= now())).rowcount
    db.commit()
    return n or 0


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
    c = _counts(db, [v.id for v in rows])
    return [_out(v, c.get(v.id, 0)) for v in rows]


@router.get("/verifications/{verification_id}", response_model=VerificationOut)
def get_verification(verification_id: uuid.UUID, request: Request, organization_id: uuid.UUID | None = None,
                     principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    org_id = _org_for(principal, organization_id, "verifications:read", request, db)
    v = db.scalar(select(Verification).where(Verification.id == verification_id, Verification.organization_id == org_id))
    if not v:
        raise not_found("Verification not found")          # also for another tenant's id
    return _out(v, _counts(db, [v.id]).get(v.id, 0))


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


# ───────── MRZ reading (server-side OCR) ─────────
def run_mrz_check(verification_id: uuid.UUID, db: Session | None = None) -> VerificationCheck | None:
    """Reads the MRZ from the document photos (every document photo is tried, the best reading wins) and stores the encrypted outcome."""
    own = db is None
    db = db or SessionLocal()
    try:
        v = db.get(Verification, verification_id)
        if not v:
            return None
        best: tuple[int, str, ocr.OcrOutcome] | None = None
        outcome = ocr.OcrOutcome("unreadable")
        source = None
        for m in db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(("document_front", "document_back")))):
            o = ocr.read_mrz(decrypt_bytes(m.data))
            if o.status == "unavailable":
                outcome, source, best = o, None, None
                break
            sc = sum(o.result.checks.values()) if o.result else -1
            if o.status == "read" and (best is None or sc > best[0]):
                best = (sc, m.kind, o)
        if best:
            _, source, outcome = best
        payload = {"result": outcome.result.to_dict() if outcome.result else None, "lines": outcome.lines}
        row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "mrz")) or VerificationCheck(
            verification_id=v.id, organization_id=v.organization_id, kind="mrz")
        row.status, row.source, row.data, row.created_at = outcome.status, source, encrypt_bytes(json.dumps(payload).encode()), now()
        db.add(row)
        audit.record(db, None, "verification.mrz_read", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"status": outcome.status})
        db.commit()
        return row
    except Exception:  # noqa: BLE001  a failing reader must never break the submission; the reviewer can re-run it
        db.rollback()
        return None
    finally:
        if own:
            db.close()


def _check_out(row: VerificationCheck | None) -> dict | None:
    if not row:
        return None
    payload = json.loads(decrypt_bytes(row.data))
    return {"status": row.status, "source": row.source, "created_at": row.created_at, "result": payload.get("result"), "lines": payload.get("lines")}


# ───────── photos uploaded by the end user (session token) ─────────
KINDS = ("document_front", "document_back", "selfie")
DOC_TYPES = ("id", "passport", "license")


def _open_for_upload(v: Verification) -> None:
    if v.consent_at is None:
        raise AppError(409, "consent_required", "Consent must be given before uploading photos")
    if v.status != "PENDING":
        raise AppError(409, "session_closed", "This verification was already submitted")


@router.put("/session/media/{kind}", status_code=204)
async def upload_media(kind: str, request: Request, doc_type: str | None = Query(default=None), country: str | None = Query(default=None, pattern=r"^[A-Z]{2}$"),
                       v: Verification = Depends(get_session), db: Session = Depends(get_db)):
    """Raw image bytes (image/jpeg | image/png | image/webp, ≤ FV_MEDIA_MAX_BYTES). Replaces a previous upload of the same kind. Stored encrypted."""
    if kind not in KINDS:
        raise not_found("Unknown kind")
    _open_for_upload(v)
    if kind != "selfie" and doc_type not in DOC_TYPES:
        raise AppError(422, "validation_error", "doc_type must be id, passport or license for documents")
    if kind == "document_back" and doc_type == "passport":
        raise AppError(422, "validation_error", "A passport has no back side")
    s = get_settings()
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    data = await read_limited(request, s.media_max_bytes)
    if not sniff_ok(ctype, data):
        raise AppError(422, "invalid_image", "Use a JPEG, PNG or WebP photo")
    purge_expired_media(db)
    db.execute(delete(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == kind))
    db.add(VerificationMedia(verification_id=v.id, organization_id=v.organization_id, kind=kind, doc_type=doc_type if kind != "selfie" else None,
                             country=country if kind != "selfie" else None, content_type=ctype, size=len(data), sha256=__import__("hashlib").sha256(data).hexdigest(),
                             data=encrypt_bytes(data), purge_after=(now() + timedelta(days=s.media_retention_days)) if s.media_retention_days > 0 else None))
    audit.record(db, request, "verification.media_uploaded", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"kind": kind, "size": len(data)})
    db.commit()
    return Response(status_code=204)


@router.post("/session/complete", status_code=204)
def complete_session(request: Request, background: BackgroundTasks, v: Verification = Depends(get_session), db: Session = Depends(get_db)):
    """Submits the verification for HUMAN review (MANUAL_REVIEW). Requires the selfie and the document photo(s)."""
    _open_for_upload(v)
    rows = {m.kind: m for m in db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id))}
    front = rows.get("document_front")
    need_back = bool(front and front.doc_type in ("id", "license"))
    missing = [k for k in ("document_front", "selfie") if k not in rows] + (["document_back"] if need_back and "document_back" not in rows else [])
    if missing:
        raise AppError(422, "incomplete", "Missing photos: " + ", ".join(missing))
    v.status, v.submitted_at = "MANUAL_REVIEW", now()
    audit.record(db, request, "verification.submitted", org_id=v.organization_id, target_type="verification", target_id=v.id)
    db.commit()
    background.add_task(run_mrz_check, v.id)                  # after the response: the end user never waits for OCR
    return Response(status_code=204)


# ───────── business side: review (dashboard users only, by organization) ─────────
def _owned(db: Session, ctx: OrgCtx, vid: uuid.UUID) -> Verification:
    v = db.scalar(select(Verification).where(Verification.id == vid, Verification.organization_id == ctx.org.id))
    if not v:
        raise not_found("Verification not found")
    return v


@router.get("/organizations/{org_id}/verifications/{verification_id}/media", response_model=list[MediaOut])
def list_media(verification_id: uuid.UUID, ctx: OrgCtx = Depends(org_access("verifications:read")), db: Session = Depends(get_db)):
    v = _owned(db, ctx, verification_id)
    return db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id).order_by(VerificationMedia.kind)).all()


@router.get("/organizations/{org_id}/verifications/{verification_id}/media/{kind}")
def view_media(verification_id: uuid.UUID, kind: str, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Decrypts and returns one photo. Owners/admins only; every view is audited."""
    v = _owned(db, ctx, verification_id)
    m = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == kind))
    if not m:
        raise not_found("No such photo (it may have been deleted)")
    audit.record(db, request, "verification.media_viewed", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id, meta={"kind": kind})
    db.commit()
    return Response(decrypt_bytes(m.data), media_type=m.content_type, headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
                                                                              "Content-Security-Policy": "default-src 'none'; sandbox"})


@router.delete("/organizations/{org_id}/verifications/{verification_id}/media", status_code=204)
def delete_media(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Deletes every uploaded photo of this verification now (the record, status and decision stay)."""
    v = _owned(db, ctx, verification_id)
    n = db.execute(delete(VerificationMedia).where(VerificationMedia.verification_id == v.id)).rowcount
    audit.record(db, request, "verification.media_deleted", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id, meta={"count": n})
    db.commit()
    return Response(status_code=204)


@router.post("/organizations/{org_id}/verifications/{verification_id}/decision", response_model=VerificationOut)
def decide(verification_id: uuid.UUID, body: DecisionIn, request: Request, ctx: OrgCtx = Depends(org_access("verifications:decide")), db: Session = Depends(get_db)):
    """Manual decision by an owner/admin on a submitted verification. This is a human decision, not an automated result."""
    v = _owned(db, ctx, verification_id)
    if v.status != "MANUAL_REVIEW":
        raise AppError(409, "not_reviewable", "Only submitted verifications awaiting review can be decided")
    v.status, v.decided_at, v.decided_by, v.decision_reason = body.decision, now(), ctx.user.id, (body.reason or None)
    audit.record(db, request, "verification.decided", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id, meta={"decision": body.decision})
    db.commit()
    return _out(v, _counts(db, [v.id]).get(v.id, 0))


@router.get("/organizations/{org_id}/verifications/{verification_id}/checks")
def get_checks(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """MRZ reading (names, birth date, document number): personal data, so owners/admins only and every read is audited."""
    v = _owned(db, ctx, verification_id)
    row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "mrz"))
    audit.record(db, request, "verification.checks_viewed", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    return {"engine_available": ocr.available(), "mrz": _check_out(row)}


@router.post("/organizations/{org_id}/verifications/{verification_id}/checks/mrz")
def rerun_mrz(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Re-reads the MRZ now (e.g. after an engine upgrade). Needs at least one stored document photo."""
    v = _owned(db, ctx, verification_id)
    if not db.scalar(select(func.count()).select_from(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(("document_front", "document_back")))):
        raise AppError(409, "no_document", "There is no document photo to read")
    audit.record(db, request, "verification.mrz_rerun", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    row = run_mrz_check(v.id, db)
    return {"engine_available": ocr.available(), "mrz": _check_out(row)}
