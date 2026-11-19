"""Request id, security headers, structured access log and the per-request log row (no bodies, headers, query strings or IPs)."""
import json
import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import RequestLog

access = logging.getLogger("fv.access")
_RID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
SKIP_LOG = ("/health",)


def _template(request: Request, status: int) -> str:
    """Route template with the real prefix, e.g. /api/v1/organizations/{org_id}: path parameters are replaced by their names (no ids, no query string)."""
    if request.scope.get("route") is None and status == 404:
        return "(unmatched)"
    path = request.url.path
    for name, value in (request.scope.get("path_params") or {}).items():
        path = path.replace(str(value), "{" + name + "}")
    return path


class RequestContext(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id", "")
        rid = rid if _RID.match(rid) else uuid.uuid4().hex
        request.state.request_id = rid
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            ms = int((time.perf_counter() - t0) * 1000)
            path = _template(request, status)
            org_id, key_id = getattr(request.state, "org_id", None), getattr(request.state, "api_key_id", None)
            access.info(json.dumps({"request_id": rid, "method": request.method, "path": path, "status": status, "ms": ms,
                                    "org": str(org_id) if org_id else None, "api_key": str(key_id) if key_id else None}))
            if not path.startswith(SKIP_LOG):
                try:
                    with SessionLocal() as db:
                        db.add(RequestLog(request_id=rid[:40], organization_id=org_id, api_key_id=key_id, method=request.method[:8],
                                          path=path[:200], status=status, latency_ms=ms))
                        db.commit()
                except Exception:  # noqa: BLE001  logging must never break a request
                    access.exception("could not persist request log")
        response.headers["X-Request-ID"] = rid
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        if get_settings().app_env == "prod":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
