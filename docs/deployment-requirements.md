# Deployment requirements

## Scope and deployment model

Deploy the UI and API as one versioned, immutable container image. One application instance serves both the browser-facing UI and the JSON API; do not deploy a separate UI web server, CDN origin, or API service for this application.

The image must contain:

- the Spring Boot API executable and a Java 21 runtime;
- the production UI build as static files; and
- the database migrations in `src/main/resources/db/migration`.

The API owns the `/api/**` path prefix. The image must serve the UI at `/` and its static assets from the same origin. If the UI is a single-page application, non-API browser routes must fall back to its entry document, while unknown `/api/**` routes must retain normal API 404 behavior. The reverse proxy/load balancer must forward both path groups to the same container and must not rewrite `/api` away.

No CORS configuration is required for the normal deployment because UI and API share an origin. Any deployment that intentionally places the UI on a different origin must explicitly configure allowed origins, methods, headers, and credential policy rather than using a wildcard policy.

## Required runtime dependencies

### PostgreSQL

A reachable PostgreSQL database is required before an application instance can become ready. The application validates its Hibernate schema and runs Flyway migrations at startup, so the database user needs permission to create and alter the application schema and to maintain Flyway's history table during deployments. After schema creation/migration, grants may be reduced only if the chosen migration process continues to have the required access.

The database must use durable storage, backups, retention appropriate to the service's data policy, encrypted connections where it crosses an untrusted network, and a connection limit sized for the maximum number of replicas. Run database migrations once per release (for example as a migration job), or ensure rollout configuration prevents multiple replicas from racing to migrate.

### Raw-artifact storage

PostgreSQL is the raw-artifact store. The API persists each downloaded payload in the `raw_artifact.payload` `BYTEA` column, along with its metadata, checksum, validation result, and generated `postgres://raw-artifacts/<artifact-id>` reference. The API, not the worker, owns database access and returns stored bytes through `GET /api/raw-artifacts/{artifactId}/content`.

Provision database storage, backups, replication, retention, and restore capacity for the raw payloads as well as relational data. Enforce a maximum artifact size in the API/ingress before accepting payloads; account for JSON base64 transport overhead and PostgreSQL write-ahead-log, backup, and replication volume. This design is appropriate for bounded, modest-sized artifacts.

The migration adds the payload column without inventing content for existing artifact rows. If prior artifacts must remain downloadable, retain their old storage long enough to backfill the payload column or document that historical payloads are unavailable; all newly completed runs store their payload in PostgreSQL.

S3-compatible object storage is a required Phase 2 capability for raw artifacts and Parquet publications. It is not required by the current Phase 1 deployment. Before entering Phase 2, the deployment must add endpoint, bucket, identity, encryption, lifecycle, backup, health-check, and PostgreSQL-to-S3 migration requirements.

### Ingestion worker

Deploy the ingestion worker as a separate, non-public workload. It does not serve the UI or browser API and must not be placed behind the public ingress. Its role is to retrieve a queued ingestion job from the API, obtain the source artifact, validate and normalize it as required, send the raw artifact to the API for database persistence, and report the terminal result.

The worker requires network access to the internal API and the approved source locations. It must be given a distinct workload identity with only these permissions:

- read the job and change its lifecycle through the API;
- read only the approved external data-source hosts/protocols; and
- submit raw payloads and lifecycle updates through the internal API.

It must not connect directly to the application database, serve a public HTTP port, or receive the UI/API image's database credentials. Treat configured source locations as untrusted input: restrict egress by allowlist where possible, block private/link-local/metadata address ranges, impose connection/read timeouts and download-size limits, and validate redirects and content types before processing.

The API provides `POST /api/pipeline-runs/claim-next` for scheduled consumers. It locks the oldest queued run with `FOR UPDATE SKIP LOCKED`, transitions it to `RUNNING`, and returns its job payload in one transaction. It returns `204 No Content` when no work is queued. This is the required platform deployment path: invoke `odip-ingest --claim-next` on the schedule and do not call `started` again. Claim mode retries connection failures for two minutes, so a job triggered during a rolling API deployment waits for the readiness endpoint rather than failing immediately. The existing explicit path remains available for manually assigned work: `GET /api/pipeline-runs/{runId}/job`, followed by `POST /api/pipeline-runs/{runId}/started` and either `completed` or `failed`.

Run ownership is exclusive for claim-mode workers. The worker must use only `claim-next`; it must not list queued runs and then attempt a separate start transition. Deploy one scheduled worker component with `concurrencyPolicy: Forbid`, `retryLimit: 0`, and a run limit sufficient for API startup and ingestion until a deliberate throughput design is introduced. The API component must use `/actuator/health/readiness` as its platform readiness path, so in-project DNS has no endpoint until Spring Boot, Flyway, and the database are ready. Completion carries the base64-encoded payload, non-negative content length, and SHA-256 checksum; the API verifies the payload length and checksum before storing it. Validation and curation details may also be supplied.

