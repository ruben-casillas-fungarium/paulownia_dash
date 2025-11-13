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
    st.header("🧱 Substrate & Plates")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            This page shows the **engine room** of PauwMyco’s physical products:
            how substrate becomes **mycelium–Paulownia plates** that can replace
            EPS and other fossil foams.

            The model tracks:

            - **Wet substrate (t)** prepared from fibres, additives and water  
            - **Dry mass (kg)** that ends up inside the plates  
            - **Number of plates produced per year**  
            - **Energy demand (kWh)** for incubation and pressing  
            - **Materials cost** (additives + inoculum)

            For investors, this is where hectares, roots and biomass flows turn
            into **a scalable industrial product line** with clear unit economics.
            """
        )

        st.markdown(
            """
            The goal is to deliver a **high-performance, low-carbon panel** that:

            - Can be produced at industrial throughput  
            - Has a **competitive cost per plate** versus EPS and mineral wool  
            - Supports **regional manufacturing** and circular value chains

            Use this page to check if your scenario supports that story.
            """
        )

    with top_col2:
        st.image(
            "assets/images/PretzlPaulowniaLogo.png",
            caption="PauwMyco – Mycelium–Paulownia biocomposites",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_substrate_plates_hero.png",
            caption="From wet substrate to scalable biocomposite plates.",
            use_container_width=True,
        )

    st.markdown("---")

    scn = _get_scenario()
    res = _ensure_results()
    df_sub = res["substrate"]
    df_pl = res["plates"]

    if df_sub.empty and df_pl.empty:
        st.info(
            "Substrate/Plates data not available. Configure industrial chain "
            "parameters in the Scenario Inputs page to enable this view."
        )
        return

    # --- KPIs derived -------------------------------------------------------
    st.subheader("Key substrate & plate indicators")

    plates = int(_safe(df_pl, "plates").sum())
    dry_mass_kg = float(_safe(df_pl, "dry_mass_kg").sum())
    E_plates = float(_safe(df_pl, "E_plates_kWh").sum())
    wet_substrate_t = float(_safe(df_sub, "wet_substrate_t").sum())
    additives_cost = float(_safe(df_sub, "additives_cost_eur").sum())
    inoculum_cost = float(_safe(df_sub, "inoculum_cost_eur").sum())

    c = st.columns(5)
    c[0].metric("Plates/year", f"{plates:,}")
    c[1].metric("Dry output", f"{dry_mass_kg:,.0f} kg")
    c[2].metric("Wet substrate", f"{wet_substrate_t:,.1f} t")
    c[3].metric("Energy (plates)", f"{E_plates:,.0f} kWh")
    c[4].metric("Materials", _fmt_eur(additives_cost + inoculum_cost))

    plate_cost_param = getattr(getattr(scn, "plates", scn), "plate_cost_eur", 3.0)
    cost_per_plate = plate_cost_param
    st.metric("Assumed manufacturing cost per plate", _fmt_eur(cost_per_plate))

    st.caption(
        "These figures provide a high-level view of **factory throughput**, "
        "**energy demand** and **materials costs**. They are key drivers for "
        "assessing PauwMyco plate margins and competitiveness."
    )

    with st.expander("How to interpret these KPIs for investors"):
        st.markdown(
            f"""
            - **Plates/year** – Total number of plates produced across the scenario.
              Higher values indicate both **scale** and **utilisation** of the plant.\n
            - **Dry output (kg)** – How much solid biocomposite ends up in products.
              This relates to **density**, **mechanical performance** and **CO₂ storage**.\n
            - **Wet substrate (t)** – Mass of substrate prepared and handled. This
              impacts **equipment sizing**, **labor** and **logistics inside the plant**.\n
            - **Energy (kWh)** – Total energy for incubation/pressing. Together with
              local electricity mix, this shapes **Scope-2 emissions** and OPEX.\n
            - **Materials (EUR)** – Combined cost of additives and inoculum. These
              are levers for **process optimisation** and **supplier strategy**.\n
            - **Manufacturing cost per plate** – A key number for pricing strategy
              against EPS and other materials, and for targeting the EBITDA levels
              described in PauwMyco’s phase roadmap.
            """
        )

    st.image(
        "assets/images/pauwmyco_substrate_plates_kpis.png",
        caption="KPIs: throughput, energy and material costs per scenario.",
        use_container_width=True,
    )

    st.markdown("---")

    # --- Throughput funnel --------------------------------------------------
    st.subheader("Throughput funnel: substrate → dry mass → plates")

    if not df_sub.empty:
        funnel = pd.DataFrame(
            {
                "stage": ["Wet substrate (t)", "Dry mass (t)", "Plates (k units)"],
                "value": [wet_substrate_t, dry_mass_kg / 1000.0, plates / 1000.0],
            }
        )
        fig_f = px.funnel(funnel, x="value", y="stage", title="Throughput funnel")
        st.plotly_chart(fig_f, width="stretch")

        st.caption(
            "The funnel shows how many tonnes of wet substrate ultimately become "
            "dry mass in plates and how many **thousands of units** that represents. "
            "It’s a quick way to validate whether the **plant size and line design** "
            "are consistent with your scenario."
        )
    else:
        st.info("No substrate data available to build the throughput funnel.")

    # --- Cost stack per year ------------------------------------------------
    st.subheader("Substrate costs per year")

    if not df_sub.empty:
        cols = [c for c in ["additives_cost_eur", "inoculum_cost_eur"] if c in df_sub.columns]
        if cols:
            fig_cs = px.bar(
                df_sub,
                x="year",
                y=cols,
                title="Substrate costs per year",
                labels={"value": "€"},
            )
            st.plotly_chart(fig_cs, width="stretch")

            st.caption(
                "Annual substrate costs highlight how materials spending evolves as "
                "production ramps up. This helps identify **cost peaks** and "
                "supports procurement and process-optimisation strategies."
            )
        else:
            st.info("No substrate cost columns found in results.")
    else:
        st.info("Substrate table is empty; no annual cost breakdown available.")

    st.markdown("---")

    # --- Tables & downloads -------------------------------------------------
    st.subheader("Detailed tables")

    if not df_sub.empty:
        st.markdown("**Substrate**")
        st.caption(
            "Full substrate dataset, including mass balances and cost breakdowns. "
            "Use this for engineering work, LCA inputs or detailed economic models."
        )
        st.dataframe(df_sub, width="stretch")
        st.download_button(
            "Download substrate CSV",
            df_sub.to_csv(index=False).encode(),
            "substrate.csv",
            "text/csv",
        )

    if not df_pl.empty:
        st.markdown("**Plates**")
        st.caption(
            "Full plates dataset, including plate counts, dry mass and energy "
            "use per period. This table underpins the product-side of the "
            "PauwMyco business case."
        )
        st.dataframe(df_pl, width="stretch")
        st.download_button(
            "Download plates CSV",
            df_pl.to_csv(index=False).encode(),
            "plates.csv",
            "text/csv",
        )


if __name__ == "__main__":
    page()
