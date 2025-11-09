"""Tests for the aggregate module.

These tests ensure that the join_all function merges the dataframes
correctly, adds derived columns without NaNs and computes expected
financial metrics on a simple synthetic example.
"""

import numpy as np
import pandas as pd

from core.aggregate import join_all
from core.params import Scenario
from core.sim_1_agriculture import run_sim
from core.sim_2_production import run_industrial_chain
from core.sim_3_eol import run_eol_module


def test_join_all_no_nans():
    scn = Scenario(years=1)
    df_agro = run_sim(scn)
    df_log, df_ext, df_sub, df_pl = run_industrial_chain(scn)
    df_cover, df_soil, df_fin = run_eol_module(df_pl, scn, scn.eol, scn.plates)
    df_joined = join_all(df_agro, df_log, df_ext, df_sub, df_pl, df_cover, df_soil, df_fin)
    # ensure no NaNs in crucial numeric columns
    numeric_cols = [c for c in df_joined.columns if df_joined[c].dtype.kind in 'fi']
    assert not df_joined[numeric_cols].isnull().any().any()
    # check derived columns exist
    for col in ["total_energy_kWh", "total_co2_t", "total_revenue", "total_costs", "cashflow", "cum_cashflow"]:
        assert col in df_joined.columns


def test_join_all_financials():
    # create a synthetic scenario with no revenues and constant costs
    scn = Scenario(years=2, co2_price_per_tonne=0.0, wood_price_per_m3=0.0, other_rev_per_ha_per_year=0.0)
    scn.other_costs_per_ha_per_year = 100.0
    df_agro = run_sim(scn)
    df_log, df_ext, df_sub, df_pl = run_industrial_chain(scn)
    df_cover, df_soil, df_fin = run_eol_module(df_pl,scn, scn.eol, scn.plates)
    df = join_all(df_agro, df_log, df_ext, df_sub, df_pl, df_cover, df_soil, df_fin)
    # since no revenue, cashflow should be negative and equal to total costs
    assert all(df["total_revenue"] == 0.0)
    assert all(df["cashflow"] == -df["total_costs"])