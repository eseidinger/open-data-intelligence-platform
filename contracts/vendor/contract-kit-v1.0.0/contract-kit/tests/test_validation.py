import copy

import pytest

from contractkit.canonical import sha256_hex
from contractkit.validation import ProfileValidationError, validate_energy_publication
from schema_support import ROOT, load_document


EXAMPLE_DIR = ROOT / "examples"


def energy_example() -> tuple[dict, dict[str, dict]]:
    manifest = load_document(EXAMPLE_DIR / "dataset-publication.json")
    artifacts = {
        descriptor["artifactId"]: load_document(
            EXAMPLE_DIR / f"{descriptor['artifactId']}.json"
        )
        for descriptor in manifest["artifacts"]
    }
    return manifest, artifacts


def test_energy_example_passes_semantic_validation() -> None:
    validate_energy_publication(*energy_example())


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda manifest, artifacts: manifest["artifacts"][0].update(
                sha256="0" * 64
            ),
            "digest",
        ),
        (
            lambda manifest, artifacts: artifacts["reference-load-shape"]["values"][
                0
            ].update(value=0.5),
            "sums to",
        ),
        (
            lambda manifest, artifacts: artifacts["pv-yield"]["values"][0].update(
                start="2024-01-01T01:00:00Z"
            ),
            "starts at",
        ),
        (
            lambda manifest, artifacts: artifacts["component-catalog"]["components"][
                1
            ].update(componentId="pv-demo-400"),
            "component IDs",
        ),
    ],
)
def test_semantic_inconsistencies_are_rejected(mutation, message) -> None:
    manifest, artifacts = energy_example()
    manifest = copy.deepcopy(manifest)
    artifacts = copy.deepcopy(artifacts)
    mutation(manifest, artifacts)
    if message != "digest":
        for descriptor in manifest["artifacts"]:
            descriptor["sha256"] = sha256_hex(artifacts[descriptor["artifactId"]])

    with pytest.raises(ProfileValidationError, match=message):
        validate_energy_publication(manifest, artifacts)
