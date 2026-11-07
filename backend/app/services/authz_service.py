from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, PermissionLevel


class AuthorizationService:
    """Centralized authorization engine enforcing strict least-privilege,
    deny-by-default access control for all document operations.
    
    Security Invariants:
    1. Document Owner has full authority (READ, EDIT, DELETE, GRANT/REVOKE).
    2. Admin does NOT automatically inherit document access. Admin rights are purely
       operational/administrative (user management, audit review).
    3. Non-owners must hold an explicit, active DocumentPermission record in the database.
    4. EDIT permission supersedes and includes READ permission.
    5. Permissions are queried directly from the database on every request to guarantee
       immediate revocation.
    """

    @staticmethod
    def get_user_document_permission(
        user_id: int,
        document_id: int,
        db: Session
    ) -> Optional[PermissionLevel]:
        """Queries the live database for an explicit document permission."""
        permission = (
            db.query(DocumentPermission)
            .filter(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == user_id
            )
            .first()
        )
        return permission.permission_level if permission else None

    @classmethod
    def can_read_document(cls, user: User, document: Document, db: Session) -> bool:
        """Determines if a user can view metadata, download, or retrieve document content.
        
        Rules:
        - If user is document owner -> True
        - If user has explicit READ or EDIT permission -> True
        - In all other cases (including Admin without explicit grant) -> False
        """
        if not user.is_active:
            return False
        
        if document.owner_id == user.id:
            return True

        perm = cls.get_user_document_permission(user.id, document.id, db)
        return perm in (PermissionLevel.READ, PermissionLevel.EDIT)

    @classmethod
    def can_edit_document(cls, user: User, document: Document, db: Session) -> bool:
        """Determines if a user can update document metadata or content.
        
        Rules:
        - If user is document owner -> True
        - If user has explicit EDIT permission -> True
        - READ-only users, unshared users, and Admins without grant -> False
        """
        if not user.is_active:
            return False

        if document.owner_id == user.id:
            return True

        perm = cls.get_user_document_permission(user.id, document.id, db)
        return perm == PermissionLevel.EDIT

    @classmethod
    def can_delete_document(cls, user: User, document: Document) -> bool:
        """Determines if a user can delete a document.
        
        Strict rule:
        - ONLY the document owner can delete the document.
        - Neither viewers with EDIT nor system Admins can delete documents they do not own.
        """
        if not user.is_active:
            return False
        return document.owner_id == user.id

    @classmethod
    def can_manage_permissions(cls, user: User, document: Document) -> bool:
        """Determines if a user can grant or revoke sharing permissions on a document.
        
        Strict rule:
        - ONLY the document owner can grant or revoke permissions.
        - Viewers (even with EDIT) and Admins cannot share documents they do not own.
        """
        if not user.is_active:
            return False
        return document.owner_id == user.id

    @classmethod
    def require_read_access(cls, user: User, document: Document, db: Session) -> None:
        """Enforces READ authorization or raises HTTP 403 Forbidden."""
        if not cls.can_read_document(user, document, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view or download this document."
            )

    @classmethod
    def require_edit_access(cls, user: User, document: Document, db: Session) -> None:
        """Enforces EDIT authorization or raises HTTP 403 Forbidden."""
        if not cls.can_edit_document(user, document, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to modify this document."
            )

    @classmethod
    def require_delete_access(cls, user: User, document: Document) -> None:
        """Enforces DELETE authorization or raises HTTP 403 Forbidden."""
        if not cls.can_delete_document(user, document):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the document owner can delete this document."
            )

    @classmethod
    def require_permission_management_access(cls, user: User, document: Document) -> None:
        """Enforces permission granting/revocation authorization or raises HTTP 403 Forbidden."""
        if not cls.can_manage_permissions(user, document):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only the document owner can grant or revoke permissions."
            )
