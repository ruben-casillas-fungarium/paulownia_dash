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


def _safe(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default] * len(df))


def page() -> None:
    st.header("💚 Carbon Credits & Cashflow (EoL)")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            At the **end of life** of PauwMyco plates, the story does not stop.
            When recovered and applied back to land, plates can help:

            - **Store additional carbon in soils** compared to a baseline  
            - Generate **certifiable carbon credits** under emerging EU frameworks  
            - Create a **new, complementary cashflow stream** linked directly to
              land restoration

            This page quantifies how much additional carbon is credited, how
            much **EoL carbon revenue** is generated, and what remains after
            **field operation and monitoring costs**.
            """
        )
        st.markdown(
            """
            In the context of the **EU Climate Law** and the new **EU Carbon
            Removal Certification Framework (CRCF)**, such transparent, scenario-based
            modelling of removals and costs is essential for credible climate
            finance and for long-term partnerships with landowners and buyers
            of high-integrity credits.
            """
        )
    with top_col2:
        st.image(
            "assets/images/PretzlPaulowniaLogo.png",
            caption="PauwMyco – turning end-of-life into financed climate action",
            use_container_width=True,
        )
        # st.image(
        #     "assets/images/pauwmyco_eol_finance_hero.png",
        #     caption="From recovered plates to certified carbon revenue.",
        #     use_container_width=True,
        # )

    st.markdown("---")

    scn = _get_scenario()
    eol = getattr(scn, "eol", None)
    res = _ensure_results()
    df_pl = res["plates"]

    if df_pl.empty:
        st.info("No plates/coverage yet. EoL finance depends on recovered plates.")
        return

    # --- Original EoL finance logic (unchanged) ----------------------------
    # Compute coverage locally to get treated area
    pp = getattr(scn, "plates", scn)
    v_plate = float(
        getattr(pp, "plate_len_m", 1.0)
        * getattr(pp, "plate_wid_m", 1.0)
        * getattr(pp, "plate_thk_m", 0.06)
    )
    recovered_frac = float(getattr(eol, "recovered_plate_frac", 0.4)) if eol else 0.4
    layer_thickness = float(getattr(eol, "layer_thickness_m", 0.02)) if eol else 0.02
    compaction = float(getattr(eol, "compaction_ratio", 1.0)) if eol else 1.0
    max_cover = float(getattr(eol, "max_land_coverage_frac", 0.5)) if eol else 0.5

    df = df_pl[["year", "plates"]].copy()
    df["plates_recovered"] = (df["plates"] * recovered_frac).astype(int)
    A_per_plate_m2 = (v_plate * compaction) / max(layer_thickness, 1e-9)
    df["treatable_area_ha"] = (
        (df["plates_recovered"] * A_per_plate_m2) / 10_000.0 * max_cover
    )

    # Soil curves (per ha) then total deltas
    after5_treated = float(
        getattr(eol, "treated_CO2_add_t_per_ha_after_5y", 4.0)
    )
    post5_treated = float(
        getattr(eol, "treated_CO2_add_t_per_ha_per_y_post_5", 1.7)
    )
    after5_base = float(
        getattr(eol, "baseline_CO2_add_t_per_ha_after_5y", 1.5)
    )
    post5_base = float(
        getattr(eol, "baseline_CO2_add_t_per_ha_per_y_post_5", 0.5)
    )

    deltas = []
    for y in df["year"]:
        if y <= 5:
            treated = after5_treated * (y / 5.0)
            base = after5_base * (y / 5.0)
        else:
            treated = after5_treated + (y - 5) * post5_treated
            base = after5_base + (y - 5) * post5_base
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
        df["credited_t"] = df["delta_total_tCO2"] * (12 / 44)

    P = price_mid if use_mid else None
    if P is not None:
        df["rev_carbon"] = df["credited_t"] * P
    else:
        df["rev_carbon_lo"] = df["credited_t"] * lo
        df["rev_carbon_hi"] = df["credited_t"] * hi
        df["rev_carbon"] = (df["rev_carbon_lo"] + df["rev_carbon_hi"]) / 2.0

    # Field ops & monitoring costs
    ops = float(getattr(eol, "field_ops_cost_eur_per_ha", 80.0)) if eol else 80.0
    mon = float(
        getattr(eol, "monitoring_cost_eur_per_ha_per_y", 10.0)
    ) if eol else 10.0
    df["cost_field_ops"] = df["treatable_area_ha"] * ops
    df["cost_monitor"] = df["treatable_area_ha"] * mon
    df["cf_eol"] = df["rev_carbon"] - (df["cost_field_ops"] + df["cost_monitor"])

    # --- KPIs ---------------------------------------------------------------
    st.subheader("Key EoL finance indicators")

    st.metric("EoL carbon revenue (sum)", _fmt_eur(float(df["rev_carbon"].sum())))
    st.metric("EoL net cashflow (sum)", _fmt_eur(float(df["cf_eol"].sum())))

    st.caption(
        "These KPIs summarise the **total revenue** from carbon credits linked to "
        "end-of-life soil application, and the **net cashflow** after subtracting "
        "field operation and monitoring costs. They can be compared to overall "
        "project NPV/IRR as an **additional upside**, not the only value driver."
    )

    # st.image(
    #     "assets/images/pauwmyco_eol_finance_kpis.png",
    #     caption="EoL carbon credits: revenue, costs and net cashflow in one view.",
    #     use_container_width=True,
    # )

    st.markdown("---")

    # --- Waterfall for typical year ----------------------------------------
    st.subheader("EoL carbon finance structure (waterfall)")

    years = df["year"].unique()
    if len(years) > 1:
        y = int(
            st.slider(
                "Year",
                int(df["year"].min()),
                int(df["year"].max()),
                int(df["year"].min()),
            )
        )
    else:
        y = int(years[0])
    row = df.loc[df["year"] == y].iloc[0]
    wf = go.Figure(
        go.Waterfall(
            x=["Carbon revenue", "Field ops", "Monitoring"],
            y=[row["rev_carbon"], -row["cost_field_ops"], -row["cost_monitor"]],
            measure=["relative", "relative", "relative"],
        )
    )
    wf.update_layout(yaxis_title="€", title=f"EoL waterfall — Year {y}")
    st.plotly_chart(wf, width="stretch")

    st.caption(
        "This waterfall shows how much of the **gross carbon revenue** in the "
        "selected year is absorbed by operational costs and monitoring. The "
        "resulting bar is the **net EoL cashflow** that can be attributed to "
        "PauwMyco’s circular land-application strategy."
    )

    st.markdown("---")

    # --- Table & download ---------------------------------------------------
    st.subheader("EoL finance table")

    st.caption(
        "Full year-by-year breakdown of recovered plates, treatable area, "
        "credited tonnes, carbon revenue, costs and net cashflow. Export this "
        "for detailed financial modelling, CRCF-aligned certification planning "
        "or voluntary carbon market due diligence."
    )

    st.dataframe(df, width="stretch")
    st.download_button(
        "Download EoL finance CSV",
        df.to_csv(index=False).encode(),
        "eol_finance.csv",
        "text/csv",
    )


if __name__ == "__main__":
    page()
