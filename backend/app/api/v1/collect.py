"""Volunteer photo collection for presentation-attack (PAD) testing.

Owner/admin creates a CAMPAIGN (a reusable link, token in the URL fragment). A volunteer opens it, must give an explicit consent, receives a personal token and uploads live selfies and
(optionally) photos of a printed photo / a screen. Photos are Fernet-encrypted, exported only by owners/admins (audited), erasable by the volunteer at any time and by the owner.
Nothing here trains or decides anything. The consent text shown to volunteers is a DRAFT that must be reviewed by a lawyer before real use (D9).
"""
import io
import uuid
import zipfile

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import ratelimit
from app.core.config import get_settings
from app.core.deps import OrgCtx, org_access
from app.core.errors import AppError, not_found, unauthorized
from app.core.security import decrypt_bytes, decrypt_secret, encrypt_bytes, encrypt_secret, new_token, sha256
from app.db.session import get_db
from app.models import PadCampaign, PadContribution, PadSample, now
from app.services import audit
from app.services.images import read_limited, sniff_ok

router = APIRouter(tags=["pad-collection"])
CAMPAIGN_PREFIX, CONTRIBUTOR_PREFIX = "fvc_", "fvp_"
KINDS = ("live", "print", "replay", "mask")
MAX_SLOT = 4
LIGHTS = ("window", "indoor", "dim", "outdoor", "backlight", "other")
CONSENT_VERSION = "draft-1"
MAX_BYTES = 2 * 1024 * 1024
MAX_EXPORT_BYTES = 120 * 1024 * 1024


class CampaignIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)


class StartIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    consent: bool
    consent_version: str = Field(max_length=16)
    skin_label: str | None = Field(default=None, max_length=24, pattern=r"^[A-Za-z0-9 ._-]*$")


def _hosted() -> str:
    return get_settings().hosted_url.rstrip("/")


def _campaign_out(db: Session, c: PadCampaign) -> dict:
    n = db.scalar(select(func.count()).select_from(PadContribution).where(PadContribution.campaign_id == c.id)) or 0
    counts = dict(db.execute(select(PadSample.kind, func.count()).join(PadContribution, PadContribution.id == PadSample.contribution_id)
                             .where(PadContribution.campaign_id == c.id).group_by(PadSample.kind)).all())
    return {"id": c.id, "name": c.name, "active": c.active, "created_at": c.created_at, "volunteers": n, "samples": {k: counts.get(k, 0) for k in KINDS},
            "url": f"{_hosted()}/contribute#c={decrypt_secret(c.token_enc)}"}


