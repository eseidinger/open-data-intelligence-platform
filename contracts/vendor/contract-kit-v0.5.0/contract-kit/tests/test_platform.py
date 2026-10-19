"""Offline shape and cross-contract checks for the pinned hosted profile."""

import copy
from urllib.parse import urlsplit

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from schema_support import ROOT, load_document, load_schemas, schema_registry


PLATFORM = ROOT / "platform"


def example(name):
    return load_document(PLATFORM / "examples" / f"{name}.json")


def input_validator(name):
    schema = load_document(PLATFORM / "upstream-inputs.schema.json")
    return Draft202012Validator({**schema, "$ref": f"#/$defs/{name}"})


def matches(policy, path, method):
    method = "GET" if method == "HEAD" else method
    result = []
    for route in policy["routes"]:
        match = route["match"]
        prefix = match.get("pathPrefix", "").rstrip("/")
        path_matches = path == match["path"] if "path" in match else (
            not prefix or path == prefix or path.startswith(prefix + "/")
        )
        if method in match["methods"] and path_matches:
            result.append(route)
    return result


def test_pinned_platform_input_schemas_and_examples():
    schema = load_document(PLATFORM / "upstream-inputs.schema.json")
    Draft202012Validator.check_schema(schema)
    index = load_document(PLATFORM / "examples.json")
    assert {p.name for p in (PLATFORM / "examples").glob("*.json")} == {
        entry["document"].split("/")[-1] for entry in index
    }
    for entry in index:
        input_validator(entry["schema"]).validate(load_document(PLATFORM / entry["document"]))


@pytest.mark.parametrize(("name", "schema", "mutation"), [
    ("odip-access-policy", "PolicyCreate", lambda v: v.update(oidcClientId="odip-api")),
    ("odip-access-policy", "PolicyCreate", lambda v: v["routes"][0]["authentication"].update(mode="none")),
    ("vef-odip-service-request", "ServiceRequest", lambda v: v.update(projectWideCredential=False)),
    ("vef-governance", "Governance", lambda v: v.update(maximumDataClassification="Restricted")),
    ("vef-application", "ApplicationEnvelopeV1Alpha2", lambda v: v["spec"].update(accessPolicy={})),
])
def test_obsolete_or_unsupported_platform_inputs_fail(name, schema, mutation):
    value = copy.deepcopy(example(name))
    mutation(value)
    with pytest.raises(ValidationError):
        input_validator(schema).validate(value)


def test_public_api_operations_have_one_matching_policy_with_consistent_auth():
    for project, filename, mode, security in [
        ("odip", "odip-publication-v1.yaml", "bearer-token", "platformBearer"),
        ("vef", "vef-optimization-v1.yaml", "browser-session", "platformSession"),
    ]:
        description = yaml.safe_load((ROOT / "openapi" / filename).read_text())
        assert description["security"] == [{security: []}]
        policy = example(f"{project}-access-policy")
        assert policy["identityAttributes"] == {"displayName": False, "email": False}
        for path, operations in description["paths"].items():
            concrete = path.replace("{datasetId}", "energy-reference-wasserburg-am-inn-2024").replace(
                "{version}", "1.0.0").replace("{artifactId}", "pv-yield").replace("{runId}", "run_example")
            for method in operations:
                if method not in {"get", "post", "put", "patch", "delete", "options"}:
                    continue
                routes = matches(policy, concrete, method.upper())
                assert len(routes) == 1, (project, path, method)
                assert routes[0]["authentication"]["mode"] == mode
                assert "503" in operations[method]["responses"]
                if mode == "browser-session":
                    assert "302" in operations[method]["responses"]
        for path in ("/api/v1/datasets-other", "/oauth2/callback", "/health/ready", "/unknown"):
            assert not matches(policy, path, "GET")
        assert not matches(policy, "/api/v1/datasets", "OPTIONS")
        if project == "odip":
            assert matches(policy, "/api/v1/datasets", "HEAD")
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                assert not matches(policy, "/api/v1/datasets", method)
        else:
            parameters = description["paths"]["/api/v1/optimization-runs"]["post"]["parameters"]
            assert {p["name"] for p in parameters if p.get("required")} >= {
                "Idempotency-Key", "Origin", "X-Platform-CSRF-Token"
            }


def test_declarations_match_policy_projects_and_consumer_network_route():
    for project in ("odip", "vef"):
        declaration = example(f"{project}-application")
        assert declaration["metadata"]["name"] == declaration["metadata"]["project"] == project
        public = [c for c in declaration["spec"]["components"] if c.get("exposure") == "public"]
        assert len(public) == 1
        assert public[0]["name"] == example(f"{project}-access-policy")["component"]
        assert declaration["spec"]["resources"][0]["deletionPolicy"] == "retain"
    vef = example("vef-application")
    api = vef["spec"]["components"][0]
    origin = vef["spec"]["configuration"]["values"]["ODIP_ORIGIN"]
    assert {tuple(sorted(d.items())) for d in api["outbound"]} == {
        tuple(sorted({"dns": urlsplit(origin).hostname, "port": 443}.items())),
        tuple(sorted({"dns": "identity.example.invalid", "port": 443}.items())),
    }
    assert example("vef-odip-service-request")["providerProject"] == "odip"
    assert example("odip-service-approval")["groups"] == ["dataset-readers"]


@pytest.mark.parametrize("mutation", [
    lambda v: v.pop("X-Platform-Principal-Id"),
    lambda v: v.pop("X-Platform-Principal-Client-Id"),
    lambda v: v.update({"X-Platform-Principal-Group-Ids": "dataset-readers"}),
    lambda v: v.update({"Authorization": "Bearer forbidden-upstream"}),
])
def test_malformed_normalized_service_context_fails(mutation):
    schemas = load_schemas()
    value = load_document(ROOT / "examples" / "platform-service-principal.json")
    mutation(value)
    validator = Draft202012Validator(
        schemas["platform-principal-headers-v1.schema.json"],
        registry=schema_registry(schemas), format_checker=FormatChecker(),
    )
    with pytest.raises(ValidationError):
        validator.validate(value)


def test_access_errors_are_separate_from_domain_error_envelopes():
    schemas = load_schemas()
    body = load_document(ROOT / "examples" / "platform-access-error.json")
    Draft202012Validator(schemas["platform-access-error-v1.schema.json"]).validate(body)
    with pytest.raises(ValidationError):
        Draft202012Validator(schemas["error-v1.schema.json"]).validate(body)
