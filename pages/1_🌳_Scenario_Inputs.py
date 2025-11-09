"""Streamlit page for scenario inputs.

This page exposes various parameters of the scenario as editable widgets.
Users can adjust the basic project settings (years, hectares, purpose,
prices) and run a simulation.  Simulation results are stored in
`st.session_state` for use on other pages.
"""

import json
import streamlit as st

from core.params import Scenario
from core.sim_1_agriculture import run_sim
from core.sim_2_production import run_industrial_chain
from core.sim_3_eol import run_eol_module
from core.aggregate import join_all, compute_business_streams



def page() -> None:
    st.header("Scenario Inputs")
    # load or initialise scenario
    if "scenario" not in st.session_state:
        st.session_state.scenario = Scenario()
    scn: Scenario = st.session_state.scenario
    # Project tab
    with st.form("project_form"):
        st.subheader("Project settings")
        years = st.number_input("Number of years", min_value=1, max_value=50, value=scn.years, step=1)
        n_hectares = st.number_input("Area (hectares)", min_value=1, max_value=10_000, value=scn.n_hectares, step=1)
        purpose = st.selectbox("Purpose", ["wood_harvest", "soil_regeneration"], index=0 if scn.purpose == "wood_harvest" else 1)
        harvest_cycle_years = st.number_input("Harvest cycle (years)", min_value=1, max_value=10, value=scn.harvest_cycle_years, step=1)
        # price inputs
        st.subheader("Prices & costs (per hectare)")
        wood_price = st.number_input("Wood price (EUR/m³)", min_value=0.0, value=float(scn.wood_price_per_m3), step=10.0)
        water_price = st.number_input("Water price (EUR/m³)", min_value=0.0, value=float(scn.water_price_per_m3), step=0.1)
        co2_price = st.number_input("CO₂ credit price (EUR/t)", min_value=0.0, value=float(scn.co2_price_per_tonne), step=1.0)
        opex = st.number_input("Other costs (EUR/ha per year)", min_value=0.0, value=float(scn.other_costs_per_ha_per_year), step=10.0)
        other_rev = st.number_input("Other revenue (EUR/ha per year)", min_value=0.0, value=float(scn.other_rev_per_ha_per_year), step=10.0)
        submitted = st.form_submit_button("Run Simulation")
        if submitted:
            # update scenario
            print("Scenario Updated: \n")
            scn.years = int(years)
            scn.n_hectares = int(n_hectares)
            scn.purpose = purpose
            scn.harvest_cycle_years = int(harvest_cycle_years)
            scn.wood_price_per_m3 = float(wood_price)
            scn.water_price_per_m3 = float(water_price)
            scn.co2_price_per_tonne = float(co2_price)
            scn.other_costs_per_ha_per_year = float(opex)
            scn.other_rev_per_ha_per_year = float(other_rev)
            # run simulation
            print("Running Simulations: \n")
            df_log, df_ext, df_sub, df_pl = run_industrial_chain(scn)
            df_cover, df_soil, df_fin = run_eol_module(df_pl, scn, scn.eol, scn.plates)
            df_agro = run_sim(scn)
            # df_econ = compute_business_streams(scn,df_agro,df_log,df_ext,df_sub,df_pl)
            print("Joining Simulations: \n")
            df_joined = join_all(df_agro, df_log, df_ext, df_sub, df_pl, df_cover, df_soil, df_fin)
            st.session_state.df_joined = df_joined
            st.success("Simulation complete! Navigate to the Results page to view outputs.")
            # persist scenario
            st.session_state.scenario = scn
    # allow user to export or import scenario JSON
    st.subheader("Scenario JSON")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download Scenario"):  # button to download scenario JSON
            json_str = scn.model_dump_json()
            st.download_button("Save JSON", json_str, file_name="scenario.json", mime="application/json")
    with col2:
        uploaded = st.file_uploader("Upload Scenario JSON", type=["json"])
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                scn_new = Scenario.model_validate_json(json.dumps(data))
                st.session_state.scenario = scn_new
                st.info("Scenario imported successfully. Run the simulation to update results.")
            except Exception as e:
                st.error(f"Failed to load scenario: {e}")


if __name__ == "__main__":
    page()