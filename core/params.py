# MIT License
"""Data models for Paulownia dashboard.

All data models are defined using [`pydantic.BaseModel`](https://pydantic-docs.helpmanual.io/)
to provide type checking, validation and JSON serialisation.  Each model
encapsulates a set of parameters for a particular stage of the project.

The top‑level :class:`Scenario` holds a collection of nested parameter
objects.  This allows users to tweak values via the Streamlit interface
without worrying about their correct structure.
"""
from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from pydantic import field_validator

class CO2Segment(BaseModel):
    """A single segment of a piecewise linear CO₂ fixation function.

    Attributes
    ----------
    start_year:
        Inclusive lower bound of the segment (in years since planting).
    end_year:
        Exclusive upper bound of the segment.
    start_value_kg_per_tree:
        Fixation rate (kg CO₂ per tree per year) at `start_year`.
    end_value_kg_per_tree:
        Fixation rate at `end_year`.  A linear interpolation is applied
        between `start_value_kg_per_tree` and `end_value_kg_per_tree` for
        years within the segment.
    """

    start_year: int = Field(1)
    end_year: int = Field(1,ge=1,le=1000)
    start_value_kg_per_tree: float = Field(0.34, ge=0.1, le=100, description="Fixation rate (kg CO₂ per tree per year) at `start_year`")
    end_value_kg_per_tree: float =Field(7.34, ge=0.1, le=100, description="Fixation rate (kg CO₂ per tree per year) at `end_year`")

    @field_validator("end_year")
    def end_after_start(cls, v, values):
        if "start_year" in values.data and v <= values.data["start_year"]:
            raise ValueError("end_year must be strictly greater than start_year")
        return v
    
    
class ProcessScaleParams(BaseModel):
    """Parameters controlling the scale of logistics and processing.

    These parameters define how many tonnes of Paulownia residue are processed per year and the fraction of roots within that residue.
    """
    inbound_mass_t_per_year: float = Field(1000.0, ge=1, le=1e15)
    root_fraction_of_inbound: float = Field(0.30, ge=0.0, le=1.0)
    substrate_to_plate_uptime_frac: float = Field(0.9, ge=0.0, le=1.0)


class LogisticsParams(BaseModel):
    """Parameters controlling inbound logistics of Paulownia residues.

    Distances are measured in kilometres, payloads in tonnes and costs in EUR.
    """

    trailer_payload_t: float = Field(20 , ge= 0, le= 100,  description="Payload capacity of one trailer (t)")
    transport_distance_km: float = Field(80,ge= 1, le= 10000, description="Distance from supplier to plant (km)")
    transport_cost_per_km: float = Field(1,ge= 0.1, le= 1000, description="Transport cost per km of travel (EUR/km)")
    backhaul_utilization: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of distance cost recovered via backhaul")
    truck_emission_kg_per_tkm: float = Field(1,ge= 0, le= 100, description="Truck GHG emissions per ton‑kilometre (kg CO₂e/t·km)")
    loading_loss_frac: float = Field(0.02, ge=0.0, le=1.0, description="Fraction of material lost during loading/unloading")

