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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import PERMS, OrgCtx, Principal, get_principal, org_access
from app.core.errors import AppError, forbidden, not_found, unauthorized
from app.core.security import decrypt_bytes, encrypt_bytes, new_token, sha256
from app.db.session import SessionLocal, get_db
from app.models import Branding, BrandingLogo, DecisionPolicy, Membership, User, Verification, VerificationCheck, VerificationMedia, now
from app.schemas import BrandingOut, DecisionIn, MediaOut, SessionBranding, SessionOut, VerificationCreatedOut, VerificationIn, VerificationOut
from app.services import audit, decision, docquality, face, forensics, idtext, mailer, ocr, pad, paddle, provenance, vision, webhooks
from app.services.images import read_limited, sniff_ok, sniff_video

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
    if body.expected and any((body.expected.name, body.expected.birth_date, body.expected.document_number)):
        v.expected_enc = encrypt_bytes(json.dumps({"name": body.expected.name or None, "birth_date": body.expected.birth_date.isoformat() if body.expected.birth_date else None,
                                                   "document_number": body.expected.document_number or None}).encode())
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


def _identity(db: Session, v: Verification) -> dict | None:
    """The identity data the system READ from the document (passport MRZ, or the printed text of an ID card). Personal data for the business that asked for the KYC (API key / dashboard);
    never in webhooks. `source` tells how reliable it is: `mrz` (check digits) or `printed_text` (OCR, unverified)."""
    rows = {r.kind: r for r in db.scalars(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind.in_(("mrz", "idfields"))))}
    front = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_front"))
    is_card = bool(front and front.doc_type in ("id", "license"))
    # ID card / licence: the identity is the PRINTED text completed with the back MRZ fields whose own check digit passed (idfields); the raw MRZ of a card is often misread (names, nationality)
    # and must not be returned as 'the identity'. Passports: the MRZ itself.
    if "mrz" in rows and rows["mrz"].status == "read" and not (is_card and "idfields" in rows and rows["idfields"].status == "extracted"):
        res = (json.loads(decrypt_bytes(rows["mrz"].data)).get("result") or {})
        if res:
            return {"source": "mrz", "document_type": "id_card" if is_card else "passport", "full_name": f'{res.get("given_names", "")} {res.get("surname", "")}'.strip(), "birth_date": res.get("birth_date"),
                    "sex": res.get("sex"), "document_number": res.get("document_number"), "expiry_date": res.get("expiry_date"), "issuing_country": res.get("issuing_country"),
                    "nationality": res.get("nationality"), "check_digits_valid": bool(res.get("all_checks_passed"))}
    if "idfields" in rows and rows["idfields"].status == "extracted":
        d = json.loads(decrypt_bytes(rows["idfields"].data))
        f = d.get("fields", {})
        return {"source": "printed_text", "document_type": "id_card", "full_name": f.get("name"), "birth_date": f.get("birth_date"), "document_number": f.get("document_number"), "national_id": f.get("national_id"),
                "expiry_date": f.get("expiry_date"), "issuing_country": d.get("country"), "plausible": d.get("plausible"), "field_sources": d.get("sources"), "unverified": True}
    return None


def _advisory(db: Session, v: Verification) -> dict:
    """Machine-readable summary of the advisory checks WITHOUT any personal data (no names, numbers, dates or scores). The human decision is the `decision` field."""
    rows = {r.kind: r for r in db.scalars(select(VerificationCheck).where(VerificationCheck.verification_id == v.id))}
    doc = "pending"
    if "mrz" in rows:
        m = rows["mrz"]
        res = json.loads(decrypt_bytes(m.data)).get("result")
        if m.status != "read" or not res:
            doc = "unreadable"
        else:
            checks = res.get("checks", {})
            core = all(checks.get(k) for k in ("document_number", "birth_date", "expiry_date"))
            doc = "valid" if res.get("all_checks_passed") else "partial" if core else "invalid"
            if res.get("expired"):
                doc = "expired"
    face_band = None
    if "face" in rows:
        f = json.loads(decrypt_bytes(rows["face"].data))
        face_band = f.get("band") if rows["face"].status == "compared" else rows["face"].status
    # experimental, uncalibrated, not certified: only says that a score exists, never a verdict
    return {"document_checks": doc, "face_similarity": face_band, "liveness": "experimental_not_certified" if "liveness" in rows and rows["liveness"].status == "scored" else "not_performed", "aml": "not_performed"}


