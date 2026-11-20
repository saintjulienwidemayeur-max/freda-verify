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
    body_html = render_html(subject, text, button, s.hosted_url)
    payload = {"sender": {"name": s.mail_from_name, "email": s.mail_from_email}, "to": recipients, "subject": subject, "textContent": plain, "htmlContent": body_html}
    try:
        c = client or httpx.Client(timeout=8)
        r = c.post(BREVO_URL, json=payload, headers={"api-key": s.brevo_api_key, "accept": "application/json"})
        ok = r.status_code in (200, 201, 202)
        log.info("mail %s (HTTP %s)", "sent" if ok else "REFUSED", r.status_code)
        return ok
    except Exception:  # noqa: BLE001  a mail problem must never break the product
        log.warning("mail failed (network or provider error)")
        return False


def render_html(subject: str, text: str, button: tuple[str, str] | None, site_url: str) -> str:
    """Branded, table-based HTML (works in Gmail/Outlook/Apple Mail). Everything dynamic is escaped; styles are inline because mail clients drop <style>."""
    e = html.escape
    site = site_url.rstrip("/")
    paragraphs = "".join(f'<p style="margin:0 0 14px;font-size:16px;line-height:1.6;color:#33406b">{e(line)}</p>' for line in text.split("\n") if line.strip())
    cta = ""
    if button:
        label, url = e(button[0]), e(button[1], quote=True)
        cta = (f'<table role="presentation" cellspacing="0" cellpadding="0" style="margin:24px 0 8px"><tr><td style="border-radius:999px;background:#1E4FE0">'
               f'<a href="{url}" style="display:inline-block;padding:14px 30px;font-size:16px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:999px">{label}</a></td></tr></table>'
               f'<p style="margin:18px 0 0;font-size:12px;line-height:1.5;color:#7a86ad">Button not working? Copy this link into your browser:<br>'
               f'<a href="{url}" style="color:#1E4FE0;word-break:break-all">{url}</a></p>')
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{e(subject)}</title></head>'
        '<body style="margin:0;padding:0;background:#EEF4FF;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0">{e(subject)}</div>'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#EEF4FF"><tr><td align="center" style="padding:32px 16px">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px">'
        f'<tr><td align="center" style="padding:0 0 18px"><a href="{e(site, quote=True)}"><img src="{e(site, quote=True)}/logo.png" width="170" alt="Freda Verify" style="display:block;border:0;height:auto"></a></td></tr>'
        '<tr><td style="background:#ffffff;border:1px solid #dbe6fb;border-radius:20px;overflow:hidden">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td style="height:6px;background:#1E4FE0;background-image:linear-gradient(90deg,#1E4FE0,#2E8BFF);font-size:0;line-height:0">&nbsp;</td></tr>'
        f'<tr><td style="padding:32px 32px 28px"><h1 style="margin:0 0 18px;font-size:22px;line-height:1.3;color:#0A1647">{e(subject)}</h1>{paragraphs}{cta}</td></tr></table>'
        '</td></tr>'
        '<tr><td align="center" style="padding:20px 8px 0;font-size:12px;line-height:1.6;color:#7a86ad">'
        'Sent by Freda Verify because of activity on your account.<br>'
        f'<a href="{e(site, quote=True)}" style="color:#7a86ad">fredaverify.com</a></td></tr>'
        '</table></td></tr></table></body></html>'
    )
