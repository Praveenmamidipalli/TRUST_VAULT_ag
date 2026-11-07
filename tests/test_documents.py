import io
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, PermissionLevel, DocumentCategory
from app.services.storage_service import StorageService


@pytest.fixture
def setup_users(db_session):
    owner = User(
        email="owner1@trustvault.io",
        username="owner1",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    owner2 = User(
        email="owner2@trustvault.io",
        username="owner2",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    viewer = User(
        email="viewer1@trustvault.io",
        username="viewer1",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    admin = User(
        email="admin1@trustvault.io",
        username="admin1",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add_all([owner, owner2, viewer, admin])
    db_session.commit()
    return {
        "owner": owner,
        "owner2": owner2,
        "viewer": viewer,
        "admin": admin
    }


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_upload_document_success(client, setup_users):
    owner = setup_users["owner"]
    fake_pdf = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    response = client.post(
        "/api/v1/documents",
        headers=auth_header(owner),
        data={
            "title": "Quarterly Financial Audit",
            "description": "Confidential Q3 Review",
            "category": "FINANCIAL"
        },
        files={"file": ("q3_audit.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Quarterly Financial Audit"
    assert data["file_name"] == "q3_audit.pdf"
    assert data["category"] == "FINANCIAL"
    assert data["owner_id"] == owner.id


def test_upload_spoofed_mime_type_rejected(client, setup_users):
    owner = setup_users["owner"]
    fake_content = b"This is not a real PDF header!"

    response = client.post(
        "/api/v1/documents",
        headers=auth_header(owner),
        data={"title": "Malicious Upload"},
        files={"file": ("fake.pdf", io.BytesIO(fake_content), "application/pdf")}
    )
    assert response.status_code == 400
    assert "signature" in response.json()["detail"].lower()


def test_path_traversal_sanitization(client, setup_users):
    owner = setup_users["owner"]
    fake_pdf = b"%PDF-1.4\nvalid_pdf_content"

    # Attack filename with path traversal
    malicious_filename = "../../../etc/passwd.pdf"
    response = client.post(
        "/api/v1/documents",
        headers=auth_header(owner),
        data={"title": "Traversal Test"},
        files={"file": (malicious_filename, io.BytesIO(fake_pdf), "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    # Filename must be strictly sanitized
    assert ".." not in data["file_name"]
    assert "/" not in data["file_name"]
    assert "\\" not in data["file_name"]


def test_document_isolation_between_users(client, setup_users):
    owner1 = setup_users["owner"]
    owner2 = setup_users["owner2"]
    fake_pdf = b"%PDF-1.4\ncontent"

    # Owner 1 uploads Doc 1
    res1 = client.post(
        "/api/v1/documents",
        headers=auth_header(owner1),
        data={"title": "Owner 1 Secret Doc"},
        files={"file": ("doc1.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    doc1_id = res1.json()["id"]

    # Owner 2 lists documents -> must NOT see Doc 1
    res_list = client.get("/api/v1/documents", headers=auth_header(owner2))
    assert res_list.status_code == 200
    doc_ids = [d["id"] for d in res_list.json()]
    assert doc1_id not in doc_ids

    # Owner 2 direct metadata request to Doc 1 -> 403 Forbidden
    res_direct = client.get(f"/api/v1/documents/{doc1_id}", headers=auth_header(owner2))
    assert res_direct.status_code == 403

    # Owner 2 download attempt -> 403 Forbidden
    res_dl = client.get(f"/api/v1/documents/{doc1_id}/download", headers=auth_header(owner2))
    assert res_dl.status_code == 403


def test_admin_cannot_download_unshared_document(client, setup_users):
    """Verifies that an Administrator is prevented from downloading confidential files."""
    owner = setup_users["owner"]
    admin = setup_users["admin"]
    fake_pdf = b"%PDF-1.4\ncontent"

    res = client.post(
        "/api/v1/documents",
        headers=auth_header(owner),
        data={"title": "Client Confidential Contract"},
        files={"file": ("contract.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    doc_id = res.json()["id"]

    # Admin attempts download
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(admin))
    assert dl_res.status_code == 403
    assert "Access denied" in dl_res.json()["detail"]


def test_download_and_update_lifecycle(client, setup_users, db_session):
    owner = setup_users["owner"]
    viewer = setup_users["viewer"]
    fake_pdf = b"%PDF-1.4\nhello world document bytes"

    # 1. Owner uploads
    res = client.post(
        "/api/v1/documents",
        headers=auth_header(owner),
        data={"title": "Original Title", "description": "Original Desc"},
        files={"file": ("test_doc.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    doc_id = res.json()["id"]

    # 2. Owner downloads
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(owner))
    assert dl_res.status_code == 200
    assert dl_res.content == fake_pdf
    assert "nosniff" in dl_res.headers.get("x-content-type-options", "")

    # 3. Grant EDIT to viewer
    perm = DocumentPermission(
        document_id=doc_id,
        user_id=viewer.id,
        permission_level=PermissionLevel.EDIT,
        granted_by_id=owner.id
    )
    db_session.add(perm)
    db_session.commit()

    # 4. Viewer updates document
    patch_res = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth_header(viewer),
        json={"title": "Updated Title", "description": "Updated Desc"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Title"

    # 5. Viewer attempts to delete document -> 403 Forbidden (Only Owner can delete)
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_header(viewer))
    assert del_res.status_code == 403

    # 6. Owner deletes document -> 200 OK
    owner_del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_header(owner))
    assert owner_del_res.status_code == 200

    # 7. Subsequent download returns 404
    assert client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(owner)).status_code == 404
