import copy

import pytest
from jsonschema import ValidationError

from contractkit.ai import validate_explanation
from contractkit.validation import ProfileValidationError
from schema_support import ROOT, load_document
from test_examples import validators


def example(name):
    return load_document(ROOT / "examples" / name)


def evidence():
    return load_document(ROOT / "ai" / "example-evidence.json")


def test_explanation_matches_approved_evidence():
    validate_explanation(example("ai-explanation.json"), evidence())


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(requiresConfirmation=False),
    lambda value: value.update(request=None),
    lambda value: value.update(clarificationQuestions=["Missing roof area?"]),
    lambda value: value["request"].update(objective="AI_CHOOSES"),
])
def test_invalid_ready_proposals_are_rejected(mutation):
    proposal = example("ai-request-proposal.json")
    mutation(proposal)
    with pytest.raises(ValidationError):
        validators()["urn:portfolio:energy:ai-request-proposal:v1"].validate(proposal)


@pytest.mark.parametrize("field,value", [
    ("request", example("optimization-request.json")),
    ("clarificationQuestions", []),
])
def test_clarification_requires_questions_and_no_submittable_request(field, value):
    proposal = example("ai-request-clarification.json")
    proposal[field] = value
    with pytest.raises(ValidationError):
        validators()["urn:portfolio:energy:ai-request-proposal:v1"].validate(proposal)


@pytest.mark.parametrize("mutation,message", [
    (lambda value: value.update(runId="run-another-0001"), "run mismatch"),
    (lambda value: value["claims"][0]["citations"][0].update(source="foreign"), "not approved"),
    (lambda value: value["claims"][0]["citations"][0].update(pointer="/absent"), "does not resolve"),
    (lambda value: value["claims"][2]["citations"][0].update(value=1), "differs"),
    (lambda value: value["claims"][0].update(category="MEASURED_SOURCE_DATA"), "category mismatch"),
    (lambda value: value["claims"].pop(2), "missing required citations"),
    (lambda value: value["claims"].pop(3), "missing required citations"),
    (lambda value: value["claims"][1]["citations"].pop(), "missing required citations"),
])
def test_invalid_explanation_evidence_is_rejected(mutation, message):
    explanation = example("ai-explanation.json")
    mutation(explanation)
    with pytest.raises(ProfileValidationError, match=message):
        validate_explanation(explanation, evidence())


def test_recommendation_cannot_be_replaced_by_another_candidate():
    sources = evidence()
    sources["candidate"]["document"]["configurationId"] = "cfg-other-candidate"
    with pytest.raises(ProfileValidationError, match="recorded recommendation"):
        validate_explanation(example("ai-explanation.json"), sources)


@pytest.mark.parametrize("mutation,message", [
    (lambda value: value.pop("candidate"), "candidate evidence is required"),
    (lambda value: value["candidate"]["document"].update(feasible=False), "not feasible"),
    (lambda value: value["result"].update(category="MEASURED_SOURCE_DATA"), "category mismatch"),
])
def test_required_evidence_is_present_and_correctly_classified(mutation, message):
    sources = evidence()
    mutation(sources)
    with pytest.raises(ProfileValidationError, match=message):
        validate_explanation(example("ai-explanation.json"), sources)


@pytest.mark.parametrize("mutation", [
    lambda value: value["claims"][0].update(citations=[]),
    lambda value: value["claims"][0]["citations"][0].update(pointer="/bad~2escape"),
    lambda value: value["claims"][0].update(category="UNVERIFIED_GUESS"),
])
def test_explanations_require_well_formed_citations(mutation):
    explanation = example("ai-explanation.json")
    mutation(explanation)
    with pytest.raises(ValidationError):
        validators()["urn:portfolio:energy:ai-explanation:v1"].validate(explanation)


@pytest.mark.parametrize("oversize", ["sources", "bytes"])
def test_evidence_bounds_are_enforced(oversize):
    sources = evidence()
    if oversize == "sources":
        sources.update({f"extra{index}": {} for index in range(17)})
    else:
        sources["extra"] = {"category": "MODEL_ASSUMPTION", "document": "x" * 65536}
    with pytest.raises(ProfileValidationError, match="evidence exceeds"):
        validate_explanation(example("ai-explanation.json"), sources)


def test_infeasible_explanation_needs_no_fabricated_candidate():
    sources = evidence()
    sources.pop("candidate")
    result = sources["result"]["document"]
    result.update(status="INFEASIBLE", recommendedConfigurationId=None,
                  optimalityStatus="NOT_APPLICABLE", feasibleCandidateCount=0)
    explanation = example("ai-explanation.json")
    explanation["claims"] = explanation["claims"][:2]
    explanation["claims"][1] = {
        "text": "The run is infeasible and has no recommended candidate.",
        "category": "CALCULATED_OUTPUT",
        "citations": [
            {"source": "result", "pointer": f"/{key}", "value": result[key]}
            for key in ["status", "recommendedConfigurationId", "optimalityStatus"]
        ],
    }
    explanation["missingEvidence"] = ["No recommendation cost or self-sufficiency is available."]
    validators()["urn:portfolio:energy:optimization-result:v1"].validate(result)
    validators()["urn:portfolio:energy:ai-explanation:v1"].validate(explanation)
    validate_explanation(explanation, sources)


def test_citations_handle_json_pointer_escaping_and_preserve_json_types():
    sources = evidence()
    sources["extra"] = {"category": "MODEL_ASSUMPTION", "document": {"a/b~c": [True]}}
    explanation = example("ai-explanation.json")
    citation = {"source": "extra", "pointer": "/a~1b~0c/0", "value": True}
    explanation["claims"].append({
        "text": "An illustrative model assumption is true.",
        "category": "MODEL_ASSUMPTION", "citations": [citation],
    })
    validate_explanation(explanation, sources)
    citation["value"] = 1
    with pytest.raises(ProfileValidationError, match="differs"):
        validate_explanation(explanation, sources)
    citation["value"] = True
    citation["pointer"] = "/a~1b~0c/00"
    with pytest.raises(ProfileValidationError, match="array index"):
        validate_explanation(explanation, sources)


def test_ai_reference_uses_existing_api_examples_without_changing_them():
    sources = evidence()
    request = copy.deepcopy(example("optimization-request.json"))
    assumptions = request.pop("assumptions")
    assert sources["request"]["document"] == request
    assert sources["assumptions"]["document"] == assumptions
    assert sources["result"]["document"] == example("optimization-result.json")
    assert sources["candidate"]["document"] == example("candidate.json")


def test_consumer_acceptance_cases_are_packaged_with_resolvable_inputs():
    cases = load_document(ROOT / "ai" / "acceptance-cases.json")
    assert len({case["id"] for case in cases}) == len(cases)
    assert {case["stage"] for case in cases} == {
        "proposal", "confirmation", "explanation", "evidence-validation",
        "failure-handling", "regression",
    }
    for case in cases:
        assert case["assertions"]
        for field in ("expectedRequest", "evidence"):
            if field in case:
                assert (ROOT / "ai" / case[field]).is_file()
