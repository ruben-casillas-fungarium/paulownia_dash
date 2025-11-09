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
from core.sim_2_production import run_industrial_chain
from core.sim_3_eol import run_eol_module



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

def _coverage_from_plates_local(plates_df: pd.DataFrame, scn: Scenario) -> pd.DataFrame:
    # Fallback coverage calculation using plate geometry from Scenario.plates
    pp = getattr(scn, "plates", scn)  # handle nested or flat
    # Plate volume (m3)
    v_plate = float(getattr(pp, "plate_len_m", 1.0) * getattr(pp, "plate_wid_m", 1.0) * getattr(pp, "plate_thk_m", 0.06))
    # EoL params
    eol = getattr(scn, "eol", None)
    recovered_frac = float(getattr(eol, "recovered_plate_frac", 0.4)) if eol else 0.4
    layer_thickness = float(getattr(eol, "layer_thickness_m", 0.02)) if eol else 0.02
    compaction = float(getattr(eol, "compaction_ratio", 1.0)) if eol else 1.0
    max_cover = float(getattr(eol, "max_land_coverage_frac", 0.5)) if eol else 0.5

    df = plates_df[["year","plates"]].copy() if "plates" in plates_df else pd.DataFrame({"year":[], "plates":[]})
    if df.empty:
        return df

    df["plates_recovered"] = (df["plates"] * recovered_frac).astype(int)
    A_per_plate_m2 = (v_plate * compaction) / max(layer_thickness, 1e-9)
    df["cover_area_ha_material_cap"] = (df["plates_recovered"] * A_per_plate_m2) / 10_000.0
    df["treatable_area_ha"] = df["cover_area_ha_material_cap"] * max_cover  # if project areas allow, this is the actual treated area
    df["area_required_total_ha_for_50pct_rule"] = df["treatable_area_ha"] / max(max_cover, 1e-9)
    return df


def page() -> None:
    st.header("♻️ End‑of‑Life: Recovery & Coverage")
    scn = _get_scenario()
    res = _ensure_results()
    df_pl = res["plates"]

    if df_pl.empty:
        st.info("No plates data available. Produce plates to enable EoL coverage.")
        return

    if run_eol_module is not None:
        try:
            df_cover, _, _ = run_eol_module(df_pl, getattr(scn, "eol", None), getattr(scn, "plates", scn))
        except Exception:
            df_cover = _coverage_from_plates_local(df_pl, scn)
    else:
        df_cover = _coverage_from_plates_local(df_pl, scn)

    if df_cover.empty:
        st.warning("Coverage could not be computed.")
        return

    # KPIs
    rec = int(df_cover["plates_recovered"].sum())
    area = float(df_cover["treatable_area_ha"].sum())
    area_req = float(df_cover["area_required_total_ha_for_50pct_rule"].sum())
    c = st.columns(3)
    c[0].metric("Recovered plates", f"{rec:,}")
    c[1].metric("Treatable area (ha)", f"{area:,.2f}")
    c[2].metric("Area required (ha) for 50% policy", f"{area_req:,.2f}")

    # Funnel
    funnel = pd.DataFrame({
        "stage":["Plates recovered","Area capacity (ha)","Treatable area (ha)"],
        "value":[rec, float(df_cover["cover_area_ha_material_cap"].sum()), area],
    })
    st.plotly_chart(px.funnel(funnel, x="value", y="stage", title="Coverage funnel"), width="stretch")

    st.subheader("Coverage table")
    st.dataframe(df_cover, width="stretch")
    st.download_button("Download EoL coverage CSV", df_cover.to_csv(index=False).encode(), "eol_coverage.csv", "text/csv")


if __name__ == "__main__":
    page()
