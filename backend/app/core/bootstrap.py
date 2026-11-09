"""
Automated database bootstrap service for TrustVault.
Runs on server startup in cloud deployments (e.g. Render, Railway, Docker)
to ensure demo accounts and sample documents exist immediately.
"""

from app.core.security import hash_password
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, PermissionLevel, DocumentCategory, AuditAction, AuditResult
from app.services.storage_service import StorageService
from app.services.audit_service import AuditService
from app.ai.vector_store import vector_store


def bootstrap_database_if_empty(db):
    """Bootstraps demo users, documents, permissions, and audit chain if empty."""
    user_count = db.query(User).count()
    if user_count > 0:
        return

    print("[*] Empty database detected. Bootstrapping TrustVault demo accounts...")

    # 1. Users
    users_data = [
        {"username": "admin", "email": "admin@trustvault.io", "full_name": "System Administrator", "role": UserRole.ADMIN, "password": "AdminPass123!"},
        {"username": "alice_owner", "email": "alice@trustvault.io", "full_name": "Alice Chen (Finance Lead)", "role": UserRole.OWNER, "password": "OwnerPass123!"},
        {"username": "bob_owner", "email": "bob@trustvault.io", "full_name": "Bob Vance (Legal Counsel)", "role": UserRole.OWNER, "password": "OwnerPass123!"},
        {"username": "carol_viewer", "email": "carol@trustvault.io", "full_name": "Carol Miller (External Auditor)", "role": UserRole.VIEWER, "password": "ViewerPass123!"},
        {"username": "dave_viewer", "email": "dave@trustvault.io", "full_name": "Dave Batista (Operations)", "role": UserRole.VIEWER, "password": "ViewerPass123!"},
    ]

    users = {}
    for u in users_data:
        user = User(
            username=u["username"],
            email=u["email"],
            full_name=u["full_name"],
            hashed_password=hash_password(u["password"]),
            role=u["role"],
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        users[u["username"]] = user

    # 2. Sample Documents
    docs_data = [
        {
            "owner": "alice_owner",
            "title": "Q3 2026 Consolidated Financial Audit",
            "filename": "q3_2026_financial_audit.txt",
            "category": DocumentCategory.FINANCIAL,
            "description": "Quarterly balance sheet, EBITDA margins, and expenditure forecast.",
            "content": "Consolidated Q3 Financial Statements. Total gross revenue reached $14.2M with net EBITDA of 24%. Payment terms require net-30 settlements with a 1.5% late fee per month after the deadline."
        },
        {
            "owner": "alice_owner",
            "title": "Enterprise Executive Employment Agreement",
            "filename": "executive_employment_agreement.txt",
            "category": DocumentCategory.HR,
            "description": "Standard VP-level compensation, equity vesting schedule and confidentiality obligations.",
            "content": "Executive Employment and Severance Agreement. Standard 4-year equity vesting with 1-year cliff. Confidential information regarding proprietary customer lists must not be disclosed."
        },
        {
            "owner": "bob_owner",
            "title": "Mutual Non-Disclosure Agreement (M&A Partner)",
            "filename": "mutual_nda_ma_partner.txt",
            "category": DocumentCategory.LEGAL,
            "description": "Binding confidentiality and non-solicitation agreement for strategic partner discussions.",
            "content": "Mutual Non-Disclosure Agreement. Both parties agree that confidential technical schematics and trade secrets disclosed during discussions remain strictly protected for five years."
        }
    ]

    created_docs = []
    for d in docs_data:
        owner = users[d["owner"]]
        content_bytes = d["content"].encode("utf-8")
        storage_path, file_size, mime = StorageService.save_file(
            filename=d["filename"],
            content=content_bytes,
            content_type="text/plain"
        )
        doc = Document(
            title=d["title"],
            description=d["description"],
            file_name=d["filename"],
            storage_path=storage_path,
            file_size=file_size,
            mime_type=mime,
            category=d["category"],
            owner_id=owner.id,
            extracted_text=d["content"],
            extraction_status="COMPLETED"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        created_docs.append(doc)
        vector_store.chunk_text(doc.id, doc.extracted_text)

        AuditService.log_event(
            db=db,
            action=AuditAction.DOCUMENT_UPLOAD,
            result=AuditResult.SUCCESS,
            actor_id=owner.id,
            document_id=doc.id,
            details={"bootstrap": True, "file_name": doc.file_name}
        )

    # 3. Permissions
    # Alice grants READ on Executive Employment Agreement to Carol
    doc_hr = created_docs[1]
    carol = users["carol_viewer"]
    perm1 = DocumentPermission(
        document_id=doc_hr.id,
        user_id=carol.id,
        permission_level=PermissionLevel.READ,
        granted_by_id=users["alice_owner"].id
    )
    db.add(perm1)

    # Bob grants EDIT on Mutual NDA to Dave
    doc_legal = created_docs[2]
    dave = users["dave_viewer"]
    perm2 = DocumentPermission(
        document_id=doc_legal.id,
        user_id=dave.id,
        permission_level=PermissionLevel.EDIT,
        granted_by_id=users["bob_owner"].id
    )
    db.add(perm2)
    db.commit()

    print("[+] Database bootstrap complete: 5 demo accounts, 3 documents, and cryptographic audit ledger sealed.")
