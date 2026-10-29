"""Producer-compatible application emission profile for central workload logs."""

import itertools

import pytest
from jsonschema import Draft202012Validator, ValidationError

from schema_support import ROOT, load_document, load_schemas


SCHEMA = load_schemas()["platform-operational-envelope-v1.schema.json"]


def test_supported_operational_events_levels_and_optional_correlation():
    validator = Draft202012Validator(SCHEMA)
    for category, action, level in itertools.product(
        ("application", "request", "job"),
        ("started", "ready", "completed", "failed"),
        ("debug", "info", "warning", "error"),
    ):
        event = {"event": f"{category}.{action}", "level": level}
        validator.validate(event)
        for correlation in ("", "a" * 32, "01234567-89ab-cdef-0123-456789abcdef"):
            validator.validate({**event, "correlationId": correlation})


@pytest.mark.parametrize("mutation", [
    {"event": "optimization.succeeded"},
    {"event": "request.completed\n"},
    {"level": "INFO"},
    {"correlationId": "energy-reference-wasserburg-am-inn-2024"},
    {"correlationId": "a" * 32 + "\n"},
    {"correlationId": "A" * 32},
    {"correlationId": None},
    {"runId": "run_customer_example"},
    {"message": "customer input must remain outside central logs"},
    {"Authorization": "Bearer excluded"},
])
def test_emission_profile_rejects_invalid_values_and_domain_or_secret_fields(mutation):
    event = load_document(ROOT / "examples" / "platform-operational-envelope.json")
    event.update(mutation)
    with pytest.raises(ValidationError):
        Draft202012Validator(SCHEMA).validate(event)
