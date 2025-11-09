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

def _scenario_from_json(txt: str) -> Scenario:
    data = json.loads(txt)
    return Scenario(**data)

def page() -> None:
    st.header("🧪 Sensitivity & Compare")
    scn = _get_scenario()

    tab_a, tab_b, tab_sens = st.tabs(["Compare A vs B","Upload/Load Scenarios","1-Way Sensitivity"])

    with tab_a:
        st.subheader("Quick KPIs")
        res = _ensure_results()
        df = res["agro"]
        base_npv = float(npv(df["cashflow"].to_list(), scn.discount_rate))
        base_co2 = float(df["co2_t"].sum())
        c1,c2 = st.columns(2)
        c1.metric("Baseline NPV", f"€{base_npv:,.0f}")
        c2.metric("Baseline CO₂ fixed", f"{base_co2:,.1f} t")

    with tab_b:
        st.write("Load two scenarios (JSON) to compare.")
        up1 = st.file_uploader("Scenario A JSON", type=["json"], key="scnA")
        up2 = st.file_uploader("Scenario B JSON", type=["json"], key="scnB")
        if up1 and up2:
            scnA = _scenario_from_json(up1.read().decode("utf-8"))
            scnB = _scenario_from_json(up2.read().decode("utf-8"))
            dfA = run_sim(scnA)
            dfB = run_sim(scnB)
            kpi = pd.DataFrame({
                "kpi":["NPV","CO₂ fixed (t)","Water (m³)"],
                "A":[npv(dfA["cashflow"].to_list(), scnA.discount_rate), dfA["co2_t"].sum(), dfA["water_m3"].sum()],
                "B":[npv(dfB["cashflow"].to_list(), scnB.discount_rate), dfB["co2_t"].sum(), dfB["water_m3"].sum()],
            })
            st.dataframe(kpi, width=True)
            fig = go.Figure()
            for col in ["A","B"]:
                fig.add_trace(go.Bar(x=kpi["kpi"], y=kpi[col], name=col))
            fig.update_layout(title="Scenario A vs B — KPIs")
            st.plotly_chart(fig, width="stretch")

    with tab_sens:
        st.write("Vary one parameter and observe NPV sensitivity.")
        wood_price = st.slider("Wood price (€/m³)", 100.0, 400.0, float(scn.wood_price_per_m3), step=5.0)
        tmp = scn.model_copy(update={"wood_price_per_m3": wood_price})
        df_s = run_sim(tmp)
        sens_npv = float(npv(df_s["cashflow"].to_list(), scn.discount_rate))
        st.metric("NPV at selected wood price", f"€{sens_npv:,.0f}")
        fig = px.line(df_s, x="year", y="cashflow", title="Cashflow under sensitivity", labels={"cashflow":"€","year":"Year"})
        st.plotly_chart(fig, width="stretch")


if __name__ == '__main__':
    page()
