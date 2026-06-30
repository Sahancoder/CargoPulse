"""Validate a parsed document and emit review-error rows (Phase 11)."""

from __future__ import annotations

from numbers import Number


def _is_number(value) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _err(file_name, rfq_no, issue_type, field_name=None,
         extracted_value=None, suggested_value=None, confidence=None):
    return {
        "file_name": file_name,
        "rfq_no": rfq_no,
        "issue_type": issue_type,
        "field_name": field_name,
        "extracted_value": extracted_value,
        "suggested_value": suggested_value,
        "confidence": confidence,
        "review_status": "open",
    }


def _item_list(item_nos):
    shown = ", ".join(str(x) for x in item_nos[:10])
    suffix = " ..." if len(item_nos) > 10 else ""
    return f"{len(item_nos)} item(s): {shown}{suffix}"


def validate(document, line_items, file_name):
    """Return a list of review-error dicts for missing / invalid fields."""
    errors = []
    rfq = document.get("rfq_no") or document.get("quotation_no")

    if not rfq:
        errors.append(_err(file_name, None, "Missing RFQ No", "rfq_no"))
    if not document.get("vessel_name"):
        errors.append(_err(file_name, rfq, "Missing Vessel Name", "vessel_name"))
    if not document.get("imo_number"):
        errors.append(_err(file_name, rfq, "Missing IMO Number", "imo_number"))

    if not line_items:
        errors.append(_err(file_name, rfq, "No Line Items Found", "line_items"))
        return errors

    missing_qty, invalid_qty, missing_uom = [], [], []
    for it in line_items:
        qty = it.get("quantity")
        no = it.get("item_no")
        if qty is None or qty == "":
            missing_qty.append(no)
        elif not _is_number(qty):
            invalid_qty.append(no)
        if not it.get("uom"):
            missing_uom.append(no)

    if missing_qty:
        errors.append(_err(file_name, rfq, "Missing Quantity", "quantity", _item_list(missing_qty)))
    if invalid_qty:
        errors.append(_err(file_name, rfq, "Invalid Quantity", "quantity", _item_list(invalid_qty)))
    if missing_uom:
        errors.append(_err(file_name, rfq, "Missing UoM", "uom", _item_list(missing_uom)))

    return errors
