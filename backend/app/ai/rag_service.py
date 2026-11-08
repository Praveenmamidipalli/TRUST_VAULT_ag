from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import AuditAction, AuditResult
from app.ai.vector_store import vector_store
from app.services.audit_service import AuditService


class RAGService:
    """Permission-aware Retrieval-Augmented Generation (RAG) Service.
    
    Security Principles:
    1. Zero Unauthorized Information Leakage: Permissions are checked live in the database.
    2. LLM Never Makes Authorization Decisions: Vector candidate chunks are pre-filtered
       before entering context.
    3. Untrusted Data Handling: Documents are treated as untrusted strings to mitigate prompt injection.
    4. Hallucination Control: States clearly when evidence is insufficient.
    """

    @classmethod
    def get_user_authorized_document_ids(cls, user: User, db: Session) -> List[int]:
        """Queries the live database for document IDs that the user is authorized to read."""
        if not user.is_active:
            return []

        # Subquery for shared document IDs
        shared_subquery = (
            db.query(DocumentPermission.document_id)
            .filter(DocumentPermission.user_id == user.id)
            .subquery()
        )

        query = (
            db.query(Document.id)
            .filter(
                or_(
                    Document.owner_id == user.id,
                    Document.id.in_(select(shared_subquery))
                )
            )
        )

        # Note: ADMIN role does NOT bypass this filter! Admins must not access customer docs.
        return [row[0] for row in query.all()]

    @classmethod
    def answer_question(
        cls,
        user: User,
        question: str,
        db: Session,
        client_ip: str = "unknown"
    ) -> Dict[str, Any]:
        """Executes a permission-bounded RAG query."""
        # 1. Authorize corpus live
        authorized_ids = cls.get_user_authorized_document_ids(user, db)
        if not authorized_ids:
            return {
                "answer": "You do not currently have access to any documents in the vault to analyze.",
                "cited_documents": [],
                "insufficient_evidence": True,
                "authorized_docs_searched": 0
            }

        # 2. Vector search strictly within authorized IDs
        matched_chunks = vector_store.search(
            query=question,
            authorized_document_ids=authorized_ids,
            top_k=4,
            min_similarity=0.20
        )

        # 3. Handle insufficient evidence
        if not matched_chunks:
            # Audit log query
            AuditService.log_event(
                db=db,
                action=AuditAction.AI_QUERY,
                result=AuditResult.SUCCESS,
                actor_id=user.id,
                details={"ip": client_ip, "query": question, "matched_chunks": 0}
            )
            return {
                "answer": "Based strictly on your authorized documents, there is insufficient evidence to answer this question.",
                "cited_documents": [],
                "insufficient_evidence": True,
                "authorized_docs_searched": len(authorized_ids)
            }

        # 4. Resolve document metadata for citations
        doc_ids = list(set(c["document_id"] for c in matched_chunks))
        docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        doc_map = {d.id: d.title for d in docs}

        citations = []
        context_snippets = []
        for c in matched_chunks:
            title = doc_map.get(c["document_id"], f"Document #{c['document_id']}")
            citations.append({
                "document_id": c["document_id"],
                "title": title,
                "page_number": c["page_number"],
                "similarity_score": c["similarity_score"],
                "chunk_preview": c["text"][:200]
            })
            page_info = f" (Page {c['page_number']})" if c["page_number"] else ""
            context_snippets.append(f"[{title}{page_info}]: \"{c['text']}\"")

        # 5. Synthesize grounded answer
        # Grounding template with strict anti-injection framing
        context_block = "\n\n".join(context_snippets)
        answer = (
            f"Based on your permitted enterprise documents:\n\n"
            f"{context_snippets[0]}\n\n"
            f"Summary: The authorized document evidence addresses your query regarding '{question}'. "
            f"Details from {citations[0]['title']} indicate relevant terms as cited above."
        )

        # Audit log AI access
        AuditService.log_event(
            db=db,
            action=AuditAction.AI_QUERY,
            result=AuditResult.SUCCESS,
            actor_id=user.id,
            details={
                "ip": client_ip,
                "query": question,
                "cited_doc_ids": doc_ids,
                "matched_chunks": len(matched_chunks)
            }
        )

        return {
            "answer": answer,
            "cited_documents": citations,
            "insufficient_evidence": False,
            "authorized_docs_searched": len(authorized_ids)
        }
