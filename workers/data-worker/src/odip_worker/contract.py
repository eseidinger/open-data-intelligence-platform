"""Pinned shared contract access. The vendored release is verified by repository CI."""

import os
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

KIT = Path(
    os.environ.get(
        "ODIP_CONTRACT_KIT",
        Path(__file__).resolve().parents[4]
        / "contracts/vendor/contract-kit-v0.5.0/contract-kit",
    )
)
sys.path.insert(0, str(KIT))
# Import after installing the pinned immutable contract kit path.
from contractkit.canonical import canonical_bytes, load_json  # noqa: E402
from contractkit.validation import validate_energy_publication  # noqa: E402

__all__ = [
    "KIT",
    "canonical_bytes",
    "load_json",
    "validate",
    "validate_energy_publication",
]

SCHEMAS = {
    p.stem.removesuffix(".schema"): load_json(p)
    for p in (KIT / "schemas").glob("*.json")
}
REGISTRY = Registry().with_resources(
    (s["$id"], Resource.from_contents(s)) for s in SCHEMAS.values()
)


def validate(name, document):
    Draft202012Validator(
        SCHEMAS[name], registry=REGISTRY, format_checker=FormatChecker()
    ).validate(document)
