"""Webhook endpoints of an organization (dashboard users, owner/admin only). Events are delivered by app.services.webhooks."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.deps import OrgCtx, org_access
from app.core.errors import AppError, not_found
from app.core.security import encrypt_secret, new_token
from app.db.session import get_db
from app.models import Verification, WebhookDelivery, WebhookEndpoint
from app.schemas import DeliveryOut, WebhookCreatedOut, WebhookIn, WebhookOut
from app.services import audit, webhooks

router = APIRouter(prefix="/organizations/{org_id}/webhooks", tags=["webhooks"])
MAX_ENDPOINTS = 5


def _ep(db: Session, ctx: OrgCtx, wid: uuid.UUID) -> WebhookEndpoint:
    ep = db.scalar(select(WebhookEndpoint).where(WebhookEndpoint.id == wid, WebhookEndpoint.organization_id == ctx.org.id))
    if not ep:
        raise not_found("Webhook not found")
    return ep


@router.get("", response_model=list[WebhookOut])
def list_endpoints(ctx: OrgCtx = Depends(org_access("webhooks:read")), db: Session = Depends(get_db)):
    return db.scalars(select(WebhookEndpoint).where(WebhookEndpoint.organization_id == ctx.org.id).order_by(WebhookEndpoint.created_at)).all()


@router.post("", response_model=WebhookCreatedOut, status_code=201)
async def create_endpoint(body: WebhookIn, request: Request, ctx: OrgCtx = Depends(org_access("webhooks:write")), db: Session = Depends(get_db)):
    if db.scalar(select(func.count()).select_from(WebhookEndpoint).where(WebhookEndpoint.organization_id == ctx.org.id)) >= MAX_ENDPOINTS:
        raise AppError(409, "limit_reached", f"At most {MAX_ENDPOINTS} webhook endpoints per organization")
    try:
        await run_in_threadpool(webhooks.check_url, body.url)
    except webhooks.UnsafeUrl as e:
        raise AppError(422, "invalid_url", str(e)) from e
    secret = "whsec_" + new_token(32)
    ep = WebhookEndpoint(organization_id=ctx.org.id, url=body.url, description=body.description, secret_enc=encrypt_secret(secret), created_by=ctx.user.id)
    db.add(ep)
    db.flush()
    audit.record(db, request, "webhook.created", org_id=ctx.org.id, user_id=ctx.user.id, target_type="webhook", target_id=ep.id)
    db.commit()
    return {"id": ep.id, "url": ep.url, "description": ep.description, "active": ep.active, "created_at": ep.created_at, "secret": secret}


@router.delete("/{webhook_id}", status_code=204)
def delete_endpoint(webhook_id: uuid.UUID, request: Request, ctx: OrgCtx = Depends(org_access("webhooks:write")), db: Session = Depends(get_db)):
    ep = _ep(db, ctx, webhook_id)
    db.delete(ep)
    audit.record(db, request, "webhook.deleted", org_id=ctx.org.id, user_id=ctx.user.id, target_type="webhook", target_id=webhook_id)
    db.commit()
    return Response(status_code=204)


@router.get("/{webhook_id}/deliveries", response_model=list[DeliveryOut])
def deliveries(webhook_id: uuid.UUID, ctx: OrgCtx = Depends(org_access("webhooks:read")), db: Session = Depends(get_db)):
    ep = _ep(db, ctx, webhook_id)
    return db.scalars(select(WebhookDelivery).where(WebhookDelivery.endpoint_id == ep.id).order_by(WebhookDelivery.created_at.desc()).limit(50)).all()


@router.post("/{webhook_id}/test", response_model=DeliveryOut, status_code=202)
def send_test(webhook_id: uuid.UUID, background: BackgroundTasks, ctx: OrgCtx = Depends(org_access("webhooks:write")), db: Session = Depends(get_db)):
    """Sends a `webhook.test` event with a made-up payload (no verification data)."""
    ep = _ep(db, ctx, webhook_id)
    fake = Verification(id=uuid.uuid4(), organization_id=ctx.org.id, env="test", status="MANUAL_REVIEW", reference="test", session_hash="-", expires_at=None)
    d = WebhookDelivery(endpoint_id=ep.id, organization_id=ctx.org.id, event="webhook.test", payload=webhooks.payload_for("webhook.test", fake))
    db.add(d)
    db.commit()
    db.refresh(d)
    background.add_task(webhooks.deliver, d.id)
    return d


@router.post("/{webhook_id}/deliveries/{delivery_id}/resend", response_model=DeliveryOut, status_code=202)
def resend(webhook_id: uuid.UUID, delivery_id: uuid.UUID, background: BackgroundTasks, ctx: OrgCtx = Depends(org_access("webhooks:write")), db: Session = Depends(get_db)):
    ep = _ep(db, ctx, webhook_id)
    d = db.scalar(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id, WebhookDelivery.endpoint_id == ep.id))
    if not d:
        raise not_found("Delivery not found")
    d.status, d.attempts = "pending", 0
    db.commit()
    background.add_task(webhooks.deliver, d.id)
    return d