@router.get("/verifications/{verification_id}/result")
def get_result(verification_id: uuid.UUID, request: Request, organization_id: uuid.UUID | None = None,
               principal: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    """What a business integration reads after the `verification.approved|rejected` webhook (or by polling). `decision` is set only once a PERSON has approved or
    rejected; `advisory` are automatic checks that never decide. No personal data is returned."""
    org_id = _org_for(principal, organization_id, "verifications:read", request, db)
    v = db.scalar(select(Verification).where(Verification.id == verification_id, Verification.organization_id == org_id))
    if not v:
        raise not_found("Verification not found")
    st = _status(v)
    auto = st in ("APPROVED", "REJECTED") and v.decided_by is None
    reasons = [c for c in (v.decision_reason or "")[len("auto: "):].split(",") if c] if auto and (v.decision_reason or "").startswith("auto: ") else None
    return {"id": v.id, "reference": v.reference, "env": v.env, "status": st, "decision": st if st in ("APPROVED", "REJECTED") else None,
            "decision_source": ("automatic" if auto else "human") if st in ("APPROVED", "REJECTED") else None, "reason_codes": reasons,
            "submitted_at": v.submitted_at, "decided_at": v.decided_at, "identity": _identity(db, v) if v.submitted_at else None,
            "advisory": _advisory(db, v) if v.submitted_at else None}


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
    if v.expires_at <= now() and v.status == "PENDING":          # a submitted or decided verification can still be read (the customer may come back for the result)
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


# ───────── e-mail notification (Brevo) ─────────
def notify_submission(verification_id: uuid.UUID) -> int:
    """Tells the owners and admins of the organization that a customer submitted a verification. No personal data in the message: only the business's own reference
    and a link to the dashboard (the reader signs in to see anything). Returns the number of recipients (0 when mail is disabled or nobody can be notified)."""
    s = get_settings()
    if not s.notify_on_submit or not mailer.enabled():
        return 0
    with SessionLocal() as db:
        v = db.get(Verification, verification_id)
        if not v:
            return 0
        emails = [e for (e,) in db.execute(select(User.email).join(Membership, Membership.user_id == User.id).where(
            Membership.organization_id == v.organization_id, Membership.role.in_(("owner", "admin")), User.is_active.is_(True)))]
        ref = f" (reference: {v.reference})" if v.reference else ""
        ok = mailer.send_email(emails, "A verification is ready for your review",
                               f"A customer submitted their documents{ref}. It is waiting for a manual review in your Freda Verify dashboard.",
                               ("Open the dashboard", f"{s.hosted_url.rstrip('/')}/dashboard/verifications"))
        audit.record(db, None, "verification.notified", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"recipients": len(emails), "sent": ok})
        db.commit()
        return len(emails) if ok else 0


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
        medias = list(db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(("document_front", "document_back")))))
        if any(m.kind == "document_front" and m.doc_type in ("id", "license") for m in medias):
            medias = [m for m in medias if m.kind == "document_back"] or medias       # a card's MRZ is on the BACK: do not spend several OCR passes on the front
        for m in medias:
            o = ocr.read_mrz(decrypt_bytes(m.data))
            if o.status == "unavailable":
                outcome, source, best = o, None, None
                break
            sc = sum(o.result.checks.values()) if o.result else -1
            if o.status == "read" and (best is None or sc > best[0]):
                best = (sc, m.kind, o)
        if best:
            _, source, outcome = best
        payload = {"result": outcome.result.to_dict() if outcome.result else None, "lines": outcome.lines, "agreeing": outcome.agreeing}
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


