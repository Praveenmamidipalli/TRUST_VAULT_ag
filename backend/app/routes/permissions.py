from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import AuditAction, AuditResult
from app.schemas.permission import PermissionCreate, PermissionOut
from app.middleware.auth_deps import get_current_user
from app.services.authz_service import AuthorizationService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/documents/{document_id}/permissions", tags=["Permissions"])


@router.post("", response_model=PermissionOut, status_code=status.HTTP_201_CREATED)
def grant_or_update_permission(
    document_id: int,
    perm_in: PermissionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Grants or updates sharing permissions for a target user on a document.
    
    Security:
    - Strictly authorized ONLY to the document OWNER.
    - Viewers and system administrators cannot grant permissions on unowned documents.
    - Cannot grant permissions to non-existent or inactive users.
    - Emits a cryptographic audit log entry.
    """
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Only document owner can manage permissions
    if not AuthorizationService.can_manage_permissions(current_user, doc):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "grant_permission"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the document owner can grant sharing permissions."
        )

    # Validate target user
    target_user = db.query(User).filter(User.id == perm_in.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")
    if not target_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot grant permissions to an inactive user account.")
    if target_user.id == doc.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Owner already possesses full unrevocable access.")

    # Check for existing permission grant
    existing_perm = db.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc.id,
        DocumentPermission.user_id == target_user.id
    ).first()

    if existing_perm:
        existing_perm.permission_level = perm_in.permission_level
        existing_perm.granted_by_id = current_user.id
        db.commit()
        db.refresh(existing_perm)
        perm_record = existing_perm
    else:
        perm_record = DocumentPermission(
            document_id=doc.id,
            user_id=target_user.id,
            permission_level=perm_in.permission_level,
            granted_by_id=current_user.id
        )
        db.add(perm_record)
        db.commit()
        db.refresh(perm_record)

    AuditService.log_event(
        db=db,
        action=AuditAction.PERMISSION_GRANT,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={
            "ip": client_ip,
            "target_user_id": target_user.id,
            "target_username": target_user.username,
            "permission_level": perm_in.permission_level.value
        }
    )

    return perm_record


@router.get("", response_model=List[PermissionOut])
def list_document_permissions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all permission grants for a document. Restricted strictly to the document OWNER."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_manage_permissions(current_user, doc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the document owner can inspect permission grants."
        )

    return db.query(DocumentPermission).filter(DocumentPermission.document_id == doc.id).all()


@router.delete("/{permission_id}", status_code=status.HTTP_200_OK)
def revoke_permission(
    document_id: int,
    permission_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Immediately revokes a user's permission to access a document.
    
    Security & Immediate Revocation Guarantees:
    - Only the document OWNER can revoke access.
    - Database record is committed and removed immediately.
    - All subsequent requests (download, metadata, search, AI retrieval) by the revoked user
      are instantaneously rejected because permissions are never cached in JWT tokens.
    - Emits a cryptographic audit log record.
    """
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_manage_permissions(current_user, doc):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "revoke_permission"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the document owner can revoke permissions."
        )

    perm = db.query(DocumentPermission).filter(
        DocumentPermission.id == permission_id,
        DocumentPermission.document_id == doc.id
    ).first()

    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission grant not found.")

    target_user_id = perm.user_id

    # Delete permission record immediately
    db.delete(perm)
    db.commit()

    AuditService.log_event(
        db=db,
        action=AuditAction.PERMISSION_REVOKE,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip, "revoked_user_id": target_user_id}
    )

    return {"message": "Permission successfully revoked with immediate effect."}
