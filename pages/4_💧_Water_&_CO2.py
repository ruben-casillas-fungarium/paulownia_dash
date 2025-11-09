# MIT License
# (c) 2025 Paulownia Circular-Economy Dashboard contributors
# This page is part of the paulownia_dash Streamlit app.
# It renders with defaults and reads the active Scenario from st.session_state["scenario"].
# All monetary values are EUR unless specified. Units in axis titles and tooltips.

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# --- Robust imports whether this file lives inside `pages/` or not

from core.params import Scenario
from core.sim_1_agriculture import run_sim
from core.sim_2_production import run_industrial_chain
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
        dfs = run_industrial_chain(scn)
        # unpack expected tuple
        df_log, df_ext, df_sub, df_pl = dfs
    except Exception:
        # If industrial chain not configured, provide empty shells
        df_log = pd.DataFrame()
        df_ext = pd.DataFrame()
        df_sub = pd.DataFrame()
        df_pl = pd.DataFrame()
    st.session_state[key] = {
        "agro": df_agro,
        "logistics": df_log,
        "extraction": df_ext,
        "substrate": df_sub,
        "plates": df_pl,
        "joined": df_agro.copy(),
    }
    return st.session_state[key]

def page() -> None:
    st.header("💧 Water & CO₂")
    res = _ensure_results()
    df = res["agro"].copy()

    # KPI cards
    total_water = float(df.get("water_m3", pd.Series([0])).sum())
    total_co2 = float(df.get("co2_t", pd.Series([0])).sum())
    k1,k2 = st.columns(2)
    k1.metric("Total Water (m³)", f"{total_water:,.0f}")
    k2.metric("Total CO₂ Fixed (t)", f"{total_co2:,.1f}")

    # Water series
    if {"year","water_m3"}.issubset(df.columns):
        fig_w = px.bar(df, x="year", y="water_m3",
                       title="Annual water need per hectare",
                       labels={"year":"Year","water_m3":"m³/ha"})
        st.plotly_chart(fig_w, width="stretch")

    # CO2 per-year and cumulative
    if {"year","co2_t"}.issubset(df.columns):
        dfc = df.copy()
        dfc["cum_co2"] = dfc["co2_t"].cumsum()
        fig_c = go.Figure()
        fig_c.add_trace(go.Bar(x=dfc["year"], y=dfc["co2_t"], name="Per year (tCO₂)"))
        fig_c.add_trace(go.Scatter(x=dfc["year"], y=dfc["cum_co2"], name="Cumulative (tCO₂)", yaxis="y2"))
        fig_c.update_layout(
            title="CO₂ fixation — annual & cumulative",
            yaxis=dict(title="tCO₂/year"),
            yaxis2=dict(title="tCO₂ cumulative", overlaying="y", side="right"),
            legend=dict(orientation="h")
        )
        st.plotly_chart(fig_c, width="stretch")

    st.caption("Note: CO₂ curve comes from the scenario’s piecewise fixation function; water is a user-set parameter (± variability).")


if __name__ == '__main__':
    page()
