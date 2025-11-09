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
         # unpack expected tuple (now only 4)
        df_log, df_ext, df_sub, df_pl = dfs
        # You can define df_joined as a copy of df_log or another DataFrame if needed
        df_joined = df_log.copy()
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
    st.header("🚚 Logistics")
    res = _ensure_results()
    df_log = res["logistics"]

    if df_log.empty:
        st.info("Industrial chain not configured. Adjust logistics parameters in Scenario to enable this view.")
        return

    # KPIs
    trips = int(df_log.get("n_trips", pd.Series([0])).sum())
    tkm = float(df_log.get("tkm", pd.Series([0])).sum())
    cost = float(df_log.get("transport_cost_eur", pd.Series([0])).sum())
    co2 = float(df_log.get("transport_co2_t", pd.Series([0])).sum())
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Trips / year", f"{trips:,}")
    c2.metric("Ton-km / year", f"{tkm:,.0f}")
    c3.metric("Transport cost / year", f"€{cost:,.0f}")
    c4.metric("Transport CO₂ / year", f"{co2:,.1f} t")

    # Charts
    if "year" in df_log.columns:
        fig_c = px.bar(df_log, x="year",
                       y="transport_cost_eur",
                       title="Transport cost per year",
                       labels={"transport_cost_eur":"€","year":"Year"})
        st.plotly_chart(fig_c, width="stretch")
        fig_e = px.line(df_log, x="year",
                        y="transport_co2_t",
                        markers=True,
                        title="Transport CO₂ per year",
                        labels={"transport_co2_t":"tCO₂","year":"Year"})
        st.plotly_chart(fig_e, width="stretch")

    st.download_button("Download logistics CSV", df_log.to_csv(index=False).encode(), "logistics.csv", "text/csv")


if __name__ == '__main__':
    page()
