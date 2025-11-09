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
        df_joined = df_agro.copy()
    out = {
        "agro": df_agro,
        "logistics": df_log,
        "extraction": df_ext,
        "substrate": df_sub,
        "plates": df_pl,
        "joined": df_joined,
    }
    st.session_state[key] = out
    return out


def _fmt_eur(x: float) -> str:
    return f"€{x:,.0f}"


def _safe(df: pd.DataFrame, col: str, default: float=0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default]*len(df))

def _soil_curves_local(years: np.ndarray, eol: Any) -> Tuple[pd.Series, pd.Series]:
    # Piecewise accumulation per spec (tCO2/ha)
    after5_treated = float(getattr(eol, "treated_CO2_add_t_per_ha_after_5y", 4.0))
    post5_treated = float(getattr(eol, "treated_CO2_add_t_per_ha_per_y_post_5", 1.7))
    after5_base = float(getattr(eol, "baseline_CO2_add_t_per_ha_after_5y", 1.5))
    post5_base = float(getattr(eol, "baseline_CO2_add_t_per_ha_per_y_post_5", 0.5))
    treated = []
    base = []
    for y in years:
        if y <= 5:
            treated.append(after5_treated * (y/5.0))
            base.append(after5_base * (y/5.0))
        else:
            treated.append(after5_treated + (y-5)*post5_treated)
            base.append(after5_base + (y-5)*post5_base)
    return pd.Series(treated), pd.Series(base)


def page() -> None:
    st.header("🌱 Soil Carbon")
    scn = _get_scenario()
    eol = getattr(scn, "eol", None)
    res = _ensure_results()
    df_pl = res["plates"]
    if df_pl.empty:
        st.info("No plates/coverage yet. Soil module requires EoL recovered material.")
        return

    years = df_pl["year"].to_numpy()
    treated, base = _soil_curves_local(years, eol)
    df = pd.DataFrame({"year": years, "treated_tCO2_per_ha": treated, "baseline_tCO2_per_ha": base})
    df["delta_tCO2_per_ha"] = df["treated_tCO2_per_ha"] - df["baseline_tCO2_per_ha"]

    # Charts
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["year"], y=df["treated_tCO2_per_ha"], name="Treated (tCO₂/ha)"))
    fig.add_trace(go.Scatter(x=df["year"], y=df["baseline_tCO2_per_ha"], name="Baseline (tCO₂/ha)"))
    fig.update_layout(title="Soil carbon per hectare — treated vs baseline", yaxis_title="tCO₂/ha")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Per‑hectare table")
    st.dataframe(df, width="stretch")
    st.download_button("Download soil carbon per‑ha CSV", df.to_csv(index=False).encode(), "soil_carbon_per_ha.csv", "text/csv")


if __name__ == "__main__":
    page()