# ───────── owner / admin (dashboard) ─────────
@router.get("/organizations/{org_id}/pad-campaigns")
def list_campaigns(ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    rows = db.scalars(select(PadCampaign).where(PadCampaign.organization_id == ctx.org.id).order_by(PadCampaign.created_at.desc())).all()
    return [_campaign_out(db, c) for c in rows]


@router.post("/organizations/{org_id}/pad-campaigns", status_code=201)
def create_campaign(body: CampaignIn, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(PadCampaign).where(PadCampaign.organization_id == ctx.org.id)) >= 10:
        raise AppError(409, "limit_reached", "At most 10 campaigns per organization")
    tok = CAMPAIGN_PREFIX + new_token(24)
    c = PadCampaign(organization_id=ctx.org.id, name=body.name, token_hash=sha256(tok), token_enc=encrypt_secret(tok), created_by=ctx.user.id)
    db.add(c)
    db.flush()
    audit.record(db, request, "pad_campaign.created", org_id=ctx.org.id, user_id=ctx.user.id, target_type="pad_campaign", target_id=c.id)
    db.commit()
    return _campaign_out(db, c)


def _camp(db: Session, ctx: OrgCtx, cid: uuid.UUID) -> PadCampaign:
    c = db.scalar(select(PadCampaign).where(PadCampaign.id == cid, PadCampaign.organization_id == ctx.org.id))
    if not c:
        raise not_found("Campaign not found")
    return c


@router.post("/organizations/{org_id}/pad-campaigns/{campaign_id}/active")
def set_active(campaign_id: uuid.UUID, active: bool, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    c = _camp(db, ctx, campaign_id)
    c.active = active
    audit.record(db, request, "pad_campaign.active", org_id=ctx.org.id, user_id=ctx.user.id, target_type="pad_campaign", target_id=c.id, meta={"active": active})
    db.commit()
    return _campaign_out(db, c)


@router.delete("/organizations/{org_id}/pad-campaigns/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """Deletes the campaign and EVERY volunteer photo in it."""
    c = _camp(db, ctx, campaign_id)
    db.delete(c)
    audit.record(db, request, "pad_campaign.deleted", org_id=ctx.org.id, user_id=ctx.user.id, target_type="pad_campaign", target_id=campaign_id)
    db.commit()
    return Response(status_code=204)


@router.get("/organizations/{org_id}/pad-campaigns/{campaign_id}/export")
def export_campaign(campaign_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("media:read")), db: Session = Depends(get_db)):
    """ZIP in the layout of tools.pad_eval: genuine/, attack_print/, attack_replay/, attack_mask/, files named <code>_<light>_<slot>.<ext>. Decrypted biometric data: owner/admin only, audited."""
    c = _camp(db, ctx, campaign_id)
    people = {p.id: p for p in db.scalars(select(PadContribution).where(PadContribution.campaign_id == c.id))}
    buf, total = io.BytesIO(), 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for sm in db.scalars(select(PadSample).where(PadSample.contribution_id.in_(list(people) or [uuid.uuid4()])).order_by(PadSample.created_at)):
            total += sm.size
            if total > MAX_EXPORT_BYTES:
                raise AppError(413, "export_too_large", "Too many photos for one download: delete old ones or export by campaign later")
            folder = "genuine" if sm.kind == "live" else f"attack_{sm.kind}"
            ext = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(sm.content_type, "bin")
            z.writestr(f"{folder}/{people[sm.contribution_id].code}_{sm.light or 'na'}_{sm.slot}.{ext}", decrypt_bytes(sm.data))
        meta = ["code,skin_label,device"] + [f"{p.code},{p.skin_label or ''},{(p.device or '').replace(',', ' ')}" for p in people.values()]
        z.writestr("people.csv", "\n".join(meta))
    audit.record(db, request, "pad_campaign.exported", org_id=ctx.org.id, user_id=ctx.user.id, target_type="pad_campaign", target_id=c.id, meta={"people": len(people)})
    db.commit()
    return Response(buf.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="pad_set_{c.id}.zip"', "Cache-Control": "no-store"})


# ───────── volunteers (public, token only) ─────────
def _bearer(authorization: str | None, prefix: str) -> str:
    tok = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else ""
    if not tok.startswith(prefix) or len(tok) > 120:
        raise unauthorized("Invalid link")
    return tok


def get_campaign(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> PadCampaign:
    tok = _bearer(authorization, CAMPAIGN_PREFIX)
    ratelimit.enforce(f"padc:{sha256(tok)[:16]}", 60)
    c = db.scalar(select(PadCampaign).where(PadCampaign.token_hash == sha256(tok)))
    if not c:
        raise unauthorized("Invalid link")
    request.state.org_id = c.organization_id
    if not c.active:
        raise AppError(410, "campaign_closed", "This collection is closed")
    return c


def get_contributor(request: Request, authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> PadContribution:
    tok = _bearer(authorization, CONTRIBUTOR_PREFIX)
    ratelimit.enforce(f"padp:{sha256(tok)[:16]}", 120)
    p = db.scalar(select(PadContribution).where(PadContribution.token_hash == sha256(tok)))
    if not p:
        raise unauthorized("Invalid link")
    request.state.org_id = p.organization_id
    return p


@router.get("/collect/info")
def info(c: PadCampaign = Depends(get_campaign)):
    return {"name": c.name, "consent_version": CONSENT_VERSION, "lights": list(LIGHTS), "kinds": list(KINDS), "max_slot": MAX_SLOT}


@router.post("/collect/start", status_code=201)
def start(body: StartIn, request: Request, c: PadCampaign = Depends(get_campaign), db: Session = Depends(get_db)):
    """Creates the volunteer. Refused without an explicit consent for the current consent text version."""
    ratelimit.enforce(f"padstart:{c.id}", 30)
    if body.consent is not True or body.consent_version != CONSENT_VERSION:
        raise AppError(422, "consent_required", "An explicit consent is required")
    n = (db.scalar(select(func.count()).select_from(PadContribution).where(PadContribution.campaign_id == c.id)) or 0) + 1
    if n > 500:
        raise AppError(409, "campaign_full", "This collection is full")
    tok = CONTRIBUTOR_PREFIX + new_token(24)
    ua = (request.headers.get("user-agent") or "")[:80]
    p = PadContribution(campaign_id=c.id, organization_id=c.organization_id, code=f"p{n:03d}", token_hash=sha256(tok), consent_version=body.consent_version,
                        skin_label=(body.skin_label or None), device=ua or None)
    db.add(p)
    db.flush()
    audit.record(db, request, "pad_contribution.consented", org_id=c.organization_id, target_type="pad_campaign", target_id=c.id, meta={"code": p.code, "version": CONSENT_VERSION})
    db.commit()
    return {"token": tok, "code": p.code}


@router.get("/collect/me")
def me(p: PadContribution = Depends(get_contributor), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(PadSample.kind, func.count()).where(PadSample.contribution_id == p.id).group_by(PadSample.kind)).all())
    return {"code": p.code, "finished": p.finished_at is not None, "samples": {k: counts.get(k, 0) for k in KINDS}}


@router.put("/collect/samples/{kind}/{slot}", status_code=204)
async def put_sample(kind: str, slot: int, request: Request, light: str | None = None, p: PadContribution = Depends(get_contributor), db: Session = Depends(get_db)):
    if kind not in KINDS or not 1 <= slot <= MAX_SLOT:
        raise not_found("Unknown sample")
    if light is not None and light not in LIGHTS:
        raise AppError(422, "validation_error", "Unknown lighting label")
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    data = await read_limited(request, MAX_BYTES)
    if not sniff_ok(ctype, data):
        raise AppError(422, "invalid_image", "Use a JPEG, PNG or WebP photo")
    db.execute(delete(PadSample).where(PadSample.contribution_id == p.id, PadSample.kind == kind, PadSample.slot == slot))
    db.add(PadSample(contribution_id=p.id, organization_id=p.organization_id, kind=kind, slot=slot, light=light, content_type=ctype, size=len(data), data=encrypt_bytes(data)))
    db.commit()
    return Response(status_code=204)


@router.post("/collect/finish", status_code=204)
def finish(p: PadContribution = Depends(get_contributor), db: Session = Depends(get_db)):
    p.finished_at = now()
    db.commit()
    return Response(status_code=204)


@router.delete("/collect/me", status_code=204)
def erase_me(request: Request, p: PadContribution = Depends(get_contributor), db: Session = Depends(get_db)):
    """The volunteer withdraws: every photo AND the volunteer record are deleted now."""
    org, code, cid = p.organization_id, p.code, p.campaign_id
    db.delete(p)
    audit.record(db, request, "pad_contribution.erased", org_id=org, target_type="pad_campaign", target_id=cid, meta={"code": code})
    db.commit()
    return Response(status_code=204)
