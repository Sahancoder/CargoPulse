"""PDF text extraction using PyMuPDF (Phase 4)."""

from __future__ import annotations

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF exposes the module as `fitz`
    import fitz

MIN_TEXT_LENGTH = 50


def extract_text_from_pdf(file_path):
    """Extract all text from a PDF.

    Returns a tuple of (full_text, page_count).
    """
    parts = []
    with fitz.open(file_path) as doc:
        page_count = doc.page_count
        for page in doc:
            parts.append(page.get_text())
    return "".join(parts), page_count


def is_scanned(text) -> bool:
    """Heuristic: very little extractable text usually means a scanned/image PDF."""
    return len((text or "").strip()) < MIN_TEXT_LENGTH
