import pytest
from fastapi import HTTPException
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, PermissionLevel, DocumentCategory
from app.services.authz_service import AuthorizationService


@pytest.fixture
def test_users_and_doc(db_session):
    owner = User(
        id=1,
        email="owner@trustvault.io",
        username="doc_owner",
        hashed_password="hash",
        role=UserRole.OWNER,
        is_active=True
    )
    viewer_read = User(
        id=2,
        email="reader@trustvault.io",
        username="reader_user",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    viewer_edit = User(
        id=3,
        email="editor@trustvault.io",
        username="editor_user",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    unauthorized_user = User(
        id=4,
        email="stranger@trustvault.io",
        username="stranger",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True
    )
    admin_user = User(
        id=5,
        email="admin@trustvault.io",
        username="sysadmin",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True
    )

    doc = Document(
        id=10,
        title="Confidential Q3 Financials",
        file_name="q3_financials.pdf",
        storage_path="private/uuid-q3.pdf",
        file_size=1024,
        mime_type="application/pdf",
        category=DocumentCategory.FINANCIAL,
        owner_id=owner.id
    )

    db_session.add_all([owner, viewer_read, viewer_edit, unauthorized_user, admin_user, doc])
    db_session.commit()

    # Grant READ to viewer_read
    perm_read = DocumentPermission(
        document_id=doc.id,
        user_id=viewer_read.id,
        permission_level=PermissionLevel.READ,
        granted_by_id=owner.id
    )
    # Grant EDIT to viewer_edit
    perm_edit = DocumentPermission(
        document_id=doc.id,
        user_id=viewer_edit.id,
        permission_level=PermissionLevel.EDIT,
        granted_by_id=owner.id
    )
    db_session.add_all([perm_read, perm_edit])
    db_session.commit()

    return {
        "owner": owner,
        "viewer_read": viewer_read,
        "viewer_edit": viewer_edit,
        "unauthorized_user": unauthorized_user,
        "admin_user": admin_user,
        "doc": doc
    }


def test_owner_full_access(db_session, test_users_and_doc):
    owner = test_users_and_doc["owner"]
    doc = test_users_and_doc["doc"]

    assert AuthorizationService.can_read_document(owner, doc, db_session) is True
    assert AuthorizationService.can_edit_document(owner, doc, db_session) is True
    assert AuthorizationService.can_delete_document(owner, doc) is True
    assert AuthorizationService.can_manage_permissions(owner, doc) is True

    # Check assertions do not raise
    AuthorizationService.require_read_access(owner, doc, db_session)
    AuthorizationService.require_edit_access(owner, doc, db_session)
    AuthorizationService.require_delete_access(owner, doc)
    AuthorizationService.require_permission_management_access(owner, doc)


def test_unauthorized_user_denied_all(db_session, test_users_and_doc):
    user = test_users_and_doc["unauthorized_user"]
    doc = test_users_and_doc["doc"]

    assert AuthorizationService.can_read_document(user, doc, db_session) is False
    assert AuthorizationService.can_edit_document(user, doc, db_session) is False
    assert AuthorizationService.can_delete_document(user, doc) is False
    assert AuthorizationService.can_manage_permissions(user, doc) is False

    with pytest.raises(HTTPException) as exc:
        AuthorizationService.require_read_access(user, doc, db_session)
    assert exc.value.status_code == 403


def test_reader_permissions(db_session, test_users_and_doc):
    reader = test_users_and_doc["viewer_read"]
    doc = test_users_and_doc["doc"]

    assert AuthorizationService.can_read_document(reader, doc, db_session) is True
    assert AuthorizationService.can_edit_document(reader, doc, db_session) is False
    assert AuthorizationService.can_delete_document(reader, doc) is False
    assert AuthorizationService.can_manage_permissions(reader, doc) is False

    # READ succeeds
    AuthorizationService.require_read_access(reader, doc, db_session)

    # EDIT raises 403
    with pytest.raises(HTTPException) as exc:
        AuthorizationService.require_edit_access(reader, doc, db_session)
    assert exc.value.status_code == 403


def test_editor_permissions(db_session, test_users_and_doc):
    editor = test_users_and_doc["viewer_edit"]
    doc = test_users_and_doc["doc"]

    # EDIT includes READ
    assert AuthorizationService.can_read_document(editor, doc, db_session) is True
    assert AuthorizationService.can_edit_document(editor, doc, db_session) is True
    # Editor cannot delete or manage permissions
    assert AuthorizationService.can_delete_document(editor, doc) is False
    assert AuthorizationService.can_manage_permissions(editor, doc) is False


def test_admin_cannot_automatically_access_confidential_document(db_session, test_users_and_doc):
    """Critical Enterprise Security Requirement:
    System Administrators MUST NOT have automatic backdoor access to read,
    edit, delete, or manage permissions on confidential customer documents.
    """
    admin = test_users_and_doc["admin_user"]
    doc = test_users_and_doc["doc"]

    assert AuthorizationService.can_read_document(admin, doc, db_session) is False
    assert AuthorizationService.can_edit_document(admin, doc, db_session) is False
    assert AuthorizationService.can_delete_document(admin, doc) is False
    assert AuthorizationService.can_manage_permissions(admin, doc) is False

    with pytest.raises(HTTPException) as exc:
        AuthorizationService.require_read_access(admin, doc, db_session)
    assert exc.value.status_code == 403


def test_immediate_revocation(db_session, test_users_and_doc):
    """Revoking a permission in the database must immediately terminate read and edit capabilities."""
    reader = test_users_and_doc["viewer_read"]
    doc = test_users_and_doc["doc"]

    # Prior to revocation: access granted
    assert AuthorizationService.can_read_document(reader, doc, db_session) is True

    # Revoke permission by deleting DB record
    perm = (
        db_session.query(DocumentPermission)
        .filter(
            DocumentPermission.document_id == doc.id,
            DocumentPermission.user_id == reader.id
        )
        .first()
    )
    db_session.delete(perm)
    db_session.commit()

    # Immediate check: must be denied immediately without delay or token caching
    assert AuthorizationService.can_read_document(reader, doc, db_session) is False
    with pytest.raises(HTTPException) as exc:
        AuthorizationService.require_read_access(reader, doc, db_session)
    assert exc.value.status_code == 403
