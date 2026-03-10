import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query

from app.auth import require_admin
from app.database_cassandra import get_session
from app.schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["Audit"])


def log_action(
    admin_id: str,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
):
    """Insère une entrée dans audit_logs. Appelé depuis tous les autres routers."""
    try:
        session = get_session()
        session.execute(
            """
            INSERT INTO audit_logs
                (log_id, admin_id, action, target_type, target_id, details, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (uuid.uuid4(), admin_id, action, target_type, target_id, details, datetime.utcnow()),
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("audit_log error: %s", e)


@router.get(
    "/",
    response_model=List[AuditLogRead],
    summary="Consulter le journal d'audit",
)
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: str | None = Query(None),
    target_type: str | None = Query(None),
    _: dict = Depends(require_admin),
):
    session = get_session()
    rows = session.execute(f"SELECT * FROM audit_logs LIMIT {limit}").all()

    logs = [
        AuditLogRead(
            log_id=str(r.log_id),
            admin_id=r.admin_id,
            action=r.action,
            target_type=r.target_type,
            target_id=r.target_id,
            details=r.details or "",
            created_at=r.created_at,
        )
        for r in rows
    ]

    if action:
        logs = [l for l in logs if l.action == action.upper()]
    if target_type:
        logs = [l for l in logs if l.target_type == target_type.lower()]

    return logs
