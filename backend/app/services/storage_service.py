import os
import uuid
import re
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

# Allowed MIME types and their canonical extensions
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

# File signatures (magic bytes) for tamper-proofing MIME spoofing
MAGIC_SIGNATURES = {
    "application/pdf": [b"%PDF"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
}


class StorageService:
    """Manages secure private file storage.
    
    Security controls:
    1. Storage outside web root.
    2. File size restriction.
    3. Filename sanitization to prevent path traversal or shell exploits.
    4. Unique UUID storage key to prevent file overwrites and guessing.
    5. Path traversal boundary assertion on all reads and writes.
    6. MIME type and magic byte verification.
    """

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Removes dangerous characters and path traversal sequences from filenames."""
        # Strip path components
        clean_name = os.path.basename(filename)
        # Remove any non-alphanumeric, dot, underscore, or dash
        clean_name = re.sub(r"[^a-zA-Z0-9._-]", "_", clean_name)
        # Avoid leading dots (hidden files)
        clean_name = clean_name.lstrip(".")
        if not clean_name:
            clean_name = "unnamed_document"
        return clean_name[:200]

    @classmethod
    def validate_file(cls, filename: str, content: bytes, content_type: str | None) -> str:
        """Validates file extension, size, and header signature."""
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file upload is not allowed."
            )

        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
            )

        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(ALLOWED_EXTENSIONS.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '{ext}' is not permitted. Allowed: {allowed}"
            )

        expected_mime = ALLOWED_EXTENSIONS[ext]

        # Check magic signature if defined
        if expected_mime in MAGIC_SIGNATURES:
            valid_sig = any(content.startswith(sig) for sig in MAGIC_SIGNATURES[expected_mime])
            if not valid_sig:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File content does not match declared extension signature for {ext}."
                )

        return expected_mime

    @classmethod
    def save_file(cls, filename: str, content: bytes, content_type: str | None) -> Tuple[str, int, str]:
        """Saves file into private storage directory with an isolated UUID prefix.
        
        Returns:
            Tuple[storage_path, file_size, verified_mime_type]
        """
        sanitized = cls.sanitize_filename(filename)
        verified_mime = cls.validate_file(sanitized, content, content_type)
        
        file_id = str(uuid.uuid4())
        unique_filename = f"{file_id}_{sanitized}"
        target_path = Path(settings.STORAGE_DIR) / unique_filename

        # Defense-in-depth path traversal check
        cls._assert_within_storage(target_path)

        with open(target_path, "wb") as f:
            f.write(content)

        return unique_filename, len(content), verified_mime

    @classmethod
    def get_file_path(cls, storage_path: str) -> Path:
        """Resolves full storage path and strictly verifies it remains within STORAGE_DIR."""
        target_path = (Path(settings.STORAGE_DIR) / storage_path).resolve()
        cls._assert_within_storage(target_path)

        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage."
            )

        return target_path

    @classmethod
    def delete_file(cls, storage_path: str) -> bool:
        """Securely deletes file from private storage."""
        try:
            target_path = cls.get_file_path(storage_path)
            target_path.unlink(missing_ok=True)
            return True
        except HTTPException:
            return False

    @staticmethod
    def _assert_within_storage(resolved_path: Path) -> None:
        """Prevents directory traversal attacks by ensuring path is bounded by STORAGE_DIR."""
        storage_root = Path(settings.STORAGE_DIR).resolve()
        try:
            resolved_path.resolve().relative_to(storage_root)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid storage path: directory traversal attempt detected."
            )