def run_face_check(verification_id: uuid.UUID, db: Session | None = None) -> VerificationCheck | None:
    """Compares the portrait on the document with the selfie (advisory similarity score, nothing stored but the number). Never decides anything."""
    own = db is None
    db = db or SessionLocal()
    try:
        v = db.get(Verification, verification_id)
        if not v:
            return None
        rows = {m.kind: m for m in db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(("document_front", "selfie"))))}
        if "document_front" not in rows or "selfie" not in rows:
            return None
        out = face.compare(decrypt_bytes(rows["document_front"].data), decrypt_bytes(rows["selfie"].data))
        payload = {"score": out.score, "band": out.band, "doc_faces": out.doc_faces, "selfie_faces": out.selfie_faces, "threshold": face.COSINE_THRESHOLD, "model": "SFace 2021dec + YuNet 2023mar"}
        row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "face")) or VerificationCheck(
            verification_id=v.id, organization_id=v.organization_id, kind="face")
        row.status, row.source, row.data, row.created_at = out.status, "doc+selfie", encrypt_bytes(json.dumps(payload).encode()), now()
        db.add(row)
        audit.record(db, None, "verification.face_compared", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"status": out.status})
        db.commit()
        return row
    except Exception:  # noqa: BLE001  never break the submission
        db.rollback()
        return None
    finally:
        if own:
            db.close()


def run_pad_check(verification_id: uuid.UUID, db: Session | None = None) -> VerificationCheck | None:
    """Experimental presentation-attack score on the SELFIE only (separate from face comparison). Advisory: it never decides anything and is not certified liveness."""
    own = db is None
    db = db or SessionLocal()
    try:
        v = db.get(Verification, verification_id)
        if not v:
            return None
        frames = db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(SELFIE_KINDS)).order_by(VerificationMedia.kind)).all()
        if not frames:
            return None
        outs = [pad.score(decrypt_bytes(m.data)) for m in frames]
        out = pad.aggregate(outs)
        payload = {"real_probability": out.real_probability, "band": out.band, "per_model": out.per_model, "models": list(out.per_model), "calibrated": False,
                   "frames": [{"status": o.status, "real_probability": o.real_probability} for o in outs], "min_frame": out.min_probability}
        row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "liveness")) or VerificationCheck(
            verification_id=v.id, organization_id=v.organization_id, kind="liveness")
        row.status, row.source, row.data, row.created_at = out.status, "selfie", encrypt_bytes(json.dumps(payload).encode()), now()
        db.add(row)
        audit.record(db, None, "verification.pad_scored", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"status": out.status})
        db.commit()
        return row
    except Exception:  # noqa: BLE001  never break the submission
        db.rollback()
        return None
    finally:
        if own:
            db.close()


def _doc_hash(org_id: uuid.UUID, number: str) -> str | None:
    n = "".join(ch for ch in number.upper() if ch.isalnum())
    return sha256(f"{org_id}:{n}") if len(n) >= 6 else None


