"""Core package for Paulownia circular‑economy modelling.

This package contains all deterministic models (growth, logistics,
extraction, substrate production, plate manufacturing and end‑of‑life),
aggregation utilities, and economic calculations used by the Streamlit
dashboard.

Each submodule exposes pure functions that accept typed parameter models
and return pandas DataFrames.  The high‑level `run_simulation` helper in
`aggregate.py` composes these functions to produce a full scenario
overview.
"""

from .params import Scenario, CO2Segment, LogisticsParams, ExtractionParams, SubstrateParams, PlateParams, ProcessScaleParams, EoLParams
from .sim_1_agriculture import run_sim
from .sim_2_production import run_industrial_chain
from .sim_3_eol import run_eol_module
from .aggregate import join_all
from .economics import npv, irr

__all__ = [
    "Scenario",
    "CO2Segment",
    "LogisticsParams",
    "ExtractionParams",
    "SubstrateParams",
    "PlateParams",
    "ProcessScaleParams",
    "EoLParams",
    "run_sim",
    "run_industrial_chain",
    "run_eol_module",
    "join_all",
    "npv",
    "irr",
]