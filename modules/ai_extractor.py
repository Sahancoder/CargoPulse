"""AI fallback extraction for unknown / difficult PDF layouts (Phase 20).

Uses Claude (Anthropic) by default and OpenAI optionally, selected by the
AI_PROVIDER env var. Every failure path degrades gracefully to ``None`` so the
processing pipeline can record a review error instead of crashing.
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from modules.schema import new_document, new_line_item
from modules.utils import clean, normalize_date, normalize_item_name, to_float, to_int

load_dotenv()

# Default models (override via env). Claude is the most capable default.
CLAUDE_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_DOC_STR_FIELDS = [
    "document_type", "rfq_no", "quotation_no", "buyer_name", "supplier_name",
    "vessel_name", "imo_number", "port_name", "department", "subject", "currency",
    "issued_date", "due_date", "deliver_by_date", "vessel_eta", "vessel_etd",
    "payment_terms",
]
_DOC_DATE_FIELDS = ["issued_date", "due_date", "deliver_by_date", "vessel_eta", "vessel_etd"]
_ITEM_STR_FIELDS = [
    "item_no", "section_name", "manufacturer", "model", "part_type", "part_number",
    "buyer_part_number", "item_code", "description", "uom", "currency", "remarks",
]
_ITEM_NUM_FIELDS = ["quantity", "unit_price", "extended_price"]

_SYSTEM_PROMPT = (
    "You are a precise maritime procurement data extractor. Extract only vessel "
    "RFQ or quotation details. Do not extract unrelated text. Do not guess or "
    "invent missing fields — use null when a value is absent. Return a document "
    "header and its line items."
)

_SHAPE_HINT = (
    'Respond with a JSON object of the form {"document": {header fields}, '
    '"line_items": [{item fields}]}. Document fields: '
    + ", ".join(_DOC_STR_FIELDS)
    + ". Item fields: "
    + ", ".join(_ITEM_STR_FIELDS + _ITEM_NUM_FIELDS)
    + ". Use null for anything missing."
)


def get_provider() -> str:
    """Return the configured AI provider: openai | claude | both | disabled."""
    return (os.getenv("AI_PROVIDER") or "disabled").strip().lower()


def is_ai_available() -> bool:
    provider = get_provider()
    if provider in ("claude", "anthropic"):
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "both":
        return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY"))
    return False


def _user_prompt(text: str) -> str:
    return (
        "Extract the RFQ/quotation header and all line items from the document "
        "text below. Return null for any field that is not present.\n\n---\n"
        f"{text}\n---"
    )


def _loads_lenient(raw):
    """Parse JSON, tolerating ```json fences or surrounding prose."""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("```", 2)[1] if s.count("```") >= 2 else s.strip("`")
        s = s[4:].strip() if s.lower().startswith("json") else s.strip()
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1:
        s = s[start:end + 1]
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _claude_schema() -> dict:
    doc_props = {k: {"type": ["string", "null"]} for k in _DOC_STR_FIELDS}
    item_props = {k: {"type": ["string", "null"]} for k in _ITEM_STR_FIELDS}
    item_props.update({k: {"type": ["number", "null"]} for k in _ITEM_NUM_FIELDS})
    item_schema = {
        "type": "object",
        "properties": item_props,
        "required": list(item_props),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "document": {
                "type": "object",
                "properties": doc_props,
                "required": list(doc_props),
                "additionalProperties": False,
            },
            "line_items": {"type": "array", "items": item_schema},
        },
        "required": ["document", "line_items"],
        "additionalProperties": False,
    }


def _extract_claude(text):
    import anthropic

    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    client = anthropic.Anthropic(api_key=key)
    kwargs = dict(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _user_prompt(text)}],
    )
    try:
        resp = client.messages.create(
            output_config={"format": {"type": "json_schema", "schema": _claude_schema()}},
            **kwargs,
        )
    except TypeError:
        # Older SDK without output_config: fall back to plain prompting.
        resp = client.messages.create(**kwargs)
    out = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), None)
    return _loads_lenient(out)


def _extract_openai(text):
    from openai import OpenAI

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": f"{_SYSTEM_PROMPT} {_SHAPE_HINT}"},
            {"role": "user", "content": _user_prompt(text)},
        ],
    )
    return _loads_lenient(resp.choices[0].message.content)


def _to_common(data: dict, document_format: str) -> dict:
    doc = new_document()
    doc["document_format"] = document_format
    src = data.get("document") or {}
    for k in _DOC_STR_FIELDS:
        doc[k] = clean(src.get(k))
    for dk in _DOC_DATE_FIELDS:
        doc[dk] = normalize_date(doc[dk])
    doc["confidence_score"] = 0.6  # AI-extracted: flag for review

    items = []
    for raw in (data.get("line_items") or []):
        it = new_line_item()
        for k in _ITEM_STR_FIELDS:
            it[k] = clean(raw.get(k))
        it["item_no"] = to_int(raw.get("item_no"))
        it["quantity"] = to_float(raw.get("quantity"))
        it["unit_price"] = to_float(raw.get("unit_price"))
        it["extended_price"] = to_float(raw.get("extended_price"))
        it["normalized_item_name"] = normalize_item_name(it["description"])
        it["confidence_score"] = 0.6
        items.append(it)

    return {"document": doc, "line_items": items, "warnings": ["AI-extracted (review recommended)"]}


def extract_with_ai(text, document_format="UNKNOWN"):
    """Run AI extraction; return the common result shape, or None on failure."""
    provider = get_provider()
    if provider in ("", "disabled"):
        return None

    order = []
    if provider in ("claude", "anthropic"):
        order = [_extract_claude]
    elif provider == "openai":
        order = [_extract_openai]
    elif provider == "both":
        order = [_extract_claude, _extract_openai]

    data = None
    for fn in order:
        try:
            data = fn(text)
        except Exception:
            data = None
        if data:
            break

    if not data or "document" not in data:
        return None
    return _to_common(data, document_format)
