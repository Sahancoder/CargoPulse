"""Dashboard page — KPI cards and charts (Phases 15, 16)."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from modules import queries


def _bar(df, x, y, orientation="v", color=None):
    fig = px.bar(df, x=x, y=y, orientation=orientation, color=color)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), showlegend=False, height=340)
    return fig


def render():
    st.header("Dashboard")
    k = queries.kpis()
    if k["total_rfqs"] == 0:
        st.info("No data yet. Go to **Upload PDFs** to import documents.")
        return

    r1 = st.columns(4)
    r1[0].metric("Total RFQs", f"{k['total_rfqs']:,}")
    r1[1].metric("Unique Vessels", f"{k['unique_vessels']:,}")
    r1[2].metric("Unique Buyers", f"{k['unique_buyers']:,}")
    r1[3].metric("Unique Ports", f"{k['unique_ports']:,}")
    r2 = st.columns(4)
    r2[0].metric("Line Items", f"{k['total_line_items']:,}")
    r2[1].metric("Total Qty Requested", f"{k['total_quantity']:,.0f}")
    r2[2].metric("Duplicate PDFs", f"{k['duplicates']:,}")
    r2[3].metric("Review Needed", f"{k['review_needed']:,}")

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("RFQs over time")
        df = queries.rfqs_over_time()
        if df.empty:
            st.caption("No dated documents.")
        else:
            fig = px.line(df, x="date", y="rfqs", markers=True)
            fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
            st.plotly_chart(fig, width="stretch")
    with c2:
        st.subheader("Document formats")
        df = queries.format_distribution()
        fig = px.pie(df, names="format", values="count", hole=0.45)
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=340)
        st.plotly_chart(fig, width="stretch")

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Top vessels by RFQs")
        df = queries.top_vessels()
        st.plotly_chart(_bar(df.iloc[::-1], x="rfqs", y="vessel", orientation="h"), width="stretch")
    with c4:
        st.subheader("Top buyers by RFQs")
        df = queries.top_buyers()
        st.plotly_chart(_bar(df.iloc[::-1], x="rfqs", y="buyer", orientation="h"), width="stretch")

    c5, c6 = st.columns(2)
    with c5:
        st.subheader("Top ports by RFQs")
        df = queries.top_ports()
        st.plotly_chart(_bar(df.iloc[::-1], x="rfqs", y="port", orientation="h"), width="stretch")
    with c6:
        st.subheader("Quantity by category")
        df = queries.category_quantity()
        st.plotly_chart(_bar(df.iloc[::-1], x="quantity", y="category", orientation="h"), width="stretch")

    st.subheader("Top requested items")
    df = queries.top_items(15)
    if df.empty:
        st.caption("No items yet.")
    else:
        fig = _bar(df.iloc[::-1], x="quantity", y="item", orientation="h")
        fig.update_layout(height=460)
        st.plotly_chart(fig, width="stretch")