class ExtractionParams(BaseModel):
    """Parameters controlling root extraction and processing.
    All energies are per tonne of root material.
    """

    grind_size_mm: float = Field(
        5.0,
        ge=0.1,
        le=100.0,
        description="Grinding size for root material before extraction (mm)."
    )
    steam_energy_kWh_per_t_root: float = Field(
        1.0,
        ge=0.0,
        le=1000.0,
        description="Steam energy used per tonne of root material (kWh/t)."
    )
    steam_time_min: int = Field(
        30,
        ge=1,
        le=240,
        description="Steam treatment time per batch (minutes)."
    )
    press_force_t: float = Field(
        80.0,
        ge=1.0,
        le=1000.0,
        description="Press force applied during extraction (tonnes)."
    )
    press_time_min: int = Field(
        3,
        ge=1,
        le=120,
        description="Pressing time per batch (minutes)."
    )
    press_energy_kWh_per_t_root: float = Field( 
        2.0,
        ge=0.0,
        le=1000.0,
        description="Press energy used per tonne of root material (kWh/t)."
    )
    line_overhead_kWh_per_t_root: float = Field(
        1.0,
        ge=0.0,
        le=1000.0,
        description="Line overhead energy per tonne of root material (kWh/t)."
    )
    fiber_yield_frac: float = Field(
        0.55,
        ge=0.0,
        le=1.0,
        description="Fraction of input root mass converted to fiber (0–1)."
    )
    extract_yield_frac: float = Field(
        0.45,
        ge=0.0,
        le=1.0,
        description="Fraction of input root mass converted to extract (0–1)."
    )
    extract_density_kg_per_L: float = Field(
        1.0,
        ge=0.1,
        le=2.0,
        description="Density of extract (kg/L)."
    )
    oleic_frac_in_extract: float = Field(
        0.35,
        ge=0.0,
        le=1.0,
        description="Fraction of oleic acid in extract (0–1)."
    )
    theobromine_frac_in_extract: float = Field(
        0.34,
        ge=0.0,
        le=1.0,
        description="Fraction of theobromine in extract (0–1)."
    )
    price_oleic_eur_per_kg: float = Field(
        36.0,
        ge=0.0,
        le=1000.0,
        description="Market price of oleic acid (EUR/kg)."
    )
    price_theobromine_eur_per_kg: float = Field(
        170.0,
        ge=0.0,
        le=5000.0,
        description="Market price of theobromine (EUR/kg)."
    )
    price_extract_eur_per_L: float = Field(
        175.0,
        ge=0.0,
        le=5000.0,
        description="Market price of crude extract (EUR/L)."
    )
    sell_crude_extract: bool = Field(
        True,
        description="Whether to sell crude extract directly (True) or purify further (False)."
    )
    purification_yield: float = Field(
        0.90,
        ge=0.0,
        le=1.0,
        description="Yield fraction after purification (0–1)."
    )

class SubstrateParams(BaseModel):
    """Parameters controlling substrate blending of crown/wood and root fibres."""

    root_fiber_share: float = Field(0.10, ge=0.0, le=1.0, description="Fraction of dry mass from root fibres")
    other_dry_share: float = Field(0.90, ge=0.0, le=1.0, description="Fraction of dry mass from crown+wood grind")
    rehydration_ratio_wet_over_dry: float = Field(3.7 / 1.1, description="Wet/dry mass ratio used in substrate")
    sterilize_kWh_per_t_substrate: float = Field(4.0, description="Energy used to sterilise 1 tonne of wet substrate (kWh)")
    inoculum_cost_eur_per_kg: float = Field(0.85, description="Inoculum cost per kg")
    additives_cost_eur_per_kg_wet: float = Field(0.85, description="Additives cost per kg wet substrate")
    yield_loss_frac: float = Field(0.05, ge=0.0, le=1.0, description="Fraction of substrate lost to contamination")

