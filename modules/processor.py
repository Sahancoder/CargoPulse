"""End-to-end processing pipeline for PDFs (Phases 3, 4, 5, 10, 11, 12, 20)."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from modules import (
    ai_extractor,
    danaos_parser,
    database as db,
    format_detector,
    garrets_parser,
    pdf_reader,
    shipserv_parser,
    validator,
)
from modules.category_mapper import map_category
from modules.format_detector import (
    DANAOS_RFQ,
    GARRETS_AMOS_QUOTATION,
    SHIPSERV_RFQ,
)

INPUT_DIR = Path("data/input_pdfs")
PROCESSED_DIR = Path("data/processed_pdfs")
FAILED_DIR = Path("data/failed_pdfs")

_PARSERS = {
    SHIPSERV_RFQ: shipserv_parser,
    GARRETS_AMOS_QUOTATION: garrets_parser,
    DANAOS_RFQ: danaos_parser,
}


def file_hash(path) -> str:
    """SHA-256 of a file's bytes (Phase 3.4)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _move(src, dest_dir) -> Path:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(src).name
    try:
        if dest.exists():
            dest.unlink()
        shutil.move(str(src), str(dest))
    except (OSError, shutil.Error):
        pass
    return dest


def _review(file_name, rfq, issue, field=None, extracted=None, confidence=None):
    return {
        "file_name": file_name, "rfq_no": rfq, "issue_type": issue,
        "field_name": field, "extracted_value": extracted,
        "suggested_value": None, "confidence": confidence, "review_status": "open",
    }


def _enrich_items(items, doc, file_name):
    """Copy document context onto each line item + assign a category."""
    for it in items:
        it["file_name"] = file_name
        it["rfq_no"] = doc.get("rfq_no")
        it["quotation_no"] = doc.get("quotation_no")
        it["buyer_name"] = doc.get("buyer_name")
        it["vessel_name"] = doc.get("vessel_name")
        it["imo_number"] = doc.get("imo_number")
        it["port_name"] = doc.get("port_name")
        it["issued_date"] = doc.get("issued_date")
        if not it.get("currency"):
            it["currency"] = doc.get("currency")
        it["category"] = map_category(it.get("description"))
    return items


def process_pdf(file_path, file_name=None) -> dict:
    """Run the full pipeline for one PDF and persist the results."""
    file_path = Path(file_path)
    file_name = file_name or file_path.name
    result = {
        "file_name": file_name, "status": "failed", "document_format": None,
        "line_items": 0, "warnings": [], "errors": 0, "duplicate": False, "message": "",
    }

    fhash = file_hash(file_path)
    conn = db.connect_db()
    try:
        # 1) Identical-file duplicate (Phase 3.5)
        existing = db.file_hash_exists(conn, fhash)
        if existing:
            result.update(status="duplicate", duplicate=True,
                          message=f"Identical file already imported ({existing['file_name']})")
            _move(file_path, PROCESSED_DIR)
            return result

        # 2) Extract text (Phase 4)
        try:
            text, _pages = pdf_reader.extract_text_from_pdf(file_path)
        except Exception as exc:  # noqa: BLE001
            db.insert_review_errors(conn, [_review(file_name, None, "PDF Read Error", extracted=str(exc))])
            conn.commit()
            _move(file_path, FAILED_DIR)
            result["message"] = f"PDF read error: {exc}"
            return result

        # 3) Scanned / empty PDF
        if pdf_reader.is_scanned(text):
            db.insert_review_errors(conn, [_review(file_name, None, "Scanned PDF / OCR Needed")])
            conn.commit()
            _move(file_path, FAILED_DIR)
            result["message"] = "Scanned PDF / OCR needed"
            return result

        # 4) Detect format (Phase 5)
        fmt = format_detector.detect_format(text)
        result["document_format"] = fmt

        # 5) Parse (Phases 7-9) or AI fallback for unknown layouts (Phase 20)
        ai_used = False
        if fmt in _PARSERS:
            parsed = _PARSERS[fmt].parse(text)
        else:
            parsed = ai_extractor.extract_with_ai(text, fmt)
            if parsed is None:
                db.insert_review_errors(conn, [_review(file_name, None, "Unknown Format")])
                conn.commit()
                _move(file_path, FAILED_DIR)
                result.update(status="unknown", message="Unknown format (no parser / AI unavailable)")
                return result
            ai_used = True

        doc = parsed["document"]
        items = parsed.get("line_items", [])
        warnings = list(parsed.get("warnings", []))
        _enrich_items(items, doc, file_name)

        # 6) Validation (Phase 11)
        errors = validator.validate(doc, items, file_name)

        # 7) Logical duplicate: RFQ + vessel + issued date (Phase 11.9)
        dup = db.find_duplicate_rfq(conn, doc.get("rfq_no"), doc.get("vessel_name"), doc.get("issued_date"))
        if dup:
            errors.append(_review(file_name, doc.get("rfq_no"), "Duplicate RFQ",
                                  extracted=f"matches document id {dup['id']}"))

        # 8) Persist (Phase 12)
        doc_row = dict(doc)
        doc_row.update(
            file_name=file_name,
            file_hash=fhash,
            total_line_items=len(items),
            duplicate_flag=1 if dup else 0,
            extraction_status="ai" if ai_used else "parsed",
        )
        doc_id = db.insert_document(conn, doc_row)
        db.insert_line_items(conn, doc_id, items)
        db.insert_review_errors(conn, errors)
        conn.commit()

        _move(file_path, PROCESSED_DIR)
        result.update(
            status="ai" if ai_used else "saved",
            line_items=len(items),
            warnings=warnings,
            errors=len(errors),
            duplicate=bool(dup),
            message="OK",
        )
        return result
    finally:
        conn.close()


def process_paths(paths) -> dict:
    """Process several PDFs and return an aggregate summary (Phase 12.5)."""
    summary = {
        "documents": 0, "line_items": 0, "duplicates": 0, "unknown": 0,
        "failed": 0, "ai": 0, "warnings": 0, "errors": 0, "results": [],
    }
    for p in paths:
        r = process_pdf(p)
        summary["results"].append(r)
        status = r["status"]
        if status in ("saved", "ai"):
            summary["documents"] += 1
            summary["line_items"] += r["line_items"]
            summary["errors"] += r["errors"]
            summary["warnings"] += len(r["warnings"])
            if status == "ai":
                summary["ai"] += 1
        elif status == "duplicate":
            summary["duplicates"] += 1
        elif status == "unknown":
            summary["unknown"] += 1
        else:
            summary["failed"] += 1
    return summary
