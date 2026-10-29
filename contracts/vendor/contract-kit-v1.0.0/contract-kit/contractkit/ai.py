"""Check structured AI citations against a VEF-approved evidence snapshot.

Call after JSON Schema validation. These checks establish citation integrity;
they do not establish that natural-language prose follows from its citations.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .validation import ProfileValidationError, _require


def _resolve(document: Any, pointer: str) -> Any:
    value = document
    for token in pointer.split("/")[1:] if pointer else []:
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            _require(bool(re.fullmatch(r"0|[1-9][0-9]*", token)), "invalid array index")
            value = value[int(token)]
        elif isinstance(value, dict):
            value = value[token]
        else:
            raise ProfileValidationError("citation traverses a scalar")
    return value


def validate_explanation(explanation: dict, sources: dict) -> None:
    """Validate against sources assembled by VEF, never supplied by the model.

    Each source has a trusted category and a JSON document. Required source IDs
    are result and, for successful runs, candidate. Other approved source IDs
    may carry customer inputs, assumptions, measured data or derived profiles.
    """
    _require(len(sources) <= 16, "evidence exceeds 16 sources")
    _require(
        len(json.dumps(sources, ensure_ascii=False, allow_nan=False).encode()) <= 65536,
        "evidence exceeds 64 KiB",
    )
    _require("result" in sources, "result evidence is required")
    _require(sources["result"]["category"] == "CALCULATED_OUTPUT", "result category mismatch")
    result = sources["result"]["document"]
    _require(result["status"] in {"SUCCEEDED", "INFEASIBLE"}, "run is not complete")
    _require(explanation["runId"] == result["runId"], "explanation run mismatch")
    required = {
        ("result", pointer)
        for pointer in (
            "/runId", "/dataset/datasetId", "/dataset/version", "/modelVersion",
            "/simulationVersion", "/recommendedConfigurationId", "/optimalityStatus",
        )
    }
    if result["status"] == "SUCCEEDED":
        _require("candidate" in sources, "recommended candidate evidence is required")
        _require(sources["candidate"]["category"] == "CALCULATED_OUTPUT", "candidate category mismatch")
        candidate = sources["candidate"]["document"]
        _require(
            candidate["configurationId"] == result["recommendedConfigurationId"],
            "candidate is not the recorded recommendation",
        )
        _require(candidate["feasible"] is True, "recommended candidate is not feasible")
        required.update({
            ("candidate", "/metrics/annualizedCostEUR"),
            ("candidate", "/metrics/selfSufficiency"),
        })
        required.update(
            ("candidate", f"/constraints/{index}")
            for index in range(len(candidate["constraints"]))
        )
    else:
        _require(result["recommendedConfigurationId"] is None, "infeasible recommendation")
        _require(bool(explanation["missingEvidence"]), "infeasible evidence gaps must be reported")
        required.add(("result", "/status"))

    cited = set()
    for claim in explanation["claims"]:
        for citation in claim["citations"]:
            source_id, pointer = citation["source"], citation["pointer"]
            _require(source_id in sources, "citation source is not approved")
            source = sources[source_id]
            _require(claim["category"] == source["category"], "evidence category mismatch")
            try:
                actual = _resolve(source["document"], pointer)
            except (KeyError, IndexError) as error:
                raise ProfileValidationError("citation pointer does not resolve") from error
            # Keep JSON booleans distinct from numbers, while allowing 1 and 1.0.
            _require(
                json.dumps(actual, sort_keys=True) == json.dumps(citation["value"], sort_keys=True)
                or (
                    type(actual) in {int, float}
                    and type(citation["value"]) in {int, float}
                    and actual == citation["value"]
                ),
                "citation value differs from evidence",
            )
            cited.add((source_id, pointer))
    _require(required <= cited, f"missing required citations: {sorted(required - cited)}")