def run_idtext_check(verification_id: uuid.UUID) -> None:
    """ID card / licence only: reads the printed text once, EXTRACTS the identity (name, birth date, number, expiry: no declared data needed), checks it for plausibility, stores a hash of the
    document number (duplicate detection) and, when the business also declared data, compares it. Stores extracted fields encrypted; never the OCR text. Never raises."""
    try:
        with SessionLocal() as db:
            v = db.get(Verification, verification_id)
            front = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_front")) if v else None
            if not v or not front or front.doc_type not in ("id", "license"):
                return
            front_img = decrypt_bytes(front.data)
            boxes = paddle.read_boxes(front_img)                              # ONE PaddleOCR pass gives both the layout (boxes) and the text
            ptext = paddle.boxes_to_text(boxes) if boxes is not None else None
            layout = (idtext.extract_boxes(boxes) or idtext.extract_boxes_generic(boxes)) if boxes else {}             # Haitian CIN layout (label -> value by position): measured far better than line text on real cards
            pf = {**(idtext.extract(ptext) if ptext else {}), **layout}
            fast = bool(pf) and all(idtext.plausible(pf).get(k) for k in ("name", "birth_date", "document_number")) and not v.expected_enc
            ttext = None if fast else idtext.read_text(front_img)          # FAST PATH: PaddleOCR already gave a plausible name, birth date and number: skip the slow Tesseract pass (up to 25 s)
            text = ptext or ttext
            back = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_back"))
            mrz_row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "mrz"))
            mrz_res = (_load(mrz_row) or {}).get("result") if mrz_row and mrz_row.status == "read" else None
            back_img = decrypt_bytes(back.data) if back else None
            back_text = (paddle.read_text(back_img) or idtext.read_text(back_img)) if back_img else None
            printed, printed_src, agree = idtext.combine_engines(ptext, ttext)
            for k, val in layout.items():
                if val and k in ("name", "first_name", "surname", "birth_date", "expiry_date", "document_number", "card_number", "national_id"):
                    printed[k], printed_src[k] = val, "paddle_layout"
            fields, sources = idtext.merge_trusted(printed, back_text, mrz_res, printed_src)
            if text:
                if v.expected_enc:
                    exp = json.loads(decrypt_bytes(v.expected_enc))
                    cands = [idtext.compare(exp, t) for t in (ptext, ttext) if t]
                    cmp_status, cmp_payload = "compared", max(cands, key=lambda c: (c.get("matched", 0), c.get("name", 0)))
                else:
                    cmp_status, cmp_payload = "no_expected", {}
            else:
                cmp_status, cmp_payload = "unreadable", {}
            engines = [n for n, t in (("paddle", ptext), ("tesseract", ttext)) if t]
            ext_payload = {"fields": fields, "plausible": idtext.plausible(fields) if fields else None, "sources": sources, "engines": engines, "engines_agree": agree, "country": front.country}
            if fields.get("national_id") or fields.get("document_number"):
                v.doc_hash = _doc_hash(v.organization_id, fields.get("national_id") or fields["document_number"])      # the permanent national number when printed (the card number changes on reissue)
            for kind, status, payload in (("idtext", cmp_status, cmp_payload), ("idfields", "extracted" if fields else "unreadable", ext_payload)):
                row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == kind)) or VerificationCheck(
                    verification_id=v.id, organization_id=v.organization_id, kind=kind)
                row.status, row.source, row.data, row.created_at = status, "document_front", encrypt_bytes(json.dumps(payload).encode()), now()
                db.add(row)
            audit.record(db, None, "verification.idtext_checked", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"status": cmp_status, "extracted": bool(fields)})
            db.commit()
    except Exception:  # noqa: BLE001
        return


def run_forensics_check(verification_id: uuid.UUID, db: Session | None = None) -> VerificationCheck | None:
    """Pixel hints (photo of a screen, local edit) on the document photos. ADVISORY: a flag sends the case to a person, it never rejects. Thresholds uncalibrated (see services/forensics.py)."""
    own = db is None
    db = db or SessionLocal()
    try:
        v = db.get(Verification, verification_id)
        if not v:
            return None
        sides = db.scalars(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind.in_(("document_front", "document_back"))).order_by(VerificationMedia.kind)).all()
        if not sides:
            return None
        per = {m.kind: forensics.analyse(decrypt_bytes(m.data)) for m in sides}
        reasons = sorted({r for o in per.values() for r in o.get("reasons", [])})
        scored = [o for o in per.values() if o.get("status") == "scored"]
        payload = {"per_side": per, "reasons": reasons, "flagged": bool(reasons), "calibrated": False}
        row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "forensics")) or VerificationCheck(
            verification_id=v.id, organization_id=v.organization_id, kind="forensics")
        row.status, row.source, row.data, row.created_at = ("scored" if scored else "unavailable"), "documents", encrypt_bytes(json.dumps(payload).encode()), now()
        db.add(row)
        audit.record(db, None, "verification.forensics_scored", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"flagged": bool(reasons)})
        db.commit()
        return row
    except Exception:  # noqa: BLE001  never break the submission
        db.rollback()
        return None
    finally:
        if own:
            db.close()


