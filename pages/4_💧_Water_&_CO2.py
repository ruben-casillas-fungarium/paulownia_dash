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
    st.header("💧 Water & CO₂")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            This view shows how your PauwMyco scenario performs on two
            **critical axes for climate-resilient growth**:

            - **Water demand** – how many cubic meters of water your Paulownia
              agroforestry area needs each year  
            - **CO₂ fixation** – how many tonnes of CO₂ are captured and kept in
              biomass and products over time

            The goal is to understand **how much climate benefit you get per
            unit of water** and how this evolves as plantations mature, are
            harvested, and feed the mycelium and chemistry value chains.
            """
        )

        st.markdown(
            """
            In the context of the **EU Climate Law** and increasing **water
            stress** in many regions, investors and policymakers are looking
            for projects that can **fix large amounts of CO₂** while using
            water **efficiently and responsibly**. This page helps you quantify
            that balance for PauwMyco.
            """
        )

    with top_col2:
        st.image(
            "assets/images/PretzlPaulowniaLogo.png",
            caption="PauwMyco – Climate impact and water efficiency",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_water_co2_hero.png",
            caption="Balancing irrigation needs with long-term carbon fixation.",
            use_container_width=True,
        )

    st.markdown("---")

    # --- Retrieve results ---------------------------------------------------
    res = _ensure_results()
    df = res["agro"].copy()

    # KPI cards (original logic, just wrapped with more explanation)
    total_water = float(df.get("water_m3", pd.Series([0])).sum())
    total_co2 = float(df.get("co2_t", pd.Series([0])).sum())

    st.subheader("Key water and CO₂ indicators")

    k1, k2 = st.columns(2)
    k1.metric("Total Water (m³)", f"{total_water:,.0f}")
    k2.metric("Total CO₂ Fixed (t)", f"{total_co2:,.1f}")

    st.caption(
        "These totals aggregate the scenario over the full time horizon. "
        "They indicate **how thirsty** and **how climate-positive** your "
        "Paulownia-based system is, given the assumptions you set on the "
        "Scenario Inputs page."
    )

    with st.expander("How to interpret these KPIs"):
        st.markdown(
            f"""
            - **Total Water (m³)** – Sum of water demand across the scenario.
              Use this to compare different **regions, irrigation regimes and "
              "climate pathways**. In water-stressed areas, investors will look "
              "for **high CO₂-per-m³ ratios**.\n
            - **Total CO₂ Fixed (t)** – Sum of yearly CO₂ fixation from the
              trees and, where relevant, long-lived products. This connects
              your scenario directly to **EU emissions reduction trajectories** "
              "and potential **carbon credit** opportunities.\n
            - Combined, these metrics show whether PauwMyco can deliver **meaningful "
              "climate mitigation per unit of water used**, compared with other "
              "land-use or biomass options.
            """
        )

    st.markdown("---")

    # --- Water series -------------------------------------------------------
    st.subheader("Annual water need per hectare")

    if {"year", "water_m3"}.issubset(df.columns):
        fig_w = px.bar(
            df,
            x="year",
            y="water_m3",
            title="Annual water need per hectare",
            labels={"year": "Year", "water_m3": "m³/ha"},
        )
        st.plotly_chart(fig_w, width="stretch")

        st.caption(
            "This bar chart shows how much water the Paulownia agroforestry "
            "system requires per hectare each year. Peaks can reflect **early "
            "establishment phases** or **dry years** (depending on how you "
            "parameterise the scenario). For investor discussions, you can "
            "compare this against **regional water availability** and stress."
        )
    else:
        st.info("Water time series not available in current scenario results.")

    # --- CO₂ per-year and cumulative ---------------------------------------
    st.subheader("CO₂ fixation – annual and cumulative")

    if {"year", "co2_t"}.issubset(df.columns):
        dfc = df.copy()
        dfc["cum_co2"] = dfc["co2_t"].cumsum()
        fig_c = go.Figure()
        fig_c.add_trace(
            go.Bar(x=dfc["year"], y=dfc["co2_t"], name="Per year (tCO₂)")
        )
        fig_c.add_trace(
            go.Scatter(
                x=dfc["year"], y=dfc["cum_co2"], name="Cumulative (tCO₂)", yaxis="y2"
            )
        )
        fig_c.update_layout(
            title="CO₂ fixation — annual & cumulative",
            yaxis=dict(title="tCO₂/year"),
            yaxis2=dict(title="tCO₂ cumulative", overlaying="y", side="right"),
            legend=dict(orientation="h"),
        )
        st.plotly_chart(fig_c, width="stretch")

        st.caption(
            "The bars show **year-by-year CO₂ fixation**; the line shows how it "
            "adds up over time. Early years may have lower values as plantations "
            "establish, followed by higher fixation as trees mature. Harvests, "
            "end-of-life assumptions and soil dynamics all shape this curve."
        )
    else:
        st.info("CO₂ time series not available in current scenario results.")

    st.markdown("### Putting water and CO₂ in context")

    col_ctx1, col_ctx2 = st.columns([2, 1])
    with col_ctx1:
        st.markdown(
            """
            **1. Policy alignment**

            - The **EU Climate Law** and **Green Deal** require deep emission
              cuts by 2030 and 2040. Scenarios with strong cumulative CO₂
              fixation can support **green finance**, impact funds and "
              "corporate climate strategies.\n
            - At the same time, climate change is increasing **drought risk** "
              "and periods of water scarcity across parts of Europe. Projects "
              "that deliver climate benefits without excessive water use "
              "are more robust.

            **2. Agroforestry practice**

            - Paulownia can be highly productive, but certain species are on "
              "alert lists for invasive potential in parts of Europe. PauwMyco "
              "emphasises **responsible species choice and management**.\n
            - Efficient irrigation, mixed-species systems and careful siting "
              "help ensure that water and biodiversity impacts remain positive.

            **3. Regional resilience**

            - Use this page to discuss **trade-offs with local stakeholders**: "
              "how much water is used, how much CO₂ is fixed, and what this "
              "means for **long-term resilience** of the region."
            """
        )
    with col_ctx2:
        st.image(
            "assets/images/pauwmyco_water_co2_context.png",
            caption="Linking scenario outputs to policy, water stress and regional resilience.",
            use_container_width=True,
        )

    st.caption(
        "Note: CO₂ curve comes from the scenario’s piecewise fixation function; "
        "water is a user-set parameter (with potential variability). Consider "
        "running multiple scenarios to test **dry vs. wet years**, different "
        "CO₂ prices and alternative management strategies."
    )


if __name__ == '__main__':
    page()
