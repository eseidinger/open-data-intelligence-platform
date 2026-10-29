"""Build deterministic shared fixtures from the pinned PVGIS source snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timedelta, timezone
from math import fsum
from pathlib import Path
from typing import Any

from contractkit.canonical import canonical_bytes, load_json, sha256_hex


DATASET_ID = "energy-reference-wasserburg-am-inn-2024"
START = datetime(2024, 1, 1, tzinfo=timezone.utc)
END = datetime(2025, 1, 1, tzinfo=timezone.utc)
RETRIEVED_AT = "2026-10-10T14:06:57Z"
SOURCE_FILENAME = "pvgis-era5-wasserburg-2023.json"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def period() -> dict[str, str]:
    return {
        "start": utc_text(START),
        "endExclusive": utc_text(END),
        "step": "PT1H",
    }


def target_hours() -> list[datetime]:
    count = int((END - START) / timedelta(hours=1))
    return [START + timedelta(hours=index) for index in range(count)]


def pvgis_values(source: dict[str, Any]) -> list[float]:
    by_month_day_hour: dict[tuple[int, int, int], float] = {}
    for row in source["outputs"]["hourly"]:
        instant = datetime.strptime(row["time"], "%Y%m%d:%H%M")
        by_month_day_hour[(instant.month, instant.day, instant.hour)] = row["P"] / 1000

    assert len(by_month_day_hour) == 8760
    values: list[float] = []
    for instant in target_hours():
        key = (instant.month, instant.day, instant.hour)
        if instant.month == 2 and instant.day == 29:
            value = (
                by_month_day_hour[(2, 28, instant.hour)]
                + by_month_day_hour[(3, 1, instant.hour)]
            ) / 2
        else:
            value = by_month_day_hour[key]
        values.append(round(value, 6))
    return values


def series(schema_version: str, unit: str, values: list[float]) -> dict[str, Any]:
    return {
        "schemaVersion": schema_version,
        "unit": unit,
        "period": period(),
        "values": [
            {"start": utc_text(instant), "value": value}
            for instant, value in zip(target_hours(), values, strict=True)
        ],
    }


def load_shape() -> list[float]:
    weights: list[float] = []
    for instant in target_hours():
        weight = 0.45
        if 6 <= instant.hour <= 9:
            weight += 0.65
        if 11 <= instant.hour <= 14:
            weight += 0.20
        if 17 <= instant.hour <= 22:
            weight += 1.00
        if instant.weekday() >= 5:
            weight += 0.15
        if instant.month in {11, 12, 1, 2}:
            weight += 0.15
        weights.append(weight)

    total = fsum(weights)
    result = [round(weight / total, 12) for weight in weights]
    result[-1] = round(result[-1] + (1.0 - fsum(result)), 12)
    assert abs(fsum(result) - 1.0) <= 1e-12
    return result


def tariffs() -> tuple[list[float], list[float]]:
    imports: list[float] = []
    for instant in target_hours():
        if 17 <= instant.hour <= 21:
            imports.append(0.40)
        elif 7 <= instant.hour <= 16:
            imports.append(0.35)
        else:
            imports.append(0.30)
    return imports, [0.08] * len(imports)


def source(owner: str, reference: str) -> dict[str, Any]:
    return {
        "owner": owner,
        "reference": reference,
        "version": "1.0.0",
        "license": "CC-BY-4.0",
        "retrievedAt": RETRIEVED_AT,
    }


def component_catalog() -> dict[str, Any]:
    synthetic = source(
        "Energy System Configuration",
        "https://github.com/eseidinger/energy-system-configuration",
    )
    return {
        "schemaVersion": "energy-component-catalog/v1",
        "catalogVersion": "1.0.0",
        "currency": "EUR",
        "components": [
            {
                "componentId": "pv-standard-400",
                "type": "PV_MODULE",
                "displayName": "Synthetic standard 400 Wp module",
                "unitPriceEUR": 130,
                "available": True,
                "source": synthetic,
                "ratedPowerKWp": 0.4,
                "areaM2": 1.9,
            },
            {
                "componentId": "pv-premium-450",
                "type": "PV_MODULE",
                "displayName": "Synthetic premium 450 Wp module",
                "unitPriceEUR": 170,
                "available": True,
                "source": synthetic,
                "ratedPowerKWp": 0.45,
                "areaM2": 2.05,
            },
            {
                "componentId": "inverter-3kw",
                "type": "INVERTER",
                "displayName": "Synthetic 3 kW inverter",
                "unitPriceEUR": 800,
                "available": True,
                "source": synthetic,
                "acPowerKW": 3,
                "efficiencyFraction": 0.96,
            },
            {
                "componentId": "inverter-5kw",
                "type": "INVERTER",
                "displayName": "Synthetic 5 kW inverter",
                "unitPriceEUR": 1100,
                "available": True,
                "source": synthetic,
                "acPowerKW": 5,
                "efficiencyFraction": 0.97,
            },
            {
                "componentId": "battery-5kwh",
                "type": "BATTERY",
                "displayName": "Synthetic 5 kWh battery",
                "unitPriceEUR": 2800,
                "available": True,
                "source": synthetic,
                "usableCapacityKWh": 5,
                "maxChargePowerKW": 2.5,
                "maxDischargePowerKW": 2.5,
                "roundTripEfficiencyFraction": 0.90,
            },
            {
                "componentId": "battery-10kwh",
                "type": "BATTERY",
                "displayName": "Synthetic 10 kWh battery",
                "unitPriceEUR": 4800,
                "available": True,
                "source": synthetic,
                "usableCapacityKWh": 10,
                "maxChargePowerKW": 5,
                "maxDischargePowerKW": 5,
                "roundTripEfficiencyFraction": 0.92,
            },
        ],
    }


def byte_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_energy(source_path: Path, fixture_root: Path) -> dict[str, str]:
    fixture_dir = fixture_root / DATASET_ID
    raw_dir = fixture_dir / "source"
    raw_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, raw_dir / SOURCE_FILENAME)
    source_document = load_json(source_path)

    import_values, export_values = tariffs()
    artifacts = {
        "pv-yield": series(
            "energy-pv-yield/v1", "kWh/kWp", pvgis_values(source_document)
        ),
        "import-tariff": series(
            "energy-import-tariff/v1", "EUR/kWh", import_values
        ),
        "export-tariff": series(
            "energy-export-tariff/v1", "EUR/kWh", export_values
        ),
        "reference-load-shape": series(
            "energy-reference-load-shape/v1", "fraction", load_shape()
        ),
        "component-catalog": component_catalog(),
    }
    for artifact_id, document in artifacts.items():
        write_json(fixture_dir / "artifacts" / f"{artifact_id}.json", document)

    descriptors = []
    descriptor_data = [
        ("pv-yield", "PV_YIELD_PER_KWP", "kWh/kWp"),
        ("import-tariff", "IMPORT_TARIFF", "EUR/kWh"),
        ("export-tariff", "EXPORT_TARIFF", "EUR/kWh"),
        ("component-catalog", "COMPONENT_CATALOG", None),
        ("reference-load-shape", "REFERENCE_LOAD_SHAPE", "fraction"),
    ]
    for artifact_id, role, unit in descriptor_data:
        descriptor = {
            "artifactId": artifact_id,
            "role": role,
            "mediaType": "application/json",
            "sha256": sha256_hex(artifacts[artifact_id]),
            "path": f"artifacts/{artifact_id}",
        }
        if unit is not None:
            descriptor["unit"] = unit
        descriptors.append(descriptor)

    manifest = {
        "schemaVersion": "dataset-publication/v1",
        "datasetId": DATASET_ID,
        "version": "1.0.0",
        "status": "PUBLISHED",
        "schemaRef": "urn:portfolio:energy-configuration-input:v1",
        "metadata": {
            "regionCode": "DE-BY-09187182",
            "period": period(),
            "profileKind": "SYNTHETIC_CALENDAR_PROFILE",
            "pvSourceYear": 2023,
            "leapDayMethod": "hourly mean of 2023-02-28 and 2023-03-01",
        },
        "publishedAt": RETRIEVED_AT,
        "artifacts": descriptors,
        "quality": {
            "status": "PASS",
            "policyRef": "urn:portfolio:energy-quality:v1",
            "warnings": [
                {
                    "code": "synthetic_reference_profile",
                    "message": "The 2024 calendar profile uses PVGIS 2023 values and a derived leap day; it is not an observed 2024 series.",
                }
            ],
        },
        "provenance": [
            {
                "sourceId": "pvgis-era5-wasserburg-2023",
                "sourceOwner": "European Commission Joint Research Centre",
                "sourceVersion": "PVGIS 5.3 / PVGIS-ERA5 2023",
                "license": "PVGIS usage conditions; acknowledgement required",
                "retrievedAt": RETRIEVED_AT,
                "rawArtifactId": SOURCE_FILENAME,
                "transformationVersion": "build-fixtures/0.2.0",
            },
            {
                "sourceId": "synthetic-energy-inputs",
                "sourceOwner": "Energy System Configuration",
                "sourceVersion": "1.0.0",
                "license": "CC-BY-4.0",
                "retrievedAt": RETRIEVED_AT,
                "transformationVersion": "build-fixtures/0.2.0",
            },
        ],
    }
    write_json(fixture_dir / "manifest.json", manifest)
    write_json(
        fixture_dir / "provenance" / "pvgis-request.json",
        {
            "apiVersion": "5.3",
            "endpoint": "https://re.jrc.ec.europa.eu/api/v5_3/seriescalc",
            "parameters": {
                "lat": 48.0622,
                "lon": 12.2347,
                "startyear": 2023,
                "endyear": 2023,
                "pvcalculation": 1,
                "peakpower": 1,
                "loss": 0,
                "pvtechchoice": "crystSi",
                "mountingplace": "free",
                "angle": 35,
                "aspect": 0,
                "raddatabase": "PVGIS-ERA5",
                "outputformat": "json",
            },
            "retrievedAt": RETRIEVED_AT,
            "rawByteSha256": byte_sha256(source_path),
        },
    )
    return {
        "datasetId": DATASET_ID,
        "version": "1.0.0",
        "manifestSha256": sha256_hex(manifest),
        "sourceByteSha256": byte_sha256(source_path),
    }


def build_non_energy(fixture_root: Path) -> dict[str, str]:
    fixture_dir = fixture_root / "non-energy-mobility-counts-2024"
    artifact = {
        "schemaVersion": "mobility-counts/v1",
        "unit": "vehicles/hour",
        "values": [
            {"start": "2024-01-01T00:00:00Z", "value": 12},
            {"start": "2024-01-01T01:00:00Z", "value": 8},
        ],
    }
    write_json(fixture_dir / "artifacts" / "hourly-counts.json", artifact)
    manifest = {
        "schemaVersion": "dataset-publication/v1",
        "datasetId": "non-energy-mobility-counts-2024",
        "version": "1.0.0",
        "status": "PUBLISHED",
        "schemaRef": "urn:portfolio:mobility-counts:v1",
        "metadata": {"kind": "synthetic-domain-neutrality-proof"},
        "publishedAt": RETRIEVED_AT,
        "artifacts": [
            {
                "artifactId": "hourly-counts",
                "role": "HOURLY_COUNTS",
                "mediaType": "application/json",
                "unit": "vehicles/hour",
                "sha256": sha256_hex(artifact),
                "path": "artifacts/hourly-counts",
            }
        ],
        "quality": {
            "status": "PASS",
            "policyRef": "urn:portfolio:mobility-counts-quality:v1",
            "warnings": [],
        },
        "provenance": [
            {
                "sourceId": "synthetic-mobility-counts",
                "sourceOwner": "Energy System Configuration",
                "sourceVersion": "1.0.0",
                "license": "CC-BY-4.0",
                "retrievedAt": RETRIEVED_AT,
                "transformationVersion": "build-fixtures/0.2.0",
            }
        ],
    }
    write_json(fixture_dir / "manifest.json", manifest)
    return {
        "datasetId": "non-energy-mobility-counts-2024",
        "version": "1.0.0",
        "manifestSha256": sha256_hex(manifest),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pvgis_source", type=Path)
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path(__file__).parents[1] / "fixtures",
    )
    args = parser.parse_args()
    energy = build_energy(args.pvgis_source, args.fixture_root)
    non_energy = build_non_energy(args.fixture_root)
    write_json(args.fixture_root / "index.json", [energy, non_energy])


if __name__ == "__main__":
    main()
