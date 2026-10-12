from decimal import Decimal

from jsonschema import Draft202012Validator, FormatChecker

from contractkit.canonical import canonical_bytes, load_json
from contractkit.optimization import optimize_reference
from schema_support import ROOT, load_schemas, schema_registry


ENERGY_DIR = ROOT / "fixtures" / "energy-reference-wasserburg-am-inn-2024"
EXPECTED_PATH = ROOT / "expected-results" / "optimization-reference.json"


def validator(schema_id: str) -> Draft202012Validator:
    schemas = load_schemas()
    registry = schema_registry(schemas)
    schema = next(item for item in schemas.values() if item["$id"] == schema_id)
    return Draft202012Validator(
        schema,
        registry=registry,
        format_checker=FormatChecker(),
    )


def fixture_documents() -> tuple[dict, dict[str, dict]]:
    manifest = load_json(ENERGY_DIR / "manifest.json")
    artifacts = {
        descriptor["artifactId"]: load_json(
            ENERGY_DIR / "artifacts" / f"{descriptor['artifactId']}.json"
        )
        for descriptor in manifest["artifacts"]
    }
    return manifest, artifacts


def test_reference_optimization_matches_fixed_expected_result() -> None:
    expected = load_json(EXPECTED_PATH)
    manifest, artifacts = fixture_documents()

    assert optimize_reference(expected["request"], manifest, artifacts) == expected
    assert EXPECTED_PATH.read_bytes() == canonical_bytes(expected)


def test_expected_candidates_and_result_validate() -> None:
    expected = load_json(EXPECTED_PATH)
    request_validator = validator("urn:portfolio:energy:optimization-request:v1")
    candidate_validator = validator("urn:portfolio:energy:candidate:v1")
    result_validator = validator("urn:portfolio:energy:optimization-result:v1")

    request_validator.validate(expected["request"])
    result_validator.validate(expected["result"])
    for candidate in expected["candidates"]:
        candidate_validator.validate(candidate)


def test_configuration_set_constraints_and_ranking_are_exact() -> None:
    expected = load_json(EXPECTED_PATH)
    candidates = expected["candidates"]
    by_id = {item["configurationId"]: item for item in candidates}

    assert len(candidates) == len(by_id) == 252
    assert expected["result"]["evaluatedCandidateCount"] == 252
    assert expected["result"]["feasibleCandidateCount"] == 194
    assert len(expected["ranking"]) == 194
    assert set(expected["ranking"]) == {
        item["configurationId"] for item in candidates if item["feasible"]
    }
    assert expected["result"]["recommendedConfigurationId"] == expected["ranking"][0]
    assert expected["ranking"][0] == (
        "pv-standard-400-q18-inverter-5kw-battery-10kwh-q1"
    )

    failed_codes = {
        constraint["code"]
        for candidate in candidates
        for constraint in candidate["constraints"]
        if constraint["status"] == "FAIL"
    }
    assert failed_codes == {"max_initial_investment", "min_self_sufficiency"}

    ranking_keys = [
        (
            Decimal(str(by_id[item]["metrics"]["annualizedCostEUR"])),
            Decimal(str(by_id[item]["metrics"]["initialInvestmentEUR"])),
            item,
        )
        for item in expected["ranking"]
    ]
    assert ranking_keys == sorted(ranking_keys)


def test_candidate_energy_and_money_serialization() -> None:
    expected = load_json(EXPECTED_PATH)
    for candidate in expected["candidates"]:
        metrics = candidate["metrics"]
        assert abs(
            metrics["selfSufficiency"]
            - (1 - metrics["gridImportKWh"] / metrics["annualDemandKWh"])
        ) <= 1e-9
        assert abs(
            metrics["onSiteSolarUseKWh"]
            - (metrics["annualDemandKWh"] - metrics["gridImportKWh"])
        ) <= 1e-6
        for field in ("initialInvestmentEUR", "annualizedCostEUR"):
            assert Decimal(str(metrics[field])).as_tuple().exponent >= -2
