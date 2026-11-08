from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.audit import AuditEvent
from app.models.enums import AuditAction, AuditResult


class AnomalyDetector:
    """Security intelligence service for detecting anomalous activity, credential stuffing,
    and bulk exfiltration attempts across the audit trail.
    """

    @classmethod
    def detect_anomalies(cls, db: Session, lookback_minutes: int = 120) -> List[Dict[str, Any]]:
        """Scans recent audit events against transparent security heuristics."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
        alerts: List[Dict[str, Any]] = []

        # 1. Rule 1: Repeated Denied Unauthorized Attempts (Brute Force / IDOR Probing)
        denied_by_actor = (
            db.query(
                AuditEvent.actor_id,
                func.count(AuditEvent.id).label("denied_count")
            )
            .filter(
                AuditEvent.result == AuditResult.DENIED,
                AuditEvent.timestamp >= cutoff,
                AuditEvent.actor_id.isnot(None)
            )
            .group_by(AuditEvent.actor_id)
            .having(func.count(AuditEvent.id) >= 3)
            .all()
        )

        for actor_id, count in denied_by_actor:
            alerts.append({
                "severity": "HIGH",
                "rule_name": "Repeated Unauthorized Access Probing",
                "actor_id": actor_id,
                "event_count": count,
                "reason": f"Actor #{actor_id} triggered {count} denied access requests in the past {lookback_minutes} minutes.",
                "recommended_action": "Inspect actor activity in audit logs and consider temporary account suspension."
            })

        # 2. Rule 2: High Frequency Download Volume (Potential Bulk Exfiltration)
        downloads_by_actor = (
            db.query(
                AuditEvent.actor_id,
                func.count(AuditEvent.id).label("download_count")
            )
            .filter(
                AuditEvent.action == AuditAction.DOCUMENT_DOWNLOAD,
                AuditEvent.result == AuditResult.SUCCESS,
                AuditEvent.timestamp >= cutoff,
                AuditEvent.actor_id.isnot(None)
            )
            .group_by(AuditEvent.actor_id)
            .having(func.count(AuditEvent.id) >= 5)
            .all()
        )

        for actor_id, count in downloads_by_actor:
            alerts.append({
                "severity": "MEDIUM",
                "rule_name": "High Volume Download Activity",
                "actor_id": actor_id,
                "event_count": count,
                "reason": f"Actor #{actor_id} downloaded {count} files within {lookback_minutes} minutes.",
                "recommended_action": "Verify if the bulk download activity is part of authorized normal business procedures."
            })

        # 3. Rule 3: Multiple Failed Logins
        failed_logins = (
            db.query(func.count(AuditEvent.id))
            .filter(
                AuditEvent.action == AuditAction.USER_LOGIN_FAILED,
                AuditEvent.timestamp >= cutoff
            )
            .scalar() or 0
        )

        if failed_logins >= 5:
            alerts.append({
                "severity": "MEDIUM",
                "rule_name": "Elevated Failed Authentication Rate",
                "actor_id": None,
                "event_count": failed_logins,
                "reason": f"System recorded {failed_logins} failed login attempts across the workspace.",
                "recommended_action": "Review source IP addresses for credential stuffing or password spray attacks."
            })

        return alerts
