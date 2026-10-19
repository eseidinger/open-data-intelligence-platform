from contractkit.canonical import load_json
from contractkit.simulation import simulate
from schema_support import ROOT


CASES = load_json(ROOT / "expected-results" / "simulation-cases.json")


def test_hand_calculated_simulation_cases() -> None:
    required_coverage = {
        "pv_clipping",
        "charge_efficiency",
        "discharge_efficiency",
        "charge_power_limit",
        "discharge_power_limit",
        "capacity_limit",
        "grid_import",
        "grid_export",
        "terminal_discarded_energy",
    }
    actual_coverage = {item for case in CASES for item in case["covers"]}
    assert required_coverage <= actual_coverage

    for case in CASES:
        assert simulate(case["inputs"]) == case["expected"], case["caseId"]
