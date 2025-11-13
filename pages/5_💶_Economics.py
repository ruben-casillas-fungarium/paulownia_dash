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

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            This page translates the **Paulownia × mycelium circular model**
            into **financial language** that investors and lenders understand:

            - How much value is created from **wood, CO₂ credits and co-products**  
            - How fast the project **pays back its CAPEX**  
            - How PauwMyco’s economics behave across **different scenarios and phases**

            Here you can see whether a given scenario has the potential to evolve
            from a **Micro pilot** to a **Phase A/B/C industrial plant** with
            attractive returns.
            """
        )

        st.markdown(
            """
            PauwMyco’s growth roadmap (Micro → A → B → C → D) targets
            step-changes in **revenue and EBITDA** at each phase, while staying
            aligned with EU climate and circular-economy policies. This dashboard
            lets you test if your assumptions are consistent with that trajectory.
            """
        )

    with top_col2:
        st.image(
            "assets/images/FullLogoGroundedRoots.png",
            caption="PauwMyco – Circular value translated into euros.",
            use_column_width=True,
        )
        st.image(
            "assets/images/pauwmyco_economics_hero.png",
            caption="From circular biomass flows to investor-grade KPIs.",
            use_column_width=True,
        )

    st.markdown("---")

    # --- Scenario & results -------------------------------------------------
    scn = _get_scenario()
    res = _ensure_results()
    df = res["agro"].copy()

    # Compute simple economics from agro (wood + CO2 credits) for now;
    # industrial/business module can extend this by merging business streams.
    must_cols = ["year", "cashflow", "wood_rev", "co2_rev", "water_cost", "opex"]
    for c in must_cols:
        if c not in df.columns:
            df[c] = 0.0

    # KPIs (NPV, IRR, Payback)
    disc = scn.discount_rate
    project_npv = float(npv(df["cashflow"].to_list(), disc))
    project_irr = float(irr(df["cashflow"].to_list()))
    payback = int((df["cum_cashflow"] > 0).idxmax() + 1) if (df["cum_cashflow"] > 0).any() else None

    st.subheader("Project KPIs")

    c1, c2, c3 = st.columns(3)
    c1.metric("NPV", f"€{project_npv:,.0f}", help=f"Discount rate={disc:.0%}")
    c2.metric("IRR", f"{project_irr*100:,.1f}%")
    c3.metric("Payback (yrs)", f"{payback if payback else 'n/a'}")

    st.caption(
        "These KPIs condense the full cashflow profile of your scenario. "
        "**NPV** and **IRR** are standard metrics for comparing projects and "
        "phases, while **payback** gives a quick sense of capital recovery speed."
    )

    with st.expander("How to read NPV, IRR and payback in PauwMyco’s context"):
        st.markdown(
            f"""
            - **NPV (Net Present Value)** – Discounted sum of all yearly cashflows,
              using the scenario discount rate. Positive NPV suggests the scenario
              may be attractive relative to your cost of capital.\n
            - **IRR (Internal Rate of Return)** – The discount rate at which NPV
              becomes zero. Compare this to your hurdle rate or to typical returns
              for industrial and infrastructure projects.\n
            - **Payback (yrs)** – First year in which cumulative cashflow becomes
              positive. Shorter payback can help de-risk early phases (e.g. **Micro**
              and **Phase A**), making it easier to raise follow-on capital.\n
            - **Phase roadmap** – Internal planning documents project order-of-
              magnitude growth from **Micro (~€0.7M, ~15% EBITDA)** to **Phase A
              (~€13.7M, 25–30% EBITDA)** and **Phase B (~€48–70M, 30–35% EBITDA)**
              before reaching **Phase C/D** scale. Your scenario should feel
              consistent with that stepwise de-risked approach.
            """
        )

    st.markdown("---")

    # --- Waterfall for a selected year -------------------------------------
    st.subheader("Year-by-year economics (waterfall view)")

    y = st.slider(
        "Select year for waterfall",
        int(df["year"].min()),
        int(df["year"].max()),
        int(df["year"].min()),
    )
    row = df.loc[df["year"] == y].iloc[0]
    wf_labels = ["Wood revenue", "CO₂ credits", "Other revenue", "Water cost", "OPEX", "Seedlings"]
    other_rev = float(row.get("other_rev_per_ha_per_year", 0.0))
    seedlings = float(row.get("seedlings_cost", 0.0))
    wf_values = [
        row["wood_rev"],
        row["co2_rev"],
        other_rev,
        -row["water_cost"],
        -row["opex"],
        -seedlings,
    ]
    fig_wf = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative"] * len(wf_values),
            x=wf_labels,
            text=[f"{v:,.0f}" for v in wf_values],
            y=wf_values,
        )
    )
    fig_wf.update_layout(title=f"Economic waterfall — Year {y}", yaxis_title="€")
    st.plotly_chart(fig_wf, width="stretch")

    st.caption(
        "This waterfall shows which levers drive **annual cashflow** in the selected year: "
        "revenues from wood and CO₂, any additional revenue, and the main cost blocks "
        "such as water, operating costs, and seedlings. Use it to identify where "
        "efficiency gains or co-product revenues can have the biggest impact."
    )

    # --- Cashflow table & chart --------------------------------------------
    st.subheader("Cashflows over the project lifetime")

    st.dataframe(
        df[["year", "cashflow", "cum_cashflow", "wood_rev", "co2_rev", "water_cost", "opex"]],
        width="stretch",
    )

    fig_cf = px.line(
        df,
        x="year",
        y=["cashflow", "cum_cashflow"],
        markers=True,
        title="Annual & cumulative cashflow",
        labels={"value": "€", "year": "Year"},
    )
    st.plotly_chart(fig_cf, width="stretch")

    st.caption(
        "The line chart shows how cashflow evolves year by year and how quickly "
        "cumulative cashflow crosses zero. For phase planning, you can map "
        "these profiles to **Micro**, **A**, **B**, **C** and **D** deployment "
        "milestones."
    )

    st.markdown("### Framing PauwMyco economics")

    ctx_col1, ctx_col2 = st.columns([2, 1])
    with ctx_col1:
        st.markdown(
            """
            **1. Phase-based scaling**

            Internal business plans foresee:

            - **Micro** – ~€0.7M annual revenue, ~15% EBITDA, 18–24 months payback.  
            - **Phase A** – ~€13.7M revenue, 25–30% EBITDA, ~3-year payback.  
            - **Phase B** – €48–70M revenue, 30–35% EBITDA, ~2–2.5-year payback.  
            - **Phase C/D** – €250M+ and later €B+ scale with 35–40%+ EBITDA.

            Your scenario here can be viewed as a **single project lens** on this
            trajectory. Strong NPVs and robust cashflows make it easier to unlock
            the next phase.

            **2. Risk and resilience**

            - Diversified biomass & co-product revenue streams help stabilise
              cashflows across climate or market shocks.  
            - Modular plants and phased CAPEX reduce the risk of over-building
              too early.

            **3. Regional development**

            - Each euro of CAPEX supports **local jobs, services and tax base**.  
            - Circular use of Paulownia and residues stands well with regional
              climate and circular-economy strategies.

            Use this page with investors to discuss both **financial return** and
            **systemic impact** side-by-side.
            """
        )
    with ctx_col2:
        st.image(
            "assets/images/pauwmyco_economics_context.png",
            caption="Connecting project cashflows to policy, phases and impact.",
            use_column_width=True,
        )

    st.markdown("---")

    # --- Downloads ---------------------------------------------------------
    st.subheader("Download cashflow data")

    st.caption(
        "Export the full cashflow table as CSV to build your own models, "
        "compare scenarios, or attach to investment memos and due-diligence packs."
    )

    st.download_button(
        "Download cashflow CSV",
        df.to_csv(index=False).encode(),
        file_name="economics_cashflow.csv",
        mime="text/csv",
    )


if __name__ == '__main__':
    page()
