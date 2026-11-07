from datetime import datetime, timezone
import json
import hashlib
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.enums import AuditAction, AuditResult


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(SQLEnum(AuditAction), nullable=False, index=True)
    result = Column(SQLEnum(AuditResult), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    details = Column(Text, nullable=True)  # JSON-encoded extra metadata (IP, user agent, target user, error reason)
    
    # Tamper-evident hash chain
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Relationships
    actor = relationship("User", back_populates="audit_events")
    document = relationship("Document", back_populates="audit_events")

    @staticmethod
    def calculate_hash(
        event_id: int,
        actor_id: int | None,
        document_id: int | None,
        action: str,
        result: str,
        iso_timestamp: str,
        details: str | None,
        previous_hash: str
    ) -> str:
        """Computes a SHA-256 digest using canonical JSON serialization of event attributes."""
        payload = {
            "id": event_id,
            "actor_id": actor_id,
            "document_id": document_id,
            "action": action,
            "result": result,
            "timestamp": iso_timestamp,
            "details": details or "",
            "previous_hash": previous_hash
        }
        canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()
