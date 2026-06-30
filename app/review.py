"""Review / Errors page — inspect and resolve extraction issues (Phase 18)."""

from __future__ import annotations

import streamlit as st

from app import components
from modules import queries

_VIEW = {
    "file_name": "File Name",
    "rfq_no": "RFQ No",
    "issue_type": "Issue Type",
    "field_name": "Field",
    "extracted_value": "Extracted Value",
    "suggested_value": "Suggested Value",
    "confidence": "Confidence",
    "review_status": "Status",
}


def _all_issues_tab():
    df = queries.load_review_errors()
    if df.empty:
        st.success("No review issues 🎉")
        return

    open_count = int((df["review_status"].fillna("open") != "resolved").sum())
    st.caption(f"{len(df)} issue(s) · {open_count} open")

    c = st.columns(3)
    df = components.multiselect_filter(df, "issue_type", "Issue Type", c[0])
    df = components.multiselect_filter(df, "review_status", "Status", c[1])
    df = components.multiselect_filter(df, "file_name", "File", c[2])

    view = df[[col for col in _VIEW if col in df.columns]].rename(columns=_VIEW)
    st.dataframe(view, width="stretch", hide_index=True)

    st.markdown("**Resolve issues**")
    unresolved = df[df["review_status"].fillna("open") != "resolved"]
    if unresolved.empty:
        st.caption("Nothing open in the current filter.")
    else:
        labels = {
            f"#{r.id} · {r.issue_type} · {r.file_name}": int(r.id)
            for r in unresolved.itertuples()
        }
        picked = st.multiselect("Select issues to mark resolved", list(labels.keys()))
        col1, col2 = st.columns(2)
        if col1.button("Mark selected resolved", disabled=not picked):
            for lbl in picked:
                queries.mark_resolved(labels[lbl])
            st.success(f"Resolved {len(picked)} issue(s).")
            st.rerun()
        if col2.button("Mark ALL resolved"):
            queries.mark_all_resolved()
            st.success("All issues marked resolved.")
            st.rerun()

    components.csv_download(view, "cargopulse_review_errors.csv")


def render():
    st.header("Review / Errors")
    tabs = st.tabs(["All issues", "Unknown formats", "Duplicate RFQs"])

    with tabs[0]:
        _all_issues_tab()

    with tabs[1]:
        df = queries.unknown_format_files()
        if df.empty:
            st.success("No unknown-format files.")
        else:
            st.caption(f"{len(df)} file(s) needing a parser or AI extraction.")
            st.dataframe(df[["file_name", "issue_type", "review_status", "created_at"]],
                         width="stretch", hide_index=True)

    with tabs[2]:
        df = queries.duplicate_rfqs()
        if df.empty:
            st.success("No duplicate RFQs detected.")
        else:
            st.caption(f"{len(df)} document(s) flagged as duplicates (same RFQ + vessel + date).")
            st.dataframe(df, width="stretch", hide_index=True)
