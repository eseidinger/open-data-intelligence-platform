from jsonschema import Draft202012Validator

from schema_support import load_schemas, schema_registry


def test_all_schemas_are_valid_draft_2020_12() -> None:
    schemas = load_schemas()

    assert schemas
    for schema in schemas.values():
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].startswith("urn:portfolio:")
        Draft202012Validator.check_schema(schema)


def test_all_schema_ids_are_unique_and_resolvable() -> None:
    schemas = load_schemas()
    identifiers = [schema["$id"] for schema in schemas.values()]
    registry = schema_registry(schemas)

    assert len(identifiers) == len(set(identifiers))
    for identifier in identifiers:
        assert registry.get(identifier) is not None
