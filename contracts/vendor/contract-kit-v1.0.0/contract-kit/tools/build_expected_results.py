"""Build the deterministic optimization golden result from shared fixtures."""

from __future__ import annotations

from pathlib import Path

from contractkit.canonical import canonical_bytes, load_json
from contractkit.optimization import optimize_reference


ROOT = Path(__file__).parents[1]
ENERGY_DIR = ROOT / "fixtures" / "energy-reference-wasserburg-am-inn-2024"


def main() -> None:
    manifest = load_json(ENERGY_DIR / "manifest.json")
    artifacts = {
        descriptor["artifactId"]: load_json(
            ENERGY_DIR / "artifacts" / f"{descriptor['artifactId']}.json"
        )
        for descriptor in manifest["artifacts"]
    }
    request = load_json(ROOT / "examples" / "optimization-request.json")
    expected = optimize_reference(request, manifest, artifacts)
    output = ROOT / "expected-results" / "optimization-reference.json"
    output.write_bytes(canonical_bytes(expected))


if __name__ == "__main__":
    main()
