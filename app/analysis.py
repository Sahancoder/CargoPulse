"""Analysis pages — vessel / item / buyer / port (Phase 17)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from app import components
from modules import queries


def _page(title, caption, df, chart_x=None, chart_y=None):
    st.header(title)
    if df.empty:
        st.info("No data yet. Import documents on the **Upload PDFs** page.")
        return
    st.caption(caption)

    if chart_x and chart_y and chart_x in df.columns and chart_y in df.columns:
        top = df.head(10).iloc[::-1]
        fig = px.bar(top, x=chart_x, y=chart_y, orientation="h")
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340, showlegend=False)
        st.plotly_chart(fig, width="stretch")

    st.dataframe(df, width="stretch", hide_index=True)
    components.csv_download(df, f"cargopulse_{title.split()[0].lower()}_analysis.csv")


def render_vessel():
    _page("Vessel Analysis",
          "RFQ activity, quantities and top items per vessel.",
          queries.vessel_analysis(), chart_x="RFQs", chart_y="Vessel")


def render_item():
    _page("Item Analysis",
          "How often each item is requested across vessels and buyers.",
          queries.item_analysis(), chart_x="Total Qty", chart_y="Item")


def render_buyer():
    _page("Buyer Analysis",
          "RFQ activity, vessels and categories per buyer.",
          queries.buyer_analysis(), chart_x="RFQs", chart_y="Buyer")


def render_port():
    _page("Port Analysis",
          "RFQ activity and quantities per supply port.",
          queries.port_analysis(), chart_x="RFQs", chart_y="Port")