class PlateParams(BaseModel):
    plates_per_ton_hint: int = Field(100, ge=1, le=1000, description="Number of plates per ton of mixture")
    plate_len_m: float = Field(1.0, ge=0.001, le=1_000, description="length of the plate in Meters (m)")
    plate_wid_m: float = Field(1.0, ge=0.001, le=1_000, description="width of the plate in Meters (m)")
    plate_thk_m: float = Field(0.06, ge=0.001, le=1_000, description="thickness of the plate in Meters (m)")
    wet_input_kg_per_plate: float = Field(3.7, ge=0.001, le=10_000, description="MyBC in Organic Phase (Alive) in Kilograms (Kg)")
    dry_output_kg_per_plate: float = Field(1.1, ge=0.001, le=10_000, description="MyBC in Material Phase (Dead) in Kilograms (Kg)")
    cure_days: int = Field(7, ge=1, le=14, description="Days of maturity in mold 24hrs (integer)")
    energy_kWh_per_100_plates: float = Field(4.0, ge=0.001, le=10_000, description="kWh used per 100 plates in kiloWatts per hour (kWh)")
    solar_share: float = Field(1.0, ge=0.001, le=1, description="Percentage of the production from Sustainable sources (%)")
    grid_emission_kg_per_kWh: float = Field(0.35, ge=0.001, le=1000, description="CO2 emission in kilograms (kg) per kilowatthour (kWh)")
    plate_cost_eur: float = Field(3.0, ge=0.1, le=100, description="Production cost per plate (eur)")
    plate_price_eur: float = Field(12.0, ge=0.01, le=100, description="Retail price per plate (eur)")
    competitor_eps_price_eur: float = Field(12.0, ge=0.01, le=100, description="Retail price of EPS plate of same volume (eur)")
    competitor_eps_cost_eur: float = Field(6.0, ge=0.01, le=100, description="Production cost of EPS plate of same volume (eur)")
    

class EoLParams(BaseModel):
    """Parameters controlling end‑of‑life soil carbon projects.

    These parameters define how mycelium plates are recovered, processed, and credited for soil carbon sequestration at end-of-life.
    """

    recovered_plate_frac: float = Field(
        0.40,
        ge=0.0,
        le=1.0,
        description="Fraction of produced plates that are recovered for soil application at end-of-life (0–1)."
    )
    max_land_coverage_frac: float = Field(
        0.50,
        ge=0.0,
        le=1.0,
        description="Maximum fraction of available land that can be covered with plates (0–1)."
    )
    layer_thickness_m: float = Field(
        0.02,
        ge=0.000001,
        le=10.0,
        description="Thickness of the plate layer applied to soil (meters)."
    )
    compaction_ratio: float = Field(
        1.00,
        ge=0.1,
        le=100,
        description="Ratio of compacted to uncompacted plate volume after soil application."
    )
    crushed_bulk_density_kg_m3: float = Field(
        180.0,
        ge=10.0,
        le=2000.0,
        description="Bulk density of crushed plates applied to soil (kg/m³)."
    )
    credit_basis: Literal["tCO2e", "tC"] = Field(
        "tC",
        description="Basis for carbon crediting: tonnes of CO₂ equivalent ('tCO2e') or tonnes of carbon ('tC')."
    )
    carbon_price_lo_eur: float = Field(
        50.0,
        ge=0.0,
        le=1000.0,
        description="Low estimate for carbon price (EUR per credit unit)."
    )
    carbon_price_hi_eur: float = Field(
        101.0,
        ge=0.0,
        le=1000.0,
        description="High estimate for carbon price (EUR per credit unit)."
    )
    use_midpoint_price: bool = Field(
        True,
        description="Whether to use the midpoint carbon price for calculations."
    )
    carbon_price_mid_eur: float = Field(
        60.0,
        ge=0.0,
        le=1000.0,
        description="Midpoint carbon price (EUR per credit unit)."
    )
    treated_CO2_add_t_per_ha_after_5y: float = Field(
        4.0,
        ge=0.0,
        le=100.0,
        description="Additional CO₂ sequestered per hectare after 5 years (treated scenario, tonnes CO₂/ha)."
    )
    treated_CO2_add_t_per_ha_per_y_post_5: float = Field(
        1.7,
        ge=0.0,
        le=20.0,
        description="Annual additional CO₂ sequestered per hectare after year 5 (treated, tonnes CO₂/ha/year)."
    )
    baseline_CO2_add_t_per_ha_after_5y: float = Field(
        1.5,
        ge=0.0,
        le=100.0,
        description="CO₂ sequestered per hectare after 5 years (baseline scenario, tonnes CO₂/ha)."
    )
    baseline_CO2_add_t_per_ha_per_y_post_5: float = Field(
        0.5,
        ge=0.0,
        le=20.0,
        description="Annual CO₂ sequestered per hectare after year 5 (baseline, tonnes CO₂/ha/year)."
    )
    field_ops_cost_eur_per_ha: float = Field(
        80.0,
        ge=0.0,
        le=10000.0,
        description="Field operations cost per hectare for plate application (EUR/ha)."
    )
    monitoring_cost_eur_per_ha_per_y: float = Field(
        10.0,
        ge=0.0,
        le=1000.0,
        description="Annual monitoring cost per hectare (EUR/ha/year)."
    )