def run_crosscheck(verification_id: uuid.UUID, db: Session | None = None) -> VerificationCheck | None:
    """PASSPORTS: the PRINTED text of the data page must agree with the machine-readable zone (name, birth date, number). An edit of the printed fields that did not touch the MRZ (or the
    other way round) shows up as a disagreement. Only when the MRZ was read with every check digit valid. Stores match results only (never the OCR text). Advisory: a mismatch sends the case
    to a person (OCR errors on the printed text also cause mismatches). Does NOT detect a forgery that changes both consistently."""
    own = db is None
    db = db or SessionLocal()
    try:
        v = db.get(Verification, verification_id)
        front = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_front")) if v else None
        mrz_row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "mrz")) if v else None
        if not v or not front or front.doc_type != "passport" or not mrz_row or mrz_row.status != "read":
            return None
        res = (_load(mrz_row) or {}).get("result") or {}
        if not res.get("all_checks_passed"):
            return None
        img = decrypt_bytes(front.data)
        text = paddle.read_text(img) or idtext.read_text(img) or ""
        expected = {"name": f"{res.get('given_names', '')} {res.get('surname', '')}".strip(), "document_number": res.get("document_number"), "birth_date": res.get("birth_date")}
        out = idtext.compare({k: x for k, x in expected.items() if x}, text) if text else {"fields": 0, "matched": 0}
        status = "compared" if out.get("fields", 0) >= 2 else "unreadable"
        row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "crosscheck")) or VerificationCheck(
            verification_id=v.id, organization_id=v.organization_id, kind="crosscheck")
        row.status, row.source, row.data, row.created_at = status, "printed_vs_mrz", encrypt_bytes(json.dumps(out).encode()), now()
        db.add(row)
        audit.record(db, None, "verification.crosschecked", org_id=v.organization_id, target_type="verification", target_id=v.id, meta={"status": status, "matched": out.get("matched"), "fields": out.get("fields")})
        db.commit()
        return row
    except Exception:  # noqa: BLE001  never break the submission
        db.rollback()
        return None
    finally:
        if own:
            db.close()


def run_pipeline(verification_id: uuid.UUID) -> None:
    """After submission: MRZ reading, face comparison and the experimental PAD score, one after the other (one process, little RAM), then the automatic decision if the organization enabled it."""
    run_mrz_check(verification_id)
    run_idtext_check(verification_id)
    run_crosscheck(verification_id)
    run_face_check(verification_id)
    run_pad_check(verification_id)
    run_forensics_check(verification_id)
    auto_decide(verification_id)


def _load(row) -> dict | None:
    return json.loads(decrypt_bytes(row.data)) if row else None


def auto_decide(verification_id: uuid.UUID) -> str | None:
    """Applies the organization's decision policy to a submitted verification. Does nothing in `manual` mode. Never raises. Returns the new status or None."""
    try:
        with SessionLocal() as db:
            v = db.get(Verification, verification_id)
            if not v:
                return None
            pol = _policy_values(db.get(DecisionPolicy, v.organization_id))
            if pol["mode"] != "auto" or v.status != "MANUAL_REVIEW":
                return None
            rows = {r.kind: r for r in db.scalars(select(VerificationCheck).where(VerificationCheck.verification_id == v.id))}
            front = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_front"))
            mrz_row = _load(rows.get("mrz")) or {}
            if mrz_row.get("result") and rows["mrz"].status == "read" and not v.doc_hash:
                v.doc_hash = _doc_hash(v.organization_id, mrz_row["result"].get("document_number", ""))
            dup = bool(v.doc_hash and db.scalar(select(func.count()).select_from(Verification).where(
                Verification.organization_id == v.organization_id, Verification.doc_hash == v.doc_hash, Verification.id != v.id,
                Verification.status.in_(("APPROVED", "MANUAL_REVIEW")))))
            idf = {"status": rows["idfields"].status, **_load(rows["idfields"])} if rows.get("idfields") else None
            verdict = decision.decide(duplicate=dup, idfields=idf, face_min=pol["face_min"], require_pad=pol["require_pad"], uncertain=pol["uncertain"], id_cards=pol["id_cards"],
                                      idtext=({"status": rows["idtext"].status, **_load(rows["idtext"])} if rows.get("idtext") else None), mrz=mrz_row.get("result") if rows.get("mrz") and rows["mrz"].status == "read" else None,
                                      agreeing=int(mrz_row.get("agreeing", 0)), face=({"status": rows["face"].status, **_load(rows["face"])} if rows.get("face") else None),
                                      pad=({"status": rows["liveness"].status, **_load(rows["liveness"])} if rows.get("liveness") else None), doc_type=front.doc_type if front else None,
                                      forensics=_load(rows["forensics"]) if rows.get("forensics") else None,
                                      crosscheck=({"status": rows["crosscheck"].status, **_load(rows["crosscheck"])} if rows.get("crosscheck") else None),
                                      has_video=bool(db.scalar(select(func.count()).select_from(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == VIDEO_KIND))))
            reason = ("auto: " + ",".join(verdict.codes))[:200]
            hooks: list[uuid.UUID] = []
            if verdict.decision:
                v.status, v.decided_at, v.decided_by, v.decision_reason = verdict.decision, now(), None, reason
                hooks = webhooks.queue(db, v.organization_id, f"verification.{verdict.decision.lower()}", v)
            else:
                v.decision_reason = ("auto: needs review (" + ",".join(verdict.codes) + ")")[:200]
            audit.record(db, None, "verification.auto_decided" if verdict.decision else "verification.auto_review", org_id=v.organization_id, target_type="verification", target_id=v.id,
                         meta={"decision": verdict.decision, "codes": verdict.codes, "repeat_document": dup})
            db.commit()
        for h in hooks:
            webhooks.deliver(h)
        return verdict.decision
    except Exception:  # noqa: BLE001  a decision problem must never break the submission: the verification simply stays in manual review
        return None


