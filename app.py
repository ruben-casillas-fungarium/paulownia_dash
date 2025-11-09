"""Streamlit entry point for the Paulownia dashboard.

This script sets up the session state, provides a scenario gallery for
loading presets, and displays a landing page.  The actual inputs and
outputs are implemented in separate files under the `pages/` directory.
"""

import json
import streamlit as st

from core.params import Scenario

st.set_page_config(page_title="Paulownia Dashboard", layout="wide")

def load_preset(name: str) -> Scenario:
    """Load a preset scenario from the assets/presets folder.

    If the file does not exist or is malformed, returns the default
    Scenario.
    """
    try:
        with open(f"assets/presets/{name}.json", "r") as f:
            data = json.load(f)
        return Scenario.model_validate_json(json.dumps(data))
    except Exception:
        return Scenario()


def main() -> None:
    st.title("Paulownia Circular‑Economy Dashboard")
    st.markdown(
        """
        This application models the circular economy of **Paulownia** forestry projects,
        from planting through biomass harvesting, processing into novel materials and
        finally the use of those materials as soil amendments.  Use the sidebar to
        configure your scenario and run the simulation.  Results are displayed on
        the other pages.
        """
    )
    if "scenario" not in st.session_state:
        st.session_state.scenario = Scenario()
    # preset gallery
    st.sidebar.header("Load Preset Scenario")
    presets = ["germany_wood_harvest", "equatorial_fast_growth", "soil_regen_5y_pullout"]
    preset_choice = st.sidebar.selectbox("Preset", ["Default"] + presets)
    if preset_choice != "Default":
        st.session_state.scenario = load_preset(preset_choice)
        # st.experimental_rerun()
    st.sidebar.markdown("""\nNavigate to **Scenario Inputs** in the page menu to configure or run your own scenario.""")


if __name__ == "__main__":
    main()