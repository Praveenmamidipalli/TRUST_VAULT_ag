from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import AuditAction, AuditResult
from app.schemas.user import UserOut


class AuditEventOut(BaseModel):
    id: int
    actor_id: Optional[int]
    document_id: Optional[int]
    action: AuditAction
    result: AuditResult
    timestamp: datetime
    details: Optional[str]
    previous_hash: str
    current_hash: str
    actor: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
