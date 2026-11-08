import sys
sys.path.insert(0, "backend")

from app.core.database import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.models.permission import DocumentPermission
from app.ai.vector_store import vector_store
from app.ai.rag_service import RAGService

db = SessionLocal()

# 1. Sync all docs into vector_store
docs = db.query(Document).all()
for d in docs:
    if d.extracted_text:
        vector_store.chunk_text(d.id, d.extracted_text)

print(f"Synced {len(docs)} docs. Total chunks in vector_store: {len(vector_store.chunks)}")

# 2. Check search for alice_owner
alice = db.query(User).filter(User.username == "alice_owner").first()
queries = [
    "Summarize confidentiality and non-disclosure obligations",
    "Payment deadlines and penalties",
    "What is the executive equity vesting schedule?"
]

for q in queries:
    ans = RAGService.answer_question(user=alice, question=q, db=db)
    print(f"\nQuery: '{q}'")
    print(f"  Insufficient evidence: {ans['insufficient_evidence']}")
    print(f"  Cited docs: {[c['title'] for c in ans['cited_documents']]}")
    if ans['cited_documents']:
        print(f"  Similarity: {ans['cited_documents'][0]['similarity_score']:.4f}")
    print(f"  Answer: {ans['answer'][:120]}...")
