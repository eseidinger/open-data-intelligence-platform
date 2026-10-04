import argparse
import base64
import hashlib
import os
import sys

import requests

from odip_worker.normalization import normalize
from odip_worker.validation import validate_payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--api-url", default=os.getenv("ODIP_API_URL", "http://localhost:8080"))
    args = parser.parse_args()
    base_url = args.api_url.rstrip("/")
    job_response = requests.get(f"{base_url}/api/pipeline-runs/{args.run_id}/job", timeout=15)
    job_response.raise_for_status()
    job = job_response.json()
    requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/started", timeout=15).raise_for_status()
    try:
        response = requests.get(job["location"], timeout=60)
        response.raise_for_status()
        payload = response.content
        validation = validate_payload(payload, response.headers.get("Content-Type"))
        energy_observation = normalize(payload, job.get("normalizer"))
        checksum = hashlib.sha256(payload).hexdigest()
        requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/completed", json={"payload": base64.b64encode(payload).decode("ascii"), "contentType": response.headers.get("Content-Type"), "contentLength": len(payload), "checksumSha256": checksum, "sourceVersion": response.headers.get("ETag"), "validation": validation, "energyObservation": energy_observation}, timeout=60).raise_for_status()
    except Exception as error:
        requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/failed", json={"reason": str(error)[:4000]}, timeout=15)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise
