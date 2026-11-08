# TrustVault – Development Chronicle & Engineering Journal

This log tracks the chronological engineering process, architectural challenges, root cause analyses, security considerations, and git commits for the **TrustVault** project.

---

## Entry 1: Core Architecture, Authentication & Centralized Authorization Engine
- **Date**: 2026-11-07
- **Git Commit**: `5dd8b92`
- **Milestone**: Milestone 1 – Backend Foundation, Models & Auth
- **Focus**: Authentication, RBAC, and Centralized Authorization

### Objectives:
Establish the backend core with FastAPI, SQLAlchemy 2.0, Argon2id password hashing, JWT authentication, and a centralized authorization engine implementing the **"Deny by Default"** invariant.

### Challenges Encountered:
1. **Thread Safety & Multi-Threading in SQLite Tests**: Initial unit tests using SQLite in-memory with `TestClient` threw SQLite operational errors regarding thread isolation (`SQLite objects created in a thread can only be used in that thread`).
2. **Separation of Administrative Role vs Document Access**: Standard RBAC patterns often inadvertently assign universal read rights to the `ADMIN` role. TrustVault strictly forbids administrators from reading confidential document data without explicit permission grants.

### Root Cause Analysis & Security Mitigations:
- **Root Cause**: SQLite enforces strict thread isolation by default, which conflicts with FastAPI's asynchronous request worker pool during testing.
- **Fix**: Configured `poolclass=StaticPool` and `connect_args={"check_same_thread": False}` in the test database fixture.
- **Security Solution**: In `AuthzService.check_document_access()`, an administrator requesting `READ`, `DOWNLOAD`, or `EDIT` on a document is subject to the exact same ownership or grant validation as standard users. Admins only receive management privileges over user lifecycle and platform compliance.

---

## Entry 2: Secure Storage Subsystem & Path Traversal Prevention
- **Date**: 2026-11-07
- **Git Commit**: `2551857`
- **Milestone**: Milestone 2 – Secure Storage & Document Management
- **Focus**: File Security, Magic Bytes, Path Traversal Mitigation

### Objectives:
Build the private filesystem storage subsystem, file upload validation (extensions and magic bytes), streaming downloads, metadata management, and document deletion.

