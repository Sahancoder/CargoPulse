"""Analytics query helpers for the dashboard and analysis pages."""

from __future__ import annotations

import pandas as pd

from modules.database import connect_db


def _df(sql, params=()):
    conn = connect_db()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Raw loaders (used by the table pages, which filter in-memory)
# --------------------------------------------------------------------------- #
def load_documents():
    return _df("SELECT * FROM documents ORDER BY id DESC")


def load_line_items():
    return _df("SELECT * FROM line_items ORDER BY id")


def load_review_errors():
    return _df("SELECT * FROM review_errors ORDER BY id DESC")


# --------------------------------------------------------------------------- #
# KPIs (Phase 15)
# --------------------------------------------------------------------------- #
def kpis() -> dict:
    conn = connect_db()
    try:
        def s(sql):
            return conn.execute(sql).fetchone()[0]
        return {
            "total_rfqs": s("SELECT COUNT(*) FROM documents"),
            "unique_vessels": s("SELECT COUNT(DISTINCT vessel_name) FROM documents WHERE vessel_name IS NOT NULL"),
            "unique_buyers": s("SELECT COUNT(DISTINCT buyer_name) FROM documents WHERE buyer_name IS NOT NULL"),
            "unique_ports": s("SELECT COUNT(DISTINCT port_name) FROM documents WHERE port_name IS NOT NULL"),
            "total_line_items": s("SELECT COUNT(*) FROM line_items"),
            "total_quantity": s("SELECT COALESCE(SUM(quantity), 0) FROM line_items"),
            "duplicates": s("SELECT COUNT(*) FROM documents WHERE duplicate_flag = 1"),
            "review_needed": s("SELECT COUNT(*) FROM review_errors WHERE IFNULL(review_status,'open') != 'resolved'"),
        }
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Dashboard charts (Phase 16)
# --------------------------------------------------------------------------- #
def rfqs_over_time():
    return _df(
        "SELECT issued_date AS date, COUNT(*) AS rfqs FROM documents "
        "WHERE issued_date IS NOT NULL GROUP BY issued_date ORDER BY issued_date"
    )


def top_vessels(n=10):
    return _df(
        "SELECT vessel_name AS vessel, COUNT(*) AS rfqs FROM documents "
        "WHERE vessel_name IS NOT NULL GROUP BY vessel_name ORDER BY rfqs DESC LIMIT ?", (n,)
    )


def top_buyers(n=10):
    return _df(
        "SELECT buyer_name AS buyer, COUNT(*) AS rfqs FROM documents "
        "WHERE buyer_name IS NOT NULL GROUP BY buyer_name ORDER BY rfqs DESC LIMIT ?", (n,)
    )


def top_ports(n=10):
    return _df(
        "SELECT port_name AS port, COUNT(*) AS rfqs FROM documents "
        "WHERE port_name IS NOT NULL GROUP BY port_name ORDER BY rfqs DESC LIMIT ?", (n,)
    )


def top_items(n=15):
    return _df(
        "SELECT normalized_item_name AS item, SUM(quantity) AS quantity, COUNT(*) AS lines "
        "FROM line_items WHERE normalized_item_name IS NOT NULL "
        "GROUP BY normalized_item_name ORDER BY quantity DESC LIMIT ?", (n,)
    )


def category_quantity():
    return _df(
        "SELECT COALESCE(category,'Others') AS category, SUM(quantity) AS quantity, COUNT(*) AS lines "
        "FROM line_items GROUP BY category ORDER BY quantity DESC"
    )


def format_distribution():
    return _df(
        "SELECT COALESCE(document_format,'UNKNOWN') AS format, COUNT(*) AS count "
        "FROM documents GROUP BY document_format ORDER BY count DESC"
    )


# --------------------------------------------------------------------------- #
# Analysis pages (Phase 17) — computed in pandas for richer per-group columns
# --------------------------------------------------------------------------- #
def _mode(series):
    s = series.dropna()
    return s.value_counts().idxmax() if not s.empty else None


