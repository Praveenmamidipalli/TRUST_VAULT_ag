from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.audit import AuditEvent
from app.models.enums import UserRole, AuditAction, AuditResult
from app.schemas.audit import AuditEventOut
from app.middleware.auth_deps import get_current_user, require_admin
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit & Compliance"])


@router.get("", response_model=List[AuditEventOut])
def get_audit_logs(
    action: Optional[AuditAction] = Query(None),
    result: Optional[AuditResult] = Query(None),
    actor_id: Optional[int] = Query(None),
    document_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieves full audit logs for compliance review. Strictly restricted to ADMIN role."""
    query = db.query(AuditEvent)

    if action:
        query = query.filter(AuditEvent.action == action)
    if result:
        query = query.filter(AuditEvent.result == result)
    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if document_id:
        query = query.filter(AuditEvent.document_id == document_id)

    return query.order_by(AuditEvent.id.desc()).offset(offset).limit(limit).all()


@router.get("/documents/{document_id}", response_model=List[AuditEventOut])
def get_document_audit_activity(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves audit trail for a specific document.
    
    Security:
    - Document OWNER can review all activity on their own document.
    - System ADMIN can review compliance events.
    - Viewers and unauthorized users receive 403 Forbidden.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if current_user.role != UserRole.ADMIN and doc.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the document owner or compliance administrators can review document audit trails."
        )

    return (
        db.query(AuditEvent)
        .filter(AuditEvent.document_id == document_id)
        .order_by(AuditEvent.id.desc())
        .limit(100)
        .all()
    )


@router.get("/verify")
def verify_audit_chain_integrity(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cryptographically scans and validates the SHA-256 hash chain of the entire audit repository."""
    return AuditService.verify_chain_integrity(db)
