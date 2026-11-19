from fastapi import Request

from app.core.config import get_settings


def client_ip(request: Request) -> str:
    """Peer address; X-Forwarded-For is trusted ONLY when FV_TRUST_PROXY=true (i.e. behind our own reverse proxy)."""
    if get_settings().trust_proxy:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()[:64]
    return (request.client.host if request.client else "unknown")[:64]
