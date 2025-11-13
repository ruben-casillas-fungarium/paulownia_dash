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

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            Use this page as a **laboratory for PauwMyco scenarios**.

            - Compare **two regions or phases** side by side (Scenario A vs B)  
            - Load **saved JSON** to align assumptions with investors or partners  
            - Run **1-way sensitivity** to see how key parameters (e.g. wood price)
              move NPV and cashflows

            This is where the circular Paulownia–mycelium story becomes a set
            of **testable, comparable business cases**.
            """
        )

        st.markdown(
            """
            In an EU context shaped by the **Green Deal, Climate Law and PPWR**,
            investors need to know not only that a concept works, but that it
            remains attractive under **different prices, policies and regions**.
            Sensitivity and comparison are your tools to show exactly that.
            """
        )

    with top_col2:
        st.image(
            "assets/images/FullLogoGroundedRoots.png",
            caption="PauwMyco – Scenario lab for investors",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_scenarios_compare_hero.png",
            caption="Compare regions, phases or strategies side by side.",
            use_container_width=True,
        )

    st.markdown("---")

    scn = _get_scenario()

    tab_a, tab_b, tab_sens = st.tabs(
        ["Compare A vs B", "Upload/Load Scenarios", "1-Way Sensitivity"]
    )

    # ------------------------- TAB A: Compare A vs B -----------------------
    with tab_a:
        st.subheader("Quick KPIs for the baseline scenario")

        res = _ensure_results()
        df = res["agro"]
        base_npv = float(npv(df["cashflow"].to_list(), scn.discount_rate))
        base_co2 = float(df["co2_t"].sum())
        c1, c2 = st.columns(2)
        c1.metric("Baseline NPV", f"€{base_npv:,.0f}")
        c2.metric("Baseline CO₂ fixed", f"{base_co2:,.1f} t")

        st.caption(
            "These values describe the **currently active scenario**. "
            "Use them as a reference point before loading alternative "
            "scenarios in the next tab."
        )

        with st.expander("How to use comparison in an investor discussion"):
            st.markdown(
                """
                - Treat the active scenario as **Scenario A** (e.g. Germany Phase A).  
                - Prepare a second scenario (Scenario B) with different assumptions
                  (e.g. another region, more hectares, different CO₂ price).  
                - Use the comparison tab to show how **NPV, CO₂ and water use**
                  change – this communicates **robustness** and **optionality**.
                """
            )

    # ------------------------- TAB B: Upload/Load -------------------------
    with tab_b:
        st.subheader("Load two scenarios (JSON) to compare")

        st.markdown(
            """
            Export scenarios from the **Scenario Inputs** page, then drag and drop
            the JSON files here to compare them.

            Typical uses:

            - Compare **Phase A vs Phase B** deployment  
            - Compare **two regions** (e.g. Germany vs LATAM)  
            - Compare **conservative vs ambitious** CO₂ price or wood price
            assumptions
            """
        )

        up1 = st.file_uploader("Scenario A JSON", type=["json"], key="scnA")
        up2 = st.file_uploader("Scenario B JSON", type=["json"], key="scnB")
        if up1 and up2:
            scnA = _scenario_from_json(up1.read().decode("utf-8"))
            scnB = _scenario_from_json(up2.read().decode("utf-8"))
            dfA = run_sim(scnA)
            dfB = run_sim(scnB)
            kpi = pd.DataFrame(
                {
                    "kpi": ["NPV", "CO₂ fixed (t)", "Water (m³)"],
                    "A": [
                        npv(dfA["cashflow"].to_list(), scnA.discount_rate),
                        dfA["co2_t"].sum(),
                        dfA["water_m3"].sum(),
                    ],
                    "B": [
                        npv(dfB["cashflow"].to_list(), scnB.discount_rate),
                        dfB["co2_t"].sum(),
                        dfB["water_m3"].sum(),
                    ],
                }
            )
            st.dataframe(kpi, width=True)

            fig = go.Figure()
            for col in ["A", "B"]:
                fig.add_trace(go.Bar(x=kpi["kpi"], y=kpi[col], name=col))
            fig.update_layout(title="Scenario A vs B — KPIs")
            st.plotly_chart(fig, width="stretch")

            st.caption(
                "This comparison highlights the **trade-offs** between two "
                "configurations: one might have higher NPV, the other stronger "
                "CO₂ impact or lower water use. Investors can use this to "
                "position PauwMyco in different **regions and policy futures**."
            )
        else:
            st.info(
                "Upload both Scenario A and Scenario B JSON files above to see "
                "a KPI comparison."
            )

    # ------------------------- TAB C: 1-way sensitivity --------------------
    with tab_sens:
        st.subheader("1-way sensitivity: test a single parameter")

        st.markdown(
            """
            Sensitivity analysis helps answer questions like:

            - *What happens if wood prices fall or rise?*  
            - *How sensitive is NPV to biomass value vs CO₂ credits?*  
            - *How robust is the project under different commodity scenarios?*

            Start with wood price below; more parameters can be added in future
            iterations.
            """
        )

        col_sens, col_img = st.columns([2, 1])
        with col_sens:
            wood_price = st.slider(
                "Wood price (€/m³)",
                100.0,
                400.0,
                float(scn.wood_price_per_m3),
                step=5.0,
            )
            tmp = scn.model_copy(update={"wood_price_per_m3": wood_price})
            df_s = run_sim(tmp)
            sens_npv = float(npv(df_s["cashflow"].to_list(), scn.discount_rate))
            st.metric("NPV at selected wood price", f"€{sens_npv:,.0f}")

            fig = px.line(
                df_s,
                x="year",
                y="cashflow",
                title="Cashflow under sensitivity",
                labels={"cashflow": "€", "year": "Year"},
            )
            st.plotly_chart(fig, width="stretch")

            st.caption(
                "Use the slider to see how changes in wood price reshape annual "
                "cashflows and overall project value. This is particularly "
                "relevant for **commodity volatility** and **policy-driven price "
                "changes** (e.g. carbon pricing, support schemes)."
            )

        with col_img:
            st.image(
                "assets/images/pauwmyco_sensitivity_hero.png",
                caption="See how key parameters shift PauwMyco cashflows.",
                use_container_width=True,
            )

        with st.expander("Ideas for further sensitivity tests"):
            st.markdown(
                """
                - CO₂ price per tonne  
                - Discount rate / cost of capital  
                - Share of revenue from **co-products** (MyzelBooster, chemistry)  
                - Logistics distance and fuel cost  
                - Recovery fraction at end-of-life

                Each of these can be turned into a slider to explore **robustness**
                under different climate and market futures.
            """
        )

    # --- Footer note -------------------------------------------------------
    st.caption(
        "Note: This page reuses the same simulation engine as the rest of the "
        "dashboard. Sensitivities and comparisons are therefore consistent with "
        "the underlying PauwMyco circular economy model."
    )


if __name__ == '__main__':
    page()