class LaborParams(BaseModel):
    min_automation_employees: int = Field(
        3,
        ge=1,
        le=100,
        description="Minimum number of employees required for automated operations (e.g., maintenance, supervision)."
    )
    jobs_per_shift_low: int = Field(
        3,
        ge=1,
        le=100,
        description="Minimum number of jobs required per shift during low activity or high automation."
    )
    jobs_per_shift_high: int = Field(
        50,
        ge=1,
        le=500,
        description="Maximum number of jobs required per shift during peak activity or low automation."
    )
    shifts_per_day: int = Field(
        3,
        ge=1,
        le=3,
        description="Number of work shifts per day (typically 1–4)."
    )

class ProfitAllocation(BaseModel):
    to_farmers: float = Field(0.10, ge=0, le=100, description="Social Equity for farming communities")      #Regional 
    to_employees: float = Field(0.10, ge=0, le=100, description="Social Equity for Employees in the new economy")    #Social
    to_company: float = Field(0.30, ge=0, le=100, description="Equity for Consortium (PauwMyco)")      #International
    to_investors: float = Field(0.50 , ge=0, le=100, description="Equity for international investment ")   #Profitable
    
    
    @field_validator("to_farmers","to_employees","to_company","to_investors", mode="after")
    @classmethod
    def _non_negative(cls, v: float) -> float:
        assert v >= 0.0, "Allocations must be non-negative"
        return v
    @field_validator("to_investors", mode="after")
    @classmethod
    def _sum_to_one(cls, v, info):
        data = info.data
        total = data.get("to_farmers",0)+data.get("to_employees",0)+data.get("to_company",0)+v
        assert abs(total-1.0) < 1e-6, f"Allocations must sum to 1.0, got {total:.6f}"
        return v

class InvestorParams(BaseModel):
    coinvest_share: float = Field(
        0.20,
        ge=0.0,
        le=1.0,
        description="Fraction of total investment provided by coinvestors (0–1)."
    )

