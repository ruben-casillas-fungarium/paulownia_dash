"""Streamlit page for results overview.

Displays high‑level KPIs and time series plots (cashflow and CO₂).
Requires a prior simulation to have been run and stored in
`st.session_state.df_joined` by the Scenario Inputs page.
"""

import streamlit as st

from core.plots import fig_cashflow, fig_co2

def page() -> None:
    st.header("Results: Time Series")
    if "df_joined" not in st.session_state:
        st.info("No simulation results available. Please run a simulation from the Scenario Inputs page.")
        return
    df = st.session_state.df_joined
    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    total_co2 = df["cum_co2_t"].iloc[-1]
    total_wood = df["cum_wood_m3"].iloc[-1]
    total_water = df["water_m3"].sum()
    cum_cashflow = df["cum_cashflow"].iloc[-1]
    col1.metric("Total CO₂ fixed (t)", f"{total_co2:,.2f}")
    col2.metric("Total wood (m³)", f"{total_wood:,.2f}")
    col3.metric("Total water (m³)", f"{total_water:,.2f}")
    col4.metric("Cumulative cashflow (EUR)", f"{cum_cashflow:,.2f}")
    # charts
    st.plotly_chart(fig_cashflow(df), width="stretch")
    st.plotly_chart(fig_co2(df), width="stretch")
    # allow downloads
    st.subheader("Download results")
    csv_str = df.to_csv(index=False)
    st.download_button("Download CSV", csv_str, file_name="results.csv", mime="text/csv")


if __name__ == "__main__":
    page()