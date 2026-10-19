"""RFC 8785 canonical JSON serialization and SHA-256 calculation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import rfc8785


class DuplicateKeyError(ValueError):
    """Raised when a JSON object contains the same key more than once."""


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    """Load UTF-8 JSON while rejecting duplicate object keys."""

    with path.open("r", encoding="utf-8") as source:
        return json.load(source, object_pairs_hook=_unique_object)


def canonical_bytes(value: Any) -> bytes:
    """Return the RFC 8785 canonical representation of a JSON value."""

    return rfc8785.dumps(value)


def sha256_hex(value: Any) -> str:
    """Return the SHA-256 digest of an RFC 8785 canonical JSON value."""

    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canonicalize a JSON document and print its SHA-256 digest."
    )
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--write",
        action="store_true",
        help="replace the input with canonical bytes after successful parsing",
    )
    args = parser.parse_args()

    value = load_json(args.path)
    canonical = canonical_bytes(value)
    if args.write:
        args.path.write_bytes(canonical)
    print(hashlib.sha256(canonical).hexdigest())


if __name__ == "__main__":
    main()
