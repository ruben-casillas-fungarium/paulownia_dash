# MIT License
# (c) 2025 Paulownia Circular-Economy Dashboard contributors
# This page is part of the paulownia_dash Streamlit app.
# It reads the active Scenario from st.session_state["scenario"] and
# gracefully handles missing dataframes/columns.
# Monetary units: EUR; Emissions: tCO2 unless noted; Energy: kWh.

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Robust imports whether this file lives inside `pages/` or not
from core.params import Scenario
from core.sim_1_agriculture import run_sim
from core.sim_2_production import run_industrial_chain
# optional modules
from core.sim_3_eol import run_eol_module
from core.aggregate import compute_business_streams
from core.economics import npv, irr


def _get_scenario() -> Scenario:
    """Return the active Scenario from session state or a default instance."""
    scn = st.session_state.get("scenario")
    if scn is None:
        scn = Scenario()  # default
        st.session_state["scenario"] = scn
    return scn


def _ensure_results() -> Dict[str, pd.DataFrame]:
    """Run sims and cache results in session_state to avoid recompute."""
    key = "results_cache"
    if key in st.session_state:
        return st.session_state[key]
    scn: Scenario = _get_scenario()
    df_agro = run_sim(scn)
    try:
        df_log, df_ext, df_sub, df_pl = run_industrial_chain(scn)
    except Exception:
        df_log = pd.DataFrame()
        df_ext = pd.DataFrame()
        df_sub = pd.DataFrame()
        df_pl = pd.DataFrame()
    out = {
        "agro": df_agro,
        "logistics": df_log,
        "extraction": df_ext,
        "substrate": df_sub,
        "plates": df_pl,
    }
    st.session_state[key] = out
    return out


def _fmt_eur(x: float) -> str:
    return f"€{x:,.0f}"


def _safe(df: pd.DataFrame, col: str, default: float=0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default]*len(df))

def page() -> None:
    st.header("🧪 Extraction & Products")
    res = _ensure_results()
    df = res["extraction"]
    if df.empty:
        st.info("Extraction data not available. Configure industrial chain parameters to enable this view.")
        return

    # KPIs
    roots_in = float(_safe(df, "roots_in_t").sum())
    extract_L = float(_safe(df, "extract_L").sum())
    fibers_t = float(_safe(df, "root_fiber_t").sum())
    E_total = float(_safe(df, "E_total_kWh", 0).sum() if "E_total_kWh" in df else (_safe(df,"E_total").sum()))
    rev_extract = float(_safe(df, "rev_extract").sum())
    co2_scope2 = float(_safe(df, "co2_scope2_t").sum())

    c = st.columns(5)
    c[0].metric("Roots processed", f"{roots_in:,.1f} t")
    c[1].metric("Extract", f"{extract_L:,.0f} L")
    c[2].metric("Fibers", f"{fibers_t:,.1f} t")
    c[3].metric("Energy", f"{E_total:,.0f} kWh")
    c[4].metric("Scope‑2 CO₂", f"{co2_scope2:,.2f} t")
    st.metric("Extract revenue (annual)", _fmt_eur(rev_extract))

    # Energy by type (if present)
    cols_energy = [c for c in ["E_steam","E_press","E_over","E_total","E_total_kWh"] if c in df.columns]
    if cols_energy:
        fig_e = px.bar(df, x="year", y=cols_energy, title="Extraction energy by year", labels={"value":"kWh","year":"Year"})
        st.plotly_chart(fig_e, width="stretch")

    # Product composition (oleic/theobromine) if available
    comp_cols = [c for c in ["oleic_kg","theobromine_kg"] if c in df.columns]
    if comp_cols:
        comp = df[["year"]+comp_cols].melt("year", var_name="component", value_name="kg")
        fig_c = px.area(comp, x="year", y="kg", color="component", title="Purified products (kg/year)")
        st.plotly_chart(fig_c, width="stretch")

    st.subheader("Extraction table")
    st.dataframe(df, width="stretch")
    st.download_button("Download extraction CSV", df.to_csv(index=False).encode(), "extraction.csv", "text/csv")


if __name__ == "__main__":
    page()
