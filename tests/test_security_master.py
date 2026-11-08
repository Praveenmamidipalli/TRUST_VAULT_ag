import io
import pytest
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.audit import AuditEvent
from app.models.enums import UserRole, PermissionLevel, DocumentCategory, AuditAction, AuditResult
from app.services.audit_service import AuditService
from app.ai.vector_store import vector_store


@pytest.fixture
def enterprise_security_fixture(db_session, client):
    vector_store.chunks.clear()

    # Create users
    admin = User(
        email="admin_sec@trustvault.io",
        username="admin_sec",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    user_a = User(
        email="usera_sec@trustvault.io",
        username="usera_sec",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.OWNER,
        is_active=True
    )
    user_b = User(
        email="userb_sec@trustvault.io",
        username="userb_sec",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.OWNER,
        is_active=True
    )
    viewer_read = User(
        email="viewer_read@trustvault.io",
        username="viewer_read",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.VIEWER,
        is_active=True
    )
    viewer_edit = User(
        email="viewer_edit@trustvault.io",
        username="viewer_edit",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.VIEWER,
        is_active=True
    )
    viewer_unshared = User(
        email="viewer_unshared@trustvault.io",
        username="viewer_unshared",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.VIEWER,
        is_active=True
    )
    inactive_user = User(
        email="inactive_sec@trustvault.io",
        username="inactive_sec",
        hashed_password=hash_password("Pass123!"),
        role=UserRole.VIEWER,
        is_active=False
    )
    db_session.add_all([admin, user_a, user_b, viewer_read, viewer_edit, viewer_unshared, inactive_user])
    db_session.commit()

    token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email, "role": user_a.role.value})

    # User A uploads a document
    file_bytes = b"Secret corporate merger terms. Apollo payment deadline is December 15th, 2026."
    res = client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"title": "Merger Terms", "description": "Strictly confidential", "category": "LEGAL"},
        files={"file": ("merger.txt", io.BytesIO(file_bytes), "text/plain")}
    )
    doc_a_id = res.json()["id"]

    # Grant READ to viewer_read
    perm_read = DocumentPermission(
        document_id=doc_a_id,
        user_id=viewer_read.id,
        permission_level=PermissionLevel.READ,
        granted_by_id=user_a.id
    )
    # Grant EDIT to viewer_edit
    perm_edit = DocumentPermission(
        document_id=doc_a_id,
        user_id=viewer_edit.id,
        permission_level=PermissionLevel.EDIT,
        granted_by_id=user_a.id
    )
    db_session.add_all([perm_read, perm_edit])
    db_session.commit()

    return {
        "admin": admin,
        "user_a": user_a,
        "user_b": user_b,
        "viewer_read": viewer_read,
        "viewer_edit": viewer_edit,
        "viewer_unshared": viewer_unshared,
        "inactive_user": inactive_user,
        "doc_a_id": doc_a_id
    }


