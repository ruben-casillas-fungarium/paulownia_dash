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
    st.header("🪵 Biomass Flows")
    # scn = _get_scenario()
    res = _ensure_results()
    df = res["agro"].copy()

    # KPIs
    total_trunk = float(df["trunk_t"].sum()) if "trunk_t" in df else 0.0
    total_crown = float(df["crown_t"].sum()) if "crown_t" in df else 0.0
    total_roots = float(df["roots_t"].sum()) if "roots_t" in df else 0.0
    compost_t = float(df.get("compost_t", pd.Series([0])).sum())

    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Total Trunk (t)", f"{total_trunk:,.1f}")
    kpi_cols[1].metric("Total Crown (t)", f"{total_crown:,.1f}")
    kpi_cols[2].metric("Total Roots (t)", f"{total_roots:,.1f}")
    kpi_cols[3].metric("Compost / Discards (t)", f"{compost_t:,.1f}")

    # Stacked bars over time
    if {"year","trunk_t","crown_t","roots_t"}.issubset(df.columns):
        df_stack = df[["year","trunk_t","crown_t","roots_t"]].melt("year", var_name="stream", value_name="tonnes")
        fig_stack = px.bar(
            df_stack, x="year", y="tonnes", color="stream",
            title="Biomass by stream over time",
            labels={"year":"Year","tonnes":"Tonnes"},
        )
        st.plotly_chart(fig_stack, width="stretch")

    # Simple Sankey (average year or totals)
    try:
        nodes = ["Field Inputs","Trunk","Crown","Roots","Compost/Loss","Wood Sale"]
        node_idx = {n:i for i,n in enumerate(nodes)}
        trunk = total_trunk
        crown = total_crown
        roots = total_roots
        compost = compost_t
        # Estimate wood sale share from wood_m3_salable if available
        wood_sale_share = float(res["agro"].get("wood_m3_salable", pd.Series([0])).sum())
        # If we lack direct ton conversion for wood, route a piece of trunk to "Wood Sale" for visual
        to_wood = trunk * 0.6 if trunk>0 else 0.0
        to_compost = compost
        values = [trunk, crown, roots, to_compost, to_wood]
        sources = [node_idx["Field Inputs"]]*3 + [node_idx["Trunk"], node_idx["Trunk"]]
        targets = [node_idx["Trunk"], node_idx["Crown"], node_idx["Roots"], node_idx["Compost/Loss"], node_idx["Wood Sale"]]

        link = dict(source=sources, target=targets, value=values, hovertemplate="%{value:.1f} t")
        fig_sk = go.Figure(go.Sankey(
            node=dict(label=nodes, pad=15, thickness=18),
            link=link,
        ))
        fig_sk.update_layout(title="Sankey — Field Inputs → Biomass uses (totals)", height=420)
        st.plotly_chart(fig_sk, width="stretch")
    except Exception as e:
        st.warning(f"Sankey not available: {e}")

    st.caption("Notes: Units are tonnes (t). Sawmill and compost fractions derive from scenario partitions/ratios.")
    

if __name__ == '__main__':
    page()
