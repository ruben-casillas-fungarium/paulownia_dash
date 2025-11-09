# MIT License
"""Industrial chain simulation: logistics, extraction, substrate, plates.

This module contains functions that model the inbound logistics of
Paulownia residues, the extraction of products from roots, the blending
of substrates using crown/wood and root fibres, and the manufacture of
mycelium plates.  Each function returns a pandas DataFrame containing
yearly results and is designed to operate on a single year (annual
average values).  The high‑level :func:`run_industrial_chain` function
orchestrates these steps.
"""

from __future__ import annotations
import math
import pandas as pd
import numpy as np
from typing import Tuple
from .params import Scenario, LogisticsParams, ExtractionParams, SubstrateParams, PlateParams, ProcessScaleParams


def compute_logistics(year: int, lp: LogisticsParams, scale: ProcessScaleParams) -> pd.DataFrame:
    """Compute inbound logistics metrics for one year.

    Parameters
    ----------
    scn:
        Scenario containing project scale (but only `scale` is used here).
    lp:
        Logistics parameter object.
    scale:
        Process scale defining inbound mass and root fraction.

    Returns
    -------
    pandas.DataFrame
        A single‑row dataframe with columns: inbound_mass_t, n_trips,
        tkm, transport_cost_eur, transport_co2_t, handling_loss_t,
        inbound_net_t.
    """
    inbound_mass_t = scale.inbound_mass_t_per_year
    n_trips = math.ceil(inbound_mass_t / max(lp.trailer_payload_t, 1e-6))
    tkm = inbound_mass_t * lp.transport_distance_km
    transport_cost = (
        lp.transport_distance_km * lp.transport_cost_per_km * n_trips * (1.0 - lp.backhaul_utilization)
    )
    transport_co2_t = (lp.truck_emission_kg_per_tkm * tkm) / 1000.0
    handling_loss_t = inbound_mass_t * lp.loading_loss_frac
    inbound_net_t = inbound_mass_t - handling_loss_t
    return pd.DataFrame([
        dict(
            year=year,
            inbound_mass_t=inbound_mass_t,
            n_trips=n_trips,
            tkm=tkm,
            transport_cost_eur=transport_cost,
            transport_co2_t=transport_co2_t,
            handling_loss_t=handling_loss_t,
            inbound_net_t=inbound_net_t,
        )
    ])


def compute_extraction(scn: Scenario, ep: ExtractionParams, roots_in_t: float) -> pd.DataFrame:
    """Compute root extraction yields, energy, GHG and revenue.

    Parameters
    ----------
    scn:
        The scenario (unused but kept for signature consistency).
    ep:
        Extraction parameter object.
    roots_in_t:
        Tonnes of root material entering the extraction line.

    Returns
    -------
    pandas.DataFrame
        A single‑row dataframe with columns: roots_in_t, root_fiber_t,
        extract_t, extract_L, E_steam, E_press, E_over, E_total,
        co2_scope2_t, rev_extract.
    """
    roots_in = roots_in_t
    root_fiber_t = roots_in * ep.fiber_yield_frac
    extract_t = roots_in * ep.extract_yield_frac
    extract_L = extract_t * 1000.0 / max(ep.extract_density_kg_per_L, 1e-6)
    # energy consumption
    E_steam = roots_in * ep.steam_energy_kWh_per_t_root
    E_press = roots_in * ep.press_energy_kWh_per_t_root
    E_over = roots_in * ep.line_overhead_kWh_per_t_root
    E_total = E_steam + E_press + E_over
    # revenue
    if ep.sell_crude_extract:
        rev_extract = extract_L * ep.price_extract_eur_per_L
    else:
        oleic_kg = extract_t * 1000.0 * ep.oleic_frac_in_extract * ep.purification_yield
        theo_kg = extract_t * 1000.0 * ep.theobromine_frac_in_extract * ep.purification_yield
        rev_extract = oleic_kg * ep.price_oleic_eur_per_kg + theo_kg * ep.price_theobromine_eur_per_kg
    # scope‑2 GHG emissions
    co2_scope2_t = (1.0 - scn.plates.solar_share) * E_total * scn.plates.grid_emission_kg_per_kWh / 1000.0
    return pd.DataFrame([
        dict(
            year=1,
            roots_in_t=roots_in,
            root_fiber_t=root_fiber_t,
            extract_t=extract_t,
            extract_L=extract_L,
            E_steam_kWh=E_steam,
            E_press_kWh=E_press,
            E_over_kWh=E_over,
            E_total_kWh=E_total,
            co2_scope2_t=co2_scope2_t,
            rev_extract=rev_extract,
        )
    ])
    
    
