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
        "joined": df_agro.copy(),
    }
    st.session_state[key] = out
    return out


def _fmt_eur(x: float) -> str:
    return f"€{x:,.0f}"


def _safe(df: pd.DataFrame, col: str, default: float=0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default]*len(df))

def _kpi_banner(df_joined: pd.DataFrame, scn: Scenario) -> None:
    cash = df_joined.get("cashflow", pd.Series([0.0]*len(df_joined))).to_list()
    total_rev = float(df_joined.get("total_revenue", pd.Series([0.0]*len(df_joined))).sum())
    total_costs = float(df_joined.get("total_costs", pd.Series([0.0]*len(df_joined))).sum())
    npv_v = float(npv(cash, scn.discount_rate)) if cash else 0.0
    irr_v = float(irr(cash)) if cash else 0.0
    c = st.columns(4)
    c[0].metric("Total revenue", _fmt_eur(total_rev))
    c[1].metric("Total costs", _fmt_eur(total_costs))
    c[2].metric("NPV", _fmt_eur(npv_v))
    c[3].metric("IRR", f"{irr_v*100:,.1f}%")


def page() -> None:
    st.header("🧮 Cradle‑to‑Gate Summary")
    scn = _get_scenario()
    res = _ensure_results()
    df_join = res["joined"]
    if df_join.empty:
        st.info("No joined dataset available. Ensure industrial chain is configured.")
        return

    _kpi_banner(df_join, scn)

    # Cashflow waterfall for selected year
    years = df_join["year"].unique()
    if len(years) == 1:
        y = int(years[0])
        st.info(f"Only one year available: {y}")
    else:
        y = int(st.slider("Select year", int(df_join["year"].min()), int(df_join["year"].max()), int(df_join["year"].min())))
    row = df_join.loc[df_join["year"]==y].iloc[0]
    rev_cols = [c for c in ["wood_rev","co2_rev","rev_extract","rev_plates","other_rev"] if c in df_join.columns]
    cost_cols = [c for c in ["water_cost","opex","transport_cost_eur","additives_cost_eur","inoculum_cost_eur","capex"] if c in df_join.columns]
    wf_labels = [*rev_cols, *cost_cols]
    wf_values = [float(row.get(c,0.0)) for c in rev_cols] + [-float(row.get(c,0.0)) for c in cost_cols]
    fig_wf = go.Figure(go.Waterfall(x=wf_labels, y=wf_values, measure=["relative"]*len(wf_values)))
    fig_wf.update_layout(title=f"Year {y} revenue & cost waterfall", yaxis_title="€")
    st.plotly_chart(fig_wf, width="stretch")   

    # Cumulative cashflow
    if "cum_cashflow" in df_join.columns:
        st.subheader("Cumulative cashflow")
        st.plotly_chart(px.line(df_join, x="year", y="cum_cashflow", markers=True, labels={"cum_cashflow":"€"}), width="stretch")

    st.subheader("Joined table")
    st.dataframe(df_join, width="stretch")
    st.download_button("Download joined CSV", df_join.to_csv(index=False).encode(), "cradle_to_gate_joined.csv", "text/csv")


if __name__ == "__main__":
    page()
