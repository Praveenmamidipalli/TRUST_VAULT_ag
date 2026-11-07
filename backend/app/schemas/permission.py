from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import PermissionLevel
from app.schemas.user import UserOut


class PermissionCreate(BaseModel):
    user_id: int
    permission_level: PermissionLevel


class PermissionOut(BaseModel):
    id: int
    document_id: int
    user_id: int
    permission_level: PermissionLevel
    granted_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
