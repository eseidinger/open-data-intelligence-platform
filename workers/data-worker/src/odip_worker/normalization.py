import json
from typing import Any


def normalize(payload: bytes, normalizer: str | None) -> dict[str, Any] | None:
    if normalizer is None:
        return None
    if normalizer == "EUROSTAT_RENEWABLE_SHARE":
        return _normalize_eurostat_renewable_share(payload)
    raise ValueError(f"Unsupported normalizer: {normalizer}")


def _normalize_eurostat_renewable_share(payload: bytes) -> dict[str, Any]:
    dataset = json.loads(payload)
    dimensions = dataset["dimension"]
    value = next(iter(dataset["value"].values()))
    return {
        "indicatorCode": "RENEWABLE_ENERGY_SHARE",
        "geoCode": _single_category(dimensions, "geo"),
        "observationYear": int(_single_category(dimensions, "time")),
        "unitCode": _single_category(dimensions, "unit"),
        "observationValue": value,
    }


def _single_category(dimensions: dict[str, Any], name: str) -> str:
    categories = dimensions[name]["category"]["index"]
    if len(categories) != 1:
        raise ValueError(f"Expected one {name} category, got {len(categories)}")
    return next(iter(categories))
