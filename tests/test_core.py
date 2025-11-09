"""Unit tests for core modules.

These tests verify the correctness of the basic computations performed
by the modelling modules.  They cover piecewise CO₂ interpolation, the
harvest schedule, logistics calculations, extraction yields and
composition, plate energy use and end‑of‑life conversions.
"""

import math

import pandas as pd

from core.params import Scenario, CO2Segment, LogisticsParams, ExtractionParams, SubstrateParams, PlateParams, ProcessScaleParams, EoLParams
from core.sim_1_agriculture import co2_fixation_per_tree, run_sim
from core.sim_2_production import compute_logistics, compute_extraction, compute_plates
from core.sim_3_eol import coverage_from_plates, soil_response_per_ha


def test_co2_piecewise_interpolation():
    segs = [
        CO2Segment(start_year=1, end_year=2, start_value_kg_per_tree=0.5, end_value_kg_per_tree=1.0),
        CO2Segment(start_year=2, end_year=5, start_value_kg_per_tree=1.0, end_value_kg_per_tree=2.0),
        CO2Segment(start_year=5, end_year=10, start_value_kg_per_tree=2.0, end_value_kg_per_tree=2.0)
    ]
    # year 1 exactly matches start value
    assert math.isclose(co2_fixation_per_tree(1, segs), 0.5)
    # mid of first segment (year 1.5)
    assert math.isclose(co2_fixation_per_tree(2, segs), 0.75)
    # year 2 exactly end of first segment (start of second)
    assert math.isclose(co2_fixation_per_tree(3, segs), 1.0)
    # mid of second segment (year 3.5)
    assert math.isclose(co2_fixation_per_tree(5, segs), 1.5)
    # beyond last segment
    assert math.isclose(co2_fixation_per_tree(10, segs), 2.0)


def test_harvest_schedule():
    scn = Scenario(years=5, harvest_cycle_years=3, purpose="wood_harvest", trees_per_hectare=1)
    df = run_sim(scn)
    # wood harvested in year 3 only
    assert df.loc[df["year"] == 3, "wood_m3"].iloc[0] > 0
    assert df.loc[df["year"] == 4, "wood_m3"].iloc[0] == 0
    # salable wood is 80% of total (discard_frac default wood=0.2)
    total_wood = df.loc[df["year"] == 3, "wood_m3"].iloc[0]
    salable = df.loc[df["year"] == 3, "wood_m3_salable"].iloc[0]
    assert math.isclose(salable, total_wood * 0.8)


def test_logistics_calculation():
    lp = LogisticsParams(trailer_payload_t=10, transport_distance_km=100, transport_cost_per_km=2.0, backhaul_utilization=0.5, truck_emission_kg_per_tkm=0.1, loading_loss_frac=0.1)
    scale = ProcessScaleParams(inbound_mass_t_per_year=25, root_fraction_of_inbound=0.3)
    df_log = compute_logistics(Scenario(), lp, scale)
    # check number of trips (ceil(25/10) = 3)
    assert df_log.loc[0, "n_trips"] == 3
    # tkm = 25 * 100 = 2500
    assert math.isclose(df_log.loc[0, "tkm"], 2500)
    # transport cost: 100 km * 2 € * 3 trips * 0.5 (after backhaul) = 300
    assert math.isclose(df_log.loc[0, "transport_cost_eur"], 300)
    # transport CO2: 0.1 kg/tkm * 2500 = 250 kg -> 0.25 t
    assert math.isclose(df_log.loc[0, "transport_co2_t"], 0.25)
    # handling loss: 25 t * 0.1 = 2.5 t
    assert math.isclose(df_log.loc[0, "handling_loss_t"], 2.5)
    # net inbound: 22.5 t
    assert math.isclose(df_log.loc[0, "inbound_net_t"], 22.5)


def test_extraction_composition_and_revenue():
    ep = ExtractionParams(sell_crude_extract=False)
    # roots_in_t = 10
    df_ext = compute_extraction(Scenario(), ep, 10)
    # yield fractions: fibre=0.55, extract=0.45
    assert math.isclose(df_ext.loc[0, "root_fiber_t"], 5.5)
    assert math.isclose(df_ext.loc[0, "extract_t"], 4.5)
    # crude vs purified: here purified -> revenue = oleic + theobromine
    oleic_kg = 4.5 * 1000 * 0.35 * ep.purification_yield
    theo_kg = 4.5 * 1000 * 0.34 * ep.purification_yield
    expected_rev = oleic_kg * ep.price_oleic_eur_per_kg + theo_kg * ep.price_theobromine_eur_per_kg
    assert math.isclose(df_ext.loc[0, "rev_extract"], expected_rev)


def test_plate_energy_and_co2():
    pp = PlateParams(solar_share=0.1, energy_kWh_per_100_plates=4.0, grid_emission_kg_per_kWh=0.5)
    df_pl = compute_plates(pp, wet_substrate_t=1.0, loss_frac=0.0, price_eur=1.0)
    # wet substrate 1 t -> kg = 1000 / 3.7 ≈ 270.27 plates
    plates = (1.0 * 1000) / 3.7
    assert math.isclose(df_pl.loc[0, "plates"], plates)
    # energy: plates/100 * 4 kWh
    expected_energy = plates / 100 * 4.0
    assert math.isclose(df_pl.loc[0, "E_plates_kWh"], expected_energy)
    # scope2 CO2: energy * 0.5 kg/kWh -> /1000 to convert to t
    expected_co2 = expected_energy * 0.5 / 1000
    assert math.isclose(df_pl.loc[0, "co2_scope2_plates_t"], expected_co2)


def test_eol_geometry_conversion():
    eol = EoLParams(recovered_plate_frac=1.0, layer_thickness_m=0.02, compaction_ratio=1.0)
    pp = PlateParams()
    # one plate
    df_cover = coverage_from_plates(1.0, pp, eol)
    # area per plate: volume 1*1*0.06 = 0.06 m3 / 0.02 m thickness = 3 m2 -> 0.0003 ha
    area = (pp.plate_len_m * pp.plate_wid_m * pp.plate_thk_m) / eol.layer_thickness_m / 10_000
    assert math.isclose(df_cover.loc[0, "cover_area_ha_material_cap"], area)


def test_soil_response_curve():
    # check piecewise shape: at year 5 equals after5, at year 6 increases by post rate
    eol = EoLParams(treated_CO2_add_t_per_ha_after_5y=4.0, treated_CO2_add_t_per_ha_per_y_post_5=1.7)
    year5 = soil_response_per_ha(5, eol.treated_CO2_add_t_per_ha_after_5y, eol.treated_CO2_add_t_per_ha_per_y_post_5)
    assert math.isclose(year5, 4.0)
    year6 = soil_response_per_ha(6, eol.treated_CO2_add_t_per_ha_after_5y, eol.treated_CO2_add_t_per_ha_per_y_post_5)
    assert math.isclose(year6, 4.0 + 1.7)