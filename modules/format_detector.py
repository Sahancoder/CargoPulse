"""Detect a PDF's document format from its extracted text (Phase 5)."""

from __future__ import annotations

SHIPSERV_RFQ = "SHIPSERV_RFQ"
GARRETS_AMOS_QUOTATION = "GARRETS_AMOS_QUOTATION"
DANAOS_RFQ = "DANAOS_RFQ"
UNKNOWN = "UNKNOWN"


def detect_format(text) -> str:
    """Classify the document into one of the known formats, or UNKNOWN."""
    t = (text or "").upper()

    if "SHIPSERV BUYER RECORD" in t or "SHIPSERV SUPPLIER RECORD" in t:
        return SHIPSERV_RFQ

    if "DANAOS SHIPPING CO" in t:
        return DANAOS_RFQ

    if "QUOTATION #:" in t:
        return GARRETS_AMOS_QUOTATION

    return UNKNOWN