def compute_substrate(sp: SubstrateParams, root_fiber_t: float, crownwood_t: float) -> pd.DataFrame:
    """Compute substrate blending metrics.

    Parameters
    ----------
    sp:
        Substrate parameter object.
    root_fiber_t:
        Tonnes of root fibre available.
    crownwood_t:
        Tonnes of crown and wood material available (dry).

    Returns
    -------
    pandas.DataFrame
        A single‑row dataframe with columns: root_fiber_used_t,
        other_dry_used_t, wet_substrate_t, E_ster_kWh, additives_cost_eur,
        inoculum_cost_eur, usable_wet_substrate_t.
    """
    # total available dry mass
    blend_demand = root_fiber_t + crownwood_t
    root_fiber_used = min(root_fiber_t, blend_demand * sp.root_fiber_share)
    other_dry_used = min(crownwood_t, blend_demand * sp.other_dry_share)
    dry_total_used = root_fiber_used + other_dry_used
    wet_substrate_t = dry_total_used * sp.rehydration_ratio_wet_over_dry
    E_ster = wet_substrate_t * 1000.0 * sp.sterilize_kWh_per_t_substrate / 1000.0  # convert tonne to kg
    additives_cost = wet_substrate_t * 1000.0 * sp.additives_cost_eur_per_kg_wet
    inoculum_cost = wet_substrate_t * 1000.0 * sp.inoculum_cost_eur_per_kg
    usable_wet_substrate_t = wet_substrate_t * (1.0 - sp.yield_loss_frac)
    return pd.DataFrame([
        dict(
            year=1,
            root_fiber_used_t=root_fiber_used,
            other_dry_used_t=other_dry_used,
            wet_substrate_t=wet_substrate_t,
            E_ster_kWh=E_ster,
            additives_cost_eur=additives_cost,
            inoculum_cost_eur=inoculum_cost,
            usable_wet_substrate_t=usable_wet_substrate_t,
        )
    ])


def compute_plates(pp: PlateParams, wet_substrate_t: float, loss_frac: float, price_eur: float) -> pd.DataFrame:
    """Compute plate production metrics.

    Parameters
    ----------
    pp:
        Plate parameter object.
    wet_substrate_t:
        Tonnes of wet substrate available for plates.
    loss_frac:
        Fraction of substrate lost prior to plate forming.
    price_eur:
        Price per plate (EUR), 0 if not sold.

    Returns
    -------
    pandas.DataFrame
        A single‑row dataframe with columns: plates, dry_mass_kg,
        E_plates_kWh, co2_scope2_plates_t, rev_plates.
    """
    usable_wet_t = wet_substrate_t * (1.0 - loss_frac)
    plates = (usable_wet_t * 1000.0) / max(pp.wet_input_kg_per_plate, 1e-6)
    dry_mass_kg = plates * pp.dry_output_kg_per_plate
    E_plates_kWh = (plates / 100.0) * pp.energy_kWh_per_100_plates
    co2_scope2_plates_t = (1.0 - pp.solar_share) * E_plates_kWh * pp.grid_emission_kg_per_kWh / 1000.0
    rev_plates = plates * price_eur
    return pd.DataFrame([
        dict(
            year=1,
            plates=plates,
            dry_mass_kg=dry_mass_kg,
            E_plates_kWh=E_plates_kWh,
            co2_scope2_plates_t=co2_scope2_plates_t,
            rev_plates=rev_plates,
        )
    ])


def run_industrial_chain(scn: Scenario) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the logistics, extraction, substrate and plates simulation for one year.

    Parameters
    ----------
    scn:
        The full scenario describing logistics, extraction, substrate and plate parameters.

    Returns
    -------
    Tuple[pandas.DataFrame, pandas.DataFrame, pandas.DataFrame, pandas.DataFrame]
        A tuple of dataframes: (df_logistics, df_extraction, df_substrate, df_plates).  Each
        contains a single row for the current year.
    """
    # logistics: compute inbound masses and costs
    print("Running Industrial Chain: \n")
    df_log = compute_logistics(scn.years, scn.logistics, scn.scale)
    inbound_net_t_raw = df_log.loc[0, "inbound_net_t"]
    try:
        inbound_net_t = float(inbound_net_t_raw)
    except Exception:
        inbound_net_t = float(str(inbound_net_t_raw))
    print("Inbound Net: ",inbound_net_t)
    # split into roots vs crown+wood
    roots_in_t = inbound_net_t * scn.scale.root_fraction_of_inbound
    crownwood_in_t = inbound_net_t * (1.0 - scn.scale.root_fraction_of_inbound)
    # extraction on roots
    df_ext = compute_extraction(scn, scn.extraction, roots_in_t)
    root_fiber_t_raw = df_ext.loc[0, "root_fiber_t"]
    extract_t_raw = df_ext.loc[0, "extract_t"]
    try:
        root_fiber_t = float(root_fiber_t_raw)
    except Exception:
        root_fiber_t = float(str(root_fiber_t_raw))
    print("root_fiber_t_raw: ",root_fiber_t_raw)
    try:
        extract_t = float(extract_t_raw)
    except Exception:
        extract_t = float(str(extract_t_raw))
    print("extract_t_raw: ",extract_t_raw)
    # substrate blending with crownwood and root fibres
    df_sub = compute_substrate(scn.substrate, root_fiber_t, crownwood_in_t)
    wet_substrate_t_raw = df_sub.loc[0, "usable_wet_substrate_t"]
    try:
        wet_substrate_t = float(wet_substrate_t_raw)
    except Exception:
        wet_substrate_t = float(str(wet_substrate_t_raw))
    print("wet_substrate_t_raw: ",wet_substrate_t_raw)
    # plate manufacturing
    df_pl = compute_plates(scn.plates, wet_substrate_t, scn.substrate.yield_loss_frac, scn.plates.plate_price_eur)
    print("df_log: \n ", df_log.head())
    print("df_ext: \n ", df_ext.head())
    print("df_sub: \n ", df_sub.head())
    print("df_pl: \n ", df_pl.head())
    return df_log, df_ext, df_sub, df_pl

