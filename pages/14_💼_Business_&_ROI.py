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


def _safe(df: pd.DataFrame, col: str, default: float=0.0) -> pd.Series:
    return df[col] if col in df.columns else pd.Series([default]*len(df))


def _alloc_normalize(a: Dict[str, float]) -> Dict[str, float]:
    s = sum(a.values()) or 1.0
    return {k: v/s for k,v in a.items()}


def page() -> None:
    st.header("💼 Business & ROI")

    # --- Intro narrative & visuals -----------------------------------------
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            This page brings the whole PauwMyco story together in **business terms**.

            It compares **mycelium–Paulownia plates vs. EPS**, aggregates revenue
            from materials and co-products, and allocates profits between
            **farmers, employees, the company and investors**.

            The result: a clear, parameter-driven view of:

            - Unit economics per plate  
            - Total profit across the scenario  
            - How value is shared along the circular chain  
            - Approximate **IRR and MoIC** for co-investors

            Use it as an interactive **investment memo** to tune pricing,
            costs and allocation assumptions live with partners.
            """
        )
    with top_col2:
        st.image(
            "assets/images/FullLogoGroundedRoots.png",
            caption="PauwMyco – circular bio-industry as an investable asset",
            use_container_width=True,
        )
        # st.image(
        #     "assets/images/pauwmyco_business_roi_hero.png",
        #     caption="From hectares and biomass to investor returns.",
        #     use_container_width=True,
        # )

    st.markdown("---")

    scn = _get_scenario()
    res = _ensure_results()
    df_join = res["joined"]
    df_pl = res["plates"]
    df_ext = res["extraction"]

    # --- Inputs (can be bound to Scenario if you later persist them)
    with st.form("biz_inputs"):
        st.subheader("Pricing & costs")
        plate_price = st.number_input(
            "Plate selling price (€/plate)",
            min_value=0.0,
            value=float(getattr(getattr(scn, "plates", scn), "plate_price_eur", 12.0)),
            step=0.1,
        )
        plate_cost = st.number_input(
            "Plate manufacturing cost (€/plate)",
            min_value=0.0,
            value=float(getattr(getattr(scn, "plates", scn), "plate_cost_eur", 3.0)),
            step=0.1,
        )
        eps_price = st.number_input(
            "EPS competitor price (€/plate)",
            min_value=0.0,
            value=float(getattr(getattr(scn, "plates", scn), "competitor_eps_price_eur", 12.0)),
            step=0.1,
        )
        eps_cost = st.number_input(
            "EPS competitor cost (€/plate)",
            min_value=0.0,
            value=float(getattr(getattr(scn, "plates", scn), "competitor_eps_cost_eur", 6.0)),
            step=0.1,
        )
        st.markdown("---")
        st.subheader("Profit allocation (must sum ~100%)")
        colA, colB, colC, colD = st.columns(4)
        to_farmers = colA.slider("Farmers %", 0, 100, 25, 1)
        to_employees = colB.slider("Employees %", 0, 100, 25, 1)
        to_company = colC.slider("Company %", 0, 100, 30, 1)
        to_investors = colD.slider("Investors %", 0, 100, 20, 1)
        st.caption("If total != 100%, values are normalized for calculations.")
        st.markdown("---")
        st.subheader("Investor settings")
        coinvest_share = st.slider(
            "Investor co-investment share of project", 0.0, 1.0, 0.20, 0.01
        )
        submitted = st.form_submit_button("Apply")

    alloc = _alloc_normalize(
        {
            "farmers": to_farmers / 100,
            "employees": to_employees / 100,
            "company": to_company / 100,
            "investors": to_investors / 100,
        }
    )

    # --- Plate unit economics ----------------------------------------------
    plates = int(_safe(df_pl, "plates").sum())
    rev_plates = plates * plate_price
    cost_plates = plates * plate_cost
    gm_plates = rev_plates - cost_plates
    margin_per_plate = (plate_price - plate_cost)
    eps_margin = (eps_price - eps_cost)
    uplift_vs_eps = margin_per_plate - eps_margin

    # --- Extract revenue ----------------------------------------------------
    if "rev_extract" in df_ext.columns:
        rev_extract = float(df_ext["rev_extract"].sum())
    else:
        # fallback: compute from composition if present
        oleic = float(df_ext.get("oleic_kg", pd.Series([0])).sum()) if "oleic_kg" in df_ext else 0.0
        theo = float(df_ext.get("theobromine_kg", pd.Series([0])).sum()) if "theobromine_kg" in df_ext else 0.0
        price_oleic = float(getattr(getattr(scn, "extraction", scn), "price_oleic_eur_per_kg", 37.0))
        price_theo = float(getattr(getattr(scn, "extraction", scn), "price_theobromine_eur_per_kg", 170.0))
        rev_extract = oleic*price_oleic + theo*price_theo

    # --- Totals (combine with existing joined streams if present) ----------
    total_revenue = (
        rev_plates
        + rev_extract
        + float(df_join.get("wood_rev", pd.Series([0])).sum())
        + float(df_join.get("co2_rev", pd.Series([0])).sum())
    )
    # Costs: manufacturing + known costs in joined
    known_costs = (
        float(df_join.get("water_cost", pd.Series([0])).sum())
        + float(df_join.get("opex", pd.Series([0])).sum())
        + float(df_join.get("transport_cost_eur", pd.Series([0])).sum())
        + float(df_join.get("additives_cost_eur", pd.Series([0])).sum())
        + float(df_join.get("inoculum_cost_eur", pd.Series([0])).sum())
    )
    total_costs = cost_plates + known_costs
    total_profit = total_revenue - total_costs

    # --- Jobs ---------------------------------------------------------------
    # Deterministic midpoint of 50–70 per shift if not provided elsewhere
    shifts_per_day = float(getattr(getattr(scn, "labor", scn), "shifts_per_day", 1.0)) if hasattr(scn, "labor") else 1.0
    jobs_min_automation = int(getattr(getattr(scn, "labor", scn), "min_automation_employees", 10)) if hasattr(scn, "labor") else 10
    jobs_dev_mid = int(round(((50+70)/2.0) * shifts_per_day))

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Plates produced", f"{plates:,}")
    c2.metric("Gross margin on plates", _fmt_eur(gm_plates))
    c3.metric("Margin uplift vs EPS", _fmt_eur(uplift_vs_eps * (plates if plates>0 else 1)))
    c4.metric("Jobs (dev. country, mid)", f"{jobs_dev_mid:,} / shift")

    st.caption(
        "These top-line KPIs show the **scale** of the plate business, the gross "
        "margin created compared to EPS, and an indicative estimate of jobs per "
        "shift in a developing-country context."
    )

    # st.image(
    #     "assets/images/pauwmyco_business_roi_kpis.png",
    #     caption="Snapshot: revenue, profit, investor returns and margin uplift vs EPS.",
    #     use_container_width=True,
    # )

    st.markdown("---")

    # --- Allocation ---------------------------------------------------------
    st.subheader("Profit allocation across the PauwMyco ecosystem")

    alloc_series = pd.Series(alloc) * total_profit
    st.plotly_chart(
        px.pie(
            alloc_series.rename("€").reset_index(),
            names="index",
            values="€",
            title="Profit allocation (normalized)",
        ),
        width="stretch",
    )

    st.caption(
        "The sliders above define how yearly profits are shared among farmers, "
        "employees, the company and investors. The chart shows the normalized "
        "allocation applied to total project profit."
    )

    # --- Investor slice & IRR/MoIC (simple) --------------------------------
    st.subheader("Investor returns")

    years = res["agro"]["year"] if "year" in res["agro"].columns else pd.Series(range(1,6))
    n = len(years)
    annual_profit_share = (total_profit / n) * alloc["investors"] if n>0 else 0.0
    investor_cf = [- coinvest_share * total_costs] + [annual_profit_share]*(n-1 if n>0 else 0)
    investor_irr = irr(investor_cf) if n>1 else 0.0
    investor_moic = (sum(c for c in investor_cf[1:]) / abs(investor_cf[0])) if investor_cf and investor_cf[0] != 0 else 0.0

    c1,c2 = st.columns(2)
    c1.metric("Investor IRR (approx)", f"{investor_irr*100:,.1f}%")
    c2.metric("Investor Multiple on Invested Capital (MoIC)", f"{investor_moic:,.2f}×")

    fig_inv = px.line(
        x=list(range(len(investor_cf))),
        y=np.cumsum(investor_cf),
        markers=True,
        labels={"x":"Year index","y":"Cumulative €"},
        title="Investor cumulative cash",
    )
    st.plotly_chart(fig_inv, width="stretch")

    with st.expander("How to read these investor metrics in an IC memo"):
        st.markdown(
            """
            - **IRR** – Internal Rate of Return for an investor co-funding a share "
              "of total project costs at the selected co-investment level.\n
            - **MoIC** – Multiple on Invested Capital based on projected profit "
              "share over the scenario period.\n
            - These are deliberately **simplified**, scenario-level estimates; "
              "they are not a full project finance model, but they show whether "
              "PauwMyco sits in the target range for impact and climate investors.
            """
        )

    st.markdown("---")

    # --- EPS vs Myco margin bars -------------------------------------------
    st.subheader("Myco plates vs EPS – unit margin comparison")

    df_cmp = pd.DataFrame({
        "product":["Myco plate","EPS plate"],
        "margin_per_plate":[margin_per_plate, eps_margin]
    })
    st.plotly_chart(
        px.bar(
            df_cmp,
            x="product",
            y="margin_per_plate",
            title="Margin per plate comparison",
            labels={"margin_per_plate":"€/plate"},
        ),
        width="stretch",
    )

    st.caption(
        "This comparison highlights PauwMyco’s potential to match or exceed EPS "
        "unit margins, while providing additional benefits in terms of CO₂ "
        "storage, circularity and alignment with EU decarbonisation policies."
    )

    # --- Downloads ----------------------------------------------------------
    st.subheader("Download business summary")

    summary = {
        "plates": plates,
        "plate_price": plate_price,
        "plate_cost": plate_cost,
        "rev_plates": rev_plates,
        "cost_plates": cost_plates,
        "rev_extract": rev_extract,
        "total_revenue": total_revenue,
        "total_costs": total_costs,
        "total_profit": total_profit,
        "alloc_eur": alloc_series.to_dict(),
        "investor_cf": investor_cf,
        "investor_irr": float(investor_irr),
        "investor_moic": float(investor_moic),
        "eps_margin_per_plate": eps_margin,
        "myco_margin_per_plate": margin_per_plate,
        "uplift_vs_eps_per_plate": uplift_vs_eps
    }
    df_summary = pd.DataFrame([summary])
    st.download_button(
        "Download Business summary CSV",
        df_summary.to_csv(index=False).encode(),
        "business_summary.csv",
        "text/csv",
    )

    st.markdown(
        """
        _Tip for investors_: combine this page with the **Cradle-to-Gate Summary**
        and **Soil Carbon** views to see how PauwMyco delivers not only attractive
        returns, but also **measurable climate and land-use impact** that fits
        within the European Green Deal and Clean Industrial Deal agendas.
        """
    )


if __name__ == "__main__":
    page()
