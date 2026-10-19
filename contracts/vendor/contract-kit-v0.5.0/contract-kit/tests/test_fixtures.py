import hashlib
from math import fsum
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from contractkit.canonical import canonical_bytes, load_json, sha256_hex
from contractkit.validation import validate_energy_publication
from schema_support import ROOT, load_schemas, schema_registry


FIXTURE_DIR = ROOT / "fixtures"
ENERGY_DIR = FIXTURE_DIR / "energy-reference-wasserburg-am-inn-2024"
NON_ENERGY_DIR = FIXTURE_DIR / "non-energy-mobility-counts-2024"


def validators() -> dict[str, Draft202012Validator]:
    schemas = load_schemas()
    registry = schema_registry(schemas)
    return {
        schema["$id"]: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for schema in schemas.values()
    }


def energy_documents() -> tuple[dict, dict[str, dict]]:
    manifest = load_json(ENERGY_DIR / "manifest.json")
    artifacts = {
        descriptor["artifactId"]: load_json(
            ENERGY_DIR / "artifacts" / f"{descriptor['artifactId']}.json"
        )
        for descriptor in manifest["artifacts"]
    }
    return manifest, artifacts


def test_energy_fixture_is_complete_and_valid() -> None:
    manifest, artifacts = energy_documents()
    available = validators()
    available["urn:portfolio:dataset-publication:v1"].validate(manifest)

    schema_by_version = {
        "energy-pv-yield/v1": "urn:portfolio:energy:pv-yield:v1",
        "energy-import-tariff/v1": "urn:portfolio:energy:import-tariff:v1",
        "energy-export-tariff/v1": "urn:portfolio:energy:export-tariff:v1",
        "energy-reference-load-shape/v1": "urn:portfolio:energy:reference-load-shape:v1",
        "energy-component-catalog/v1": "urn:portfolio:energy:component-catalog:v1",
    }
    for document in artifacts.values():
        available[schema_by_version[document["schemaVersion"]]].validate(document)
    validate_energy_publication(manifest, artifacts)

    assert len(artifacts["pv-yield"]["values"]) == 8784
    assert len(artifacts["reference-load-shape"]["values"]) == 8784
    assert artifacts["pv-yield"]["values"][0]["start"] == "2024-01-01T00:00:00Z"
    assert artifacts["pv-yield"]["values"][-1]["start"] == "2024-12-31T23:00:00Z"
    assert abs(
        fsum(item["value"] for item in artifacts["reference-load-shape"]["values"])
        - 1.0
    ) <= 1e-12


def test_pvgis_snapshot_and_leap_day_derivation_are_pinned() -> None:
    source_path = ENERGY_DIR / "source" / "pvgis-era5-wasserburg-2023.json"
    source = load_json(source_path)
    request = load_json(ENERGY_DIR / "provenance" / "pvgis-request.json")
    _, artifacts = energy_documents()

    assert len(source["outputs"]["hourly"]) == 8760
    assert source["inputs"]["meteo_data"]["radiation_db"] == "PVGIS-ERA5"
    assert request["rawByteSha256"] == hashlib.sha256(source_path.read_bytes()).hexdigest()

    source_power = {
        row["time"]: row["P"] / 1000 for row in source["outputs"]["hourly"]
    }
    pv = {item["start"]: item["value"] for item in artifacts["pv-yield"]["values"]}
    for hour in range(24):
        expected = round(
            (
                source_power[f"20230228:{hour:02d}30"]
                + source_power[f"20230301:{hour:02d}30"]
            )
            / 2,
            6,
        )
        assert pv[f"2024-02-29T{hour:02d}:00:00Z"] == expected


def test_fixture_digests_and_transfer_limits() -> None:
    index = {item["datasetId"]: item for item in load_json(FIXTURE_DIR / "index.json")}
    for fixture_dir in (ENERGY_DIR, NON_ENERGY_DIR):
        manifest_path = fixture_dir / "manifest.json"
        manifest = load_json(manifest_path)
        assert manifest_path.read_bytes() == canonical_bytes(manifest)
        assert index[manifest["datasetId"]]["manifestSha256"] == sha256_hex(manifest)
        assert manifest_path.stat().st_size <= 1024 * 1024

        total_size = 0
        for descriptor in manifest["artifacts"]:
            path = fixture_dir / f"{descriptor['path']}.json"
            document = load_json(path)
            assert path.read_bytes() == canonical_bytes(document)
            assert descriptor["sha256"] == sha256_hex(document)
            assert path.stat().st_size <= 10 * 1024 * 1024
            total_size += path.stat().st_size
        assert total_size <= 50 * 1024 * 1024


def test_non_energy_fixture_uses_generic_manifest() -> None:
    manifest = load_json(NON_ENERGY_DIR / "manifest.json")
    validators()["urn:portfolio:dataset-publication:v1"].validate(manifest)
    assert manifest["schemaRef"] == "urn:portfolio:mobility-counts:v1"
    assert {artifact["role"] for artifact in manifest["artifacts"]} == {
        "HOURLY_COUNTS"
    }