def vessel_analysis():
    docs, items = load_documents(), load_line_items()
    if docs.empty:
        return pd.DataFrame()
    rows = []
    for vessel, g in docs[docs.vessel_name.notna()].groupby("vessel_name"):
        li = items[items.vessel_name == vessel]
        imo = g.imo_number.dropna()
        rows.append({
            "Vessel": vessel,
            "IMO": imo.iloc[0] if not imo.empty else None,
            "RFQs": g.id.nunique(),
            "Items": len(li),
            "Total Qty": round(li.quantity.fillna(0).sum(), 2),
            "First RFQ": g.issued_date.dropna().min(),
            "Last RFQ": g.issued_date.dropna().max(),
            "Top Category": _mode(li.category),
            "Top Item": _mode(li.normalized_item_name),
        })
    return pd.DataFrame(rows).sort_values("RFQs", ascending=False).reset_index(drop=True)


def item_analysis():
    items = load_line_items()
    if items.empty:
        return pd.DataFrame()
    rows = []
    for name, g in items[items.normalized_item_name.notna()].groupby("normalized_item_name"):
        rows.append({
            "Item": name,
            "Category": _mode(g.category),
            "Total Qty": round(g.quantity.fillna(0).sum(), 2),
            "RFQ Count": g.document_id.nunique(),
            "Vessels": g.vessel_name.nunique(),
            "Buyers": g.buyer_name.nunique(),
            "First Seen": g.issued_date.dropna().min(),
            "Last Seen": g.issued_date.dropna().max(),
        })
    return pd.DataFrame(rows).sort_values("Total Qty", ascending=False).reset_index(drop=True)


def buyer_analysis():
    docs, items = load_documents(), load_line_items()
    if docs.empty:
        return pd.DataFrame()
    rows = []
    for buyer, g in docs[docs.buyer_name.notna()].groupby("buyer_name"):
        li = items[items.buyer_name == buyer]
        rows.append({
            "Buyer": buyer,
            "RFQs": g.id.nunique(),
            "Vessels": g.vessel_name.nunique(),
            "Items": len(li),
            "Total Qty": round(li.quantity.fillna(0).sum(), 2),
            "Top Vessel": _mode(g.vessel_name),
            "Top Category": _mode(li.category),
        })
    return pd.DataFrame(rows).sort_values("RFQs", ascending=False).reset_index(drop=True)


def port_analysis():
    docs, items = load_documents(), load_line_items()
    if docs.empty:
        return pd.DataFrame()
    rows = []
    for port, g in docs[docs.port_name.notna()].groupby("port_name"):
        li = items[items.port_name == port]
        rows.append({
            "Port": port,
            "RFQs": g.id.nunique(),
            "Vessels": g.vessel_name.nunique(),
            "Items": len(li),
            "Total Qty": round(li.quantity.fillna(0).sum(), 2),
        })
    return pd.DataFrame(rows).sort_values("RFQs", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Review / Errors (Phase 18)
# --------------------------------------------------------------------------- #
def mark_resolved(error_id):
    conn = connect_db()
    try:
        conn.execute("UPDATE review_errors SET review_status='resolved' WHERE id=?", (error_id,))
        conn.commit()
    finally:
        conn.close()


def mark_all_resolved():
    conn = connect_db()
    try:
        conn.execute("UPDATE review_errors SET review_status='resolved' WHERE IFNULL(review_status,'open')!='resolved'")
        conn.commit()
    finally:
        conn.close()


def unknown_format_files():
    return _df("SELECT * FROM review_errors WHERE issue_type='Unknown Format' ORDER BY id DESC")


def duplicate_rfqs():
    return _df(
        "SELECT id, file_name, rfq_no, vessel_name, issued_date, document_format "
        "FROM documents WHERE duplicate_flag=1 ORDER BY id DESC"
    )
