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
    }
    st.session_state[key] = out
    return out


def _fmt_eur(x: float) -> str:
    return f"€{x:,.0f}"


def _safe(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default] * len(df))


def page() -> None:
    st.header("🧪 Extraction & Products")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            In the PauwMyco model, **Paulownia roots** don’t just stay underground –
            they become **high-value biotech products**.

            This page shows how the extraction unit converts roots into:

            - **MyzelBooster (L)** – a growth booster for fungal cultivation  
            - **Oleic acid (kg)** – a bio-based fatty acid for materials and cosmetics  
            - **Theobromine (kg)** – a bioactive molecule with food and pharma potential  
            - **Root fibres (t)** – a solid fraction that can return into substrates

            At the same time, it tracks **energy use**, **Scope-2 CO₂ emissions**
            and **extract revenues**, making the biorefinery economics transparent.
            """
        )

        st.markdown(
            """
            Within the EU’s **bioeconomy and climate policies**, value-adding steps
            like this are essential: they increase revenue per hectare, create
            **local industrial jobs**, and help phase out fossil-based chemicals –
            provided plantations are managed responsibly and species/regulations
            are respected.
            """
        )

    with top_col2:
        st.image(
            "assets/images/FullLogoGroundedRoots.png",
            caption="PauwMyco – from roots to biotech products",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_extraction_products_hero.png",
            caption="Turning Paulownia roots into MyzelBooster and co-products.",
            use_container_width=True,
        )

    st.markdown("---")

    # --- Load results -------------------------------------------------------
    res = _ensure_results()
    df = res["extraction"]
    if df.empty:
        st.info(
            "Extraction data not available. Configure industrial chain parameters "
            "in the Scenario Inputs page to enable this view."
        )
        return

    # --- KPIs ---------------------------------------------------------------
    st.subheader("Key extraction indicators")

    roots_in = float(_safe(df, "roots_in_t").sum())
    extract_L = float(_safe(df, "extract_L").sum())
    fibers_t = float(_safe(df, "root_fiber_t").sum())
    E_total = float(
        _safe(df, "E_total_kWh", 0).sum()
        if "E_total_kWh" in df
        else (_safe(df, "E_total").sum())
    )
    rev_extract = float(_safe(df, "rev_extract").sum())
    co2_scope2 = float(_safe(df, "co2_scope2_t").sum())

    c = st.columns(5)
    c[0].metric("Roots processed", f"{roots_in:,.1f} t")
    c[1].metric("Extract", f"{extract_L:,.0f} L")
    c[2].metric("Fibers", f"{fibers_t:,.1f} t")
    c[3].metric("Energy", f"{E_total:,.0f} kWh")
    c[4].metric("Scope-2 CO₂", f"{co2_scope2:,.2f} t")
    st.metric("Extract revenue (annual)", _fmt_eur(rev_extract))

    st.caption(
        "These indicators summarise **how much root biomass is upgraded**, "
        "how much liquid extract is produced, how much solid fibre remains, and "
        "what energy and emissions are associated with the process."
    )

    with st.expander("How to read these extraction KPIs"):
        st.markdown(
            f"""
            - **Roots processed (t)** – Total mass of Paulownia roots entering the
              extraction process. This ties back directly to **hectares planted**
              and **harvest cycles** in the agricultural module.\n
            - **Extract (L)** – Main liquid output used for **MyzelBooster** and
              related applications. Higher volumes can open up additional markets
              in specialty agriculture or biotech.\n
            - **Fibers (t)** – Solid fraction remaining after extraction, which can
              become part of **substrate mixes** or other bio-based materials.\n
            - **Energy (kWh)** – Total electricity/thermal energy used. This
              informs both **OPEX** and **Scope-2 emissions**, especially important
              as electricity grids decarbonise.\n
            - **Scope-2 CO₂ (t)** – Emissions from purchased energy. For scenarios
              aligned with **EU climate targets**, this should be modest relative
              to **CO₂ fixed** in biomass and products.\n
            - **Extract revenue (annual)** – Gross revenue from extract sales
              (all years combined in this KPI). This is a key pillar of PauwMyco’s
              **multi-stream business model** alongside plates and wood.
            """
        )

    st.image(
        "assets/images/pauwmyco_extraction_products_kpis.png",
        caption="Extraction KPIs: linking roots processed to revenue, energy and CO₂.",
        use_container_width=True,
    )

    st.markdown("---")

    # --- Energy by type (if present) ---------------------------------------
    st.subheader("Energy demand over time")

    cols_energy = [c for c in ["E_steam", "E_press", "E_over", "E_total", "E_total_kWh"] if c in df.columns]
    if cols_energy:
        fig_e = px.bar(
            df,
            x="year",
            y=cols_energy,
            title="Extraction energy by year",
            labels={"value": "kWh", "year": "Year"},
        )
        st.plotly_chart(fig_e, width="stretch")

        st.caption(
            "This view breaks down the energy use of the extraction train by type "
            "(where provided). It helps identify **energy hotspots** for process "
            "optimisation and for sourcing **low-carbon electricity or heat**."
        )
    else:
        st.info("No energy breakdown columns found in extraction results.")

    # --- Product composition (oleic/theobromine) ---------------------------
    st.subheader("Purified products over time")

    comp_cols = [c for c in ["oleic_kg", "theobromine_kg"] if c in df.columns]
    if comp_cols:
        comp = df[["year"] + comp_cols].melt("year", var_name="component", value_name="kg")
        fig_c = px.area(
            comp,
            x="year",
            y="kg",
            color="component",
            title="Purified products (kg/year)",
        )
        st.plotly_chart(fig_c, width="stretch")

        st.caption(
            "Here you can see how much **oleic acid** and **theobromine** the "
            "scenario produces each year. These streams support entry into "
            "higher-margin **chemical, cosmetic and nutraceutical** markets."
        )
    else:
        st.info("No purified product columns (oleic_kg, theobromine_kg) found in extraction results.")

    st.markdown("---")

    # --- Table & download --------------------------------------------------
    st.subheader("Extraction table")

    st.caption(
        "Inspect the full extraction dataset for engineering or due-diligence "
        "work. Each row typically represents a year or batch of operation, with "
        "mass balances, energy demand and emissions."
    )

    st.dataframe(df, width="stretch")
    st.download_button(
        "Download extraction CSV",
        df.to_csv(index=False).encode(),
        "extraction.csv",
        "text/csv",
    )


if __name__ == "__main__":
    page()
