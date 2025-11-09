# MIT License
"""Aggregation utilities for Paulownia dashboard.

Functions in this module merge the outputs of the agro‑forestry simulator,
industrial chain and end‑of‑life module into a single annual dataset and
compute high‑level key performance indicators (KPIs) such as total
energy use, GHG emissions, revenues, costs and cashflow.  The
implementation deliberately keeps the transformation simple and
transparent.  Additional metrics can be added in a straightforward
manner.
"""

from __future__ import annotations
from typing import Tuple,Iterable, List
import numpy as np
from .params import Scenario
import pandas as pd


def join_all(
    df_agro: pd.DataFrame,
    df_log: pd.DataFrame,
    df_ext: pd.DataFrame,
    df_sub: pd.DataFrame,
    df_pl: pd.DataFrame,
    df_eol_cover: pd.DataFrame,
    df_eol_soil: pd.DataFrame,
    df_eol_fin: pd.DataFrame,
) -> pd.DataFrame:
    """Join dataframes from all stages and compute KPIs.

    The logistics, extraction, substrate and plates dataframes contain
    single rows describing one year of industrial operations.  These
    rows are broadcast across the length of the agro dataframe.

    Parameters
    ----------
    df_agro:
        Agro‑forestry output from :func:`run_sim` with a 'year' column.
    df_log:
        Logistics output from :func:`compute_logistics`.
    df_ext:
        Extraction output from :func:`compute_extraction`.
    df_sub:
        Substrate output from :func:`compute_substrate`.
    df_pl:
        Plate output from :func:`compute_plates`.
    df_eol_cover:
        Coverage output from :func:`coverage_from_plates`.
    df_eol_soil:
        Soil output from :func:`compute_eol_soil_and_finance`.
    df_eol_fin:
        Finance output from :func:`compute_eol_soil_and_finance`.

    Returns
    -------
    pandas.DataFrame
        A dataframe with one row per year and columns aggregating
        metrics across all stages.  Additional columns include
        `total_energy_kWh`, `total_co2_t`, `total_revenue`,
        `total_costs`, `cashflow`, `cum_cashflow`, `eol_cf` and per‑
        plate metrics.
    """
    # replicate industrial data across years
    n_years = len(df_agro)
    df_log_rep = pd.concat([df_log] * n_years, ignore_index=True)
    df_ext_rep = pd.concat([df_ext] * n_years, ignore_index=True)
    df_sub_rep = pd.concat([df_sub] * n_years, ignore_index=True)
    df_pl_rep = pd.concat([df_pl] * n_years, ignore_index=True)
    # merge by index order; assume sorted by year
    df = df_agro.reset_index(drop=True).copy()
    df = pd.concat([df, df_log_rep.drop(columns=["year"]), df_ext_rep.drop(columns=["year"]), df_sub_rep.drop(columns=["year"]), df_pl_rep.drop(columns=["year"])], axis=1)
    # broadcast EoL finance for each year; the soil and finance tables already have year indexes starting at 1
    eol_fin_broadcast = pd.merge(df[["year"]], df_eol_fin, how="left", on="year").fillna(0.0)
    df = pd.concat([df, eol_fin_broadcast.drop(columns=["year"])], axis=1)
    # calculate totals
    # energy: sum of extraction, sterilisation, plates (logistics energy not included here)
    df["total_energy_kWh"] = (
        df["E_steam_kWh"] + df["E_press_kWh"] + df["E_over_kWh"] + df["E_ster_kWh"] + df["E_plates_kWh"]
    )
    # total GHG emissions (t) from agro and industrial scopes
    df["total_co2_t"] = df["co2_t"] + df["transport_co2_t"] + df["co2_scope2_t"] + df["co2_scope2_plates_t"]
    # revenue terms
    df["total_revenue"] = (
        df["wood_rev"] + df["co2_rev"] + df["other_rev"] + df["rev_extract"] + df["rev_plates"] + df.get("rev_carbon", 0.0)
    )
    # cost terms
    df["total_costs"] = (
        df["seedlings_cost"]
        + df["water_cost"]
        + df["opex"]
        + df["transport_cost_eur"]
        + df["additives_cost_eur"]
        + df["inoculum_cost_eur"]
        + df.get("cost_field_ops", 0.0)
        + df.get("cost_monitor", 0.0)
    )
    df["cashflow"] = df["total_revenue"] - df["total_costs"]
    df["cum_cashflow"] = df["cashflow"].cumsum()
    # plate level metrics
    df["euro_per_plate"] = df["total_revenue"] / df["plates"].replace(0.0, float("nan"))
    df["kwh_per_plate"] = df["total_energy_kWh"] / df["plates"].replace(0.0, float("nan"))
    df["kgco2_per_plate"] = df["total_co2_t"] * 1000.0 / df["plates"].replace(0.0, float("nan"))
    return df

