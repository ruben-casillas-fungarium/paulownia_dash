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
    st.header("💶 Economics")
    scn = _get_scenario()
    res = _ensure_results()
    df = res["agro"].copy()

    # Compute simple economics from agro (wood + CO2 credits) for now;
    # industrial/business module can extend this by merging business streams.
    must_cols = ["year","cashflow","wood_rev","co2_rev","water_cost","opex"]
    for c in must_cols:
        if c not in df.columns:
            df[c] = 0.0

    # KPIs
    disc = scn.discount_rate
    project_npv = float(npv(df["cashflow"].to_list(), disc))
    project_irr = float(irr(df["cashflow"].to_list()))
    payback = int((df["cum_cashflow"]>0).idxmax()+1) if (df["cum_cashflow"]>0).any() else None

    c1,c2,c3 = st.columns(3)
    c1.metric("NPV", f"€{project_npv:,.0f}", help=f"Discount rate={disc:.0%}")
    c2.metric("IRR", f"{project_irr*100:,.1f}%")
    c3.metric("Payback (yrs)", f"{payback if payback else 'n/a'}")

    # Waterfall for a selected year
    y = st.slider("Select year for waterfall", int(df["year"].min()), int(df["year"].max()), int(df["year"].min()))
    row = df.loc[df["year"]==y].iloc[0]
    wf_labels = ["Wood revenue","CO₂ credits","Other revenue","Water cost","OPEX","Seedlings"]
    other_rev = float(row.get("other_rev_per_ha_per_year", 0.0))
    seedlings = float(row.get("seedlings_cost", 0.0))
    wf_values = [row["wood_rev"], row["co2_rev"], other_rev, -row["water_cost"], -row["opex"], -seedlings]
    fig_wf = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"]*len(wf_values),
        x=wf_labels,
        text=[f"{v:,.0f}" for v in wf_values],
        y=wf_values,
    ))
    fig_wf.update_layout(title=f"Economic waterfall — Year {y}", yaxis_title="€")
    st.plotly_chart(fig_wf, width="stretch")

    # Cashflow table & chart
    st.subheader("Cashflows")
    st.dataframe(df[["year","cashflow","cum_cashflow","wood_rev","co2_rev","water_cost","opex"]], width="stretch")
    fig_cf = px.line(df, x="year", y=["cashflow","cum_cashflow"],
                     markers=True,
                     title="Annual & cumulative cashflow",
                     labels={"value":"€","year":"Year"})
    st.plotly_chart(fig_cf, width="stretch")

    # Downloads
    st.download_button("Download cashflow CSV", df.to_csv(index=False).encode(), file_name="economics_cashflow.csv", mime="text/csv")


if __name__ == '__main__':
    page()
