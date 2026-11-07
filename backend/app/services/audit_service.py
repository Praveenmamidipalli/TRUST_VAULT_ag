from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.enums import AuditAction, AuditResult

GENESIS_HASH = "0" * 64


class AuditService:
    """Service for recording immutable, SHA-256 hash-chained audit events.
    
    Each audit log record cryptographically seals:
    - ID, Actor ID, Document ID
    - Action, Result, Timestamp
    - Optional metadata details (IP, reason, user-agent)
    - Previous record's hash -> establishing a verifiable tamper-evident chain.
    """

    @staticmethod
    def format_timestamp(dt: datetime) -> str:
        """Standardizes datetime to UTC ISO-8601 string across diverse DB drivers."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    @classmethod
    def get_latest_hash(cls, db: Session) -> str:
        """Retrieves the current_hash of the most recent audit event, or GENESIS_HASH if empty."""
        last_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        if last_event and last_event.current_hash:
            return last_event.current_hash
        return GENESIS_HASH

    @classmethod
    def log_event(
        cls,
        db: Session,
        action: AuditAction,
        result: AuditResult,
        actor_id: Optional[int] = None,
        document_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Appends a new hash-chained audit record to the log."""
        prev_hash = cls.get_latest_hash(db)
        details_str = json.dumps(details) if details else ""
        now = datetime.now(timezone.utc)
        iso_timestamp = cls.format_timestamp(now)

        max_id_row = db.query(AuditEvent.id).order_by(AuditEvent.id.desc()).first()
        next_id = (max_id_row[0] + 1) if max_id_row else 1

        curr_hash = AuditEvent.calculate_hash(
            event_id=next_id,
            actor_id=actor_id,
            document_id=document_id,
            action=action.value if hasattr(action, "value") else str(action),
            result=result.value if hasattr(result, "value") else str(result),
            iso_timestamp=iso_timestamp,
            details=details_str,
            previous_hash=prev_hash
        )

        event = AuditEvent(
            id=next_id,
            actor_id=actor_id,
            document_id=document_id,
            action=action,
            result=result,
            timestamp=now,
            details=details_str,
            previous_hash=prev_hash,
            current_hash=curr_hash
        )

        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @classmethod
    def verify_chain_integrity(cls, db: Session) -> Dict[str, Any]:
        """Scans the entire audit chain and verifies that all SHA-256 cryptographic hashes match."""
        events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
        if not events:
            return {"valid": True, "total_events": 0, "message": "Audit chain is empty."}

        expected_prev_hash = GENESIS_HASH
        for event in events:
            if event.previous_hash != expected_prev_hash:
                return {
                    "valid": False,
                    "tampered_event_id": event.id,
                    "reason": f"Chain link broken at event #{event.id}. Previous hash does not match prior event."
                }

            iso_timestamp = cls.format_timestamp(event.timestamp)
            recalculated_hash = AuditEvent.calculate_hash(
                event_id=event.id,
                actor_id=event.actor_id,
                document_id=event.document_id,
                action=event.action.value if hasattr(event.action, "value") else str(event.action),
                result=event.result.value if hasattr(event.result, "value") else str(event.result),
                iso_timestamp=iso_timestamp,
                details=event.details or "",
                previous_hash=event.previous_hash
            )

            if event.current_hash != recalculated_hash:
                return {
                    "valid": False,
                    "tampered_event_id": event.id,
                    "reason": f"Tampering detected at event #{event.id}. Hash does not match event contents."
                }

            expected_prev_hash = event.current_hash

        return {"valid": True, "total_events": len(events), "message": "Audit chain verified intact."}
