# Container builds

Build the single public application image from the repository root. It bundles the
production Angular build into the Spring Boot executable, so the UI and `/api/**`
are served from the same origin.

```bash
docker build --target platform --tag odip-platform:<release-id> .
```

The image listens on port `8080` and starts with the `prod` Spring profile. On
Developer Platform, an approved named PostgreSQL binding on `web` injects the
`PG*` connection variables consumed by the production configuration. For other
deployments, set `ODIP_DATABASE_URL`, `ODIP_DATABASE_USERNAME`, and
`ODIP_DATABASE_PASSWORD` at runtime. Set an appropriate
`ODIP_RAW_ARTIFACT_MAX_PAYLOAD_BYTES`. Keep credentials out of images and build
arguments.

Build the worker from the repository root so its pinned contract resources are included:

```bash
docker build --file workers/data-worker/Dockerfile --tag odip-data-worker:<release-id> .
```

Run the worker with `ODIP_API_URL` set to the protected HTTPS application origin.
Provide its approved project-wide service binding and `ODIP_WORKER_BINDING_PREFIX`
through the platform; it does not construct production identity headers:

```bash
docker run --rm --env-file <protected-worker-environment-file> \
  odip-data-worker:<release-id> --claim-next
```

The worker image has no database configuration and exposes no port. It installs
from the frozen lock and includes the immutable contract kit. Follow the
[integration runbook](energy-configuration-integration-runbook.md) to provision
bindings and apply the checked-in production or test deployment descriptor.

## Continuous delivery

GitHub Actions verifies pull requests. A push to `main` verifies all components
again and then publishes the images as `eseidinger/odip-platform` and
`eseidinger/odip-data-worker`. Configure the repository secret
`DOCKERHUB_TOKEN` with a Docker Hub access token that can write those
repositories.

A successful `main` build publishes `latest` images and deploys
`infrastructure/deployments/application-test.json` to `odip-test` using the GitHub `test` environment.
Version tags such as `v0.4.1` publish versioned images and deploy to `odip` using
the `production` environment. The workflow runs `scripts/render-release.py` to
replace the `:__VERSION__` placeholders in `infrastructure/deployments/application.json` with `:0.4.1` and
deploys the resulting temporary descriptor. The checked-in template stays unchanged. Release builds
never overwrite `latest`. Each environment needs its own scoped platform deployment
credentials (`PLATFORM_CLIENT_ID_TEST` / `PLATFORM_CLIENT_SECRET_TEST` for test,
`PLATFORM_CLIENT_ID` / `PLATFORM_CLIENT_SECRET` for production). Both descriptors must contain their approved database binding and
worker managed prefix before automatic deployment.
