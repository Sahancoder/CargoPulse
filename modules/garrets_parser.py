"""Parser for Garrets / Amos quotation PDFs (Phase 8).

Header is a block of inline 'Label: value' lines. Each line item is:
    <no>
    <part#>
    <description line(s)...>
    <Dlv:int> <Disc:dec> <Qty:dec> <Unit> <UnitPrice:dec> <ExtPrice:dec>
The fixed 6-field numeric tail is used to detect where each item ends, which
makes parsing robust against the buyer's terms paragraph injected mid-table.
"""

from __future__ import annotations

import re

from modules.format_detector import GARRETS_AMOS_QUOTATION
from modules.schema import new_document, new_line_item
from modules.utils import clean, normalize_date, normalize_item_name, to_float, to_int

_INT_RE = re.compile(r"^\d+$")
_DEC_RE = re.compile(r"^\d+\.\d+$")
_UNIT_RE = re.compile(r"^[A-Za-z]{1,5}$")
_IMO_RE = re.compile(r"IMO\s*#?\s*:?\s*(\d{5,})", re.IGNORECASE)

_NOISE_PREFIXES = (
    "buyer terms and conditions", "all transport", "charges to be quoted",
    "quotation is accepted", "separate credit note",
)


def _inline(lines, label):
    low = label.lower()
    for ln in lines:
        s = ln.strip()
        if s.lower().startswith(low):
            return clean(s[len(label):].strip(" :"))
    return None


def _search(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1) if m else None


def _is_tail(region, j):
    """True if region[j:j+6] matches Dlv/Disc/Qty/Unit/UnitPrice/ExtPrice."""
    if j + 6 > len(region):
        return False
    a, b, c, d, e, f = (region[j + k].strip() for k in range(6))
    return bool(
        _INT_RE.match(a) and _DEC_RE.match(b) and _DEC_RE.match(c)
        and _UNIT_RE.match(d) and _DEC_RE.match(e) and _DEC_RE.match(f)
    )


def _parse_line_items(lines, currency):
    # Items begin just after the 'Vessel: ... IMO #: ...' line.
    start = 0
    for i, ln in enumerate(lines):
        s = ln.strip().lower()
        if s.startswith("vessel:") and "imo" in s:
            start = i + 1
            break
    end = len(lines)
    for i in range(start, len(lines)):
        s = lines[i].strip().lower()
        if s.startswith("items subtotal") or s.startswith("total ext cost"):
            end = i
            break

    region = [lines[i] for i in range(start, end)]
    items = []
    n = len(region)
    i = 0
    while i < n:
        s = region[i].strip()
        if not _INT_RE.match(s):
            i += 1
            continue
        item_no = to_int(s)
        part = region[i + 1].strip() if i + 1 < n else ""
        desc, j, found = [], i + 2, False
        while j < n:
            if _is_tail(region, j):
                found = True
                break
            lj = region[j].strip()
            if any(lj.lower().startswith(p) for p in _NOISE_PREFIXES):
                j += 1
                continue
            if lj:
                desc.append(lj)
            j += 1
        if not found:
            i += 1
            continue
        dlv, disc, qty, unit, up, ep = (region[j + k].strip() for k in range(6))
        it = new_line_item()
        it["item_no"] = item_no
        it["part_number"] = clean(part)
        it["item_code"] = clean(part)
        it["description"] = clean(" ".join(desc)) if desc else None
        it["normalized_item_name"] = normalize_item_name(it["description"])
        it["quantity"] = to_float(qty)
        it["uom"] = clean(unit)
        it["unit_price"] = to_float(up)
        it["extended_price"] = to_float(ep)
        it["currency"] = currency
        items.append(it)
        i = j + 6
    return items


def parse(text):
    """Parse Garrets/Amos quotation text into the common result shape."""
    lines = text.splitlines()
    doc = new_document()
    doc["document_format"] = GARRETS_AMOS_QUOTATION
    doc["document_type"] = "Quotation"
    doc["quotation_no"] = _inline(lines, "Quotation #:")
    doc["supplier_name"] = _inline(lines, "Seller:")
    doc["buyer_name"] = _inline(lines, "Buyer:")
    doc["port_name"] = _inline(lines, "Port:")

    vessel = _inline(lines, "Vessels:")
    if not vessel:
        raw = _inline(lines, "Vessel:")
        vessel = clean(re.split(r"\(|IMO", raw)[0]) if raw else None
    doc["vessel_name"] = vessel

    m = _IMO_RE.search(text)
    doc["imo_number"] = m.group(1) if m else None

    doc["issued_date"] = normalize_date(_search(text, r"Issued on:\s*([0-9A-Za-z-]+)"))
    doc["due_date"] = normalize_date(_inline(lines, "Respond By:"))
    doc["deliver_by_date"] = normalize_date(_inline(lines, "Deliver By:"))

    cm = re.search(r"Total Ext Cost\s*\((\w+)\)", text, re.IGNORECASE)
    doc["currency"] = cm.group(1).upper() if cm else "USD"
    doc["payment_terms"] = _search(text, r"Terms of payment:\s*(.+)")

    items = _parse_line_items(lines, doc["currency"])
    warnings = []
    if not items:
        warnings.append("No line items parsed")
    return {"document": doc, "line_items": items, "warnings": warnings}
