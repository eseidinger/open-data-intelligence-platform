import argparse
import base64
import hashlib
import logging
import time
import os
import requests
from odip_worker.auth import api_url, call, headers as platform_principal_headers
from odip_worker.transformation import transform
from odip_worker.validation import validate_payload
from odip_worker.retrieval import download
from odip_worker.publication import claim_and_validate
from odip_worker.tracing import configure, span
from odip_worker.logging import configure_logging

def claim_next(base_url):
    for attempt in range(24):
        try:
            response = call("post", f"{base_url}/api/pipeline-runs/claim-next")
            if response.status_code == 204: return None
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError:
            if attempt == 23: raise
            time.sleep(5)

def main():
    configure_logging()
    logger = logging.getLogger(__name__)
    try:
        provider = configure()
        try:
            logger.info("Worker started", extra={"event": "job.started"})
            with span("odip.worker.run"):
                run()
            logger.info("Worker completed", extra={"event": "job.completed"})
        finally:
            if provider is not None:
                provider.shutdown()
    except Exception as error:
        logger.error("Worker failed; inspect the run status and configuration",
                     extra={"event": "job.failed", "error_type": type(error).__name__})
        raise SystemExit(1) from None

def run():
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--run-id")
    selection.add_argument("--claim-next", action="store_true")
    selection.add_argument("--publication-only", action="store_true")
    parser.add_argument("--api-url", default=os.getenv("ODIP_API_URL", "http://localhost:8080"))
    args = parser.parse_args()
    base_url = api_url(args.api_url)
    if args.publication_only:
        claim_and_validate(base_url)
        return
    if args.claim_next:
        if claim_and_validate(base_url): return
        job = claim_next(base_url)
        if job is None: return
    else:
        response = call("get", f"{base_url}/api/pipeline-runs/{args.run_id}/job")
        response.raise_for_status()
        job = response.json()
        started = call("post", f"{base_url}/api/pipeline-runs/{args.run_id}/started")
        started.raise_for_status()
        job["claimToken"] = started.json()["claimToken"]
    run_id = job["runId"]
    try:
        with span("odip.ingestion.download"):
            payload, content_type, source_version = download(job["location"])
        with span("odip.ingestion.validate"):
            validation = validate_payload(payload, content_type)
        with span("odip.ingestion.transform"):
            transformation = transform(payload, job.get("normalizer"))
        complete = {"payload": base64.b64encode(payload).decode("ascii"), "contentType": content_type, "contentLength": len(payload),
                    "checksumSha256": hashlib.sha256(payload).hexdigest(), "sourceVersion": source_version,
                    "validation": validation, "transformation": transformation, "claimToken": job.get("claimToken")}
        for attempt in range(3):
            try:
                call("post", f"{base_url}/api/pipeline-runs/{run_id}/completed", json=complete).raise_for_status()
                break
            except requests.ConnectionError:
                if attempt == 2: raise
                time.sleep(2 ** attempt)
    except Exception:
        try:
            call("post", f"{base_url}/api/pipeline-runs/{run_id}/failed", json={"reason": "ingestion_failed"}).raise_for_status()
        finally:
            raise RuntimeError("Ingestion failed; see the run's safe diagnostic") from None

if __name__ == "__main__":
    main()
