"""Parser for ShipServ RFQ PDFs (Phase 7).

Layout (line-oriented text from PyMuPDF):
    Request for Quotation
    <date>
    Reference: <rfq>
    SHIPSERV BUYER RECORD / <buyer>
    SHIPSERV SUPPLIER RECORD / <supplier>
    RFQ Ref: / <rfq>   Subject: / <subject>   Vessel: / <name>   IMO #: / <imo> ...
    Currency:<ccy>
    Equipment Section Name: <section>
    # Part Type | Part Number | Supplier Part No. | Description | UoM | Qty
    <item_no> <part_type> <part_number> <description...> [Buyer Comments: ...] <uom> <qty>
"""

from __future__ import annotations

import re

from modules.format_detector import SHIPSERV_RFQ
from modules.schema import new_line_item
from modules.utils import clean, normalize_date, normalize_item_name, to_float, to_int
from modules.schema import new_document

_FOOTER_RE = re.compile(r"^(Sent from .+Document Number|Page \d+ of \d+)", re.IGNORECASE)
_SECTION_RE = re.compile(r"^Equipment Section Name:\s*(.*)$", re.IGNORECASE)
_ITEM_NO_RE = re.compile(r"^\d+$")
_PART_TYPE_RE = re.compile(r"^[A-Z]{2,3}$")
_HEADER_TOKENS = {
    "#", "Part", "Type", "Part Number", "Supplier Part", "No.",
    "Description", "UoM", "Qty",
}


def _value_after(lines, label):
    """Return the value for a label (inline 'Label: value' or on the next line)."""
    low = label.lower()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.lower().startswith(low):
            after = s[len(label):].strip(" :")
            if after:
                return clean(after)
            for j in range(i + 1, min(i + 4, len(lines))):
                if lines[j].strip():
                    return clean(lines[j])
            return None
    return None


def _line_after_marker(lines, marker):
    """Return the first non-empty line after an exact (case-insensitive) marker."""
    up = marker.upper()
    for i, ln in enumerate(lines):
        if ln.strip().upper() == up:
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    return clean(lines[j])
    return None


def _build_item(item_no, part_type, section, block):
    it = new_line_item()
    it["item_no"] = item_no
    it["part_type"] = part_type
    it["section_name"] = section
    if not block:
        return it

    it["part_number"] = clean(block[0])
    rest = block[1:]
    if len(rest) >= 2:
        it["quantity"] = to_float(rest[-1])
        it["uom"] = clean(rest[-2])
        middle = rest[:-2]
    else:
        middle = rest

    desc_parts = []
    for ln in middle:
        if ln.lower().startswith("buyer comments"):
            bp = re.search(r"Buyer Part\s*:\s*([^,]+)", ln, re.IGNORECASE)
            if bp:
                it["buyer_part_number"] = clean(bp.group(1))
            mk = re.search(r"Maker\s*:\s*(.+)$", ln, re.IGNORECASE)
            if mk:
                maker = re.split(r",\s*R\.?O\.?B", mk.group(1), flags=re.IGNORECASE)[0]
                it["manufacturer"] = clean(maker.lstrip("* "))
        else:
            desc_parts.append(ln)

    it["description"] = clean(" ".join(desc_parts)) if desc_parts else None
    it["normalized_item_name"] = normalize_item_name(it["description"])
    return it


def _parse_line_items(lines):
    items = []
    section = None
    n = len(lines)
    i = 0
    while i < n:
        s = lines[i].strip()
        m = _SECTION_RE.match(s)
        if m:
            section = clean(m.group(1))
            i += 1
            continue
        if _FOOTER_RE.match(s):
            i += 1
            continue
        # An item starts with a number line followed by a 2-3 letter part-type code.
        if _ITEM_NO_RE.match(s) and i + 1 < n and _PART_TYPE_RE.match(lines[i + 1].strip()):
            item_no = to_int(s)
            part_type = lines[i + 1].strip()
            block = []
            j = i + 2
            while j < n:
                lj = lines[j].strip()
                if _SECTION_RE.match(lj) or _FOOTER_RE.match(lj):
                    break
                if _ITEM_NO_RE.match(lj) and j + 1 < n and _PART_TYPE_RE.match(lines[j + 1].strip()):
                    break
                if lj and lj not in _HEADER_TOKENS:
                    block.append(lj)
                j += 1
            items.append(_build_item(item_no, part_type, section, block))
            i = j
            continue
        i += 1
    return items


def _parse_header(lines):
    doc = new_document()
    doc["document_format"] = SHIPSERV_RFQ
    doc["document_type"] = "RFQ"
    doc["rfq_no"] = _value_after(lines, "RFQ Ref:") or _value_after(lines, "Reference:")
    doc["buyer_name"] = _line_after_marker(lines, "SHIPSERV BUYER RECORD")
    doc["supplier_name"] = _line_after_marker(lines, "SHIPSERV SUPPLIER RECORD")
    doc["vessel_name"] = _value_after(lines, "Vessel:")
    doc["imo_number"] = _value_after(lines, "IMO #:")
    doc["port_name"] = _value_after(lines, "Port Name:")
    doc["subject"] = _value_after(lines, "Subject:")
    doc["payment_terms"] = _value_after(lines, "Payment Terms:")
    doc["currency"] = _value_after(lines, "Currency:")
    doc["vessel_eta"] = normalize_date(_value_after(lines, "Vessel ETA:"))
    doc["vessel_etd"] = normalize_date(_value_after(lines, "Vessel ETD:"))
    doc["due_date"] = normalize_date(_value_after(lines, "Quote by Date:"))
    doc["deliver_by_date"] = normalize_date(_value_after(lines, "Requested Delivery:"))
    doc["issued_date"] = normalize_date(_line_after_marker(lines, "Request for Quotation"))
    return doc


def parse(text):
    """Parse ShipServ RFQ text into the common {document, line_items, warnings} shape."""
    lines = text.splitlines()
    doc = _parse_header(lines)
    items = _parse_line_items(lines)
    warnings = []
    if not items:
        warnings.append("No line items parsed")
    return {"document": doc, "line_items": items, "warnings": warnings}
