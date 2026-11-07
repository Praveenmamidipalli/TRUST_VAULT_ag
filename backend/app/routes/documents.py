from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, DocumentCategory, AuditAction, AuditResult
from app.schemas.document import DocumentOut, DocumentUpdate
from app.middleware.auth_deps import get_current_user
from app.services.authz_service import AuthorizationService
from app.services.storage_service import StorageService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None),
    category: DocumentCategory = Form(DocumentCategory.GENERAL),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads a new document to private storage.
    
    Security:
    - Only OWNER or ADMIN accounts can upload.
    - Owner is strictly locked to current_user.id.
    - File is verified for size, extension, and magic-byte signature.
    - Stored outside web root with a cryptographically random UUID key.
    - Emits a tamper-evident audit log record.
    """
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only accounts with OWNER role may upload documents."
        )

    content = await file.read()
    storage_path, file_size, mime_type = StorageService.save_file(
        filename=file.filename or "uploaded_file",
        content=content,
        content_type=file.content_type
    )

    doc = Document(
        title=title,
        description=description,
        file_name=StorageService.sanitize_filename(file.filename or "uploaded_file"),
        storage_path=storage_path,
        file_size=file_size,
        mime_type=mime_type,
        category=category,
        owner_id=current_user.id,
        extraction_status="PENDING"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Audit logging
    client_ip = request.client.host if request.client else "unknown"
    AuditService.log_event(
        db=db,
        action=AuditAction.DOCUMENT_UPLOAD,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip, "file_name": doc.file_name, "size": doc.file_size}
    )

    return doc


@router.get("", response_model=List[DocumentOut])
def list_documents(
    q: Optional[str] = Query(None, description="Search term for title or description"),
    category: Optional[DocumentCategory] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all documents visible to the current user.
    
    Security:
    - Enforces zero cross-tenant metadata leakage.
    - User only sees: (1) Documents they own, OR (2) Documents explicitly shared with them.
    - System Admins do not receive automatic access to view unauthorized customer documents.
    """
    # Subquery for shared document IDs
    shared_doc_ids = (
        db.query(DocumentPermission.document_id)
        .filter(DocumentPermission.user_id == current_user.id)
        .subquery()
    )

    query = db.query(Document).filter(
        or_(
            Document.owner_id == current_user.id,
            Document.id.in_(select(shared_doc_ids))
        )
    )

    if q:
        query = query.filter(
            or_(Document.title.ilike(f"%{q}%"), Document.description.ilike(f"%{q}%"))
        )
    if category:
        query = query.filter(Document.category == category)

    return query.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document_details(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves document metadata. Protected by server-side READ authorization."""
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_read_document(current_user, doc, db):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "read_metadata"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view this document."
        )

    AuditService.log_event(
        db=db,
        action=AuditAction.DOCUMENT_READ,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip}
    )
    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Downloads the physical document file.
    
    Security:
    - Never uses static, permanent, or unauthenticated links.
    - Always re-verifies live database permissions on every call.
    - Sets security headers (X-Content-Type-Options: nosniff).
    """
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_read_document(current_user, doc, db):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "download"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to download this document."
        )

    file_path = StorageService.get_file_path(doc.storage_path)

    AuditService.log_event(
        db=db,
        action=AuditAction.DOCUMENT_DOWNLOAD,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip, "file_name": doc.file_name}
    )

    return FileResponse(
        path=file_path,
        media_type=doc.mime_type,
        filename=doc.file_name,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.file_name}"',
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.patch("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: int,
    doc_in: DocumentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates document metadata. Requires EDIT permission."""
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_edit_document(current_user, doc, db):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "edit_metadata"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to edit this document."
        )

    if doc_in.title is not None:
        doc.title = doc_in.title
    if doc_in.description is not None:
        doc.description = doc_in.description
    if doc_in.category is not None:
        doc.category = doc_in.category

    db.commit()
    db.refresh(doc)

    AuditService.log_event(
        db=db,
        action=AuditAction.DOCUMENT_UPDATE,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip, "updated_fields": list(doc_in.model_dump(exclude_unset=True).keys())}
    )
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a document and its private storage file.
    
    Security:
    - Strictly reserved for the DOCUMENT OWNER.
    - Admins and viewers with EDIT permissions CANNOT delete documents they do not own.
    """
    client_ip = request.client.host if request.client else "unknown"
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_delete_document(current_user, doc):
        AuditService.log_event(
            db=db,
            action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
            result=AuditResult.DENIED,
            actor_id=current_user.id,
            document_id=doc.id,
            details={"ip": client_ip, "attempted_action": "delete"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only the document owner can delete this document."
        )

    # Remove storage file
    StorageService.delete_file(doc.storage_path)

    # Log before deleting DB row
    AuditService.log_event(
        db=db,
        action=AuditAction.DOCUMENT_DELETE,
        result=AuditResult.SUCCESS,
        actor_id=current_user.id,
        document_id=doc.id,
        details={"ip": client_ip, "file_name": doc.file_name}
    )

    db.delete(doc)
    db.commit()

    return {"message": f"Document '{doc.title}' successfully deleted."}
