import io
import csv
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.audit import AuditEvent
from app.models.enums import UserRole, AuditAction, AuditResult
from app.schemas.user import UserOut
from app.middleware.auth_deps import require_admin
from app.services.audit_service import AuditService

router = APIRouter(prefix="/admin", tags=["Administration & Reporting"])


class AdminUserUpdatePayload(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


@router.get("/users", response_model=List[UserOut])
def list_users_for_admin(
    q: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists enterprise users with filtering. Admin only."""
    query = db.query(User)
    if q:
        query = query.filter(
            (User.username.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%")) | (User.full_name.ilike(f"%{q}%"))
        )
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    return query.order_by(User.id.asc()).offset(offset).limit(limit).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user_status_or_role(
    user_id: int,
    payload: AdminUserUpdatePayload,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Updates account active status or role.
    
    Security:
    - Protects against admin self-lockout (admin cannot deactivate themselves).
    - Prevents admin from removing their own admin role if they are the sole admin.
    - Emits a cryptographic audit log record.
    """
    client_ip = request.client.host if request.client else "unknown"
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if target_user.id == admin.id:
        if payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security protection: You cannot deactivate your own administrative account."
            )
        if payload.role and payload.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security protection: You cannot remove your own administrative role."
            )

    changes = {}
    if payload.role is not None and payload.role != target_user.role:
        changes["previous_role"] = target_user.role.value
        changes["new_role"] = payload.role.value
        target_user.role = payload.role

    if payload.is_active is not None and payload.is_active != target_user.is_active:
        changes["previous_status"] = target_user.is_active
        changes["new_status"] = payload.is_active
        target_user.is_active = payload.is_active

    db.commit()
    db.refresh(target_user)

    AuditService.log_event(
        db=db,
        action=AuditAction.ADMIN_USER_UPDATE,
        result=AuditResult.SUCCESS,
        actor_id=admin.id,
        details={"ip": client_ip, "target_user_id": target_user.id, "changes": changes}
    )

    return target_user


@router.get("/reports")
def get_administrative_reports(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Provides high-level system compliance and activity aggregates.
    
    Security boundary:
    - Reports counts and metrics ONLY.
    - Never exposes confidential document text or unauthorized contents.
    """
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    
    roles_breakdown = dict(
        db.query(User.role, func.count(User.id)).group_by(User.role).all()
    )

    total_docs = db.query(func.count(Document.id)).scalar() or 0
    total_storage_bytes = db.query(func.coalesce(func.sum(Document.file_size), 0)).scalar() or 0

    total_events = db.query(func.count(AuditEvent.id)).scalar() or 0
    unauthorized_attempts = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.action == AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT)
        .scalar() or 0
    )
    permission_grants = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.action == AuditAction.PERMISSION_GRANT)
        .scalar() or 0
    )
    permission_revocations = (
        db.query(func.count(AuditEvent.id))
        .filter(AuditEvent.action == AuditAction.PERMISSION_REVOKE)
        .scalar() or 0
    )

    # Recent security alerts (denied attempts)
    recent_denied_events = (
        db.query(AuditEvent)
        .filter(AuditEvent.result == AuditResult.DENIED)
        .order_by(AuditEvent.id.desc())
        .limit(10)
        .all()
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "roles": {k.value if hasattr(k, "value") else str(k): v for k, v in roles_breakdown.items()}
        },
        "documents": {
            "total_count": total_docs,
            "total_storage_bytes": total_storage_bytes,
            "total_storage_mb": round(total_storage_bytes / (1024 * 1024), 2)
        },
        "compliance": {
            "total_audit_events": total_events,
            "unauthorized_attempts": unauthorized_attempts,
            "permission_grants": permission_grants,
            "permission_revocations": permission_revocations,
        },
        "recent_security_alerts": [
            {
                "id": ev.id,
                "actor_id": ev.actor_id,
                "document_id": ev.document_id,
                "action": ev.action.value,
                "timestamp": ev.timestamp.isoformat(),
                "details": ev.details
            }
            for ev in recent_denied_events
        ]
    }


@router.get("/reports/export")
def export_audit_csv(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Generates and streams a downloadable CSV of all audit events for external compliance archiving."""
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Timestamp", "Actor ID", "Document ID", "Action", "Result", "Previous Hash", "Current Hash", "Details"
    ])

    for ev in events:
        writer.writerow([
            ev.id,
            ev.timestamp.isoformat(),
            ev.actor_id or "N/A",
            ev.document_id or "N/A",
            ev.action.value if hasattr(ev.action, "value") else str(ev.action),
            ev.result.value if hasattr(ev.result, "value") else str(ev.result),
            ev.previous_hash,
            ev.current_hash,
            ev.details or ""
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trustvault_compliance_audit_log.csv"}
    )
