"""Tests for download helpers.

These tests ensure that scenario serialisation and results export work
correctly.  They do not interact with Streamlit's download buttons but
verify that the JSON and CSV are well‑formed.
"""

import json

from core.params import Scenario
from core.sim_1_agriculture import run_sim


def test_scenario_json_roundtrip():
    scn = Scenario()
    data = json.loads(scn.model_dump_json())
    scn2 = Scenario.model_validate_json(json.dumps(data))
    assert scn == scn2


def test_results_csv_export():
    scn = Scenario(years=1)
    df_agro = run_sim(scn)
    csv_str = df_agro.to_csv(index=False)
    # ensure CSV has header line
    first_line = csv_str.splitlines()[0]
    assert "year" in first_line and "cashflow" in first_line