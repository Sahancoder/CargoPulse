"""Parser for Danaos Shipping RFQ PDFs (Phase 9).

Quirks of the extracted text:
  * Header labels are listed first, then their values follow in the same order.
  * 'VENDOR' is rendered vertically (V / E / N / D / O / R on separate lines).
  * Items sit under 'Catalogue Group:' headers; each item is:
        <no>.
        <qty> <uom>
        <item_code>
        <description line(s)...>
"""

from __future__ import annotations

import re

from modules.format_detector import DANAOS_RFQ
from modules.schema import new_document, new_line_item
from modules.utils import clean, normalize_date, normalize_item_name, to_float

_ITEM_NO_RE = re.compile(r"^(\d+)\.$")
_QTY_UOM_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s+([A-Za-z]+)$")
_CATALOGUE_RE = re.compile(r"Catalogue.*Catalogue Group:\s*(.+)$", re.IGNORECASE)


def _header_values(stripped):
    """Lines between the last header label and the vertical VENDOR block."""
    try:
        start = next(i for i, s in enumerate(stripped)
                     if s.lower().startswith("vessel eta/etd"))
    except StopIteration:
        return []
    values = []
    i = start + 1
    while i < len(stripped):
        s = stripped[i]
        if s == "V" and i + 1 < len(stripped) and stripped[i + 1] == "E":
            break  # start of vertical 'VENDOR'
        if s:
            values.append(s)
        i += 1
    return values


def _vendor_name(stripped):
    for i in range(len(stripped) - 6):
        if [stripped[i + k] for k in range(6)] == ["V", "E", "N", "D", "O", "R"]:
            for j in range(i + 6, len(stripped)):
                if stripped[j]:
                    return clean(stripped[j])
    return None


def _currency(stripped):
    for i, s in enumerate(stripped):
        if s.lower().startswith("discount"):
            for j in range(i + 1, min(i + 4, len(stripped))):
                if re.fullmatch(r"[A-Z]{3}", stripped[j]):
                    return stripped[j]
    m = re.search(r"TOTAL PRICE\s+([A-Z]{3})", "\n".join(stripped))
    return m.group(1) if m else "USD"


def _bottom_date(stripped):
    dates = [s for s in stripped if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", s)]
    return dates[-1] if dates else None


def _parse_items(stripped, currency):
    items = []
    section = None
    n = len(stripped)
    start = 0
    for i in range(n):
        if stripped[i].lower().startswith("catalogue:"):
            start = i
            break
    ccy = (currency or "USD").upper()

    i = start
    while i < n:
        s = stripped[i]
        if s.upper().startswith("NET TOTAL") or s.lower().startswith("form contains"):
            break
        cm = _CATALOGUE_RE.search(s)
        if cm:
            section = clean(cm.group(1))
            i += 1
            continue
        m = _ITEM_NO_RE.match(s)
        if m and i + 2 < n:
            item_no = int(m.group(1))
            qm = _QTY_UOM_RE.match(stripped[i + 1])
            if qm:
                qty, uom, code_idx = to_float(qm.group(1)), qm.group(2), i + 2
            else:
                qty, uom, code_idx = None, None, i + 1
            item_code = stripped[code_idx]
            desc, j = [], code_idx + 1
            while j < n:
                sj = stripped[j]
                if (_ITEM_NO_RE.match(sj) or _CATALOGUE_RE.search(sj)
                        or sj.upper().startswith("NET TOTAL")
                        or sj.upper() == ccy
                        or sj.lower().startswith("form contains")):
                    break
                if sj:
                    desc.append(sj)
                j += 1
            it = new_line_item()
            it["item_no"] = item_no
            it["item_code"] = clean(item_code)
            it["part_number"] = clean(item_code)
            it["description"] = clean(" ".join(desc)) if desc else None
            it["normalized_item_name"] = normalize_item_name(it["description"])
            it["quantity"] = qty
            it["uom"] = uom
            it["section_name"] = section
            it["currency"] = ccy
            items.append(it)
            i = j
            continue
        i += 1
    return items


def _form_item_count(text):
    m = re.search(r"Form Contains\s+(\d+)\s+Items?", text, re.IGNORECASE)
    return int(m.group(1)) if m else None


def parse(text):
    """Parse Danaos RFQ text into the common result shape."""
    stripped = [ln.strip() for ln in text.splitlines()]

    doc = new_document()
    doc["document_format"] = DANAOS_RFQ
    doc["document_type"] = "RFQ"

    values = _header_values(stripped)

    def get(idx):
        return clean(values[idx]) if idx < len(values) else None

    doc["rfq_no"] = get(0)
    doc["vessel_name"] = get(1)
    doc["department"] = get(2)
    doc["port_name"] = get(3)
    doc["due_date"] = normalize_date(get(4))
    doc["vessel_eta"] = normalize_date(get(5))
    doc["vessel_etd"] = normalize_date(get(6))
    doc["supplier_name"] = _vendor_name(stripped)
    doc["currency"] = _currency(stripped)
    doc["issued_date"] = normalize_date(_bottom_date(stripped))

    items = _parse_items(stripped, doc["currency"])

    warnings = []
    if not items:
        warnings.append("No line items parsed")
    expected = _form_item_count(text)
    if expected is not None and expected != len(items):
        warnings.append(f"Item count mismatch: parsed {len(items)} vs form states {expected}")

    return {"document": doc, "line_items": items, "warnings": warnings}
