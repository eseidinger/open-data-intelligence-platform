"""Compatibility entry point for callers of the original annual normalizer."""

from odip_worker.transformation import transform


def normalize(payload, normalizer):
    result = transform(payload, normalizer)
    return result["data"] if result is not None else None
