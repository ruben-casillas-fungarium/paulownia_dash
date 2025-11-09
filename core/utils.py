# MIT License
from __future__ import annotations
import hashlib, json
from .params import Scenario
from typing import Any, Dict



def scenario_hash(scn: Scenario) -> str:
    """Compute a stable hash for a Scenario.

    Serialises the scenario to JSON (with sorted keys) and computes a
    SHA256 hash.  Used to identify unique scenarios for caching.

    Parameters
    ----------
    scn:
        Scenario instance.

    Returns
    -------
    str
        Hexadecimal string representation of the hash.
    """
    scn_json = scn.model_dump(mode="json", exclude_none=True)
    # ensure deterministic key ordering
    payload = json.dumps(scn_json, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ha_to_m2(ha: float) -> float:
    """Convert hectares to square metres."""
    return ha * 10_000.0


def m2_to_ha(m2: float) -> float:
    """Convert square metres to hectares."""
    return m2 / 10_000.0


def kg_to_tonnes(kg: float) -> float:
    """Convert kilograms to metric tonnes."""
    return kg / 1000.0


def tonnes_to_kg(t: float) -> float:
    """Convert metric tonnes to kilograms."""
    return t * 1000.0