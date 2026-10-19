"""Semantic validation for the energy publication profile."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from math import fsum
from typing import Any

from .canonical import sha256_hex


ENERGY_SCHEMA_REF = "urn:portfolio:energy-configuration-input:v1"
LOAD_SHAPE_TOLERANCE = 1e-6
REQUIRED_ROLES = {
    "PV_YIELD_PER_KWP": ("energy-pv-yield/v1", "kWh/kWp"),
    "IMPORT_TARIFF": ("energy-import-tariff/v1", "EUR/kWh"),
    "EXPORT_TARIFF": ("energy-export-tariff/v1", "EUR/kWh"),
    "REFERENCE_LOAD_SHAPE": ("energy-reference-load-shape/v1", "fraction"),
    "COMPONENT_CATALOG": ("energy-component-catalog/v1", None),
}


class ProfileValidationError(ValueError):
    """Raised when documents are schema-valid but semantically inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileValidationError(message)


def _utc_instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    _require(parsed.tzinfo == timezone.utc, f"timestamp is not UTC: {value}")
    return parsed


def _validate_series(document: Mapping[str, Any]) -> list[str]:
    period = document["period"]
    start = _utc_instant(period["start"])
    end = _utc_instant(period["endExclusive"])
    _require(end > start, "series period must have positive duration")

    duration = end - start
    _require(
        duration % timedelta(hours=1) == timedelta(0),
        "series period must contain whole UTC hours",
    )
    expected_count = duration // timedelta(hours=1)
    values = document["values"]
    _require(
        len(values) == expected_count,
        f"series has {len(values)} values; expected {expected_count}",
    )

    expected = start
    timestamps: list[str] = []
    for index, item in enumerate(values):
        actual = _utc_instant(item["start"])
        _require(
            actual == expected,
            f"series interval {index} starts at {item['start']}; expected {expected.isoformat()}",
        )
        timestamps.append(item["start"])
        expected += timedelta(hours=1)
    return timestamps


def _validate_catalog(document: Mapping[str, Any]) -> None:
    components = document["components"]
    component_ids = [component["componentId"] for component in components]
    _require(len(component_ids) == len(set(component_ids)), "component IDs must be unique")

    counts = Counter(component["type"] for component in components)
    for component_type in ("PV_MODULE", "INVERTER", "BATTERY"):
        _require(counts[component_type] >= 1, f"catalog has no {component_type} model")
        _require(
            counts[component_type] <= 20,
            f"catalog has more than 20 {component_type} models",
        )


def validate_energy_publication(
    manifest: Mapping[str, Any], artifacts: Mapping[str, Mapping[str, Any]]
) -> None:
    """Validate cross-document energy profile rules and canonical digests.

    Inputs are expected to have passed their JSON Schemas first. ``artifacts``
    is keyed by manifest ``artifactId``.
    """

    _require(manifest["schemaRef"] == ENERGY_SCHEMA_REF, "unexpected energy schemaRef")
    descriptors: Sequence[Mapping[str, Any]] = manifest["artifacts"]
    artifact_ids = [item["artifactId"] for item in descriptors]
    roles = [item["role"] for item in descriptors]
    paths = [item["path"] for item in descriptors]

    _require(len(artifact_ids) == len(set(artifact_ids)), "artifact IDs must be unique")
    _require(len(roles) == len(set(roles)), "artifact roles must be unique")
    _require(len(paths) == len(set(paths)), "artifact paths must be unique")
    _require(set(roles) == set(REQUIRED_ROLES), "energy publication must contain exactly five required roles")
    _require(set(artifacts) == set(artifact_ids), "provided artifacts must match manifest artifact IDs")

    manifest_period = manifest["metadata"].get("period")
    _require(manifest_period is not None, "energy publication metadata requires period")

    common_timestamps: list[str] | None = None
    for descriptor in descriptors:
        role = descriptor["role"]
        document = artifacts[descriptor["artifactId"]]
        expected_schema, expected_unit = REQUIRED_ROLES[role]
        _require(document["schemaVersion"] == expected_schema, f"{role} has unexpected schemaVersion")
        _require(descriptor["mediaType"] == "application/json", f"{role} must be JSON")
        _require(descriptor.get("unit") == expected_unit, f"{role} has unexpected manifest unit")
        _require(
            descriptor["path"] == f"artifacts/{descriptor['artifactId']}",
            f"{role} path must match its artifact ID",
        )
        _require(
            descriptor["sha256"] == sha256_hex(document),
            f"{role} digest does not match canonical artifact bytes",
        )

        if role == "COMPONENT_CATALOG":
            _validate_catalog(document)
            continue

        _require(document["period"] == manifest_period, f"{role} period differs from manifest")
        timestamps = _validate_series(document)
        if common_timestamps is None:
            common_timestamps = timestamps
        else:
            _require(timestamps == common_timestamps, f"{role} intervals are not aligned")

        if role == "REFERENCE_LOAD_SHAPE":
            total = fsum(item["value"] for item in document["values"])
            _require(
                abs(total - 1.0) <= LOAD_SHAPE_TOLERANCE,
                f"reference load shape sums to {total}; expected 1 within {LOAD_SHAPE_TOLERANCE}",
            )
