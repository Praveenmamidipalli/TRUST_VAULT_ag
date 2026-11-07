import pytest
from app.core.security import create_access_token
from app.models.user import User
from app.models.document import Document
from app.models.enums import UserRole, AuditAction, AuditResult, DocumentCategory
from app.services.audit_service import AuditService


@pytest.fixture
def admin_test_setup(db_session):
    admin = User(
        email="superadmin@trustvault.io",
        username="superadmin",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )
    owner = User(
        email="report_owner@trustvault.io",
        username="report_owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    viewer = User(
        email="report_viewer@trustvault.io",
        username="report_viewer",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add_all([admin, owner, viewer])
    db_session.commit()

    doc = Document(
        title="Confidential Audit Target",
        file_name="target.pdf",
        storage_path="target_uuid.pdf",
        file_size=2048,
        mime_type="application/pdf",
        category=DocumentCategory.LEGAL,
        owner_id=owner.id
    )
    db_session.add(doc)
    db_session.commit()

    # Log sample events
    AuditService.log_event(
        db=db_session,
        action=AuditAction.DOCUMENT_UPLOAD,
        result=AuditResult.SUCCESS,
        actor_id=owner.id,
        document_id=doc.id
    )
    AuditService.log_event(
        db=db_session,
        action=AuditAction.UNAUTHORIZED_ACCESS_ATTEMPT,
        result=AuditResult.DENIED,
        actor_id=viewer.id,
        document_id=doc.id
    )

    return {
        "admin": admin,
        "owner": owner,
        "viewer": viewer,
        "doc": doc
    }


def auth_header(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


def test_audit_logs_access_control(client, admin_test_setup):
    admin = admin_test_setup["admin"]
    viewer = admin_test_setup["viewer"]

    # Viewer gets 403 Forbidden
    v_res = client.get("/api/v1/audit", headers=auth_header(viewer))
    assert v_res.status_code == 403

    # Admin gets 200 OK
    a_res = client.get("/api/v1/audit", headers=auth_header(admin))
    assert a_res.status_code == 200
    events = a_res.json()
    assert len(events) >= 2


def test_audit_chain_verification_endpoint(client, admin_test_setup):
    admin = admin_test_setup["admin"]
    res = client.get("/api/v1/audit/verify", headers=auth_header(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["total_events"] >= 2


def test_document_owner_audit_activity_view(client, admin_test_setup):
    owner = admin_test_setup["owner"]
    viewer = admin_test_setup["viewer"]
    doc = admin_test_setup["doc"]

    # Owner can review own document activity
    owner_res = client.get(f"/api/v1/audit/documents/{doc.id}", headers=auth_header(owner))
    assert owner_res.status_code == 200
    assert len(owner_res.json()) >= 1

    # Unauthorized viewer cannot review document activity -> 403
    v_res = client.get(f"/api/v1/audit/documents/{doc.id}", headers=auth_header(viewer))
    assert v_res.status_code == 403


def test_admin_user_management_and_self_lockout_prevention(client, admin_test_setup):
    admin = admin_test_setup["admin"]
    viewer = admin_test_setup["viewer"]

    # Admin lists users
    users_res = client.get("/api/v1/admin/users", headers=auth_header(admin))
    assert users_res.status_code == 200
    assert len(users_res.json()) >= 3

    # Admin deactivates viewer
    patch_res = client.patch(
        f"/api/v1/admin/users/{viewer.id}",
        headers=auth_header(admin),
        json={"is_active": False}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False

    # Admin cannot deactivate themselves (self-lockout prevention)
    self_lockout = client.patch(
        f"/api/v1/admin/users/{admin.id}",
        headers=auth_header(admin),
        json={"is_active": False}
    )
    assert self_lockout.status_code == 400
    assert "cannot deactivate your own" in self_lockout.json()["detail"].lower()


def test_admin_reports_and_csv_export(client, admin_test_setup):
    admin = admin_test_setup["admin"]

    # Reports
    rep_res = client.get("/api/v1/admin/reports", headers=auth_header(admin))
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "users" in rep_data
    assert "compliance" in rep_data
    assert rep_data["compliance"]["unauthorized_attempts"] >= 1

    # CSV Export
    csv_res = client.get("/api/v1/admin/reports/export", headers=auth_header(admin))
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")
    assert "Event ID,Timestamp,Actor ID" in csv_res.text