def _eps_margin(price: float, cost: float) -> float:
    return price - cost

def _myco_margin(price: float, cost: float) -> float:
    return price - cost

def compute_business_streams(scn: Scenario, df_agro: pd.DataFrame, df_log: pd.DataFrame, df_ext: pd.DataFrame, df_sub: pd.DataFrame, df_pl: pd.DataFrame) -> pd.DataFrame:
    df = df_agro.copy()
    plates = float(df_pl.loc[0, "plates"]) if not df_pl.empty else 0.0
    rev_plates = plates * scn.plates.plate_price_eur
    cost_plates = plates * scn.plates.plate_cost_eur
    gm_plates = rev_plates - cost_plates
    rev_extract = float(df_ext.loc[0, "rev_extract"]) if not df_ext.empty else 0.0
    transport_cost = float(df_log.loc[0, "transport_cost_eur"]) if not df_log.empty else 0.0
    additives_cost = float(df_sub.loc[0, "additives_cost_eur"]) if not df_sub.empty else 0.0
    inoculum_cost  = float(df_sub.loc[0, "inoculum_cost_eur"]) if not df_sub.empty else 0.0
    eps_margin = _eps_margin(scn.plates.competitor_eps_price_eur, scn.plates.competitor_eps_cost_eur)
    myco_margin = _myco_margin(scn.plates.plate_price_eur, scn.plates.plate_cost_eur)
    df["plates"] = plates
    df["rev_plates"] = rev_plates
    df["cost_plates"] = cost_plates
    df["gm_plates"] = gm_plates
    df["rev_extract"] = rev_extract
    df["transport_cost_eur"] = transport_cost
    df["additives_cost_eur"] = additives_cost
    df["inoculum_cost_eur"] = inoculum_cost
    df["eps_margin_per_plate"] = eps_margin
    df["myco_margin_per_plate"] = myco_margin
    df["margin_uplift_per_plate"] = myco_margin - eps_margin
    df["total_revenue_business"] = df["rev_plates"] + df["rev_extract"]
    df["total_costs_business"] = df["transport_cost_eur"] + df["additives_cost_eur"] + df["inoculum_cost_eur"] + df["cost_plates"]
    df["cashflow_business"] = df["total_revenue_business"] - df["total_costs_business"]
    df["cashflow_total"] = df["cashflow"] + df["cashflow_business"]
    pool = df["cashflow_total"].clip(lower=0.0)
    a = scn.allocation
    df["to_farmers"] = pool * a.to_farmers
    df["to_employees"] = pool * a.to_employees
    df["to_company"] = pool * a.to_company
    df["to_investors"] = pool * a.to_investors
    df["investor_cashflow_y"] = df["to_investors"]
    jobs_min = scn.labor.min_automation_employees
    jobs_dev_mid = (scn.labor.jobs_per_shift_low + scn.labor.jobs_per_shift_high)/2 * scn.labor.shifts_per_day
    df["jobs_min_automation"] = jobs_min
    df["jobs_dev_mid"] = jobs_dev_mid
    inbound = float(df_log.loc[0,"inbound_mass_t"]) if not df_log.empty else 1.0
    df["eur_per_t_inbound"] = (df["total_revenue_business"] - df["total_costs_business"]) / max(inbound,1e-9)
    df["eur_per_plate"] = np.where(df["plates"]>0, df["gm_plates"]/df["plates"], np.nan)
    df["cum_cashflow_total"] = df["cashflow_total"].cumsum()
    return df
