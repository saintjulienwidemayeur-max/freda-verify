"""Signed webhooks (verification.submitted / verification.approved / verification.rejected).

Security: HTTPS only; the destination host is resolved and refused when it points to a private, loopback, link-local or reserved address (SSRF), both when the
endpoint is saved and again at every delivery; redirects are never followed; short timeout; the response body is never stored.
Signature: header `Freda-Signature: t=<unix seconds>,v1=<hex HMAC-SHA256 of "<t>.<raw body>" with the endpoint secret>`. The receiver must recompute it with the raw body and
reject timestamps older than 5 minutes (replay window). Payloads carry NO personal data: ids, reference, status, timestamps.
Delivery runs in a background task with 3 attempts (1 s, 4 s pauses); a failed delivery stays visible in the dashboard and can be re-sent by hand. There is no scheduler:
nothing is retried after the process restarts, which is a known limit.
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import time
import uuid
from urllib.parse import urlparse

import httpx

from app.core.security import decrypt_secret
from app.db.session import SessionLocal
from app.models import WebhookDelivery, WebhookEndpoint, now

log = logging.getLogger("freda.webhooks")
EVENTS = ("verification.submitted", "verification.approved", "verification.rejected", "webhook.test")
ATTEMPT_PAUSES = (1, 4)


class UnsafeUrl(ValueError):
    pass


def _public(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return a.is_global and not a.is_multicast


def check_url(url: str) -> None:
    """Raises UnsafeUrl unless the URL is https, has a host and every address the host resolves to is public."""
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        raise UnsafeUrl("The URL must start with https:// and must not contain credentials")
    try:
        ipaddress.ip_address(u.hostname)
        addrs = [u.hostname]
    except ValueError:
        try:
            addrs = [i[4][0] for i in socket.getaddrinfo(u.hostname, u.port or 443, proto=socket.IPPROTO_TCP)]
        except OSError as e:
            raise UnsafeUrl("The host name cannot be resolved") from e
    if not addrs or not all(_public(a) for a in addrs):
        raise UnsafeUrl("The URL must point to a public internet address")


def sign(secret: str, timestamp: int, body: bytes) -> str:
    return hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256).hexdigest()


def payload_for(event: str, verification) -> dict:
    d = {"verification_id": str(verification.id), "reference": verification.reference, "env": verification.env, "status": verification.status,
         "submitted_at": verification.submitted_at.isoformat() if verification.submitted_at else None,
         "decided_at": verification.decided_at.isoformat() if verification.decided_at else None}
    return {"id": "evt_" + uuid.uuid4().hex, "type": event, "created_at": now().isoformat(), "data": d}


def queue(db, org_id: uuid.UUID, event: str, verification) -> list[uuid.UUID]:
    """Adds one pending delivery per active endpoint of the organization to the CURRENT transaction (committed with the change that caused it)."""
    ids = []
    for ep in db.query(WebhookEndpoint).filter(WebhookEndpoint.organization_id == org_id, WebhookEndpoint.active.is_(True)).all():
        d = WebhookDelivery(endpoint_id=ep.id, organization_id=org_id, event=event, payload=payload_for(event, verification))
        db.add(d)
        db.flush()
        ids.append(d.id)
    return ids


def deliver(delivery_id: uuid.UUID, *, client: httpx.Client | None = None, pauses: tuple[int, ...] = ATTEMPT_PAUSES) -> str:
    """Sends the delivery (up to 1 + len(pauses) attempts). Returns the final status. Never raises."""
    with SessionLocal() as db:
        d = db.get(WebhookDelivery, delivery_id)
        ep = db.get(WebhookEndpoint, d.endpoint_id) if d else None
        if not d or not ep:
            return "failed"
        body = json.dumps(d.payload, separators=(",", ":"), sort_keys=True).encode()
        secret, url = decrypt_secret(ep.secret_enc), ep.url
        for attempt in range(len(pauses) + 1):
            d.attempts += 1
            try:
                check_url(url)
                ts = int(time.time())
                c = client or httpx.Client(timeout=8, follow_redirects=False)
                r = c.post(url, content=body, headers={"Content-Type": "application/json", "User-Agent": "FredaVerify-Webhook/1", "Freda-Event": d.event,
                                                      "Freda-Signature": f"t={ts},v1={sign(secret, ts, body)}"})
                d.response_code, d.last_error = r.status_code, None
                if 200 <= r.status_code < 300:
                    d.status, d.delivered_at = "delivered", now()
                    break
                d.last_error = f"HTTP {r.status_code}"
            except UnsafeUrl as e:
                d.last_error = str(e)[:120]
                d.status = "failed"
                break                                                  # retrying cannot make an unsafe address safe
            except Exception:  # noqa: BLE001  network failure, TLS error, timeout
                d.last_error = "network or TLS error"
            d.status = "failed"
            db.commit()
            if attempt < len(pauses):
                time.sleep(pauses[attempt])
        db.commit()
        log.info("webhook %s %s after %s attempt(s)", d.event, d.status, d.attempts)
        return d.status
