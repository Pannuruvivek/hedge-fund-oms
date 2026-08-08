from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, User, RoleName
from ..auth import require_roles
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditLogOut(BaseModel):
    id: str
    actor_username: str
    actor_role: RoleName
    action: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    detail: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditLogOut])
def list_audit_log(limit: int = 200, db: Session = Depends(get_db),
                    # BRD names no explicit "compliance officer" role, so audit
                    # access is restricted to ADMIN. Broaden this if your org
                    # has a dedicated compliance/audit reviewer role.
                    _: User = Depends(require_roles(RoleName.ADMIN))):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
