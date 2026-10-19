import re
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_version_is_semantic_and_matches_project() -> None:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version
    )
    assert f'version = "{version}"' in pyproject


def test_required_directories_exist() -> None:
    required = {
        "schemas",
        "openapi",
        "examples",
        "fixtures",
        "expected-results",
        "contractkit",
        "tests",
        "platform",
    }

    assert required <= {path.name for path in ROOT.iterdir() if path.is_dir()}