### Challenges Encountered:
1. **Malicious Filename Path Traversal**: Users submitting filenames containing `../../` or Windows backslashes `..\` could escape the storage root or overwrite system binaries.
2. **MIME Spoofing**: Attackers could submit executable payloads disguised with `.pdf` extensions.

### Root Cause Analysis & Security Mitigations:
- **Root Cause**: Relying on user-provided `file.filename` or HTTP `content-type` headers headers is inherently untrusted.
- **Fix**: Built `StorageService.sanitize_filename()` utilizing `Path(filename).name` and regex stripping. Assigned cryptographically secure `uuid.uuid4()` filenames for on-disk persistence in a directory outside the public web root.
- **Magic-Byte Inspection**: Integrated header sniffing (`%PDF-` for PDFs, strict text decoding for `.txt`/`.md`/`.csv`). Any file whose header fails signature checks is rejected immediately with `400 Bad Request`.

---

## Entry 3: Immediate Permission Revocation & Real-Time Enforcement
- **Date**: 2026-11-07
- **Git Commit**: `8970fb3`
- **Milestone**: Milestone 3 – Sharing & Immediate Revocation
- **Focus**: Granular Sharing, Live Access Lookup, Zero Stale Token Risk

### Objectives:
Implement granular per-document permission grants (`READ`, `EDIT`) and enforce immediate revocation without waiting for token or session timeouts.

### Challenges Encountered:
1. **Session & Token Caching Delay**: Common architectures encode user permissions in JWT claims or cache them in Redis. If Alice shares a document with Bob and then revokes it, Bob could still access the file until token expiration.

### Root Cause Analysis & Security Mitigations:
- **Root Cause**: Distributed caching or stateless tokens decouple permission state from transactional truth.
- **Fix**: Implemented a **Zero-JWT-Permission** model. JWTs contain only identity claims (`sub`, `role`). `AuthzService` performs an indexed, transactional database lookup (`DocumentPermission.is_active == True`) on every single request to `/download`, `/metadata`, and `/query`. When an owner revokes a permission, the commit is instantaneous, and subsequent requests fail in sub-millisecond time.

---

## Entry 4: Cryptographic Tamper-Evident Audit Logging
- **Date**: 2026-11-07
- **Git Commit**: `3b1a782`
- **Milestone**: Milestone 4 – Audit Chain & Admin Reporting
- **Focus**: SHA-256 Hash Chaining, Tamper Detection, CSV Exports

### Objectives:
Record all system events (logins, uploads, downloads, sharing, denials) in a cryptographically chained audit log ($H_n = \text{SHA-256}(H_{n-1} + \text{canonical\_payload})$) and provide an administrative verification endpoint.

### Challenges Encountered:
1. **Hash Inconsistencies Across SQLite & PostgreSQL**: Tests failed with hash mismatch when verifying the audit chain on SQLite.
2. **JSON Serialization Key Ordering**: Inconsistent dictionary key ordering across Python runtime invocations would alter the calculated SHA-256 digest.

### Root Cause Analysis & Security Mitigations:
- **Root Cause 1**: SQLite deserialized `DateTime(timezone=True)` columns without timezone offset metadata (`2026-11-07 18:30:00.123456`), causing the verification calculation to differ from the creation calculation.
- **Root Cause 2**: Default Python `json.dumps()` does not guarantee deterministic key sorting.
- **Fix**: Standardized timestamp formatting via `AuditService.format_timestamp()` to strictly enforce UTC ISO-8601 representation (`YYYY-MM-DDTHH:MM:SS.ffffff+00:00`), and enforced `sort_keys=True` in `canonical_serialize()`.
- **Result**: The audit verification endpoint `/api/v1/audit/verify` accurately detects single-character edits to past log entries and flags the exact corrupted event index.

---

## Entry 5: Enterprise React UI & Role-Based Workspaces
- **Date**: 2026-11-07
- **Git Commit**: `7893d2f`
- **Milestone**: Milestone 5 – Frontend Interface & UX
- **Focus**: Enterprise Single-Page Application, TypeScript, Tailwind CSS

### Objectives:
Develop a modern, professional SaaS web client featuring dedicated views for Authentication, Dashboard, Document Library, Document Detail, Sharing Modal, Audit Logs, User Administration, and AI Assistant.

### Challenges Encountered:
1. **TypeScript Compilation Strictness (`tsc -b`)**: Vite production build failed due to unused import warnings (`TS6133`) in administrative components.
2. **Client-Side vs Server-Side Authorization Invariant**: Ensuring that frontend visual controls (e.g. hiding "Delete" button for viewers) are recognized purely as UX convenience while maintaining 100% backend enforcement.

### Root Cause Analysis & Security Mitigations:
- **Fix**: Cleaned up all unused imports across `AdminUsersPage.tsx`, `DocumentDetailPage.tsx`, and `DocumentsPage.tsx`. Verified clean production bundle generation in `frontend/dist/`.
- **Architecture**: Implemented responsive UI states while ensuring every component handles `403 Forbidden` gracefully with clear user feedback if server policies deny an action.

---

## Entry 6: Permission-Aware AI Search & Context Isolation
- **Date**: 2026-11-08
- **Git Commit**: `a691e5a`
- **Milestone**: Milestone 6 – AI Extraction & Pre-Retrieval RAG
- **Focus**: Offline AI, TF-IDF Vector Store, Zero-Leakage Retrieval

### Objectives:
Implement native document text extraction (`pypdf`), an in-memory TF-IDF vector store with cosine similarity, and an AI question-answering service strictly bound by document permissions.

### Challenges Encountered:
1. **PyMuPDF Python 3.13 Wheel Availability**: `pymupdf` prebuilt binary wheels were unavailable on Windows for Python 3.13.
2. **Cross-Tenant Vector Corpus Leakage**: In simple RAG setups, vector retrieval runs across the whole corpus, and permissions are checked afterward. This can leak chunk existence or allow prompt-injection attacks.
3. **Low-Similarity False Positives**: Queries with common words (e.g. "Project") could return irrelevant low-scoring chunks (~0.08 similarity) from unrelated documents.

### Root Cause Analysis & Security Mitigations:
- **Fix 1**: Switched to `pypdf>=5.0.0`, a robust pure-Python library compatible with Python 3.13 and completely cross-platform.
- **Fix 2 (Pre-Retrieval Filtering)**: In `RAGService.query()`, we first query the database for the user's authorized document IDs. Only chunks belonging to those IDs are fed into the vector search engine.
- **Fix 3 (Similarity Threshold)**: Set a strict cosine similarity cutoff (`min_similarity = 0.20`). If no authorized chunk exceeds 0.20, the system safely responds with insufficient evidence rather than hallucinating.

---

## Entry 7: Machine Learning Classification & Anomaly Detection
- **Date**: 2026-11-08
- **Git Commit**: `78382d1`
- **Milestone**: Milestone 7 – ML Intelligence & Master Security Test Suite
- **Focus**: Text Classification, Statistical Outlier Detection, Comprehensive Testing

### Objectives:
Build an offline ML document classifier (Multinomial Naive Bayes), a statistical audit anomaly detector, and a master security test suite verifying all 16 core security requirements.

### Challenges Encountered:
1. **Cold Start ML Pipeline**: Need an offline classifier that trains instantly on enterprise document vocabulary without requiring gigabytes of model downloads or external API keys.
2. **Comprehensive Security Verification**: Formulating automated regression tests verifying that all 16 security requirements pass in an end-to-end multi-tenant environment.

### Root Cause Analysis & Security Mitigations:
- **Solution 1**: Built `DocumentClassifier` using `scikit-learn`'s `TfidfVectorizer` and `MultinomialNB`, pretrained on standard enterprise document types (Financial, Legal, Technical, HR, Compliance).
- **Solution 2**: Created `tests/test_security_master.py` with 16 distinct test cases directly mapped to the security criteria (`SEC-01` through `SEC-16`). All 51 tests across the entire test suite passed with 100% success.

---

## Entry 8: Containerized Deployment, Database Seeder & Production Documentation
- **Date**: 2026-11-08
- **Git Commit**: *Pending Milestone 8*
- **Milestone**: Milestone 8 – Docker Deployment, Seeding & Final Documentation
- **Focus**: Multi-Stage Dockerfiles, Nginx Gateway, Docker Compose, Seeding Script, System Documentation

### Objectives:
Package the platform for one-command deployment using Docker Compose, provide an automated enterprise database seeder, and author comprehensive documentation (`README.md`, `THREATS.md`, `PROMPTS.md`).

### Highlights:
- Multi-stage Dockerfiles for both Backend (Python 3.11 with non-root security user) and Frontend (Node build + Nginx Alpine).
- Production-ready `docker-compose.yml` linking PostgreSQL 16, FastAPI backend, and Nginx frontend with healthchecks and persistent volumes.
- Verified database seeding (`scripts/seed_db.py`) creating 5 accounts and generating 5 verified SHA-256 audit events.
