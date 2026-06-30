"""Shared helpers: date normalisation, text cleaning, numeric parsing."""

from __future__ import annotations

import re
from datetime import datetime

NOT_PROVIDED_TOKENS = {"not provided", "n/a", "na", "none", "-", "", "tba"}

_DATE_FORMATS = [
    "%d %B %Y",   # 25 June 2026
    "%d %b %Y",   # 25 Jun 2026
    "%d-%b-%Y",   # 29-Jun-2026
    "%d-%B-%Y",   # 29-June-2026
    "%d/%m/%Y",   # 27/6/2026
    "%d.%m.%Y",   # 27.06.2026
    "%Y-%m-%d",   # 2026-06-27 (already ISO)
]


def is_not_provided(value) -> bool:
    """True for empty / placeholder values like 'Not Provided', 'N/A', '-'."""
    if value is None:
        return True
    return str(value).strip().lower() in NOT_PROVIDED_TOKENS


def clean(value):
    """Strip and collapse whitespace; return None for empty / placeholder text."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value)).strip()
    return None if is_not_provided(s) else s


def normalize_date(value):
    """Return ISO 'YYYY-MM-DD' when parseable, else the cleaned string, else None."""
    if value is None:
        return None
    s = str(value).split(",")[0]          # drop time, e.g. '... , 13:13 (GMT)'
    s = s.replace("(GMT)", "").strip()
    s = s.lstrip("/").strip()             # Danaos ETD looks like '/ 1/7/2026'
    s = re.sub(r"\s+", " ", s)
    if not s or is_not_provided(s):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s  # unparseable: keep the cleaned original so nothing is silently lost


def to_float(value):
    """Parse a number that may use either '.' or ',' as the decimal separator."""
    if value is None:
        return None
    s = re.sub(r"[^\d.,-]", "", str(value)).strip()
    if not s or s in {"-", ".", ","}:
        return None
    if "," in s and "." in s:
        s = s.replace(",", "")            # 1,234.56 -> 1234.56 (comma = thousands)
    elif "," in s:
        s = s.replace(",", ".")           # 0,00 -> 0.00 (comma = decimal)
    try:
        return float(s)
    except ValueError:
        return None


def to_int(value):
    f = to_float(value)
    return int(f) if f is not None else None


_MEASURE_RE = re.compile(
    r"\b\d+[.,]?\d*\s?(mm|cm|mtr|metre|meter|ltr|lt|kg|gr|cc|ml|vac|vdc|ah|v|w|pcs|pce|pc)\b",
    re.IGNORECASE,
)
_REF_RE = re.compile(r"\b(offer|issa|imo|impa|cat\s*no\.?)\s*:?\s*\S+", re.IGNORECASE)


def normalize_item_name(description):
    """Reduce a verbose description to a short, group-able item name.

    e.g. 'PVC Insulation tape 15mm x 25meter rolls Black' -> 'Pvc Insulation Tape Rolls'
    """
    s = clean(description)
    if not s:
        return None
    s = re.sub(r"^\[[^\]]*\]\s*", "", s)          # drop leading [PC] / [BAG] tag
    s = _REF_RE.sub("", s)                         # drop Offer:/ISSA:/Cat No. refs
    s = _MEASURE_RE.sub("", s)                     # drop dimensions like 15mm, 1.5V
    s = re.sub(r"\d+", "", s)                       # drop remaining bare numbers
    s = re.sub(r"[^A-Za-z&/\s]", " ", s)          # keep letters only
    words = [w for w in re.sub(r"\s+", " ", s).split() if len(w) > 1 or w == "&"]
    name = " ".join(words[:4]) if words else s.strip()
    return name.title() if name else None