def _face_out(row: VerificationCheck | None) -> dict | None:
    if not row:
        return None
    return {"status": row.status, "created_at": row.created_at, **json.loads(decrypt_bytes(row.data))}


def _check_out(row: VerificationCheck | None) -> dict | None:
    if not row:
        return None
    payload = json.loads(decrypt_bytes(row.data))
    return {"status": row.status, "source": row.source, "created_at": row.created_at, "result": payload.get("result"), "lines": payload.get("lines"), "agreeing": payload.get("agreeing", 0)}


# ───────── photos uploaded by the end user (session token) ─────────
KINDS = ("document_front", "document_back", "selfie", "selfie_2", "selfie_3", "selfie_video")     # selfie_2/3: extra frontal frames for the experimental PAD score (optional)
SELFIE_KINDS = ("selfie", "selfie_2", "selfie_3")
VIDEO_KIND = "selfie_video"          # short clip of the head-turn challenge, for the HUMAN reviewer (no automatic analysis)
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
    if kind not in SELFIE_KINDS and kind != VIDEO_KIND and doc_type not in DOC_TYPES:
        raise AppError(422, "validation_error", "doc_type must be id, passport or license for documents")
    if kind == "document_back" and doc_type == "passport":
        raise AppError(422, "validation_error", "A passport has no back side")
    s = get_settings()
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if kind == VIDEO_KIND:
        data = await read_limited(request, s.media_video_max_bytes)
        if not sniff_video(ctype, data):
            raise AppError(422, "invalid_video", "Use a short WebM or MP4 video")
    else:
        data = await read_limited(request, s.media_max_bytes)
        if not sniff_ok(ctype, data):
            raise AppError(422, "invalid_image", "Use a JPEG, PNG or WebP photo")
    if kind == "document_front" and doc_type == "passport" and ocr.available():
        # authoritative content gate: a passport photo page must contain machine-readable-zone text. The in-browser check is only a heuristic (a real national ID card
        # passed it in testing), so the server refuses a photo in which no MRZ-shaped text can be read (the check digits are NOT required here: OCR may be imperfect).
        found = await run_in_threadpool(ocr.read_mrz, data, True)
        if found.status != "read":
            raise AppError(422, "mrz_not_found", "The two lines of characters at the bottom of the passport page could not be read")
    if kind in ("document_front", "document_back") and s.reject_non_camera_documents:
        bad = provenance.check(data, ctype)
        if bad:
            raise AppError(422, "not_camera_photo" if bad == "not_camera_photo" else "edited_image", "Use a photo taken with the camera: screenshots and edited images are not accepted", details=[{"reason": bad}])
    if kind in ("document_front", "document_back") and doc_type in ("id", "license"):
        why = await run_in_threadpool(docquality.check, data)
        if why:
            raise AppError(422, "unreadable_document", "The photo is not clear enough to read: retake it in a bright place, flat and steady", details=[{"reason": why}])
    purge_expired_media(db)
    db.execute(delete(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == kind))
    db.add(VerificationMedia(verification_id=v.id, organization_id=v.organization_id, kind=kind, doc_type=doc_type if kind not in SELFIE_KINDS and kind != VIDEO_KIND else None,
                             country=country if kind not in SELFIE_KINDS and kind != VIDEO_KIND else None, content_type=ctype, size=len(data), sha256=__import__("hashlib").sha256(data).hexdigest(),
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
    hooks = webhooks.queue(db, v.organization_id, "verification.submitted", v)
    db.commit()
    for h in hooks:
        background.add_task(webhooks.deliver, h)
    background.add_task(run_pipeline, v.id)                   # after the response: the end user never waits for OCR / face / PAD; then the automatic decision if enabled
    background.add_task(notify_submission, v.id)
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
def decide(verification_id: uuid.UUID, body: DecisionIn, request: Request, background: BackgroundTasks, ctx: OrgCtx = Depends(org_access("verifications:decide")), db: Session = Depends(get_db)):
    """Manual decision by an owner/admin on a submitted verification. This is a human decision, not an automated result."""
    v = _owned(db, ctx, verification_id)
    automatic = v.status in ("APPROVED", "REJECTED") and v.decided_by is None and v.decided_at is not None
    if v.status != "MANUAL_REVIEW" and not automatic:
        raise AppError(409, "not_reviewable", "Only submitted verifications awaiting review, or decided automatically, can be decided by a person")
    v.status, v.decided_at, v.decided_by, v.decision_reason = body.decision, now(), ctx.user.id, (body.reason or None)
    audit.record(db, request, "verification.decided", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id, meta={"decision": body.decision, "override_of_automatic": automatic})
    hooks = webhooks.queue(db, ctx.org.id, f"verification.{body.decision.lower()}", v)
    db.commit()
    for h in hooks:
        background.add_task(webhooks.deliver, h)
    return _out(v, _counts(db, [v.id]).get(v.id, 0))


@router.get("/organizations/{org_id}/verifications/{verification_id}/checks")
def get_checks(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """MRZ reading (names, birth date, document number): personal data, so owners/admins only and every read is audited."""
    v = _owned(db, ctx, verification_id)
    row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "mrz"))
    audit.record(db, request, "verification.checks_viewed", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    frow = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "face"))
    lrow = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "liveness"))
    return {"engine_available": ocr.available(), "mrz": _check_out(row), "face_available": face.available(), "face": _face_out(frow),
            "pad_available": pad.available(), "pad": _face_out(lrow),
            "idtext": _face_out(db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "idtext"))),
            "idfields": _face_out(db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "idfields"))),
            "forensics": _face_out(db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "forensics"))),
            "vision_available": vision.available(),
            "vision": _face_out(db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "vision")))}


