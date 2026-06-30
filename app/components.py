"""Small shared UI helpers for the page modules."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def search_filter(df: pd.DataFrame, cols, query) -> pd.DataFrame:
    """Keep rows where any of `cols` contains the (case-insensitive) query."""
    if not query:
        return df
    ql = str(query).lower()
    mask = pd.Series(False, index=df.index)
    for c in cols:
        if c in df.columns:
            mask |= df[c].astype(str).str.lower().str.contains(ql, na=False, regex=False)
    return df[mask]


def multiselect_filter(df: pd.DataFrame, col, label, container=st) -> pd.DataFrame:
    """Render a multiselect of a column's distinct values and apply it."""
    if col not in df.columns or df[col].dropna().empty:
        return df
    options = sorted(df[col].dropna().astype(str).unique())
    chosen = container.multiselect(label, options)
    if chosen:
        return df[df[col].astype(str).isin(chosen)]
    return df


def date_range_filter(df: pd.DataFrame, col, label="Date range") -> pd.DataFrame:
    if col not in df.columns:
        return df
    dates = pd.to_datetime(df[col], errors="coerce")
    valid = dates.dropna()
    if valid.empty:
        return df
    dmin, dmax = valid.min().date(), valid.max().date()
    if dmin == dmax:
        return df
    rng = st.date_input(label, (dmin, dmax), min_value=dmin, max_value=dmax)
    if isinstance(rng, (tuple, list)) and len(rng) == 2:
        lo, hi = rng
        keep = ((dates.dt.date >= lo) & (dates.dt.date <= hi)) | dates.isna()
        return df[keep]
    return df


def csv_download(df: pd.DataFrame, filename, label="⬇ Download CSV"):
    st.download_button(
        label,
        df.to_csv(index=False).encode("utf-8-sig"),
        filename,
        "text/csv",
        width="content",
    )
