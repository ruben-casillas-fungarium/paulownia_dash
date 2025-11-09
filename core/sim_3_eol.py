# MIT License
"""End‑of‑life soil carbon module.

This module computes how recovered plates are applied to agricultural land as
a soil amendment, estimates the resulting carbon sequestration over time
relative to a baseline and calculates associated revenues from carbon
credits.  It operates on the output of the plate production stage.
"""

from __future__ import annotations
from typing import Tuple
import numpy as np
import pandas as pd
from .params import Scenario, LogisticsParams, ExtractionParams, EoLParams,  SubstrateParams, PlateParams, ProcessScaleParams


def coverage_from_plates(df_pl, plate_params: PlateParams, eol_params: EoLParams) -> pd.DataFrame:
    """Compute the area that can be covered with recovered plates in one year using scenario and parameter objects.

    Parameters
    ----------
    scn:
        Scenario object containing simulation settings (must have attribute 'plates' or similar).
    plate_params:
        PlateParams object describing plate geometry and mass.
    eol_params:
        EoLParams object with end-of-life parameters.

    Returns
    -------
    pandas.DataFrame
        A single-row dataframe with columns: plates_produced,
        plates_recovered, cover_area_ha_material_cap, treatable_area_ha,
        area_required_total_ha_for_50pct_rule.
    """
    # Number of plates produced in the year (assume attribute 'plates' in Scenario)
    plates_y =df_pl["plates"]
    # recovered plates
    plates_recovered = plates_y * eol_params.recovered_plate_frac
    # volume per plate (m³) using geometry (length × width × thickness)
    V_plate = plate_params.plate_len_m * plate_params.plate_wid_m * plate_params.plate_thk_m
    V_eff = V_plate * eol_params.compaction_ratio
    A_per_plate = V_eff / max(eol_params.layer_thickness_m, 1e-6)
    A_cover_m2 = plates_recovered * A_per_plate
    A_cover_ha = A_cover_m2 / 10_000.0
    treatable_area_ha = A_cover_ha
    area_required_total_ha_for_50pct_rule = treatable_area_ha / max(eol_params.max_land_coverage_frac, 1e-6)
    df_cov_plates = pd.DataFrame([
        dict(
            year=1,
            plates_produced=plates_y,
            plates_recovered=plates_recovered,
            cover_area_ha_material_cap=A_cover_ha,
            treatable_area_ha=treatable_area_ha,
            area_required_total_ha_for_50pct_rule=area_required_total_ha_for_50pct_rule,
        )
    ])
    print("df_cov: \n", df_cov_plates.head())
    return df_cov_plates
    
    
def soil_response_per_ha(year: int, after5: float, post5_rate: float) -> float:
    """Return the additional CO₂ stored per hectare in a given year.

    The accumulation ramps linearly up to year 5 and then increases
    linearly thereafter at a constant annual increment.

    Parameters
    ----------
    year:
        Year index (starting from 1).
    after5:
        Additional CO₂ (tonnes) per hectare after 5 years.
    post5_rate:
        Annual increase in tonnes CO₂ per hectare after year 5.

    Returns
    -------
    float
        Tonnes CO₂ per hectare in year `year`.
    """
    if year <= 5:
        return after5 * (year / 5.0)
    else:
        return after5 + (year - 5) * post5_rate




def compute_eol_soil_and_finance(df_cover: pd.DataFrame,scn: Scenario, eol: EoLParams) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute soil carbon deltas and financial returns over the project years.

    Parameters
    ----------
    df_cover:
        DataFrame from :func:`coverage_from_plates` with area columns.
    eol:
        End‑of‑life parameter object.

    Returns
    -------
    Tuple[pandas.DataFrame, pandas.DataFrame]
        Two dataframes: one describing soil carbon per hectare and
        total deltas; the other describing financial returns per year.
    """
    A_treated_ha_raw = df_cover.loc[0, "treatable_area_ha"]
    try:
        A_treated_ha = float( A_treated_ha_raw)
    except Exception:
        A_treated_ha = float(str( A_treated_ha_raw))
    years = np.arange(1, scn.years + 1)
    soil_rows = []
    finance_rows = []
    for y in years:
        treated_co2_per_ha = soil_response_per_ha(y, eol.treated_CO2_add_t_per_ha_after_5y, eol.treated_CO2_add_t_per_ha_per_y_post_5)
        baseline_co2_per_ha = soil_response_per_ha(y, eol.baseline_CO2_add_t_per_ha_after_5y, eol.baseline_CO2_add_t_per_ha_per_y_post_5)
        delta_per_ha = treated_co2_per_ha - baseline_co2_per_ha
        delta_total_tCO2 = delta_per_ha * A_treated_ha
        delta_total_tC = delta_total_tCO2 * (12.0 / 44.0)
        # determine price
        if eol.use_midpoint_price:
            price = eol.carbon_price_mid_eur
        else:
            price = (eol.carbon_price_lo_eur + eol.carbon_price_hi_eur) / 2.0
        if eol.credit_basis == "tCO2e":
            revenue = delta_total_tCO2 * price
        else:
            revenue = delta_total_tC * price
        cost_field_ops = A_treated_ha * eol.field_ops_cost_eur_per_ha
        cost_monitor = A_treated_ha * eol.monitoring_cost_eur_per_ha_per_y
        cf_eol = revenue - (cost_field_ops + cost_monitor)
        soil_rows.append(
            dict(
                year=y,
                S_treated_per_ha_tCO2=treated_co2_per_ha,
                S_baseline_per_ha_tCO2=baseline_co2_per_ha,
                delta_per_ha_tCO2=delta_per_ha,
                delta_total_tCO2=delta_total_tCO2,
                delta_total_tC=delta_total_tC,
            )
        )
        finance_rows.append(
            dict(
                year=y,
                carbon_price=price,
                rev_carbon=revenue,
                cost_field_ops=cost_field_ops,
                cost_monitor=cost_monitor,
                cf_eol=cf_eol,
            )
        )
    df_soil = pd.DataFrame(soil_rows)
    df_fin = pd.DataFrame(finance_rows)
    print("df_soil: \n ", df_soil.head())
    print("df_fin: \n ", df_fin.head())
    return df_soil, df_fin


def run_eol_module(plates_df: pd.DataFrame, scn: Scenario, eol: EoLParams, plate_params: PlateParams) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Compute the end‑of‑life module given plates production data.

    Parameters
    ----------
    plates_df:
        DataFrame returned by :func:`compute_plates` with at least a
        'plates' column.
    eol:
        End‑of‑life parameter object.
    plate_params:
        Plate parameter object used for geometry and mass information.

    Returns
    -------
    Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        DataFrames for coverage (`df_eol_coverage`), soil (`df_eol_soil`)
        and finance (`df_eol_finance`).
    """
    print("Running EoL Module: \n")
    plates_y_raw = plates_df["plates"].iloc[0]
    try:
        plates_y_t = float(plates_y_raw)
    except Exception:
        plates_y_t = float(str(plates_y_raw))
    print("plates_y_raw: ", plates_y_t)
    df_cover = coverage_from_plates(plates_df, plate_params, eol)
    df_soil, df_fin = compute_eol_soil_and_finance(df_cover, scn, eol)
    return df_cover, df_soil, df_fin
