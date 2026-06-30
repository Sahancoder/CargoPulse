"""SQLite database setup, inserts and low-level helpers (Phase 2 & 12)."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/vesseliq.sqlite")


# --------------------------------------------------------------------------- #
# Connection
# --------------------------------------------------------------------------- #
def connect_db() -> sqlite3.Connection:
    """Open a SQLite connection (creating the parent folder if needed)."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def db_exists() -> bool:
    return Path(DATABASE_PATH).exists()


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #
_DOCUMENTS_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name         TEXT,
    file_hash         TEXT,
    document_format   TEXT,
    document_type     TEXT,
    rfq_no            TEXT,
    quotation_no      TEXT,
    buyer_name        TEXT,
    supplier_name     TEXT,
    vessel_name       TEXT,
    imo_number        TEXT,
    port_name         TEXT,
    department        TEXT,
    subject           TEXT,
    currency          TEXT,
    issued_date       TEXT,
    due_date          TEXT,
    deliver_by_date   TEXT,
    vessel_eta        TEXT,
    vessel_etd        TEXT,
    payment_terms     TEXT,
    total_line_items  INTEGER,
    duplicate_flag    INTEGER DEFAULT 0,
    extraction_status TEXT,
    confidence_score  REAL,
    created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_LINE_ITEMS_SQL = """
CREATE TABLE IF NOT EXISTS line_items (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id          INTEGER,
    file_name            TEXT,
    rfq_no               TEXT,
    quotation_no         TEXT,
    buyer_name           TEXT,
    vessel_name          TEXT,
    imo_number           TEXT,
    port_name            TEXT,
    issued_date          TEXT,
    item_no              INTEGER,
    section_name         TEXT,
    manufacturer         TEXT,
    model                TEXT,
    part_type            TEXT,
    part_number          TEXT,
    buyer_part_number    TEXT,
    item_code            TEXT,
    description          TEXT,
    normalized_item_name TEXT,
    category             TEXT,
    uom                  TEXT,
    quantity             REAL,
    unit_price           REAL,
    extended_price       REAL,
    currency             TEXT,
    remarks              TEXT,
    confidence_score     REAL,
    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
);
"""

_REVIEW_ERRORS_SQL = """
CREATE TABLE IF NOT EXISTS review_errors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name       TEXT,
    rfq_no          TEXT,
    issue_type      TEXT,
    field_name      TEXT,
    extracted_value TEXT,
    suggested_value TEXT,
    confidence      REAL,
    review_status   TEXT DEFAULT 'open',
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_documents_hash ON documents (file_hash)",
    "CREATE INDEX IF NOT EXISTS ix_documents_rfq ON documents (rfq_no)",
    "CREATE INDEX IF NOT EXISTS ix_line_items_doc ON line_items (document_id)",
    "CREATE INDEX IF NOT EXISTS ix_review_status ON review_errors (review_status)",
]


def init_db() -> None:
    """Create all tables and indexes if they do not exist."""
    conn = connect_db()
    try:
        conn.execute(_DOCUMENTS_SQL)
        conn.execute(_LINE_ITEMS_SQL)
        conn.execute(_REVIEW_ERRORS_SQL)
        for ix in _INDEXES:
            conn.execute(ix)
        conn.commit()
    finally:
        conn.close()


def drop_all() -> None:
    """Delete every row from all tables (keeps the schema)."""
    conn = connect_db()
    try:
        for t in ("line_items", "review_errors", "documents"):
            conn.execute(f"DELETE FROM {t}")
        conn.commit()
    finally:
        conn.close()


def table_counts() -> dict:
    conn = connect_db()
    try:
        out = {}
        for t in ("documents", "line_items", "review_errors"):
            try:
                out[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            except sqlite3.OperationalError:
                out[t] = None
        return out
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Inserts (Phase 12)
# --------------------------------------------------------------------------- #
DOCUMENT_COLUMNS = [
    "file_name", "file_hash", "document_format", "document_type", "rfq_no",
    "quotation_no", "buyer_name", "supplier_name", "vessel_name", "imo_number",
    "port_name", "department", "subject", "currency", "issued_date", "due_date",
    "deliver_by_date", "vessel_eta", "vessel_etd", "payment_terms",
    "total_line_items", "duplicate_flag", "extraction_status", "confidence_score",
]

LINE_ITEM_COLUMNS = [
    "document_id", "file_name", "rfq_no", "quotation_no", "buyer_name",
    "vessel_name", "imo_number", "port_name", "issued_date", "item_no",
    "section_name", "manufacturer", "model", "part_type", "part_number",
    "buyer_part_number", "item_code", "description", "normalized_item_name",
    "category", "uom", "quantity", "unit_price", "extended_price", "currency",
    "remarks", "confidence_score",
]

REVIEW_ERROR_COLUMNS = [
    "file_name", "rfq_no", "issue_type", "field_name", "extracted_value",
    "suggested_value", "confidence", "review_status",
]


def insert_document(conn: sqlite3.Connection, data: dict) -> int:
    placeholders = ",".join("?" for _ in DOCUMENT_COLUMNS)
    values = [data.get(c) for c in DOCUMENT_COLUMNS]
    cur = conn.execute(
        f"INSERT INTO documents ({','.join(DOCUMENT_COLUMNS)}) VALUES ({placeholders})",
        values,
    )
    return cur.lastrowid


def insert_line_items(conn: sqlite3.Connection, document_id: int, items: list) -> int:
    if not items:
        return 0
    placeholders = ",".join("?" for _ in LINE_ITEM_COLUMNS)
    sql = f"INSERT INTO line_items ({','.join(LINE_ITEM_COLUMNS)}) VALUES ({placeholders})"
    rows = []
    for it in items:
        d = dict(it)
        d["document_id"] = document_id
        rows.append([d.get(c) for c in LINE_ITEM_COLUMNS])
    conn.executemany(sql, rows)
    return len(rows)


def insert_review_errors(conn: sqlite3.Connection, errors: list) -> int:
    if not errors:
        return 0
    placeholders = ",".join("?" for _ in REVIEW_ERROR_COLUMNS)
    sql = f"INSERT INTO review_errors ({','.join(REVIEW_ERROR_COLUMNS)}) VALUES ({placeholders})"
    rows = [[e.get(c) for c in REVIEW_ERROR_COLUMNS] for e in errors]
    conn.executemany(sql, rows)
    return len(rows)


# --------------------------------------------------------------------------- #
# Duplicate detection helpers
# --------------------------------------------------------------------------- #
def file_hash_exists(conn: sqlite3.Connection, file_hash: str):
    """Return the existing row (id, file_name) for a hash, or None."""
    return conn.execute(
        "SELECT id, file_name FROM documents WHERE file_hash = ?", (file_hash,)
    ).fetchone()


def find_duplicate_rfq(conn: sqlite3.Connection, rfq_no, vessel_name, issued_date):
    """Detect a logical duplicate by RFQ No + Vessel + Issued date (Phase 11.9)."""
    if not rfq_no:
        return None
    return conn.execute(
        """
        SELECT id FROM documents
        WHERE rfq_no = ?
          AND IFNULL(vessel_name, '') = IFNULL(?, '')
          AND IFNULL(issued_date, '') = IFNULL(?, '')
        """,
        (rfq_no, vessel_name, issued_date),
    ).fetchone()
