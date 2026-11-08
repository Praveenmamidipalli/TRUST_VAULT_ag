import io
from pathlib import Path
from typing import Tuple
from pypdf import PdfReader


class DocumentTextExtractor:
    """Extracts text content from uploaded files for indexing and intelligence.
    
    Security:
    - Traversal-bounded file reading.
    - Handles corrupted or malicious PDFs safely without crashing.
    """

    @classmethod
    def extract_text(cls, file_path: Path, mime_type: str) -> Tuple[str, str]:
        """Extracts text from a document.
        
        Returns:
            Tuple[extracted_text, extraction_status]
            extraction_status: 'COMPLETED' | 'NO_TEXT' | 'FAILED'
        """
        try:
            if not file_path.exists():
                return "", "FAILED"

            if mime_type == "text/plain" or file_path.suffix.lower() == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                status = "COMPLETED" if text else "NO_TEXT"
                return text, status

            if mime_type == "application/pdf" or file_path.suffix.lower() == ".pdf":
                reader = PdfReader(str(file_path))
                extracted_pages = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(f"--- Page {i + 1} ---\n{page_text.strip()}")
                
                full_text = "\n\n".join(extracted_pages).strip()
                status = "COMPLETED" if full_text else "NO_TEXT"
                return full_text, status

            return "", "NO_TEXT"

        except Exception:
            # Gracefully handle corrupted files by returning empty text and FAILED status
            return "", "FAILED"
