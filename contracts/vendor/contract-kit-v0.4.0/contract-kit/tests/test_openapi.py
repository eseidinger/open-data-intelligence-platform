from pathlib import Path
from typing import Any

import yaml
from openapi_spec_validator import validate

from schema_support import ROOT


OPENAPI_DIR = ROOT / "openapi"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as source:
        return yaml.safe_load(source)


def omit_external_schemas(value: Any) -> Any:
    """Leave external schema graph validation to the JSON Schema test suite.

    openapi-spec-validator resolves file references but has no registry hook for
    the stable URN references used inside those schemas.
    """

    if isinstance(value, dict):
        if str(value.get("$ref", "")).startswith("../schemas/"):
            return {}
        return {key: omit_external_schemas(item) for key, item in value.items()}
    if isinstance(value, list):
        return [omit_external_schemas(item) for item in value]
    return value


def test_all_openapi_descriptions_validate() -> None:
    descriptions = sorted(OPENAPI_DIR.glob("*.yaml"))
    assert {path.name for path in descriptions} == {
        "odip-publication-v1.yaml",
        "vef-optimization-v1.yaml",
    }

    for path in descriptions:
        validate(omit_external_schemas(load_yaml(path)), base_uri=path.as_uri())


def test_all_external_schema_references_exist() -> None:
    for path in sorted(OPENAPI_DIR.glob("*.yaml")):
        description = load_yaml(path)

        def check(value: Any) -> None:
            if isinstance(value, dict):
                reference = str(value.get("$ref", ""))
                if reference.startswith("../schemas/"):
                    assert (path.parent / reference).resolve().is_file()
                for item in value.values():
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)

        check(description)


def test_operation_ids_are_unique_across_contracts() -> None:
    operation_ids: list[str] = []
    for path in sorted(OPENAPI_DIR.glob("*.yaml")):
        description = load_yaml(path)
        for path_item in description["paths"].values():
            for method, operation in path_item.items():
                if method in {"get", "post", "put", "patch", "delete"}:
                    operation_ids.append(operation["operationId"])

    assert len(operation_ids) == len(set(operation_ids))
