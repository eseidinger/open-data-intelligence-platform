import json
from pathlib import Path
from typing import Any

from referencing import Registry, Resource


ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / "schemas"


def load_document(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def load_schemas() -> dict[str, dict[str, Any]]:
    return {
        path.name: load_document(path)
        for path in sorted(SCHEMA_DIR.glob("*.schema.json"))
    }


def schema_registry(schemas: dict[str, dict[str, Any]]) -> Registry:
    resources = [
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
    ]
    return Registry().with_resources(resources)
