"""Export Excel page (Phase 19)."""

from __future__ import annotations

import streamlit as st

from modules import excel_exporter, queries

_SHEETS = [
    "Documents", "Line_Items", "Vessel_Summary", "Item_Summary",
    "Buyer_Summary", "Port_Summary", "Review_Errors",
]
_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render():
    st.header("Export Excel")
    k = queries.kpis()
    if k["total_rfqs"] == 0:
        st.info("No data to export yet.")
        return

    st.write("Generate a formatted workbook (bold headers, frozen top row, filters, "
             "auto column widths) with these sheets:")
    st.markdown("\n".join(f"- **{s}**" for s in _SHEETS))

    cols = st.columns(3)
    cols[0].metric("Documents", f"{k['total_rfqs']:,}")
    cols[1].metric("Line items", f"{k['total_line_items']:,}")
    cols[2].metric("Review issues", f"{k['review_needed']:,}")

    if st.button("Build Excel workbook", type="primary"):
        with st.spinner("Building workbook…"):
            st.session_state["vesseliq_xlsx"] = excel_exporter.build_workbook()
            st.session_state["vesseliq_xlsx_name"] = excel_exporter.default_filename()
        st.success("Workbook ready — download below.")

    data = st.session_state.get("vesseliq_xlsx")
    if data:
        st.download_button(
            "⬇ Download Excel",
            data,
            st.session_state.get("vesseliq_xlsx_name", excel_exporter.default_filename()),
            _MIME,
            type="primary",
        )
