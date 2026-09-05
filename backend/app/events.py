"""Small shared helpers used by several routers: writing an audit-log row
and creating an in-app notification. Kept in one place so every workflow
action records history the same way."""

import uuid

from app.models import AuditLog, Notification


def log_action(
    db,
    *,
    vendor_id: int | None,
    actor_id: int | None,
    actor_role: str | None = None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    before_value: str | None = None,
    after_value: str | None = None,
    result: str = "Success",
    details: str | None = None,
):
    db.add(
        AuditLog(
            vendor_id=vendor_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_value=before_value,
            after_value=after_value,
            result=result,
            correlation_id=uuid.uuid4().hex[:12],
            details=details,
        )
    )


def notify(db, *, vendor_id: int, title: str, message: str, category: str = "General"):
    db.add(Notification(vendor_id=vendor_id, title=title, message=message, category=category))
