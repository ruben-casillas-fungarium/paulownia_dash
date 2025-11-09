# MIT License
"""Agro‑forestry simulator for Paulownia.

This module implements the yearly dynamics of the Paulownia plantation.  It
takes a :class:`~paulownia_dash.core.params.Scenario` and produces a
pandas DataFrame where each row corresponds to a year and lists biomass
flows, revenues, costs and a raw cashflow before any extraction or
industrial processing is applied.  The outputs of this function form the
base for further processing by the industrial chain and end‑of‑life
modules.
"""

from __future__ import annotations
from typing import List
import numpy as np
import pandas as pd
from .params import Scenario, CO2Segment


def co2_fixation_per_tree(year: int, segments: List[CO2Segment]) -> float:
    """Compute the CO₂ fixation per tree for a given year.

    A piecewise linear interpolation is performed between the segments.

    Parameters
    ----------
    year:
        Integer year index (starting from 1) for which to compute the
        fixation rate.
    segments:
        A list of :class:`CO2Segment` objects defining the piecewise
        linear curve.

    Returns
    -------
    float
        The fixation rate in kg CO₂ per tree per year.
    """
    for s in segments:
        if s.start_year <= year < s.end_year:
            t = (year - s.start_year) / (s.end_year - s.start_year)
            return s.start_value_kg_per_tree + t * (s.end_value_kg_per_tree - s.start_value_kg_per_tree)
    # if year is beyond last segment, use the last end value
    return segments[-1].end_value_kg_per_tree


def run_sim(scn: Scenario)->pd.DataFrame:
    print("Running Last Simulation: \n")
    years=np.arange(1, scn.years+1)
    n_trees=scn.trees_per_hectare
    rows=[]
    for y in years:
        co2_per_tree_kg=co2_fixation_per_tree(y, scn.co2_curve)
        co2_t=(co2_per_tree_kg*n_trees)/1000.0
        water_m3=scn.water_need_m3_per_ha_per_year
        wood_m3=wood_m3_salable=0.0
        # harvest only on schedule
        if scn.purpose=='wood_harvest' and y>=3 and ((y-3)%scn.harvest_cycle_years==0):
            wood_m3=scn.wood_yield_m3_per_tree_per_cycle*n_trees
            wood_m3_salable=wood_m3*(1-scn.discard_frac.get('wood',0.1))
        # biomass partitions: approximate using density factor
        trunk_t=(wood_m3*scn.biomass_density_kg_per_m3)/1000.0*scn.above_partition.get('trunk',0.0)
        crown_t=trunk_t*(scn.above_partition.get('crown',0.0)/max(scn.above_partition.get('trunk',1e-6),1e-6))
        roots_t=(trunk_t+crown_t)*scn.below_vs_above_ratio
        #compost is used for MyBCs
        compost_t=crown_t*scn.discard_frac.get('crown',0.0)+roots_t*scn.discard_frac.get('roots',0.1)
        # revenues
        wood_rev=wood_m3_salable*scn.wood_price_per_m3 
        co2_rev=co2_t*scn.co2_price_per_tonne
        other=scn.other_rev_per_ha_per_year
        # costs
        seedlings=n_trees*scn.seedling_price_per_tree if y==1 else 0.0
        water_cost=water_m3*scn.water_price_per_m3
        opex=scn.other_costs_per_ha_per_year  # Operational costs
        cf=(wood_rev+co2_rev+other)-(seedlings+water_cost+opex)
        rows.append(dict(year=y,
                         co2_t=co2_t*scn.n_hectares,
                         water_m3=water_m3*scn.n_hectares,
                         wood_m3=wood_m3*scn.n_hectares,
                         wood_m3_salable=wood_m3_salable*scn.n_hectares,
                         trunk_t=trunk_t*scn.n_hectares,
                         crown_t=crown_t*scn.n_hectares,
                         roots_t=roots_t*scn.n_hectares,
                         compost_t=compost_t*scn.n_hectares,
                         wood_rev=wood_rev*scn.n_hectares,
                         co2_rev=co2_rev*scn.n_hectares,
                         other_rev=other*scn.n_hectares,
                         seedlings_cost=seedlings*scn.n_hectares,
                         water_cost=water_cost*scn.n_hectares,
                         opex=opex*scn.n_hectares,
                         cashflow=cf*scn.n_hectares))
    df=pd.DataFrame(rows)
    df['cum_cashflow']=df['cashflow'].cumsum()
    df['cum_co2_t']=df['co2_t'].cumsum()
    df['cum_wood_m3']=df['wood_m3_salable'].cumsum()
    print("sim: \n", df.head())
    return df