def auth(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# 1. User A cannot access User B's documents
def test_sec_01_user_cannot_access_other_users_document(client, enterprise_security_fixture):
    user_b = enterprise_security_fixture["user_b"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(user_b))
    assert res.status_code == 403


# 2. Viewer cannot access unshared documents
def test_sec_02_viewer_cannot_access_unshared_documents(client, enterprise_security_fixture):
    viewer = enterprise_security_fixture["viewer_unshared"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(viewer))
    assert res.status_code == 403


# 3. READ permission permits reading and download
def test_sec_03_read_permission_permits_reading(client, enterprise_security_fixture):
    viewer_read = enterprise_security_fixture["viewer_read"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    meta_res = client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(viewer_read))
    assert meta_res.status_code == 200
    dl_res = client.get(f"/api/v1/documents/{doc_a_id}/download", headers=auth(viewer_read))
    assert dl_res.status_code == 200


# 4. READ permission does not permit editing
def test_sec_04_read_permission_denies_editing(client, enterprise_security_fixture):
    viewer_read = enterprise_security_fixture["viewer_read"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.patch(f"/api/v1/documents/{doc_a_id}", headers=auth(viewer_read), json={"title": "Hacked Title"})
    assert res.status_code == 403


# 5. EDIT permission permits allowed editing
def test_sec_05_edit_permission_permits_editing(client, enterprise_security_fixture):
    viewer_edit = enterprise_security_fixture["viewer_edit"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.patch(f"/api/v1/documents/{doc_a_id}", headers=auth(viewer_edit), json={"title": "Legit Edit"})
    assert res.status_code == 200
    assert res.json()["title"] == "Legit Edit"


# 6. Non-owner cannot grant permissions
def test_sec_06_non_owner_cannot_grant_permissions(client, enterprise_security_fixture):
    viewer_edit = enterprise_security_fixture["viewer_edit"]
    user_b = enterprise_security_fixture["user_b"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.post(
        f"/api/v1/documents/{doc_a_id}/permissions",
        headers=auth(viewer_edit),
        json={"user_id": user_b.id, "permission_level": "READ"}
    )
    assert res.status_code == 403


# 7. Non-owner cannot revoke permissions
def test_sec_07_non_owner_cannot_revoke_permissions(client, enterprise_security_fixture, db_session):
    viewer_edit = enterprise_security_fixture["viewer_edit"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    perm = db_session.query(DocumentPermission).filter(DocumentPermission.document_id == doc_a_id).first()
    res = client.delete(f"/api/v1/documents/{doc_a_id}/permissions/{perm.id}", headers=auth(viewer_edit))
    assert res.status_code == 403


# 8 & 9. Revoked users cannot download or access metadata
def test_sec_08_09_revoked_users_cannot_access_metadata_or_download(client, enterprise_security_fixture, db_session):
    user_a = enterprise_security_fixture["user_a"]
    viewer_read = enterprise_security_fixture["viewer_read"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]

    perm = db_session.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc_a_id,
        DocumentPermission.user_id == viewer_read.id
    ).first()

    # Revoke
    revoke_res = client.delete(f"/api/v1/documents/{doc_a_id}/permissions/{perm.id}", headers=auth(user_a))
    assert revoke_res.status_code == 200

    # Test immediate denial
    assert client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(viewer_read)).status_code == 403
    assert client.get(f"/api/v1/documents/{doc_a_id}/download", headers=auth(viewer_read)).status_code == 403


# 10. Unauthorized documents do not appear in search
def test_sec_10_unauthorized_documents_not_in_search(client, enterprise_security_fixture):
    viewer_unshared = enterprise_security_fixture["viewer_unshared"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    res = client.get("/api/v1/documents?q=merger", headers=auth(viewer_unshared))
    assert res.status_code == 200
    assert doc_a_id not in [d["id"] for d in res.json()]


# 11. Admin cannot automatically read all documents
def test_sec_11_admin_cannot_automatically_read_all_documents(client, enterprise_security_fixture):
    admin = enterprise_security_fixture["admin"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]
    assert client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(admin)).status_code == 403
    assert client.get(f"/api/v1/documents/{doc_a_id}/download", headers=auth(admin)).status_code == 403


# 12. Inactive users cannot use protected endpoints
def test_sec_12_inactive_users_rejected(client, enterprise_security_fixture):
    inactive = enterprise_security_fixture["inactive_user"]
    res = client.get("/api/v1/documents", headers=auth(inactive))
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()


# 13. Audit events are created for successful and denied actions
def test_sec_13_audit_events_created_for_success_and_denial(client, enterprise_security_fixture, db_session):
    user_b = enterprise_security_fixture["user_b"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]

    # Trigger a denied access attempt
    res = client.get(f"/api/v1/documents/{doc_a_id}", headers=auth(user_b))
    assert res.status_code == 403

    denied_events = db_session.query(AuditEvent).filter(AuditEvent.result == AuditResult.DENIED).all()
    assert len(denied_events) >= 1
    assert denied_events[0].action == AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT


# 14. Hash-chain verification detects modification
def test_sec_14_hash_chain_detects_tampering(db_session):
    # Log 2 events
    AuditService.log_event(
        db=db_session,
        action=AuditAction.USER_LOGIN_SUCCESS,
        result=AuditResult.SUCCESS,
        actor_id=1
    )
    AuditService.log_event(
        db=db_session,
        action=AuditAction.DOCUMENT_UPLOAD,
        result=AuditResult.SUCCESS,
        actor_id=1,
        document_id=10
    )

    # Valid initial state
    res = AuditService.verify_chain_integrity(db_session)
    assert res["valid"] is True

    # Tamper with an event in DB
    ev = db_session.query(AuditEvent).filter(AuditEvent.id == 1).first()
    ev.details = '{"tampered": true}'
    db_session.commit()

    tamper_res = AuditService.verify_chain_integrity(db_session)
    assert tamper_res["valid"] is False
    assert "Tampering detected" in tamper_res["reason"]


# 15. Unauthorized chunks never reach the LLM
def test_sec_15_unauthorized_chunks_never_reach_llm(client, enterprise_security_fixture):
    viewer_unshared = enterprise_security_fixture["viewer_unshared"]
    res = client.post(
        "/api/v1/ai/ask",
        headers=auth(viewer_unshared),
        json={"question": "What is the payment deadline for the Apollo merger?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["insufficient_evidence"] is True
    assert len(data["cited_documents"]) == 0


# 16. Revocation blocks subsequent AI retrieval
def test_sec_16_revocation_blocks_subsequent_ai_retrieval(client, enterprise_security_fixture, db_session):
    user_a = enterprise_security_fixture["user_a"]
    viewer_read = enterprise_security_fixture["viewer_read"]
    doc_a_id = enterprise_security_fixture["doc_a_id"]

    # Before revoke: viewer_read has READ access
    res_before = client.post(
        "/api/v1/ai/ask",
        headers=auth(viewer_read),
        json={"question": "What is the payment deadline for the Apollo merger?"}
    )
    assert res_before.status_code == 200
    assert res_before.json()["insufficient_evidence"] is False

    # Revoke permission
    perm = db_session.query(DocumentPermission).filter(
        DocumentPermission.document_id == doc_a_id,
        DocumentPermission.user_id == viewer_read.id
    ).first()
    client.delete(f"/api/v1/documents/{doc_a_id}/permissions/{perm.id}", headers=auth(user_a))

    # After revoke: immediate AI retrieval is blocked
    res_after = client.post(
        "/api/v1/ai/ask",
        headers=auth(viewer_read),
        json={"question": "What is the payment deadline for the Apollo merger?"}
    )
    assert res_after.status_code == 200
    assert res_after.json()["insufficient_evidence"] is True
    assert len(res_after.json()["cited_documents"]) == 0
