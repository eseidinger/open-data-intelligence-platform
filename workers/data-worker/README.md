# ODIP data worker

This Python worker is managed with [uv](https://docs.astral.sh/uv/). It downloads a public HTTP source, stores its untouched response in the S3-compatible raw-artifact store, and reports the run outcome to the platform API.

```bash
cd workers/data-worker
uv sync
uv run odip-ingest --run-id <pipeline-run-id>
```

For local development, the defaults target the API at `http://localhost:8080`, MinIO at `http://localhost:9000`, and the `odip-raw` bucket. Override them with `ODIP_API_URL`, `ODIP_S3_ENDPOINT`, `ODIP_S3_ACCESS_KEY`, `ODIP_S3_SECRET_KEY`, and `ODIP_S3_BUCKET` when required.
