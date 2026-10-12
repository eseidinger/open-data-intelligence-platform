"""Verify every vendored byte against the pinned immutable release archive."""
import hashlib
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.4.0"
DIGEST = "884e3590614328c2adafa457153e11575dc1be09b9f53d7b0f53704fe39d02b0"
ARCHIVE = ROOT / "contracts/vendor/contract-kit-v0.4.0.tar.gz"
assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == DIGEST, "Contract archive checksum mismatch"
with tarfile.open(ARCHIVE, "r:gz") as archive:
    expected = set()
    for entry in archive.getmembers():
        if not entry.isfile(): continue
        relative = Path(entry.name)
        assert not relative.is_absolute() and ".." not in relative.parts
        expected.add(relative)
        actual = ROOT / "contracts/vendor" / relative
        assert actual.read_bytes() == archive.extractfile(entry).read(), f"Vendored contract drift: {relative}"
    actual = {p.relative_to(ROOT / "contracts/vendor") for p in (ROOT / "contracts/vendor/contract-kit-v0.4.0").rglob("*") if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts and ".venv" not in p.parts}
    assert actual == expected, "Unexpected or missing contract files"
print(f"Verified contract-kit {VERSION}, archive SHA-256 {DIGEST}")
