from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import DocumentCategory


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=False)
    storage_path = Column(String(512), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    category = Column(SQLEnum(DocumentCategory), default=DocumentCategory.GENERAL, nullable=False, index=True)
    
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # AI & text extraction fields
    extracted_text = Column(Text, nullable=True)
    extraction_status = Column(String(50), default="PENDING", nullable=False)  # PENDING, COMPLETED, FAILED, NO_TEXT
    is_classified = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="owned_documents")
    permissions = relationship("DocumentPermission", back_populates="document", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="document", cascade="all, delete-orphan")
