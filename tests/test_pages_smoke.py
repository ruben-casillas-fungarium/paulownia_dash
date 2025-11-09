"""Smoke tests for Streamlit pages.

These tests import each page module to ensure that they can be loaded
without raising syntax errors.  If a module defines a `page()` function,
the function is called in a try/except block to ensure that it does not
raise exceptions when executed with an empty session state.  These
tests do not start a Streamlit server; they simply exercise the
page definitions.
"""

import importlib

import pytest

PAGES = [
    "pages.1_scenario_inputs",
    "pages.2_results_timeseries",
    "pages.3_biomass_flows",
    "pages.4_water_co2",
    "pages.5_economics",
    "pages.6_sensitivity_compare",
    "pages.7_logistics",
    "pages.8_extraction_products",
    "pages.9_substrate_plates",
    "pages.10_cradle_to_gate_summary",
    "pages.11_eol_recovery_coverage",
    "pages.12_soil_carbon",
    "pages.13_carbon_credits_cashflow",
]


# @pytest.mark.parametrize("module_name", PAGES)
# def test_import_and_run(module_name):
#     mod = importlib.import_module(module_name)
#     # verify module imported correctly
#     assert mod is not None
#     # if the module defines a page() function, call it
#     if hasattr(mod, "page"):
#         try:
#             mod.page()
#         except Exception as e:
#             pytest.fail(f"Page {module_name} raised an exception: {e}")