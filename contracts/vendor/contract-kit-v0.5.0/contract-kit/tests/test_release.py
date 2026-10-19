import hashlib
import tarfile

from contractkit.canonical import load_json
from schema_support import ROOT
from tools.build_release import build_release


def test_release_archive_is_reproducible_and_complete(tmp_path) -> None:
    first_archive, first_checksums = build_release(tmp_path / "first")
    second_archive, _ = build_release(tmp_path / "second")

    assert first_archive.read_bytes() == second_archive.read_bytes()
    digest = hashlib.sha256(first_archive.read_bytes()).hexdigest()
    assert first_checksums.read_text(encoding="utf-8") == (
        f"{digest}  {first_archive.name}\n"
    )

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    prefix = f"contract-kit-v{version}"
    with tarfile.open(first_archive, "r:gz") as archive:
        names = set(archive.getnames())
    assert {
        f"{prefix}/LICENSE",
        f"{prefix}/NOTICE",
        f"{prefix}/LICENSES/Apache-2.0.txt",
        f"{prefix}/LICENSES/CC-BY-4.0.txt",
        f"{prefix}/contract-kit/VERSION",
        f"{prefix}/contract-kit/uv.lock",
        f"{prefix}/contract-kit/platform/baseline.json",
        f"{prefix}/contract-kit/platform/upstream-inputs.schema.json",
        f"{prefix}/contract-kit/platform/README.md",
        f"{prefix}/contract-kit/schemas/platform-operational-envelope-v1.schema.json",
        f"{prefix}/contract-kit/examples/platform-operational-envelope.json",
        f"{prefix}/contract-kit/platform/examples/odip-access-policy.json",
        f"{prefix}/contract-kit/fixtures/index.json",
        f"{prefix}/contract-kit/expected-results/optimization-reference.json",
        f"{prefix}/contract-kit/ai/README.md",
        f"{prefix}/contract-kit/ai/acceptance-cases.json",
        f"{prefix}/contract-kit/ai/example-evidence.json",
        f"{prefix}/contract-kit/schemas/energy-ai-request-proposal-v1.schema.json",
        f"{prefix}/contract-kit/schemas/energy-ai-explanation-v1.schema.json",
        f"{prefix}/contract-kit/contractkit/ai.py",
    } <= names
    assert not any(".venv" in name or "__pycache__" in name for name in names)


def test_fixture_index_remains_parseable_before_release() -> None:
    assert len(load_json(ROOT / "fixtures" / "index.json")) == 2
