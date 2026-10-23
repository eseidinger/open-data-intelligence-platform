"""Validate claimed publication jobs using the pinned schemas and named policy."""

import hashlib
import json
import logging
import time

import requests

from odip_worker.auth import DependencyError, call
from odip_worker.contract import canonical_bytes, validate
from odip_worker.energy.profile import validate_profile

PROFILES = {
    "urn:portfolio:energy-configuration-input:v1": (
        "urn:portfolio:energy-quality:v1",
        [
            "schema",
            "integrity",
            "intervals",
            "units",
            "ranges",
            "catalog",
            "usage_rights",
        ],
    ),
    "urn:portfolio:mobility-counts:v1": (
        "urn:portfolio:mobility-counts-quality:v1",
        ["schema", "integrity", "usage_rights"],
    ),
}


def validate_job(base_url, job):
    started_at = time.monotonic()
    logger = logging.getLogger(__name__)
    logger.info(
        "Publication validation started",
        extra={"event": "publication.validation.started", "publication_id": job["id"]},
    )
    manifest = job["manifest"]
    policy, checks = PROFILES[manifest["schemaRef"]]
    digests = {a["artifactId"]: a["sha256"] for a in manifest["artifacts"]}
    report = {
        "manifestSha256": job["manifestSha256"],
        "policyRef": policy,
        "artifactDigests": digests,
        "checks": {name: "PASS" for name in checks},
        "failureCode": None,
        "claimToken": job["claimToken"],
    }
    try:
        validate("dataset-publication-v1", manifest)
        if (
            hashlib.sha256(canonical_bytes(manifest)).hexdigest()
            != job["manifestSha256"]
        ):
            raise ValueError("Manifest integrity failure")
        artifacts = {}
        total = 0
        for descriptor in manifest["artifacts"]:
            response = call(
                "get",
                f"{base_url}/api/v1/publication-jobs/{job['id']}/artifacts/{descriptor['artifactId']}",
                stream=True,
            )
            response.raise_for_status()
            try:
                payload = bytearray()
                for chunk in response.iter_content(65536):
                    if len(payload) + len(chunk) > 10 * 1024 * 1024:
                        raise ValueError("Artifact limit exceeded")
                    payload.extend(chunk)
                total += len(payload)
                if total > 50 * 1024 * 1024:
                    raise ValueError("Publication limit exceeded")
                if hashlib.sha256(payload).hexdigest() != descriptor["sha256"]:
                    raise ValueError("Artifact integrity failure")
                document = json.loads(payload)
                if canonical_bytes(document) != bytes(payload):
                    raise ValueError("Noncanonical artifact")
                artifacts[descriptor["artifactId"]] = document
            finally:
                response.close()
        if not all(
            p.get("license")
            and p.get("sourceOwner")
            and p.get("retrievedAt")
            and p.get("transformationVersion")
            for p in manifest["provenance"]
        ):
            raise ValueError("Usage rights or provenance are missing")
        if manifest["schemaRef"] == "urn:portfolio:energy-configuration-input:v1":
            validate_profile(manifest, artifacts)
        else:
            if (
                len(manifest["artifacts"]) != 1
                or manifest["artifacts"][0]["role"] != "HOURLY_COUNTS"
            ):
                raise ValueError("Invalid mobility profile")
            if (
                manifest["artifacts"][0]["mediaType"] != "application/json"
                or manifest["artifacts"][0].get("unit") != "vehicles/hour"
            ):
                raise ValueError("Invalid mobility descriptor")
            values = artifacts[manifest["artifacts"][0]["artifactId"]]
            if (
                values.get("schemaVersion") != "mobility-counts/v1"
                or values.get("unit") != "vehicles/hour"
            ):
                raise ValueError("Invalid mobility units")
            if not values.get("values") or any(
                v["value"] < 0 for v in values["values"]
            ):
                raise ValueError("Invalid mobility values")
    except (requests.RequestException, DependencyError):
        # Leave the leased job recoverable; outages are not failed data checks.
        raise
    except Exception:
        report["checks"] = {name: "FAIL" for name in checks}
        report["failureCode"] = "profile_validation_failed"
    result = call(
        "post", f"{base_url}/api/v1/publication-jobs/{job['id']}/completed", json=report
    )
    result.raise_for_status()
    failed = report["failureCode"] is not None
    logger.log(
        logging.WARNING if failed else logging.INFO,
        "Publication validation failed"
        if failed
        else "Publication validation completed",
        extra={
            "event": "publication.validation.failed"
            if failed
            else "publication.validation.completed",
            "publication_id": job["id"],
            "duration_ms": round((time.monotonic() - started_at) * 1000),
        },
    )
    return result.json()


def claim_and_validate(base_url):
    response = call("post", base_url + "/api/v1/publication-jobs/claim-next")
    if response.status_code == 204:
        return False
    response.raise_for_status()
    validate_job(base_url, response.json())
    return True