@router.post("/organizations/{org_id}/verifications/{verification_id}/checks/face")
def rerun_face(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Re-runs the advisory face comparison now (needs the document front and the selfie)."""
    v = _owned(db, ctx, verification_id)
    have = {k for (k,) in db.execute(select(VerificationMedia.kind).where(VerificationMedia.verification_id == v.id))}
    if not {"document_front", "selfie"} <= have:
        raise AppError(409, "missing_photos", "The document front and the selfie are both needed")
    audit.record(db, request, "verification.face_rerun", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    row = run_face_check(v.id, db)
    return {"face_available": face.available(), "face": _face_out(row)}


@router.post("/organizations/{org_id}/verifications/{verification_id}/checks/pad")
def rerun_pad(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Re-runs the experimental presentation-attack score on the selfie."""
    v = _owned(db, ctx, verification_id)
    if "selfie" not in {k for (k,) in db.execute(select(VerificationMedia.kind).where(VerificationMedia.verification_id == v.id))}:
        raise AppError(409, "missing_photos", "The selfie is needed")
    audit.record(db, request, "verification.pad_rerun", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    return {"pad_available": pad.available(), "pad": _face_out(run_pad_check(v.id, db))}


@router.post("/organizations/{org_id}/verifications/{verification_id}/checks/vision")
def run_vision(verification_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """On demand (reviewer): the self-hosted vision model describes the document front. ADVISORY ONLY: never used by the automatic decision, stored encrypted, can be wrong."""
    v = _owned(db, ctx, verification_id)
    if not vision.available():
        raise AppError(503, "vision_not_configured", "The private Vision AI service is not configured")
    front = db.scalar(select(VerificationMedia).where(VerificationMedia.verification_id == v.id, VerificationMedia.kind == "document_front"))
    if not front:
        raise AppError(409, "missing_photos", "The document photo is needed")
    dt = {"id": "id_card", "license": "driver_license", "passport": "passport"}.get(front.doc_type or "", "other")
    try:
        out = vision.analyze(decrypt_bytes(front.data), dt)
        status = out.get("status", "failed") if isinstance(out.get("status"), str) else "failed"
        payload = {k: out.get(k) for k in ("status", "document_type", "extracted_text", "fields", "image_quality", "missing_information", "suspicious_visual_anomalies", "confidence", "model", "engine")}
    except vision.VisionUnavailable:
        status, payload = "unavailable", {}
    row = db.scalar(select(VerificationCheck).where(VerificationCheck.verification_id == v.id, VerificationCheck.kind == "vision")) or VerificationCheck(
        verification_id=v.id, organization_id=v.organization_id, kind="vision")
    row.status, row.source, row.data, row.created_at = status, "document_front", encrypt_bytes(json.dumps(payload).encode()), now()
    db.add(row)
    audit.record(db, request, "verification.vision_read", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id, meta={"status": status})
    db.commit()
    return {"vision_available": True, "vision": _face_out(row)}


@router.post("/organizations/{org_id}/verifications/{verification_id}/recheck", status_code=202)
def recheck(verification_id: uuid.UUID, request: Request, background: BackgroundTasks, ctx: OrgCtx = Depends(org_access("verifications:decide")), db: Session = Depends(get_db)):
    """Runs every automatic check again and then the automatic decision (if the organization enabled it). Useful when the server restarted before the checks finished (nothing is retried after a restart)."""
    v = _owned(db, ctx, verification_id)
    if v.status != "MANUAL_REVIEW":
        raise AppError(409, "not_reviewable", "Only verifications awaiting review can be re-checked")
    audit.record(db, request, "verification.rechecked", org_id=ctx.org.id, user_id=ctx.user.id, target_type="verification", target_id=v.id)
    db.commit()
    background.add_task(run_pipeline, v.id)
    return {"started": True}


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


class PolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(pattern=r"^(manual|auto)$")
    uncertain: str = Field(pattern=r"^(review|reject)$")
    face_min: float = Field(ge=0.2, le=0.9)
    require_pad: bool
    id_cards: str = Field(default="face_and_extracted", pattern=r"^(review|face_and_extracted|face_and_data|face_only)$")


def _policy_values(p: DecisionPolicy | None) -> dict:
    """The organization's saved policy, or the platform defaults (FV_DECISION_DEFAULT_MODE / FV_DECISION_DEFAULT_ID_CARDS: automatic, ID cards need face + declared data) when it never saved one."""
    st = get_settings()
    return {"mode": p.mode if p else st.decision_default_mode, "uncertain": p.uncertain if p else "review", "face_min": p.face_min if p else 0.363,
            "require_pad": p.require_pad if p else False, "id_cards": p.id_cards if p else st.decision_default_id_cards}


def _policy_out(p: DecisionPolicy | None) -> dict:
    return _policy_values(p)


@router.get("/organizations/{org_id}/decision-policy")
def get_policy(ctx: OrgCtx = Depends(org_access("verifications:read")), db: Session = Depends(get_db)):
    return _policy_out(db.get(DecisionPolicy, ctx.org.id))


@router.put("/organizations/{org_id}/decision-policy")
def put_policy(body: PolicyIn, request: Request, ctx: OrgCtx = Depends(org_access("verifications:decide")), db: Session = Depends(get_db)):
    """Owner/admin. `auto` makes the SYSTEM approve/reject submitted verifications by the rules in app.services.decision; every automatic decision is audited and can be overridden by a person."""
    p = db.get(DecisionPolicy, ctx.org.id) or DecisionPolicy(organization_id=ctx.org.id)
    p.mode, p.uncertain, p.face_min, p.require_pad, p.id_cards, p.updated_at = body.mode, body.uncertain, round(body.face_min, 3), body.require_pad, body.id_cards, now()
    db.add(p)
    audit.record(db, request, "decision_policy.updated", org_id=ctx.org.id, user_id=ctx.user.id, meta={"mode": p.mode, "uncertain": p.uncertain, "face_min": p.face_min, "require_pad": p.require_pad, "id_cards": p.id_cards})
    db.commit()
    return _policy_out(p)
