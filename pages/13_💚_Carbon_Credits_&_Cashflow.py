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
try:
    from core.sim_3_eol import run_eol_module
except Exception:
    run_eol_module = None  # type: ignore
try:
    from core.aggregate import compute_business_streams
except Exception:
    compute_business_streams = None  # type: ignore
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

def page() -> None:
    st.header("💚 Carbon Credits & Cashflow (EoL)")
    scn = _get_scenario()
    eol = getattr(scn, "eol", None)
    res = _ensure_results()
    df_pl = res["plates"]

    if df_pl.empty:
        st.info("No plates/coverage yet. EoL finance depends on recovered plates.")
        return

    # Compute coverage locally to get treated area
    pp = getattr(scn, "plates", scn)
    v_plate = float(getattr(pp, "plate_len_m", 1.0) * getattr(pp, "plate_wid_m", 1.0) * getattr(pp, "plate_thk_m", 0.06))
    recovered_frac = float(getattr(eol, "recovered_plate_frac", 0.4)) if eol else 0.4
    layer_thickness = float(getattr(eol, "layer_thickness_m", 0.02)) if eol else 0.02
    compaction = float(getattr(eol, "compaction_ratio", 1.0)) if eol else 1.0
    max_cover = float(getattr(eol, "max_land_coverage_frac", 0.5)) if eol else 0.5

    df = df_pl[["year","plates"]].copy()
    df["plates_recovered"] = (df["plates"] * recovered_frac).astype(int)
    A_per_plate_m2 = (v_plate * compaction) / max(layer_thickness, 1e-9)
    df["treatable_area_ha"] = (df["plates_recovered"] * A_per_plate_m2) / 10_000.0 * max_cover

    # Soil curves (per ha) then total deltas
    after5_treated = float(getattr(eol, "treated_CO2_add_t_per_ha_after_5y", 4.0))
    post5_treated = float(getattr(eol, "treated_CO2_add_t_per_ha_per_y_post_5", 1.7))
    after5_base = float(getattr(eol, "baseline_CO2_add_t_per_ha_after_5y", 1.5))
    post5_base = float(getattr(eol, "baseline_CO2_add_t_per_ha_per_y_post_5", 0.5))

    deltas = []
    for y in df["year"]:
        if y <= 5:
            treated = after5_treated * (y/5.0)
            base = after5_base * (y/5.0)
        else:
            treated = after5_treated + (y-5)*post5_treated
            base = after5_base + (y-5)*post5_base
        deltas.append(treated - base)
    df["delta_tCO2_per_ha"] = deltas
    df["delta_total_tCO2"] = df["delta_tCO2_per_ha"] * df["treatable_area_ha"]

    # Pricing (tC vs tCO2e)
    credit_basis = getattr(eol, "credit_basis", "tC") if eol else "tC"
    price_mid = float(getattr(eol, "carbon_price_mid_eur", 60.0)) if eol else 60.0
    lo = float(getattr(eol, "carbon_price_lo_eur", 50.0)) if eol else 50.0
    hi = float(getattr(eol, "carbon_price_hi_eur", 70.0)) if eol else 70.0
    use_mid = bool(getattr(eol, "use_midpoint_price", True)) if eol else True

    if credit_basis == "tCO2e":
        df["credited_t"] = df["delta_total_tCO2"]
    else:
        df["credited_t"] = df["delta_total_tCO2"] * (12/44)

    P = price_mid if use_mid else None
    if P is not None:
        df["rev_carbon"] = df["credited_t"] * P
    else:
        df["rev_carbon_lo"] = df["credited_t"] * lo
        df["rev_carbon_hi"] = df["credited_t"] * hi
        df["rev_carbon"] = (df["rev_carbon_lo"] + df["rev_carbon_hi"]) / 2.0

    # Field ops & monitoring costs
    ops = float(getattr(eol, "field_ops_cost_eur_per_ha", 80.0)) if eol else 80.0
    mon = float(getattr(eol, "monitoring_cost_eur_per_ha_per_y", 10.0)) if eol else 10.0
    df["cost_field_ops"] = df["treatable_area_ha"] * ops
    df["cost_monitor"] = df["treatable_area_ha"] * mon
    df["cf_eol"] = df["rev_carbon"] - (df["cost_field_ops"] + df["cost_monitor"])

    # KPIs
    st.metric("EoL carbon revenue (sum)", _fmt_eur(float(df["rev_carbon"].sum())))
    st.metric("EoL net cashflow (sum)", _fmt_eur(float(df["cf_eol"].sum())))

    st.subheader("Waterfall (typical year)")
    years = df["year"].unique()
    if len(years) > 1:
        y = int(st.slider("Year", int(df["year"].min()), int(df["year"].max()), int(df["year"].min())))
    else:
        y = int(years[0])
    row = df.loc[df["year"]==y].iloc[0]
    wf = go.Figure(go.Waterfall(x=["Carbon revenue","Field ops","Monitoring"],
                                y=[row["rev_carbon"], -row["cost_field_ops"], -row["cost_monitor"]],
                                measure=["relative","relative","relative"]))
    wf.update_layout(yaxis_title="€", title=f"EoL waterfall — Year {y}")
    st.plotly_chart(wf, width="stretch")


    st.subheader("EoL table")
    st.dataframe(df, width="stretch")
    st.download_button("Download EoL finance CSV", df.to_csv(index=False).encode(), "eol_finance.csv", "text/csv")


if __name__ == "__main__":
    page()
