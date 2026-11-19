from fastapi import Request
from sqlalchemy.orm import Session

from app.core.net import client_ip
from app.models import AuditLog


def record(db: Session, request: Request | None, action: str, *, org_id=None, user_id=None, api_key_id=None,
           target_type: str | None = None, target_id=None, meta: dict | None = None) -> None:
    """Adds an audit row to the current transaction (committed together with the change it describes). Never pass secrets in `meta`."""
    db.add(AuditLog(
        organization_id=org_id, actor_user_id=user_id, actor_api_key_id=api_key_id, action=action,
        target_type=target_type, target_id=str(target_id) if target_id is not None else None,
        ip=client_ip(request) if request else None, user_agent=(request.headers.get("user-agent", "")[:300] if request else None),
        meta=meta or {},
    ))
