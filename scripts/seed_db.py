import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend"))
sys.path.append(backend_path)

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.permission import DocumentPermission
from app.models.enums import UserRole, DocumentCategory, PermissionLevel, AuditAction, AuditResult
from app.services.storage_service import StorageService
from app.services.audit_service import AuditService
from app.ai.vector_store import vector_store


def seed_database():
    print("[*] Initializing TrustVault Database Seeding...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # 1. Seed Users
        users_data = [
            {"username": "admin", "email": "admin@trustvault.io", "full_name": "System Administrator", "role": UserRole.ADMIN, "password": "AdminPass123!"},
            {"username": "alice_owner", "email": "alice@trustvault.io", "full_name": "Alice Chen (Finance Lead)", "role": UserRole.OWNER, "password": "OwnerPass123!"},
            {"username": "bob_owner", "email": "bob@trustvault.io", "full_name": "Bob Vance (Legal Counsel)", "role": UserRole.OWNER, "password": "OwnerPass123!"},
            {"username": "carol_viewer", "email": "carol@trustvault.io", "full_name": "Carol Miller (External Auditor)", "role": UserRole.VIEWER, "password": "ViewerPass123!"},
            {"username": "dave_viewer", "email": "dave@trustvault.io", "full_name": "Dave Batista (Operations)", "role": UserRole.VIEWER, "password": "ViewerPass123!"},
        ]

        users = {}
        for u in users_data:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
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
                print(f"  + Created user: {u['username']} ({u['role'].value})")
            else:
                users[u["username"]] = existing
                print(f"  - Existing user: {u['username']}")

        # 2. Seed Sample Documents
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
                "filename": "mutual_nda_partner.txt",
                "category": DocumentCategory.LEGAL,
                "description": "Binding confidentiality and non-solicitation agreement for strategic partner discussions.",
                "content": "Mutual Non-Disclosure Agreement. Both parties agree that confidential technical schematics and trade secrets disclosed during discussions remain strictly protected for five years."
            }
        ]

        created_docs = []
        for d in docs_data:
            owner = users[d["owner"]]
            existing_doc = db.query(Document).filter(Document.title == d["title"]).first()
            if not existing_doc:
                # Save file to storage
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

                # Chunk in vector store
                vector_store.chunk_text(doc.id, doc.extracted_text)

                # Audit log
                AuditService.log_event(
                    db=db,
                    action=AuditAction.DOCUMENT_UPLOAD,
                    result=AuditResult.SUCCESS,
                    actor_id=owner.id,
                    document_id=doc.id,
                    details={"seed": True, "file_name": doc.file_name}
                )
                print(f"  + Uploaded document: '{doc.title}' (Owner: {owner.username})")
            else:
                created_docs.append(existing_doc)
                print(f"  - Existing document: '{existing_doc.title}'")

        # 3. Seed Permissions
        # Alice grants READ on Executive Employment Agreement to Carol (Auditor)
        doc_hr = next((d for d in created_docs if d.category == DocumentCategory.HR), None)
        if doc_hr:
            carol = users["carol_viewer"]
            existing_p = db.query(DocumentPermission).filter(
                DocumentPermission.document_id == doc_hr.id,
                DocumentPermission.user_id == carol.id
            ).first()
            if not existing_p:
                p = DocumentPermission(
                    document_id=doc_hr.id,
                    user_id=carol.id,
                    permission_level=PermissionLevel.READ,
                    granted_by_id=doc_hr.owner_id
                )
                db.add(p)
                db.commit()
                AuditService.log_event(
                    db=db,
                    action=AuditAction.PERMISSION_GRANT,
                    result=AuditResult.SUCCESS,
                    actor_id=doc_hr.owner_id,
                    document_id=doc_hr.id,
                    details={"seed": True, "grantee": carol.username, "level": "READ"}
                )
                print(f"  + Granted READ permission to {carol.username} on '{doc_hr.title}'")

        # Bob grants EDIT on Mutual NDA to Dave
        doc_legal = next((d for d in created_docs if d.category == DocumentCategory.LEGAL), None)
        if doc_legal:
            dave = users["dave_viewer"]
            existing_p2 = db.query(DocumentPermission).filter(
                DocumentPermission.document_id == doc_legal.id,
                DocumentPermission.user_id == dave.id
            ).first()
            if not existing_p2:
                p2 = DocumentPermission(
                    document_id=doc_legal.id,
                    user_id=dave.id,
                    permission_level=PermissionLevel.EDIT,
                    granted_by_id=doc_legal.owner_id
                )
                db.add(p2)
                db.commit()
                AuditService.log_event(
                    db=db,
                    action=AuditAction.PERMISSION_GRANT,
                    result=AuditResult.SUCCESS,
                    actor_id=doc_legal.owner_id,
                    document_id=doc_legal.id,
                    details={"seed": True, "grantee": dave.username, "level": "EDIT"}
                )
                print(f"  + Granted EDIT permission to {dave.username} on '{doc_legal.title}'")

        # 4. Verify Audit Integrity of Seed Data
        verification = AuditService.verify_chain_integrity(db)
        print(f"\n[+] Audit Chain Verification: {verification['message']} ({verification['total_events']} events sealed)")

        print("\n[+] Database seeding completed successfully!")
        print("Demo Accounts:")
        print("  - ADMIN:  admin        / AdminPass123!")
        print("  - OWNER:  alice_owner  / OwnerPass123!")
        print("  - OWNER:  bob_owner    / OwnerPass123!")
        print("  - VIEWER: carol_viewer / ViewerPass123! (Permitted: Executive Employment Agreement)")
        print("  - VIEWER: dave_viewer  / ViewerPass123! (Permitted: Mutual NDA)")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
