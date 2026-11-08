from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.document import Document
from app.middleware.auth_deps import get_current_user
from app.services.authz_service import AuthorizationService
from app.ai.rag_service import RAGService
from app.ai.vector_store import vector_store

router = APIRouter(prefix="/ai", tags=["AI Document Intelligence"])


class AskQueryPayload(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


class SearchQueryPayload(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(5, ge=1, le=20)


@router.post("/ask")
def ask_document_assistant(
    payload: AskQueryPayload,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Executes a permission-bounded RAG query against documents the user is authorized to read.
    
    Security:
    - Queries are pre-filtered to user's authorized document IDs.
    - Chunks from unauthorized documents are strictly isolated and never entered into the model context.
    - Emits an AI_QUERY audit log record.
    """
    client_ip = request.client.host if request.client else "unknown"
    return RAGService.answer_question(
        user=current_user,
        question=payload.question,
        db=db,
        client_ip=client_ip
    )


@router.post("/search")
def semantic_search(
    payload: SearchQueryPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Performs semantic similarity search across user's authorized document chunks."""
    authorized_ids = RAGService.get_user_authorized_document_ids(current_user, db)
    if not authorized_ids:
        return {"query": payload.query, "results": [], "authorized_docs_searched": 0}

    results = vector_store.search(
        query=payload.query,
        authorized_document_ids=authorized_ids,
        top_k=payload.top_k
    )

    return {
        "query": payload.query,
        "results": results,
        "authorized_docs_searched": len(authorized_ids)
    }


@router.get("/documents/{document_id}/status")
def get_document_ai_status(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves AI extraction and classification status for a document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not AuthorizationService.can_read_document(current_user, doc, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view this document."
        )

    return {
        "document_id": doc.id,
        "extraction_status": doc.extraction_status,
        "is_classified": doc.is_classified,
        "has_extracted_text": bool(doc.extracted_text),
        "text_preview": (doc.extracted_text[:200] + "...") if doc.extracted_text else None
    }
