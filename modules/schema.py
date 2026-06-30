"""Common document & line-item structures shared by every parser (Phase 6)."""

from __future__ import annotations


def new_document() -> dict:
    """A blank document header dict with every field defaulted to None."""
    return {
        "document_format": None,
        "document_type": None,
        "rfq_no": None,
        "quotation_no": None,
        "buyer_name": None,
        "supplier_name": None,
        "vessel_name": None,
        "imo_number": None,
        "port_name": None,
        "department": None,
        "subject": None,
        "currency": None,
        "issued_date": None,
        "due_date": None,
        "deliver_by_date": None,
        "vessel_eta": None,
        "vessel_etd": None,
        "payment_terms": None,
        "confidence_score": 1.0,
    }


def new_line_item() -> dict:
    """A blank line-item dict with every field defaulted to None."""
    return {
        "item_no": None,
        "section_name": None,
        "manufacturer": None,
        "model": None,
        "part_type": None,
        "part_number": None,
        "buyer_part_number": None,
        "item_code": None,
        "description": None,
        "normalized_item_name": None,
        "category": None,
        "uom": None,
        "quantity": None,
        "unit_price": None,
        "extended_price": None,
        "currency": None,
        "remarks": None,
        "confidence_score": 1.0,
    }


def empty_result() -> dict:
    """The standard parser return shape."""
    return {"document": new_document(), "line_items": [], "warnings": []}
