from datetime import datetime, timezone

from tools.build_fixtures import (
    component_catalog,
    load_shape,
    pvgis_values,
    series,
    tariffs,
)

from odip_worker.contract import validate, validate_energy_publication

SCHEMAS = {
    "PV_YIELD_PER_KWP": "energy-pv-yield-v1",
    "IMPORT_TARIFF": "energy-import-tariff-v1",
    "EXPORT_TARIFF": "energy-export-tariff-v1",
    "REFERENCE_LOAD_SHAPE": "energy-reference-load-shape-v1",
    "COMPONENT_CATALOG": "energy-component-catalog-v1",
}


def validate_profile(manifest, artifacts):
    calendar_year_hours(manifest["metadata"]["period"])
    for descriptor in manifest["artifacts"]:
        validate(SCHEMAS[descriptor["role"]], artifacts[descriptor["artifactId"]])
    validate_energy_publication(manifest, artifacts)


def calendar_year_hours(period):
    """DEC-08: annual optimization data spans January 1 to the next January 1 UTC."""
    start = datetime.fromisoformat(period["start"].replace("Z", "+00:00"))
    end = datetime.fromisoformat(period["endExclusive"].replace("Z", "+00:00"))
    if (
        period.get("step") != "PT1H"
        or start.tzinfo != timezone.utc
        or end.tzinfo != timezone.utc
        or start != datetime(start.year, 1, 1, tzinfo=timezone.utc)
        or end != datetime(start.year + 1, 1, 1, tzinfo=timezone.utc)
    ):
        raise ValueError("energy profiles require one complete UTC calendar year")
    return (end - start).days * 24


def reference_outputs(source_document):
    """Reproduce the accepted transformed 2023 PVGIS source on the 2024 calendar."""
    imports, exports = tariffs()
    return {
        "pv-yield": series(
            "energy-pv-yield/v1", "kWh/kWp", pvgis_values(source_document)
        ),
        "import-tariff": series("energy-import-tariff/v1", "EUR/kWh", imports),
        "export-tariff": series("energy-export-tariff/v1", "EUR/kWh", exports),
        "reference-load-shape": series(
            "energy-reference-load-shape/v1", "fraction", load_shape()
        ),
        "component-catalog": component_catalog(),
    }
