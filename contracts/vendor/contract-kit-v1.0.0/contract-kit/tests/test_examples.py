import copy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from schema_support import ROOT, load_document, load_schemas, schema_registry


EXAMPLE_DIR = ROOT / "examples"


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


def test_all_indexed_examples_validate() -> None:
    index = load_document(EXAMPLE_DIR / "index.json")
    available = validators()

    assert index
    for entry in index:
        validator = available[entry["schema"]]
        validator.validate(load_document(EXAMPLE_DIR / entry["document"]))


@pytest.mark.parametrize(
    ("filename", "mutation"),
    [
        ("pv-yield.json", lambda value: value.update(unit="kWh")),
        ("optimization-request.json", lambda value: value.update(extra="rejected")),
        (
            "optimization-result.json",
            lambda value: value["dataset"].update(manifestSha256="not-a-digest"),
        ),
    ],
)
def test_invalid_contract_examples_are_rejected(filename, mutation) -> None:
    index = load_document(EXAMPLE_DIR / "index.json")
    schema_id = next(item["schema"] for item in index if item["document"] == filename)
    value = copy.deepcopy(load_document(EXAMPLE_DIR / filename))
    mutation(value)

    with pytest.raises(ValidationError):
        validators()[schema_id].validate(value)
