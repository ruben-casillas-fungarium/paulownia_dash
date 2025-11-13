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
# from streamlit_vertical_slider import vertical_slider


def page() -> None:
    st.header("Scenario Inputs")

    # Introductory layout for investors
    top_col1, top_col2 = st.columns([2, 1])
    with top_col1:
        st.markdown(
            """
            Configure a **Paulownia × mycelium circular-economy scenario** here.

            This page lets you translate high-level assumptions – hectares, prices,
            logistics, extraction, plate manufacturing, labor, and end-of-life – into
            **quantitative simulations** of PauwMyco's integrated value chain.

            Use this as an **investor cockpit**:

            - Tune **space-time factors** (years, hectares, harvest cycles)  
            - Adjust **biomass, logistics, and chemistry economics**  
            - Explore **plate output, energy demand and labor intensity**  
            - Test **end-of-life recovery and carbon price assumptions**

            When you click **Run Simulation**, the app pushes these assumptions
            through our agriculture, production and end-of-life models and saves the
            results for the **Results** page.
            """
        )

    with top_col2:
        # Placeholder logo block (ensure the file exists in your repo)
        st.image(
            "assets/images/FullLogoGroundedRoots.png",
            caption=" Paulownia & mycelium circular model",
            use_container_width=True,
        )
        st.image(
            "assets/images/pauwmyco_scenario_inputs_hero.png",
            caption="From hectares and prices to plates, chemistry and CO2.",
            use_container_width=True,
        )

    st.markdown("---")

    # Schematic flow image to guide the form structure
    st.image(
        "assets/images/pauwmyco_scenario_inputs_flow.png",
        caption="Each block corresponds to a section of the Scenario Inputs form.",
        use_container_width=True,
    )

    st.info(
        "Tip for investors: start from a known project size (e.g. a Phase A or B "
        "plant), then vary one parameter block at a time (logistics, extraction, "
        "plates, labor, end-of-life) to see how robust the business becomes under "
        "different EU climate and packaging policy conditions."
    )

    # load or initialise scenario
    if "scenario" not in st.session_state:
        st.session_state.scenario = Scenario()
    scn: Scenario = st.session_state.scenario

    # Project form
    with st.form("project_form"):
        st.subheader("Configure your PauwMyco scenario")

        st.caption(
            "All values below are **per scenario**. Use them to model anything from a "
            "small Micro pilot to a Phase B or C industrial configuration. "
            "The structure follows the PauwMyco value chain: agriculture → logistics "
            "→ extraction → substrate → plates → labor → end-of-life."
        )

        col1, col2, col3 = st.columns(3)

        # ----------------- COLUMN 1: SPACE-TIME, AGRICULTURE, LOGISTICS -----------------
        with col1:
            st.markdown("### 1. Space-time & agroforestry context")

            st.subheader("Space-Time Factors")
            years = st.number_input(
                "Number of years",
                min_value=1,
                max_value=50,
                value=scn.years,
                step=1,
            )
            n_hectares = st.number_input(
                "Area (hectares)",
                min_value=1,
                max_value=10_000,
                value=scn.n_hectares,
                step=1,
            )

            st.caption(
                "Years define the simulation horizon. Hectares represent the "
                "Paulownia-dominated agroforestry area feeding the PauwMyco value "
                "chain. Use larger areas for Phase B/C-style regional hubs."
            )

            # Agriculture
            st.subheader("Prices & costs (per hectare)")
            purpose = st.selectbox(
                "Purpose",
                ["wood_harvest", "soil_regeneration"],
                index=0 if scn.purpose == "wood_harvest" else 1,
            )
            harvest_cycle_years = st.number_input(
                "Harvest cycle (years)",
                min_value=1,
                max_value=10,
                value=scn.harvest_cycle_years,
                step=1,
            )
            wood_price = st.number_input(
                "Wood price (EUR/m³)",
                min_value=0.0,
                value=float(scn.wood_price_per_m3),
                step=10.0,
            )
            water_price = st.number_input(
                "Water price (EUR/m³)",
                min_value=0.0,
                value=float(scn.water_price_per_m3),
                step=0.1,
            )
            tCO2_price = st.number_input(
                "CO₂ credit price (EUR/t)",
                min_value=0.0,
                value=float(scn.co2_price_per_tonne),
                step=1.0,
            )
            Op_Cost = st.number_input(
                "Other costs (EUR/ha per year)",
                min_value=0.0,
                value=float(scn.other_costs_per_ha_per_year),
                step=10.0,
            )
            Extra_Rev = st.number_input(
                "Other revenue (EUR/ha per year)",
                min_value=0.0,
                value=float(scn.other_rev_per_ha_per_year),
                step=10.0,
            )

            st.caption(
                "These values anchor the **agriculture cash flow**. "
                "Paulownia yields, water and CO₂ prices connect the project "
                "directly to EU climate policies and local resource costs."
            )

            # Logistics
            st.subheader("Logistics Farm to Production")
            Trailer_payload = st.number_input(
                "Load for each trailer (t)",
                min_value=1,
                max_value=120,
                value=scn.logistics.trailer_payload_t,
                step=1,
            )
            Max_distance = st.number_input(
                "Maximum distance (km)",
                min_value=1,
                max_value=1000,
                value=scn.logistics.transport_distance_km,
                step=1,
            )
            Cost_per_km = st.number_input(
                "Gas/Employee/Cost km (Eur)",
                min_value=1,
                max_value=80,
                value=scn.logistics.transport_cost_per_km,
                step=1,
            )
            truck_emiss_CO2 = st.number_input(
                "Emission from logistics (tCO2)",
                min_value=0,
                max_value=120,
                value=scn.logistics.truck_emission_kg_per_tkm,
                step=1,
            )

            st.caption(
                "Here you capture **regional reality**: distance from fields to "
                "factory, truck size and cost, and logistics emissions. "
                "For high-impact scenarios, experiment with shorter supply chains "
                "and more efficient loads."
            )

        # ----------------- COLUMN 2: EXTRACTION & SUBSTRATE -----------------
        with col2:
            st.markdown("### 2. Chemistry & substrate (Paulownia as a refinery)")

            # Root Extraction
            st.subheader("Paulownia Root Extraction")
            Price_Oleic_kg = st.number_input(
                "Retail Price of Oleic Acid (kg)",
                min_value=0.0,
                max_value=1000.0,
                value=scn.extraction.price_oleic_eur_per_kg,
                step=0.1,
            )
            Price_Theobromine = st.number_input(
                "Retail Price of Theobromine (kg)",
                min_value=0.0,
                max_value=5000.0,
                value=scn.extraction.price_theobromine_eur_per_kg,
                step=0.1,
            )
            Price_Myzelbooster = st.number_input(
                "Retail Price of MyzelBooster (L)",
                min_value=0.0,
                max_value=5000.0,
                value=scn.extraction.price_extract_eur_per_L,
                step=0.1,
            )

            st.caption(
                "Extraction turns Paulownia roots and biomass into **co-products**: "
                "MyzelBooster, theobromine and oleic acid. These help subsidise "
                "material production and boost overall project margins."
            )

            # Substrate
            st.subheader("Substrate composition of Material")
            root_percentage = st.number_input(
                "Per_roots (%)",
                min_value=0.0,
                max_value=1.0,
                value=scn.substrate.root_fiber_share,
                step=0.01,
            )
            other_percentage = st.number_input(
                "Per_substrates+additives (%)",
                min_value=0.0,
                max_value=1.0,
                value=scn.substrate.other_dry_share,
                step=0.01,
            )
            kWh_per_t_sterilized = st.number_input(
                "kWh per ton sterilized",
                min_value=0.0,
                max_value=100.0,
                value=scn.substrate.sterilize_kWh_per_t_substrate,
                step=0.01,
            )

            st.caption(
                "Substrate fractions express how much of each tonne is Paulownia "
                "fiber versus other residues and additives. Sterilisation energy is "
                "a key part of the **energy and CO₂ footprint** of the material."
            )

        # ----------------- COLUMN 3: PLATES, LABOR, END OF LIFE -----------------
        with col3:
            st.markdown("### 3. Plates, labor & end-of-life loop")

            # PlateParameters
            st.subheader("Parameters of Plate Manufacturing")
            plates_per_ton_substrate = st.number_input(
                "Plates Produced per ton of mixture",
                min_value=1,                     # int
                max_value=1000,                  # int
                value=int(scn.plates.plates_per_ton_hint),  # ensure int
                step=1,                          # int
                format="%d"                      # helps enforce integer display
            )
            cure_days = st.slider(
                "Days of Curation",
                min_value=1,                     # int
                max_value=14,                    # int
                value=int(scn.plates.cure_days), # ensure int
                step=1                           # int
            )
            # Plate Parameters (FLOAT widgets)
            KwH_per_100plts = st.number_input(
                "Energy consumed by producing 100 plates, (Exclude sterilization)",
                min_value=0.1,                   # float
                max_value=10000.0,               # float (note the .0)
                value=float(scn.plates.energy_kWh_per_100_plates),  # ensure float
                step=0.1                         # float
            )
            plate_cost = st.number_input(
                "Production cost per plate (Eur)",
                min_value=0.1,                   # float
                max_value=15.0,                  # float
                value=float(scn.plates.plate_cost_eur),
                step=0.1                         # float
            )
            plate_retail = st.number_input(
                "Retail Price per plate (Eur)",
                min_value=0.1,                   # float
                max_value=20.0,                  # float
                value=float(scn.plates.plate_price_eur),
                step=0.1                         # float
            )

            st.caption(
                "These parameters drive the **core unit economics** of PauwMyco's "
                "mycelium boards and packaging: energy per 100 plates, cost, and "
                "retail price per plate."
            )

            # Manufacturing Labor
            st.subheader("Parameters of Plate Labor")
            Employees_Automation = st.slider(
                "Min Employees at Full automation",
                min_value=0,
                max_value=100,
                value=scn.labor.min_automation_employees,
                step=1,
            )
            Employees_NON_Automation = st.slider(
                "Max Employees in Manual Labor",
                min_value=0,
                max_value=100,
                value=scn.labor.jobs_per_shift_high,
                step=1,
            )
            Shifts_per_day = st.number_input(
                "Shifts per day",
                min_value=0,
                max_value=4,
                value=scn.labor.shifts_per_day,
                step=1,
            )

            st.caption(
                "Labor assumptions link directly to **regional employment** and "
                "operating leverage. Higher automation reduces jobs per tonne but "
                "can increase scalability."
            )

            # End_of_Life (EoL)
            st.subheader("End-of-Life of Material")
            Recovered_Perc = st.slider(
                "Percentage recovered yearly",
                min_value=0.0,
                max_value=1.0,
                value=float(scn.eol.recovered_plate_frac),
                step=0.01,
            )
            CarbonPrice = st.slider(
                "Carbon Price at the year of exchange",
                min_value=0.0,
                max_value=100.0,
                value=float(scn.eol.carbon_price_mid_eur),
                step=0.01,
            )

            st.caption(
                "End-of-life captures how much material re-enters the **soil loop** "
                "and at what carbon price these climate benefits can be monetised. "
                "This is where circularity becomes a **financial lever**."
            )

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
            scn.co2_price_per_tonne = float(tCO2_price)
            scn.other_costs_per_ha_per_year = float(Op_Cost)
            scn.other_rev_per_ha_per_year = float(Extra_Rev)
            # Logistics
            scn.logistics.trailer_payload_t = float(Trailer_payload)
            scn.logistics.transport_distance_km = float(Max_distance)
            scn.logistics.transport_cost_per_km = float(Cost_per_km)
            scn.logistics.truck_emission_kg_per_tkm = float(truck_emiss_CO2)
            # Root Extraction
            scn.extraction.price_oleic_eur_per_kg = float(Price_Oleic_kg)
            scn.extraction.price_theobromine_eur_per_kg = float(Price_Theobromine)
            scn.extraction.price_extract_eur_per_L = float(Price_Myzelbooster)
            # Substrate
            scn.substrate.root_fiber_share = float(root_percentage)
            scn.substrate.other_dry_share = float(other_percentage)
            scn.substrate.sterilize_kWh_per_t_substrate = float(kWh_per_t_sterilized)
            # PlateParameters
            scn.plates.plates_per_ton_hint = int(plates_per_ton_substrate)
            scn.plates.cure_days = int(cure_days)
            scn.plates.energy_kWh_per_100_plates = float(KwH_per_100plts)
            scn.plates.plate_cost_eur = float(plate_cost)
            scn.plates.plate_price_eur = float(plate_retail)
            # EndOfLife
            scn.eol.recovered_plate_frac = float(Recovered_Perc)
            scn.eol.carbon_price_mid_eur = float(CarbonPrice)
            # Manufacturing Labor
            scn.labor.min_automation_employees = int(Employees_Automation)
            scn.labor.jobs_per_shift_high = int(Employees_NON_Automation)
            scn.labor.shifts_per_day = int(Shifts_per_day)

            # run simulation
            print("Running Simulations: \n")
            df_log, df_ext, df_sub, df_pl = run_industrial_chain(scn)
            df_cover, df_soil, df_fin = run_eol_module(
                df_pl, scn, scn.eol, scn.plates
            )
            df_agro = run_sim(scn)
            # df_econ = compute_business_streams(scn,df_agro,df_log,df_ext,df_sub,df_pl)
            print("Joining Simulations: \n")
            df_joined = join_all(
                df_agro, df_log, df_ext, df_sub, df_pl, df_cover, df_soil, df_fin
            )
            st.session_state.df_joined = df_joined
            st.success(
                "Simulation complete! Navigate to the Results page to view outputs."
            )
            # persist scenario
            st.session_state.scenario = scn

    # Scenario JSON section with explanation
    st.subheader("Scenario JSON")

    st.caption(
        "Export a scenario to share it with the PauwMyco team or other investors, "
        "or import a JSON file with predefined assumptions. This ensures everyone "
        "is looking at **the same numbers** when discussing project phases and risk."
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Download Scenario"):  # button to download scenario JSON
            json_str = scn.model_dump_json()
            st.download_button(
                "Save JSON",
                json_str,
                file_name="scenario.json",
                mime="application/json",
            )
    with col2:
        uploaded = st.file_uploader("Upload Scenario JSON", type=["json"])
        if uploaded is not None:
            try:
                data = json.load(uploaded)
                scn_new = Scenario.model_validate_json(json.dumps(data))
                st.session_state.scenario = scn_new
                st.info(
                    "Scenario imported successfully. Run the simulation to update results."
                )
            except Exception as e:
                st.error(f"Failed to load scenario: {e}")


if __name__ == "__main__":
    page()