class Scenario(BaseModel):
    """A complete set of parameters describing a Paulownia project.

    The scenario groups together all parameter objects.  This makes it
    straightforward to serialise and restore the entire state from a
    JSON file.  Additional stages can be added by adding new fields.
    """

    years: int = Field(
        20,
        ge=1,
        le=100,
        description="Total duration of the project scenario (years)."
    )
    n_hectares: int = Field(
        1,
        ge=1,
        le=100_000,
        description="Number of hectares included in the project."
    )
    purpose: Literal["soil_regeneration", "wood_harvest"] = Field(
        "wood_harvest",
        description="Main project purpose: 'soil_regeneration' or 'wood_harvest'."
    )
    harvest_cycle_years: int = Field(
        3,
        ge=1,
        le=50,
        description="Length of each harvest cycle (years)."
    )
    trees_per_hectare: int = Field(
        500,
        ge=1,
        le=10_000,
        description="Number of trees planted per hectare."
    )
    seedling_price_per_tree: float = Field(
        9.10,
        ge=0.0,
        le=100.0,
        description="Price per tree seedling (EUR/tree)."
    )
    water_need_m3_per_ha_per_year: float = Field(
        760.0,
        ge=0.0,
        le=10_000.0,
        description="Annual water requirement per hectare (m³/ha/year)."
    )
    water_price_per_m3: float = Field(
        1.20,
        ge=0.0,
        le=100.0,
        description="Price of irrigation water (EUR/m³)."
    )
    wood_yield_m3_per_tree_per_cycle: float = Field(
        0.5,
        ge=0.0,
        le=10.0,
        description="Wood yield per tree per harvest cycle (m³/tree/cycle)."
    )
    wood_price_per_m3: float = Field(
        220.0,
        ge=0.0,
        le=10_000.0,
        description="Market price for harvested wood (EUR/m³)."
    )
    co2_price_per_tonne: float = Field(
        45.0,
        ge=0.0,
        le=1_000.0,
        description="Market price for CO₂ credits (EUR/tonne CO₂)."
    )
    discount_rate: float = Field(
        0.10,
        ge=0.0,
        le=1.0,
        description="Discount rate for net present value calculations (fraction, 0–1)."
    )
    above_partition: Dict[str, float] = Field(
        default_factory=lambda: {"crown": 0.35, "trunk": 0.65},
        description="Partitioning of above-ground biomass into 'crown' and 'trunk' fractions (must sum to 1.0)."
    )
    below_vs_above_ratio: float = Field(
        0.35,
        ge=0.0,
        le=10.0,
        description="Ratio of below-ground to above-ground biomass."
    )
    discard_frac: Dict[str, float] = Field(
        default_factory=lambda: {"wood": 0.2, "crown": 0.3, "roots": 0.1},
        description="Fraction of each biomass component discarded: keys must include 'wood', 'crown', 'roots'."
    )
    other_costs_per_ha_per_year: float = Field(
        150.0,
        ge=0.0,
        le=10_000.0,
        description="Other annual costs per hectare (EUR/ha/year)."
    )
    other_rev_per_ha_per_year: float = Field(
        0.0,
        ge=0.0,
        le=10_000.0,
        description="Other annual revenues per hectare (EUR/ha/year)."
    )
    biomass_density_kg_per_m3: float = Field(
        350.0,
        ge=10.0,
        le=2_000.0,
        description="Bulk density of harvested biomass (kg/m³)."
    )
    co2_curve: List[CO2Segment] = Field(
        default_factory=lambda: [
            CO2Segment(start_year=1, end_year=2, start_value_kg_per_tree=0.36, end_value_kg_per_tree=0.36),
            CO2Segment(start_year=2, end_year=5, start_value_kg_per_tree=0.36, end_value_kg_per_tree=4.54),
            CO2Segment(start_year=5, end_year=50, start_value_kg_per_tree=5.0, end_value_kg_per_tree=5.0),
        ],
        description="Piecewise linear segments describing annual CO₂ fixation per tree."
    )
    # Nested parameter objects
    logistics: LogisticsParams = Field(default_factory=lambda: LogisticsParams())
    extraction: ExtractionParams = Field(default_factory=lambda: ExtractionParams())
    substrate: SubstrateParams = Field(default_factory=lambda: SubstrateParams())
    plates: PlateParams = Field(default_factory=lambda: PlateParams())
    scale: ProcessScaleParams = Field(default_factory=lambda: ProcessScaleParams())
    eol: EoLParams = Field(default_factory=lambda: EoLParams())
    labor: LaborParams = Field(default_factory=lambda: LaborParams())
    allocation: ProfitAllocation = Field(default_factory=lambda: ProfitAllocation())
    investors: InvestorParams = Field(default_factory=lambda: InvestorParams())

    @field_validator("above_partition")
    def partition_sums_to_one(cls, v):
        total = sum(v.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError("above_partition fractions must sum to 1.0")
        return v

    @field_validator("discard_frac")
    def discard_keys(cls, v):
        for key in ("wood", "crown", "roots"):
            if key not in v:
                raise ValueError(f"discard_frac must contain key {key}")
        return v