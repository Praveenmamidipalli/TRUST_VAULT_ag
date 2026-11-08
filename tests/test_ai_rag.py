import io
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, PermissionLevel
from app.ai.vector_store import vector_store


@pytest.fixture
def rag_test_setup(db_session, client):
    # Clear vector store before test
    vector_store.chunks.clear()

    user_a = User(
        email="usera_rag@trustvault.io",
        username="usera_rag",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    user_b = User(
        email="userb_rag@trustvault.io",
        username="userb_rag",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    admin = User(
        email="admin_rag@trustvault.io",
        username="admin_rag",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add_all([user_a, user_b, admin])
    db_session.commit()

    token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email, "role": user_a.role.value})
    token_b = create_access_token({"sub": str(user_b.id), "email": user_b.email, "role": user_b.role.value})

    # User A uploads Doc A
    content_a = b"Project Apollo confidential agreement. The final payment deadline is December 15th, 2026."
    res_a = client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"title": "Apollo Agreement", "description": "Payment terms for Apollo project."},
        files={"file": ("apollo.txt", io.BytesIO(content_a), "text/plain")}
    )
    doc_a_id = res_a.json()["id"]

    # User B uploads Doc B
    content_b = b"Project Neptune classified contract. The allocated budget is 5 million dollars approved."
    res_b = client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"title": "Neptune Budget", "description": "Budget allocation for Neptune project."},
        files={"file": ("neptune.txt", io.BytesIO(content_b), "text/plain")}
    )
    doc_b_id = res_b.json()["id"]

    return {
        "user_a": user_a,
        "user_b": user_b,
        "admin": admin,
        "doc_a_id": doc_a_id,
        "doc_b_id": doc_b_id
    }


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_permission_aware_rag_isolation(client, rag_test_setup):
    user_a = rag_test_setup["user_a"]
    doc_a_id = rag_test_setup["doc_a_id"]
    doc_b_id = rag_test_setup["doc_b_id"]

    # 1. User A asks about their own document (Apollo)
    res_apollo = client.post(
        "/api/v1/ai/ask",
        headers=auth_header(user_a),
        json={"question": "What is the payment deadline for Project Apollo?"}
    )
    assert res_apollo.status_code == 200
    data_apollo = res_apollo.json()
    assert data_apollo["insufficient_evidence"] is False
    assert len(data_apollo["cited_documents"]) > 0
    assert data_apollo["cited_documents"][0]["document_id"] == doc_a_id

    # 2. User A asks about User B's unshared document (Neptune)
    res_neptune = client.post(
        "/api/v1/ai/ask",
        headers=auth_header(user_a),
        json={"question": "What is the allocated budget for Project Neptune?"}
    )
    assert res_neptune.status_code == 200
    data_neptune = res_neptune.json()
    # Must report insufficient evidence because User A cannot read Doc B
    assert data_neptune["insufficient_evidence"] is True
    # Crucially, Doc B must NEVER appear in citations or context
    assert len(data_neptune["cited_documents"]) == 0
    assert "Neptune" not in data_neptune["answer"] or "insufficient evidence" in data_neptune["answer"].lower()


def test_admin_cannot_query_unshared_documents_via_ai(client, rag_test_setup):
    """Admin has no automatic backdoor access to query confidential documents via RAG."""
    admin = rag_test_setup["admin"]

    res = client.post(
        "/api/v1/ai/ask",
        headers=auth_header(admin),
        json={"question": "What is the payment deadline for Project Apollo?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["insufficient_evidence"] is True
    assert len(data["cited_documents"]) == 0


def test_immediate_revocation_blocks_subsequent_ai_retrieval(client, rag_test_setup):
    user_a = rag_test_setup["user_a"]
    user_b = rag_test_setup["user_b"]
    doc_b_id = rag_test_setup["doc_b_id"]

    # User B grants READ on Doc B to User A
    grant_res = client.post(
        f"/api/v1/documents/{doc_b_id}/permissions",
        headers=auth_header(user_b),
        json={"user_id": user_a.id, "permission_level": "READ"}
    )
    assert grant_res.status_code == 201
    perm_id = grant_res.json()["id"]

    # Now User A queries Neptune -> MUST succeed
    res_granted = client.post(
        "/api/v1/ai/ask",
        headers=auth_header(user_a),
        json={"question": "What is the allocated budget for Project Neptune?"}
    )
    assert res_granted.status_code == 200
    assert res_granted.json()["insufficient_evidence"] is False
    assert res_granted.json()["cited_documents"][0]["document_id"] == doc_b_id

    # User B revokes permission immediately
    revoke_res = client.delete(
        f"/api/v1/documents/{doc_b_id}/permissions/{perm_id}",
        headers=auth_header(user_b)
    )
    assert revoke_res.status_code == 200

    # User A immediately queries Neptune again -> MUST FAIL (insufficient evidence)
    res_revoked = client.post(
        "/api/v1/ai/ask",
        headers=auth_header(user_a),
        json={"question": "What is the allocated budget for Project Neptune?"}
    )
    assert res_revoked.status_code == 200
    assert res_revoked.json()["insufficient_evidence"] is True
    assert len(res_revoked.json()["cited_documents"]) == 0


def test_semantic_search_endpoint(client, rag_test_setup):
    user_a = rag_test_setup["user_a"]
    doc_a_id = rag_test_setup["doc_a_id"]

    search_res = client.post(
        "/api/v1/ai/search",
        headers=auth_header(user_a),
        json={"query": "payment deadline", "top_k": 3}
    )
    assert search_res.status_code == 200
    data = search_res.json()
    assert len(data["results"]) >= 1
    assert data["results"][0]["document_id"] == doc_a_id
