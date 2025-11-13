"""Streamlit page for results overview.

Displays high-level KPIs and time series plots (cashflow and CO₂).
Requires a prior simulation to have been run and stored in
`st.session_state.df_joined` by the Scenario Inputs page.
"""

import streamlit as st

from core.plots import fig_cashflow, fig_co2


def page() -> None:
    st.header("Results: Time Series")

    # Introductory investor view
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            These time series translate your **Paulownia × mycelium scenario**
            into a **dynamic story over time**:

            - How much **CO₂ is fixed and kept out of the atmosphere**  
            - How much **wood and water** flow through the system  
            - How **cashflow accumulates** as PauwMyco plants scale

            Each simulation respects the underlying assumptions you set on the
            **Scenario Inputs** page and reflects the integrated agriculture,
            production, and end-of-life modules.
            """
        )

        st.markdown(
            """
            In the context of the **European Green Deal** and the **EU climate
            law** – with at least **55% emissions reductions by 2030** and a
            **90% target by 2040** on the table – these curves show how a
            responsible, circular Paulownia–mycelium system can contribute
            to climate goals **while generating cashflow**.
            """
        )

    with top_col2:
        # Logos / hero image placeholders
        st.image(
            "assets/images/PretzlPaulowniaLogo.png",
            caption="Circular economy in time series",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_results_timeseries_hero.png",
            caption="KPIs and time series powered by your scenario.",
            use_container_width=True,
        )

    st.markdown("---")

    # Guard clause – keep original logic
    if "df_joined" not in st.session_state:
        st.info(
            "No simulation results available. "
            "Please run a simulation from the Scenario Inputs page."
        )
        return

    df = st.session_state.df_joined

    st.subheader("High-level KPIs")

    # KPI cards (original logic preserved)
    col1, col2, col3, col4 = st.columns(4)
    total_co2 = df["cum_co2_t"].iloc[-1]
    total_wood = df["cum_wood_m3"].iloc[-1]
    total_water = df["water_m3"].sum()
    cum_cashflow = df["cum_cashflow"].iloc[-1]
    col1.metric("Total CO₂ fixed (t)", f"{total_co2:,.2f}")
    col2.metric("Total wood (m³)", f"{total_wood:,.2f}")
    col3.metric("Total water (m³)", f"{total_water:,.2f}")
    col4.metric("Cumulative cashflow (EUR)", f"{cum_cashflow:,.2f}")

    st.caption(
        "These indicators summarise the **climate, biomass and financial footprint** "
        "of your scenario over the full simulation horizon."
    )

    with st.expander("What do these KPIs mean in the PauwMyco model?"):
        st.markdown(
            f"""
            - **Total CO₂ fixed (t)** – The cumulative tonnes of CO₂ fixed in
              biomass and products across the scenario period. This is where the
              PauwMyco system connects to **EU climate law** trajectories and
              potential carbon credit schemes.\n
            - **Total wood (m³)** – The total Paulownia wood volume harvested and
              routed into materials and chemistry. This links directly to **plant
              size (hectares)** and **harvest cycle** decisions.\n
            - **Total water (m³)** – The sum of water used in the system
              (e.g. irrigation, processing). This is critical for assessing the
              **resource efficiency** of the concept in water-stressed regions.\n
            - **Cumulative cashflow (EUR)** – The sum of all yearly cashflows
              (revenues minus costs) over the project life. This is the **headline
              economic signal** for investors: does the circular model pay back,
              and how robustly?
            """
        )

    st.markdown("---")
    st.subheader("Time series: cashflow and CO₂")

    # Charts (original logic preserved)
    st.plotly_chart(fig_cashflow(df), use_container_width=True)
    st.plotly_chart(fig_co2(df), use_container_width=True)

    st.caption(
        "The first chart typically shows annual and cumulative **cashflows**. "
        "The second one presents annual and cumulative **CO₂ dynamics** "
        "(sequestration and, where relevant, emissions from operations and logistics)."
    )

    # Interpretation helper
    st.markdown("### How to read these curves as an investor")

    col_story1, col_story2 = st.columns([2, 1])
    with col_story1:
        st.markdown(
            """
            **1. Shape of the cashflow curve**

            - A **slow start** followed by steeper growth indicates early CAPEX
              and learning, then scaling of plate and chemistry revenues.  
            - A **plateau** later in the curve reflects saturation in hectares,
              plant capacity or market demand.  
            - Negative early years followed by strong positive cumulative cashflow
              are typical for **Phase A/B industrial deployments**.

            **2. Shape of the CO₂ curve**

            - Upward cumulative CO₂ indicates that forests and materials are
              acting as a **long-lived carbon sink**, not just a short-term
              storage.  
            - If the curve flattens or dips, it can represent **harvest-heavy
              periods** or **end-of-life emissions** overtaking sequestration.  
            - Responsible Paulownia management (avoiding invasive behaviour,
              respecting national rules) ensures this sink is **climate-positive
              and compliant**.

            **3. Linking to policy**

            - Scenarios with strong, sustained CO₂ fixation and positive
              cashflows can align with **Green Deal**, **Fit for 55** and
              tightening **packaging regulation (PPWR)**, which increasingly
              favours bio-based, low-carbon materials over EPS and other foams.  
            - Investors can use these curves to build an argument for **green
              loans, transition finance or impact funds**.
            """
        )

    with col_story2:
        st.image(
            "assets/images/pauwmyco_results_timeseries_story.png",
            caption="Each time series connects climate impact, materials and money.",
            use_container_width=True,
        )

    st.info(
        "Consider running multiple scenarios (e.g. conservative vs. ambitious "
        "CO₂ price, different Paulownia areas, logistics assumptions) and "
        "comparing their time series to understand risk and upside."
    )

    st.markdown("---")

    # allow downloads (original logic preserved)
    st.subheader("Download results")

    st.caption(
        "Export the full joined dataset for deeper analysis in Excel, Python, or "
        "for sharing with the PauwMyco team and investors."
    )

    csv_str = df.to_csv(index=False)
    st.download_button(
        "Download CSV",
        csv_str,
        file_name="results.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    page()
