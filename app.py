"""CargoPulse — Ship RFQ Analytics & PDF Extraction.

Streamlit entry point. The sidebar routes to page modules in ``app/``;
all business logic lives in ``modules/``.

Run with:  streamlit run app.py
"""

import base64
from pathlib import Path

import streamlit as st

from app import (
    analysis,
    dashboard,
    documents,
    export,
    line_items,
    review,
    settings,
    upload,
)
from modules import database as db

APP_TITLE = "CargoPulse"
APP_SUBTITLE = "Ship RFQ Analytics & PDF Extraction"
APP_VERSION = "v1.0"

_LOGO_PATH = Path(__file__).parent / "app" / "public" / "75-years-footer-logo.svg"


def _logo_data_uri():
    """Inline the SVG logo as a data URI (shown on a dark panel since it's white)."""
    try:
        svg = _LOGO_PATH.read_bytes()
    except OSError:
        return None
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode("ascii")


_LOGO_URI = _logo_data_uri()

# Page label -> render function.
PAGES = {
    "Dashboard": dashboard.render,
    "Upload PDFs": upload.render,
    "Documents": documents.render,
    "Line Items": line_items.render,
    "Vessel Analysis": analysis.render_vessel,
    "Item Analysis": analysis.render_item,
    "Buyer Analysis": analysis.render_buyer,
    "Port Analysis": analysis.render_port,
    "Review / Errors": review.render,
    "Export Excel": export.render,
    "Settings": settings.render,
}


@st.cache_resource
def _bootstrap():
    """Create the database/tables once per server start."""
    db.init_db()
    return True


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🚢",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _bootstrap()

    with st.sidebar:
        if _LOGO_URI:
            st.markdown(
                '<div style="background:#0b2942;border-radius:10px;padding:14px 10px;'
                'text-align:center;margin-bottom:8px;">'
                f'<img src="{_LOGO_URI}" style="width:78%;max-width:190px;"/></div>',
                unsafe_allow_html=True,
            )
            st.markdown(f"### {APP_TITLE}")
        else:
            st.title(f"🚢 {APP_TITLE}")
        st.caption(APP_SUBTITLE)
        st.divider()
        page = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
        st.divider()
        try:
            counts = db.table_counts()
            st.caption(
                f"📄 {counts.get('documents') or 0} docs · "
                f"📦 {counts.get('line_items') or 0} items"
            )
        except Exception:  # noqa: BLE001
            pass
        st.caption(APP_VERSION)

    PAGES[page]()


if __name__ == "__main__":
    main()
