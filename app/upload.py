"""Upload PDFs page — bulk upload and process (Phases 3, 4)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from modules import format_detector, pdf_reader, processor

_STATUS_ICON = {
    "saved": "✅", "ai": "🤖", "duplicate": "♻️", "unknown": "❓", "failed": "⚠️",
}


def _show_summary(summary):
    st.success("Processing complete.")
    cols = st.columns(5)
    cols[0].metric("Documents saved", summary["documents"])
    cols[1].metric("Line items", summary["line_items"])
    cols[2].metric("Duplicates", summary["duplicates"])
    cols[3].metric("Unknown / Failed", summary["unknown"] + summary["failed"])
    cols[4].metric("Review flags", summary["errors"])

    rows = [
        {
            "": _STATUS_ICON.get(r["status"], ""),
            "File": r["file_name"],
            "Status": r["status"],
            "Format": r["document_format"] or "-",
            "Items": r["line_items"],
            "Flags": r["errors"],
            "Note": r["message"],
        }
        for r in summary["results"]
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _preview_section():
    with st.expander("🔍 Preview extracted text from a PDF (without importing)"):
        prev = st.file_uploader("Pick a PDF to preview", type=["pdf"], key="preview_pdf")
        if prev is not None:
            tmp = Path(tempfile.gettempdir()) / prev.name
            with open(tmp, "wb") as out:
                out.write(prev.getbuffer())
            try:
                text, pages = pdf_reader.extract_text_from_pdf(tmp)
                fmt = format_detector.detect_format(text)
                scanned = pdf_reader.is_scanned(text)
                st.write(f"Pages: **{pages}** · Detected format: **{fmt}**"
                         + ("  · ⚠️ looks scanned (little text)" if scanned else ""))
                st.text_area("Extracted text", text[:8000], height=320)
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass


def render():
    st.header("Upload PDFs")
    st.caption("Bulk-upload RFQ / quotation PDFs. Identical files and re-issued RFQs are detected automatically.")

    files = st.file_uploader(
        "Choose PDF files", type=["pdf"], accept_multiple_files=True,
    )
    if files:
        st.info(f"{len(files)} file(s) ready to process.")

    process = st.button("Process PDFs", type="primary", disabled=not files)

    if process and files:
        processor.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        saved = []
        for f in files:
            dest = processor.INPUT_DIR / f.name
            with open(dest, "wb") as out:
                out.write(f.getbuffer())
            saved.append(dest)
        with st.spinner(f"Processing {len(saved)} PDF(s)…"):
            summary = processor.process_paths(saved)
        _show_summary(summary)

    st.divider()
    _preview_section()
