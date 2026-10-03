import csv
import hashlib
import io
import json
from typing import Any


def validate_payload(payload: bytes, content_type: str | None) -> dict[str, Any]:
    normalized_content_type = (content_type or "").split(";", 1)[0].lower()
    if normalized_content_type in {"application/json", "application/ld+json"} or normalized_content_type.endswith("+json"):
        return _validate_json(payload)
    if normalized_content_type in {"text/csv", "application/csv"}:
        return _validate_csv(payload)
    return {"status": "UNSUPPORTED", "detectedFormat": normalized_content_type or None}


def _validate_json(payload: bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "INVALID", "detectedFormat": "JSON", "failureReason": str(error)}
    record_count = len(value) if isinstance(value, list) else 1
    return {
        "status": "VALID",
        "detectedFormat": "JSON",
        "recordCount": record_count,
        "schemaFingerprint": _fingerprint(_shape(value)),
    }


def _validate_csv(payload: bytes) -> dict[str, Any]:
    try:
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
    except (UnicodeDecodeError, csv.Error) as error:
        return {"status": "INVALID", "detectedFormat": "CSV", "failureReason": str(error)}
    if not rows and not csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))).fieldnames:
        return {"status": "INVALID", "detectedFormat": "CSV", "failureReason": "CSV header is missing"}
    field_names = sorted(rows[0].keys()) if rows else sorted(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))).fieldnames or [])
    return {"status": "VALID", "detectedFormat": "CSV", "recordCount": len(rows), "schemaFingerprint": _fingerprint({"columns": field_names})}


def _shape(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return ["array", _shape(value[0]) if value else None]
    return type(value).__name__


def _fingerprint(shape: Any) -> str:
    canonical_shape = json.dumps(shape, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical_shape.encode()).hexdigest()
