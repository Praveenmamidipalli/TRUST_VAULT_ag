from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    owned_documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    granted_permissions = relationship(
        "DocumentPermission",
        foreign_keys="DocumentPermission.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    assigned_permissions = relationship(
        "DocumentPermission",
        foreign_keys="DocumentPermission.granted_by_id",
        back_populates="granter"
    )
    audit_events = relationship("AuditEvent", back_populates="actor")
