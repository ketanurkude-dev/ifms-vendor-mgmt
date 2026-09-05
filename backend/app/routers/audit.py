from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_reviewer
from app.csv_export import rows_to_csv_response
from app.database import get_db
from app.events import log_action
from app.models import AuditLog, Vendor
from app.schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["audit"])


def _query_logs(
    db: Session, entity_type: str | None, action: str | None, vendor_id: int | None,
    result: str | None, date_from: date | None, date_to: date | None,
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if vendor_id:
        query = query.filter(AuditLog.vendor_id == vendor_id)
    if result:
        query = query.filter(AuditLog.result == result)
    if date_from:
        query = query.filter(AuditLog.server_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        query = query.filter(AuditLog.server_date <= datetime.combine(date_to, datetime.max.time()))
    return query.order_by(AuditLog.server_date.desc())


@router.get("/logs", response_model=list[AuditLogOut])
def search_audit_logs(
    reviewer: Vendor = Depends(require_reviewer),
    db: Session = Depends(get_db),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    vendor_id: int | None = Query(default=None),
    result: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
):
    logs = _query_logs(db, entity_type, action, vendor_id, result, date_from, date_to).limit(limit).all()
    log_action(db, vendor_id=None, actor_id=reviewer.id, actor_role=reviewer.role, action="Audit log searched", entity_type="AuditLog", entity_id=None, details=f"filters: entity_type={entity_type}, action={action}, vendor_id={vendor_id}")
    db.commit()
    return logs


@router.get("/logs/export")
def export_audit_logs(
    reviewer: Vendor = Depends(require_reviewer),
    db: Session = Depends(get_db),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    vendor_id: int | None = Query(default=None),
    result: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
):
    logs = _query_logs(db, entity_type, action, vendor_id, result, date_from, date_to).limit(5000).all()
    rows = [
        {
            "event_id": log.id, "timestamp": log.server_date, "actor_id": log.actor_id, "actor_role": log.actor_role,
            "vendor_id": log.vendor_id, "entity_type": log.entity_type, "entity_id": log.entity_id,
            "action": log.action, "result": log.result, "correlation_id": log.correlation_id,
            "before_value": log.before_value, "after_value": log.after_value, "details": log.details,
        }
        for log in logs
    ]
    log_action(db, vendor_id=None, actor_id=reviewer.id, actor_role=reviewer.role, action="Audit log exported", entity_type="AuditLog", entity_id=None)
    db.commit()
    return rows_to_csv_response(rows, "audit_log.csv")
