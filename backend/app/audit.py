"""
Audit logging helper.

Call `record(db, user, action, ...)` from any router after a security- or
trade-relevant action. Rows are append-only and intended for compliance
review — the app never updates or deletes them.
"""
from sqlalchemy.orm import Session

from .models import AuditLog, User


def record(db: Session, user: User, action: str, entity_type: str | None = None,
           entity_id: str | None = None, detail: str | None = None) -> None:
    entry = AuditLog(
        actor_username=user.username,
        actor_role=user.role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
    )
    db.add(entry)
    # Caller is expected to commit as part of its own transaction.
