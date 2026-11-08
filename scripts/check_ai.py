import sys
sys.path.insert(0, "backend")

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.models.permission import DocumentPermission
from app.ai.vector_store import vector_store
from app.ai.rag_service import RAGService

db = SessionLocal()
users = db.query(User).all()
print("=== USERS IN DB ===")
for u in users:
    print(f"User #{u.id}: {u.username} (Role: {u.role.value})")

docs = db.query(Document).all()
print("\n=== DOCUMENTS IN DB ===")
for d in docs:
    print(f"Doc #{d.id}: '{d.title}' | Owner ID: {d.owner_id} | Text len: {len(d.extracted_text or '')}")
    if d.extracted_text:
        print(f"  Excerpt: {d.extracted_text[:120]}...")

perms = db.query(DocumentPermission).all()
print("\n=== PERMISSIONS IN DB ===")
for p in perms:
    print(f"Perm #{p.id}: Doc #{p.document_id} -> User #{p.user_id} ({p.permission_level.value})")

print("\n=== VECTOR STORE CHUNKS IN MEMORY ===")
print("Total chunks in vector_store:", len(vector_store.chunks))

# Test RAG query for each user
print("\n=== TEST RAG QUERY FOR EACH USER ===")
test_query = "What is the compensation or payment terms?"
for u in users:
    ans = RAGService.answer_question(user=u, question=test_query, db=db)
    print(f"\nUser: {u.username} ({u.role.value})")
    print(f"  Authorized docs: {ans['authorized_docs_searched']}")
    print(f"  Insufficient evidence: {ans['insufficient_evidence']}")
    print(f"  Cited docs: {len(ans['cited_documents'])}")
    print(f"  Answer: {ans['answer'][:150]}...")
