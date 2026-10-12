import hashlib
import json
from pathlib import Path

import pytest

from contractkit.canonical import (
    DuplicateKeyError,
    canonical_bytes,
    load_json,
    sha256_hex,
)


def test_canonical_serialization_is_order_independent() -> None:
    left = {"z": 1, "a": [True, None, "Wasserburg"]}
    right = {"a": [True, None, "Wasserburg"], "z": 1}

    assert canonical_bytes(left) == b'{"a":[true,null,"Wasserburg"],"z":1}'
    assert canonical_bytes(left) == canonical_bytes(right)
    assert sha256_hex(left) == hashlib.sha256(canonical_bytes(left)).hexdigest()


def test_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    document = tmp_path / "duplicate.json"
    document.write_text('{"value":1,"value":2}', encoding="utf-8")

    with pytest.raises(DuplicateKeyError, match="duplicate JSON object key"):
        load_json(document)


def test_canonical_output_round_trips() -> None:
    original = {"region": "DE-BY-09187182", "value": 0.125}
    canonical = canonical_bytes(original)

    assert json.loads(canonical) == original
