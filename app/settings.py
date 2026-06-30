"""Settings page — database admin and AI provider (Phase 21)."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from modules import ai_extractor, database as db, excel_exporter

_PROVIDERS = ["openai", "claude", "both", "disabled"]
_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def render():
    st.header("Settings")

    # ---- Database -------------------------------------------------------- #
    st.subheader("Database")
    st.write("Database path:")
    st.code(db.DATABASE_PATH)
    counts = db.table_counts()
    c = st.columns(3)
    c[0].metric("Documents", counts.get("documents") or 0)
    c[1].metric("Line items", counts.get("line_items") or 0)
    c[2].metric("Review errors", counts.get("review_errors") or 0)

    b = st.columns(2)
    if b[0].button("Initialize Database"):
        db.init_db()
        st.success("Database initialized (tables created if missing).")
    if b[1].button("Backup database"):
        src = Path(db.DATABASE_PATH)
        if src.exists():
            backups = Path("data/backups")
            backups.mkdir(parents=True, exist_ok=True)
            dest = backups / f"cargopulse_{datetime.now():%Y%m%d_%H%M%S}.sqlite"
            shutil.copy(src, dest)
            st.success(f"Backup saved → {dest}")
        else:
            st.warning("No database file to back up yet.")

    with st.expander("⚠️ Danger zone — clear all data"):
        confirm = st.checkbox("I understand this permanently deletes all imported data.")
        if st.button("Clear database", disabled=not confirm):
            db.drop_all()
            st.success("All documents, line items and review errors deleted.")
            st.rerun()

    st.divider()

    # ---- AI provider ----------------------------------------------------- #
    st.subheader("AI fallback provider")
    current = ai_extractor.get_provider()
    idx = _PROVIDERS.index(current) if current in _PROVIDERS else _PROVIDERS.index("disabled")
    choice = st.selectbox(
        "Provider used for unknown / difficult PDF layouts",
        _PROVIDERS, index=idx,
    )
    if choice != current:
        os.environ["AI_PROVIDER"] = choice
        st.info(f"Provider set to **{choice}** for this session. "
                "Edit `.env` (AI_PROVIDER) to make it permanent.")
    st.write(f"Status: {'✅ available' if ai_extractor.is_ai_available() else '❌ no API key configured'}")
    st.caption("API keys (OPENAI_API_KEY / ANTHROPIC_API_KEY) are read from the `.env` file.")

    st.divider()

    # ---- Raw data export ------------------------------------------------- #
    st.subheader("Export raw data")
    if counts.get("documents"):
        if st.button("Build raw-data workbook"):
            st.session_state["settings_xlsx"] = excel_exporter.build_workbook()
        if st.session_state.get("settings_xlsx"):
            st.download_button(
                "⬇ Download all data (Excel)",
                st.session_state["settings_xlsx"],
                excel_exporter.default_filename(),
                _MIME,
            )
    else:
        st.caption("Nothing to export yet.")
