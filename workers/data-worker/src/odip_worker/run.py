import argparse
import hashlib
import os
import sys

import boto3
import requests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--api-url", default=os.getenv("ODIP_API_URL", "http://localhost:8080"))
    args = parser.parse_args()
    base_url = args.api_url.rstrip("/")
    job = requests.get(f"{base_url}/api/pipeline-runs/{args.run_id}/job", timeout=15).json()
    requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/started", timeout=15).raise_for_status()
    try:
        response = requests.get(job["location"], timeout=60)
        response.raise_for_status()
        payload = response.content
        checksum = hashlib.sha256(payload).hexdigest()
        key = f"raw/{job['sourceId']}/{args.run_id}/source"
        s3 = boto3.client("s3", endpoint_url=os.getenv("ODIP_S3_ENDPOINT", "http://localhost:9000"), aws_access_key_id=os.getenv("ODIP_S3_ACCESS_KEY", "odip"), aws_secret_access_key=os.getenv("ODIP_S3_SECRET_KEY", "odip-local-development"))
        bucket = os.getenv("ODIP_S3_BUCKET", "odip-raw")
        try:
            s3.create_bucket(Bucket=bucket)
        except s3.exceptions.BucketAlreadyOwnedByYou:
            pass
        s3.put_object(Bucket=bucket, Key=key, Body=payload, ContentType=response.headers.get("Content-Type", "application/octet-stream"))
        requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/completed", json={"storageUri": f"s3://{bucket}/{key}", "contentType": response.headers.get("Content-Type"), "contentLength": len(payload), "checksumSha256": checksum, "sourceVersion": response.headers.get("ETag")}, timeout=15).raise_for_status()
    except Exception as error:
        requests.post(f"{base_url}/api/pipeline-runs/{args.run_id}/failed", json={"reason": str(error)[:4000]}, timeout=15)
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise
