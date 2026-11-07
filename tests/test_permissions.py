import io
import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.enums import UserRole


@pytest.fixture
def permission_test_setup(db_session, client):
    owner = User(
        email="owner_perm@trustvault.io",
        username="owner_perm",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    viewer1 = User(
        email="viewer1_perm@trustvault.io",
        username="viewer1_perm",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    viewer2 = User(
        email="viewer2_perm@trustvault.io",
        username="viewer2_perm",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    admin = User(
        email="admin_perm@trustvault.io",
        username="admin_perm",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add_all([owner, viewer1, viewer2, admin])
    db_session.commit()

    token = create_access_token({"sub": str(owner.id), "email": owner.email, "role": owner.role.value})
    fake_pdf = b"%PDF-1.4\nSuper confidential NDA"
    res = client.post(
        "/api/v1/documents",
        headers={"Authorization": f"Bearer {token}"},
        data={"title": "M&A Agreement NDA", "description": "Strictly confidential"},
        files={"file": ("nda.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    )
    doc_id = res.json()["id"]

    return {
        "owner": owner,
        "viewer1": viewer1,
        "viewer2": viewer2,
        "admin": admin,
        "doc_id": doc_id
    }


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_grant_read_permission_and_access(client, permission_test_setup):
    owner = permission_test_setup["owner"]
    viewer = permission_test_setup["viewer1"]
    doc_id = permission_test_setup["doc_id"]

    # Before grant: Viewer cannot see document in list
    res_before = client.get("/api/v1/documents", headers=auth_header(viewer))
    assert doc_id not in [d["id"] for d in res_before.json()]

    # Owner grants READ permission
    grant_res = client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(owner),
        json={"user_id": viewer.id, "permission_level": "READ"}
    )
    assert grant_res.status_code == 201
    perm_data = grant_res.json()
    assert perm_data["permission_level"] == "READ"
    assert perm_data["user_id"] == viewer.id

    # After grant: Viewer sees document in list
    res_after = client.get("/api/v1/documents", headers=auth_header(viewer))
    assert doc_id in [d["id"] for d in res_after.json()]

    # Viewer can download
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(viewer))
    assert dl_res.status_code == 200

    # Viewer cannot edit with READ permission
    patch_res = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth_header(viewer),
        json={"title": "Hacked Title"}
    )
    assert patch_res.status_code == 403


def test_upgrade_permission_to_edit(client, permission_test_setup):
    owner = permission_test_setup["owner"]
    viewer = permission_test_setup["viewer1"]
    doc_id = permission_test_setup["doc_id"]

    # Grant READ
    client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(owner),
        json={"user_id": viewer.id, "permission_level": "READ"}
    )

    # Upgrade to EDIT
    upgrade_res = client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(owner),
        json={"user_id": viewer.id, "permission_level": "EDIT"}
    )
    assert upgrade_res.status_code == 201
    assert upgrade_res.json()["permission_level"] == "EDIT"

    # Viewer can now edit
    patch_res = client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth_header(viewer),
        json={"title": "Legitimately Edited Title"}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Legitimately Edited Title"


def test_non_owner_and_admin_cannot_grant_permission(client, permission_test_setup):
    viewer1 = permission_test_setup["viewer1"]
    viewer2 = permission_test_setup["viewer2"]
    admin = permission_test_setup["admin"]
    doc_id = permission_test_setup["doc_id"]

    # Viewer attempts to grant permission -> 403
    v_res = client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(viewer1),
        json={"user_id": viewer2.id, "permission_level": "READ"}
    )
    assert v_res.status_code == 403

    # Admin attempts to grant permission on unowned document -> 403
    a_res = client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(admin),
        json={"user_id": viewer2.id, "permission_level": "READ"}
    )
    assert a_res.status_code == 403


def test_immediate_revocation_lifecycle(client, permission_test_setup):
    owner = permission_test_setup["owner"]
    viewer = permission_test_setup["viewer1"]
    doc_id = permission_test_setup["doc_id"]

    # Grant READ
    grant_res = client.post(
        f"/api/v1/documents/{doc_id}/permissions",
        headers=auth_header(owner),
        json={"user_id": viewer.id, "permission_level": "READ"}
    )
    perm_id = grant_res.json()["id"]

    # Verify active access
    assert client.get(f"/api/v1/documents/{doc_id}", headers=auth_header(viewer)).status_code == 200
    assert client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(viewer)).status_code == 200

    # Non-owner cannot revoke -> 403
    fake_revoke = client.delete(
        f"/api/v1/documents/{doc_id}/permissions/{perm_id}",
        headers=auth_header(viewer)
    )
    assert fake_revoke.status_code == 403

    # Owner revokes permission
    revoke_res = client.delete(
        f"/api/v1/documents/{doc_id}/permissions/{perm_id}",
        headers=auth_header(owner)
    )
    assert revoke_res.status_code == 200
    assert "immediate effect" in revoke_res.json()["message"]

    # IMMEDIATE REVOCATION VERIFICATION:
    # 1. Download attempt is immediately 403
    dl_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_header(viewer))
    assert dl_res.status_code == 403

    # 2. Metadata read attempt is immediately 403
    meta_res = client.get(f"/api/v1/documents/{doc_id}", headers=auth_header(viewer))
    assert meta_res.status_code == 403

    # 3. Document is immediately absent from viewer's document library
    list_res = client.get("/api/v1/documents", headers=auth_header(viewer))
    assert doc_id not in [d["id"] for d in list_res.json()]