The platform declaration grants the scheduled worker HTTPS egress only to `jsonplaceholder.typicode.com` for deployment smoke tests. DNS egress rules resolve to fixed IP rules when deployed, so reapply the declaration if the source address changes. Each additional production source host or CIDR must be explicitly approved; the application must not deploy broad egress to accommodate arbitrary user-provided source URLs.

Workers must be restart-safe and idempotent. Use a persistent or recoverable work queue, retry only transient failures with bounded exponential backoff, and use an idempotency/ownership key so a retry cannot create duplicate artifacts or complete another worker's run. Define an operational timeout for runs left in `QUEUED` or `RUNNING` after a worker crash; an operator or a reconciliation process must safely mark, requeue, or fail them. Because terminal API transitions currently reject invalid states, reconciliation must avoid blindly replaying lifecycle calls.

Size worker CPU, memory, ephemeral disk, concurrency, and maximum artifact size for the largest supported source. Prefer streaming downloads/uploads and clean up temporary files on success, failure, and shutdown. Emit structured logs and metrics tagged with the pipeline-run ID and source ID; alert on queue age, repeatedly failing sources, exhausted retries, stuck runs, download-limit violations, and upload/checksum failures.

## Configuration and secrets

Provide the following environment variables (or equivalent platform-injected configuration) for every non-development deployment:

| Setting | Required value |
| --- | --- |
| `ODIP_DATABASE_URL` | JDBC PostgreSQL URL for the target database, including TLS options where required. |
| `ODIP_DATABASE_USERNAME` | Least-privileged database account used by the application/migration process. |
| `ODIP_DATABASE_PASSWORD` | Password for that account, injected as a secret. |
| `ODIP_RAW_ARTIFACT_MAX_PAYLOAD_BYTES` | Maximum accepted raw artifact size in bytes; defaults to 10 MiB and must be set to a database-tested limit. |

Configure each worker with `ODIP_API_URL`, the internal base URL of the API (`http://web:8080` for the Developer Platform declaration). The worker needs no PostgreSQL credentials; it posts the payload to the API over the internal network.

Do not use the development defaults (`localhost` or database user/password `odip`) in a deployed environment. Keep passwords and any future signing keys out of the image, source control, logs, and command-line arguments.

Set an explicit production Spring profile/configuration rather than relying on the current default `dev` profile. The production configuration must retain `ddl-auto: validate`; schema changes are delivered only through Flyway migrations.

## Container and platform requirements

The container must run as a non-root, read-only user where practical, with a writable temporary directory only if the JVM or runtime needs one. It must accept the platform-provided HTTP port (or document and expose its fixed port), have no public database port, and receive traffic through an HTTPS-terminating ingress/load balancer. Redirect HTTP to HTTPS and set appropriate forwarded-header handling when TLS terminates upstream.

Tag images with an immutable release identifier (such as a Git commit SHA) and record the UI build and API revision together. Build the UI in a reproducible build stage and copy only its production output into the final runtime image; do not include package-manager caches, source trees, development dependencies, or secret files.

Size CPU, memory, JVM heap, database connections, and PostgreSQL storage/IOPS based on load testing. Include base64 decoding and raw-payload persistence in that test. Start with at least two replicas for availability when PostgreSQL is highly available. Configure graceful termination: remove an instance from load balancing before its termination grace period expires, and allow ongoing requests to complete.

## Health checks, observability, and operations

Spring Actuator exposes `health` and `info`. Configure the platform probes to use the application's health endpoints (including the liveness/readiness probe paths enabled by the application) and do not send public internet traffic to them. Readiness must reflect PostgreSQL so a replica is not added to service prematurely. Liveness should detect a stuck process without repeatedly restarting a healthy process solely because a transient dependency is unavailable.

Collect structured application logs from stdout/stderr, attach release, environment, and request/correlation identifiers, and redact secrets. Alert on unavailable replicas, failing readiness checks, migration failures, database connection exhaustion, insufficient database storage, repeated ingestion failures, and oversized payload rejections. Retain audit/operational logs according to the organization's policy.

Before a release, verify: the image starts with production configuration, Flyway completes successfully, the UI loads and client-side routes work, a representative `/api/**` request succeeds, static assets are cacheable with content-hashed names, health probes pass, and rollback to the previous image is possible. Database rollback must be planned separately; Flyway migrations are normally forward-only.
