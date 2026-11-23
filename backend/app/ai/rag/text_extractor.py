"""
SupportPilot AI — Document Text Extractor & Cleaner
Extracts clean, normalized text from PDF, DOCX, TXT, and Markdown files.
Uses PyMuPDF (fitz) for PDF and python-docx for Word documents.
"""

import re
import unicodedata
from pathlib import Path
from app.core.exceptions import ValidationError
from app.core.logger import get_logger

logger = get_logger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text:
    - Normalize Unicode (NFKC)
    - Remove non-printable control characters
    - Collapse excessive spaces, tabs, and newlines
    - Preserve clean paragraph structure
    """
    if not text:
        return ""

    # 1. Normalize Unicode forms
    text = unicodedata.normalize("NFKC", text)

    # 2. Replace non-standard whitespace (non-breaking space, etc.) with standard space
    text = re.sub(r"[\r\f\v]", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    # 3. Strip control characters (keep \n and \t)
    text = "".join(ch for ch in text if ch in ("\n", "\t") or not unicodedata.category(ch).startswith("C"))

    # 4. Collapse 3+ newlines into 2 (preserve paragraph separation)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 5. Strip whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    cleaned = "\n".join(lines).strip()

    return cleaned


class DocumentTextExtractor:
    """Extracts raw text from various document formats with robust error handling."""

    @staticmethod
    def extract_from_pdf(file_path: str) -> str:
        """Extract text from PDF using PyMuPDF (fitz)."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ValidationError("PyMuPDF (fitz) is not installed on this system.")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error("pdf_open_failed", path=file_path, error=str(e))
            raise ValidationError(f"Could not open PDF file. It may be corrupted or unreadable: {e}")

        if doc.is_encrypted:
            doc.close()
            raise ValidationError("Encrypted or password-protected PDF files are not supported.")

        pages_text: list[str] = []
        try:
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text("text")
                if page_text.strip():
                    pages_text.append(page_text)
        except Exception as e:
            logger.error("pdf_page_read_failed", path=file_path, error=str(e))
            raise ValidationError(f"Failed to read content from PDF page: {e}")
        finally:
            doc.close()

        full_text = "\n\n".join(pages_text)
        return clean_text(full_text)

    @staticmethod
    def extract_from_docx(file_path: str) -> str:
        """Extract text from Word DOCX document."""
        try:
            import docx
        except ImportError:
            raise ValidationError("python-docx is not installed on this system.")

        try:
            doc = docx.Document(file_path)
        except Exception as e:
            logger.error("docx_open_failed", path=file_path, error=str(e))
            raise ValidationError(f"Could not open DOCX file. It may be corrupted: {e}")

        paragraphs = []
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text.strip())

        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        full_text = "\n\n".join(paragraphs)
        return clean_text(full_text)

    @staticmethod
    def extract_from_text(file_path: str) -> str:
        """Extract text from TXT or Markdown with encoding auto-fallback."""
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        raw_bytes = Path(file_path).read_bytes()

        for enc in encodings:
            try:
                decoded = raw_bytes.decode(enc)
                return clean_text(decoded)
            except UnicodeDecodeError:
                continue

        raise ValidationError("Could not decode text file using supported character encodings.")

    @classmethod
    def extract(cls, file_path: str) -> str:
        """Extract text based on file extension."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            text = cls.extract_from_pdf(str(path))
        elif ext in (".docx", ".doc"):
            text = cls.extract_from_docx(str(path))
        elif ext in (".txt", ".md", ".markdown", ".html", ".csv", ".json"):
            text = cls.extract_from_text(str(path))
        else:
            raise ValidationError(f"Unsupported file format '{ext}'. Allowed: .pdf, .docx, .txt, .md")

        if not text or len(text.strip()) < 10:
            raise ValidationError("Document contains no extractable text or is empty.")

        return text
