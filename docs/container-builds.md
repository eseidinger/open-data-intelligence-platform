# Container builds

Build the single public application image from the repository root. It bundles the
production Angular build into the Spring Boot executable, so the UI and `/api/**`
are served from the same origin.

```bash
docker build --target platform --tag odip-platform:<release-id> .
```

The image listens on port `8080` and starts with the `prod` Spring profile. Set
`ODIP_DATABASE_URL`, `ODIP_DATABASE_USERNAME`, `ODIP_DATABASE_PASSWORD`, and an
appropriate `ODIP_RAW_ARTIFACT_MAX_PAYLOAD_BYTES` at runtime. Do not place those
values in an image or build argument.

Build the worker separately from its own directory:

```bash
docker build --tag odip-data-worker:<release-id> workers/data-worker
```

Run the worker with `ODIP_API_URL` set to the API's internal URL and provide the
pipeline run when starting the container:

```bash
docker run --rm -e ODIP_API_URL=http://platform-api:8080 \
  odip-data-worker:<release-id> --run-id <pipeline-run-id>
```

The worker image has no database configuration and exposes no port.

## Continuous delivery

GitHub Actions verifies pull requests. A push to `main` verifies all components
again and then publishes the images as `eseidinger/odip-platform` and
`eseidinger/odip-data-worker`. Configure the repository secret
`DOCKERHUB_TOKEN` with a Docker Hub access token that can write those
repositories.
