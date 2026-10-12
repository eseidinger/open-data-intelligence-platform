from odip_worker.contract import KIT, canonical_bytes, load_json, validate, validate_energy_publication
from tools.build_fixtures import pvgis_values, series, load_shape, tariffs, component_catalog

SCHEMAS = {
    "PV_YIELD_PER_KWP": "energy-pv-yield-v1",
    "IMPORT_TARIFF": "energy-import-tariff-v1",
    "EXPORT_TARIFF": "energy-export-tariff-v1",
    "REFERENCE_LOAD_SHAPE": "energy-reference-load-shape-v1",
    "COMPONENT_CATALOG": "energy-component-catalog-v1",
}

def validate_profile(manifest, artifacts):
    for descriptor in manifest["artifacts"]:
        validate(SCHEMAS[descriptor["role"]], artifacts[descriptor["artifactId"]])
    validate_energy_publication(manifest, artifacts)

def reference_outputs(source_document):
    """Reproduce the accepted transformed 2023 PVGIS source on the 2024 calendar."""
    imports, exports = tariffs()
    return {
        "pv-yield": series("energy-pv-yield/v1", "kWh/kWp", pvgis_values(source_document)),
        "import-tariff": series("energy-import-tariff/v1", "EUR/kWh", imports),
        "export-tariff": series("energy-export-tariff/v1", "EUR/kWh", exports),
        "reference-load-shape": series("energy-reference-load-shape/v1", "fraction", load_shape()),
        "component-catalog": component_catalog(),
    }
