# ruff: noqa: E501
"""Transactional e-mail through Brevo's HTTP API (https://developers.brevo.com/reference/sendtransacemail).

Rules: the API key comes from FV_BREVO_API_KEY only; without it nothing is sent (a log line says so). Sending never raises and never blocks a request (callers run it in a
background task). Messages never contain identity data (names, document numbers, photos): only a reference chosen by the business and a link to the dashboard.
Only the HTTP status is logged, never the recipient list, subject, body or key.
"""
import html
import logging

import httpx

from app.core.config import get_settings

log = logging.getLogger("freda.mail")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def enabled() -> bool:
    return bool(get_settings().brevo_api_key)


def send_email(to: list[str], subject: str, text: str, button: tuple[str, str] | None = None, *, client: httpx.Client | None = None) -> bool:
    """Returns True when Brevo accepted the message. `button` = (label, https URL) is rendered in the HTML part and repeated as plain text."""
    s = get_settings()
    if not s.brevo_api_key:
        log.info("mail disabled (FV_BREVO_API_KEY not set): message not sent")
        return False
    recipients = [{"email": e} for e in dict.fromkeys(x.strip() for x in to if x and "@" in x)]
    if not recipients:
        return False
    plain = text + (f"\n\n{button[0]}: {button[1]}" if button else "")
    body_html = "".join(f"<p>{html.escape(line)}</p>" for line in text.split("\n") if line.strip())
    if button:
        body_html += f'<p><a href="{html.escape(button[1], quote=True)}" style="display:inline-block;padding:12px 22px;background:#1E4FE0;color:#fff;border-radius:999px;text-decoration:none;font-weight:600">{html.escape(button[0])}</a></p><p style="color:#667">{html.escape(button[1])}</p>'
    payload = {"sender": {"name": s.mail_from_name, "email": s.mail_from_email}, "to": recipients, "subject": subject, "textContent": plain, "htmlContent": f"<div style=\"font-family:Arial,sans-serif;color:#0A1647\">{body_html}</div>"}
    try:
        c = client or httpx.Client(timeout=8)
        r = c.post(BREVO_URL, json=payload, headers={"api-key": s.brevo_api_key, "accept": "application/json"})
        ok = r.status_code in (200, 201, 202)
        log.info("mail %s (HTTP %s)", "sent" if ok else "REFUSED", r.status_code)
        return ok
    except Exception:  # noqa: BLE001  a mail problem must never break the product
        log.warning("mail failed (network or provider error)")
        return False
