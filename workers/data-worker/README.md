# ODIP data worker

This Python worker is managed with [uv](https://docs.astral.sh/uv/). It downloads a public HTTP source and sends its untouched response to the platform API, which stores it in PostgreSQL and records the run outcome.

```bash
cd workers/data-worker
uv sync
uv run odip-ingest --run-id <pipeline-run-id>
```

For platform deployment, run `odip-ingest --claim-next`. It atomically claims one queued run and exits successfully when no work is available, which lets a scheduled platform component safely invoke it. The API marks a claimed run as `RUNNING`; therefore claim mode does not call the separate `started` endpoint.

For local development, the API default is `http://localhost:8080`. Override it with `ODIP_API_URL` or the `--api-url` option when required. The worker does not need database credentials.
