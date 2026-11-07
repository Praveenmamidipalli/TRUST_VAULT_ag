from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import DocumentCategory
from app.schemas.user import UserOut


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: DocumentCategory = DocumentCategory.GENERAL


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[DocumentCategory] = None


class DocumentOut(DocumentBase):
    id: int
    file_name: str
    file_size: int
    mime_type: str
    owner_id: int
    extraction_status: str
    is_classified: bool
    created_at: datetime
    updated_at: datetime
    owner: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
