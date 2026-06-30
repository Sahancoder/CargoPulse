"""Line Items page — browse, filter, search, export (Phase 14)."""

from __future__ import annotations

import streamlit as st

from app import components
from modules import queries

_VIEW = {
    "rfq_no": "RFQ No",
    "vessel_name": "Vessel",
    "buyer_name": "Buyer",
    "description": "Item",
    "part_number": "Part No",
    "item_code": "Item Code",
    "quantity": "Qty",
    "uom": "UoM",
    "category": "Category",
    "issued_date": "Date",
    "file_name": "Source File",
}


def render():
    st.header("Line Items")
    df = queries.load_line_items()
    if df.empty:
        st.info("No line items yet. Import some on the **Upload PDFs** page.")
        return

    with st.expander("Filters & search", expanded=True):
        c = st.columns(4)
        df = components.multiselect_filter(df, "vessel_name", "Vessel", c[0])
        df = components.multiselect_filter(df, "buyer_name", "Buyer", c[1])
        df = components.multiselect_filter(df, "category", "Category", c[2])
        df = components.multiselect_filter(df, "uom", "UoM", c[3])
        query = st.text_input("Search (Description / Part Number / Item Code)")
        df = components.date_range_filter(df, "issued_date")

    df = components.search_filter(df, ["description", "part_number", "item_code"], query)

    m = st.columns(3)
    m[0].metric("Line items", f"{len(df):,}")
    m[1].metric("Total quantity", f"{df['quantity'].fillna(0).sum():,.0f}")
    m[2].metric("Distinct items", f"{df['normalized_item_name'].nunique():,}")

    view = df[[c for c in _VIEW if c in df.columns]].rename(columns=_VIEW)
    st.dataframe(view, width="stretch", hide_index=True)
    components.csv_download(view, "cargopulse_line_items.csv")
