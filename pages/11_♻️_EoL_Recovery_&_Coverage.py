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


def _safe(df: pd.DataFrame, col: str, default: float = 0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default] * len(df))


def _coverage_from_plates_local(plates_df: pd.DataFrame, scn: Scenario) -> pd.DataFrame:
    # Fallback coverage calculation using plate geometry from Scenario.plates
    pp = getattr(scn, "plates", scn)  # handle nested or flat
    # Plate volume (m3)
    v_plate = float(
        getattr(pp, "plate_len_m", 1.0)
        * getattr(pp, "plate_wid_m", 1.0)
        * getattr(pp, "plate_thk_m", 0.06)
    )
    # EoL params
    eol = getattr(scn, "eol", None)
    recovered_frac = float(getattr(eol, "recovered_plate_frac", 0.4)) if eol else 0.4
    layer_thickness = float(getattr(eol, "layer_thickness_m", 0.02)) if eol else 0.02
    compaction = float(getattr(eol, "compaction_ratio", 1.0)) if eol else 1.0
    max_cover = float(getattr(eol, "max_land_coverage_frac", 0.5)) if eol else 0.5

    df = (
        plates_df[["year", "plates"]].copy()
        if "plates" in plates_df
        else pd.DataFrame({"year": [], "plates": []})
    )
    if df.empty:
        return df

    df["plates_recovered"] = (df["plates"] * recovered_frac).astype(int)
    A_per_plate_m2 = (v_plate * compaction) / max(layer_thickness, 1e-9)
    df["cover_area_ha_material_cap"] = (df["plates_recovered"] * A_per_plate_m2) / 10_000.0
    df["treatable_area_ha"] = df["cover_area_ha_material_cap"] * max_cover  # if project areas allow, this is the actual treated area
    df["area_required_total_ha_for_50pct_rule"] = df["treatable_area_ha"] / max(
        max_cover, 1e-9
    )
    return df


def page() -> None:
    st.header("♻️ End-of-Life: Recovery & Coverage")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            PauwMyco does not stop at the factory gate.

            This page explores what happens **at the end of life** of our
            mycelium–Paulownia plates:

            - How many plates can realistically be **recovered**?  
            - How much land area (ha) could they **treat or cover** when reused
              as soil-improving material or protective mulch?  
            - How does this relate to emerging **EU soil health and nature
              restoration targets**?

            The goal is to show that PauwMyco can contribute to **land and soil
            restoration**, not just to low-carbon materials.
            """
        )

        st.markdown(
            """
            The model uses parameters such as **recovery fraction**, **layer
            thickness**, **compaction** and a **50% land coverage policy rule**
            to translate recovered plates into hectares of potential coverage.
            These can be tuned to reflect local regulations and practice.
            """
        )

    with top_col2:
        st.image(
            "assets/images/PretzlPaulowniaLogo.png",
            caption="PauwMyco – closing the loop at end of life",
            use_container_width=True,
        )
        # st.image(
        #     "assets/images/pauwmyco_eol_coverage_hero.png",
        #     caption="Recovered plates applied back to land as a resource.",
        #     use_container_width=True,
        # )

    st.markdown("---")

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

    # --- KPIs ---------------------------------------------------------------
    st.subheader("Key recovery & coverage indicators")

    rec = int(df_cover["plates_recovered"].sum())
    area = float(df_cover["treatable_area_ha"].sum())
    area_req = float(df_cover["area_required_total_ha_for_50pct_rule"].sum())
    c = st.columns(3)
    c[0].metric("Recovered plates", f"{rec:,}")
    c[1].metric("Treatable area (ha)", f"{area:,.2f}")
    c[2].metric("Area required (ha) for 50% policy", f"{area_req:,.2f}")

    st.caption(
        "These KPIs translate end-of-life recovery into **land area impact**. "
        "`Treatable area` represents how many hectares could be improved with "
        "recovered plates, while `Area required` links this to a 50% coverage "
        "policy assumption in the model."
    )

    with st.expander("End-of-life in the EU circular economy & soil policies"):
        st.markdown(
            """
            - The **EU Soil Strategy for 2030** and the new **Soil Health Law**
              trajectory aim for healthy soils, reduced land degradation and "
              "better soil management across the EU.\n
            - The **Nature Restoration Law** sets binding restoration targets for "
              "degraded ecosystems, including agricultural land and soils.\n
            - Circular economy measures increasingly expect producers to think "
              about **end-of-life and material recovery** as part of the business "
              "model, not an afterthought.\n
            - In this context, PauwMyco’s concept of **re-applying plates to "
              "land** (where safe and permitted) can support erosion control, "
              "soil cover and organic matter build-up – provided local rules and "
              "biodiversity safeguards are respected.
            """
        )

    # st.image(
    #     "assets/images/pauwmyco_eol_kpis.png",
    #     caption="Coverage KPIs and land restoration potential per scenario.",
    #     use_container_width=True,
    # )

    st.markdown("---")

    # --- Coverage funnel ----------------------------------------------------
    st.subheader("From plates to hectares: coverage funnel")

    funnel = pd.DataFrame(
        {
            "stage": ["Plates recovered", "Area capacity (ha)", "Treatable area (ha)"],
            "value": [
                rec,
                float(df_cover["cover_area_ha_material_cap"].sum()),
                area,
            ],
        }
    )
    st.plotly_chart(
        px.funnel(funnel, x="value", y="stage", title="Coverage funnel"),
        width="stretch",
    )

    st.caption(
        "The funnel illustrates how **recovered plates** translate into a maximum "
        "coverage capacity and then into **actual treatable area**, after "
        "applying policy or design constraints (such as limiting coverage to "
        "50% of available land)."
    )

    # --- Table & download ---------------------------------------------------
    st.subheader("Coverage table")

    st.caption(
        "This table contains the year-by-year coverage calculations (plates "
        "recovered, area capacity, treatable area and land requirements). "
        "Export it to feed into **LCA**, **regional restoration planning** or "
        "**extended producer responsibility** discussions."
    )

    st.dataframe(df_cover, width="stretch")
    st.download_button(
        "Download EoL coverage CSV",
        df_cover.to_csv(index=False).encode(),
        "eol_coverage.csv",
        "text/csv",
    )


if __name__ == "__main__":
    page()
