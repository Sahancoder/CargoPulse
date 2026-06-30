"""Documents page — browse, filter, search, export (Phase 13)."""

from __future__ import annotations

import streamlit as st

from app import components
from modules import queries

_VIEW = {
    "file_name": "File Name",
    "document_format": "Format",
    "rfq_no": "RFQ No",
    "quotation_no": "Quotation No",
    "vessel_name": "Vessel",
    "imo_number": "IMO",
    "buyer_name": "Buyer",
    "port_name": "Port",
    "issued_date": "Date",
    "total_line_items": "Items",
    "confidence_score": "Confidence",
}


def render():
    st.header("Documents")
    df = queries.load_documents()
    if df.empty:
        st.info("No documents yet. Import some on the **Upload PDFs** page.")
        return

    with st.expander("Filters & search", expanded=True):
        c = st.columns(4)
        df = components.multiselect_filter(df, "document_format", "Format", c[0])
        df = components.multiselect_filter(df, "buyer_name", "Buyer", c[1])
        df = components.multiselect_filter(df, "vessel_name", "Vessel", c[2])
        df = components.multiselect_filter(df, "port_name", "Port", c[3])
        query = st.text_input("Search (RFQ No / Quotation No / Vessel / IMO / File Name)")
        df = components.date_range_filter(df, "issued_date")

    df = components.search_filter(
        df, ["rfq_no", "quotation_no", "vessel_name", "imo_number", "file_name"], query
    )

    st.caption(f"{len(df)} document(s)")
    view = df[[c for c in _VIEW if c in df.columns]].rename(columns=_VIEW)
    st.dataframe(view, width="stretch", hide_index=True)
    components.csv_download(view, "cargopulse_documents.csv")
