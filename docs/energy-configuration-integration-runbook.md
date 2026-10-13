# Energy Configuration Integration Runbook

ODIP implements the contract kit 0.4.0 publication milestone. The reference fixture is Wasserburg am Inn, region `DE-BY-09187182`, with 8,784 hourly UTC intervals on the 2024 calendar. Its PV profile derives from pinned PVGIS 2023 data; the leap day, tariffs, load shape, and catalog follow the shared decisions. It is a regional demonstration rather than observed 2024 building production or a commercial offer.

## Verify the repository

From the repository root:

```bash
python scripts/verify-contract-kit.py
cd workers/data-worker
uv sync --locked
uv run python -m unittest discover -s tests
```

Run the shared kit from its own project directory:

```bash
cd contracts/vendor/contract-kit-v0.4.0/contract-kit
uv run --frozen pytest
```

The API tests require an isolated PostgreSQL database. Point `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, and `SPRING_DATASOURCE_PASSWORD` to it before running `./gradlew --no-daemon test bootJar` in `services/platform-api`. Publication integration tests enable principal enforcement; production header-format checks have separate tests.

From `web`, run `npm ci`, `npm test -- --watch=false`, `npm run build`, `npx playwright install chromium`, and `npm run test:a11y`. The browser check exercises operator and read-only views at desktop and mobile widths.

After building the API jar, execute the local acceptance harness from the repository root:

```bash
uv run --project workers/data-worker --locked python scripts/local-publication-acceptance.py
```

The harness creates its own PostgreSQL container and temporary files. It ingests fixture bytes, derives the energy outputs, publishes both domains, verifies digests and conditional reads, rejects a missing-hour version, preserves earlier versions, restarts the API, and performs a real dump/restore into another database. It binds the API only to loopback and uses explicit development mode. It removes its own container and temporary backup afterward. This is local durability evidence, not deployed platform authentication evidence.

## Prepare platform resources

Use [ADR0001](architecture/adr/0001-energy-configuration-integration.md) and the shared DEC-01 through DEC-06 as the accepted implementation decisions.

The [integration inputs](../infrastructure/integration/) include application groups, a disjoint access policy, governance, and the ODIP worker service request and approval. Provision the groups through the platform, record their stable IDs, then apply the policy to the `web` component. Approve human operator membership explicitly. The consumer reader group has only bearer GET access; operator routes use browser sessions and CSRF; worker job routes use bearer authentication. No anonymous or combined session/bearer route is declared.

### Configure the access policy

After deploying an eligible application with public component `web` and creating the active `dataset-operators`, `dataset-readers`, and `ingestion-workers` groups, use the [policy configuration script](../scripts/configure-access-policy.py). It invokes the reviewed [Developer Platform CLI v0.2.0](https://github.com/eseidinger/developer-platform/tree/cli-v0.2.0) for every platform operation; it has no HTTP client or token prompt. Install that release with Python 3.12 or newer and put `devplat` on PATH:

```bash
uv tool install --python 3.12 \
  'git+https://github.com/eseidinger/developer-platform.git@cli-v0.2.0#subdirectory=platform/cli'
devplat --version
```

Create a CLI profile and sign in as a project administrator. Confirm the installation's issuer before creating the profile; the commands below use `https://identity.eseidinger.de/realms/platform`:

```bash
devplat profiles create odip-lab --api-url https://platform.eseidinger.de \
  --issuer https://identity.eseidinger.de/realms/platform --project odip
devplat --profile odip-lab auth login
```

If `odip-lab` already exists, inspect it with `devplat profiles show odip-lab` and reuse it rather than recreating it. Human login uses the CLI's device flow and secure OS keyring. Clear `PLATFORM_ACCESS_TOKEN`, `PLATFORM_TOKEN_ENDPOINT`, `PLATFORM_CLIENT_ID`, and `PLATFORM_CLIENT_SECRET` when using profile login: environment authentication takes precedence. On headless systems without a secure keyring, securely supply a short-lived administrator token in `PLATFORM_ACCESS_TOKEN` and set `PLATFORM_API_URL`. Tokens and credentials never belong in command-line arguments or source control. A deployment credential or hosted ODIP token cannot administer access policy.

Preview the complete policy for the disposable installation:

```bash
python3 scripts/configure-access-policy.py \
  --profile odip-lab --project odip
```

The script checks the CLI version and authentication source, then uses `devplat access context`, `access groups list`, and `access policy get` with JSON output to validate eligibility, resolve group IDs, and preview the policy. `--platform-url` overrides the CLI profile's API origin when needed; otherwise the active or selected profile supplies it. HTTPS is required, and the script never requests insecure TLS. The CLI honors `PLATFORM_CA_BUNDLE` or the profile's CA bundle.

Review the preview, then apply it:

```bash
python3 scripts/configure-access-policy.py \
  --profile odip-lab --project odip --apply
```

`--apply` creates or **replaces the entire access policy**, including any manually added rules. It sends non-secret policy JSON through stdin to `devplat access policy apply --file - --wait`. Existing-policy updates pass the exact quoted CLI ETag through `--if-match`; initial creation uses CLI v0.2.0's native version handling because that release rejects the zero-version ETag. Do not run concurrent initial policy creation from another administrator or automation. The CLI owns HTTPS transport, redirect rejection, authentication, and operation watching. The wrapper does not print raw CLI errors or credentials, preserves CLI failure exit codes, and never retries a write. It neither creates groups nor changes governance, membership, service approval, or dataset grants.

CLI v0.2.0 redacts the entire `authorization` block of each policy rule, including its non-secret group assignments. The preview reports `currentGroupsRedacted`; it cannot establish equality with the desired policy from that incomplete response. An explicit apply therefore replaces a redacted policy even when its other fields look unchanged. After the CLI confirms operation success and activation, the script checks the visible fields and reports that independent group read-back is unavailable. Verify group selections in the portal and through allowed/denied access tests. A fully readable, identical active policy would cause no write.

The activation timeout defaults to 120 seconds; `--wait-seconds` accepts 1–600 and is passed to the CLI's `--timeout`, with bounded subprocess overhead. An already pending, unchanged policy is observed through CLI reads without resubmission. A timeout or interrupted run does not cancel a submitted operation. Inspect **Application access → Policy / Operations** or rerun the preview before proceeding. A failed, unchanged policy requires an explicit operation retry through the platform. Once active, open ODIP, sign in, and approve the pending human request with `dataset-operators`; creating groups and applying policy does not grant membership.

### Configure service bindings and dataset grants

The worker requests service access to ODIP from the ODIP project itself. Its approved `ingestion-workers` binding is project-wide. Record the binding's stable principal and managed prefix; the platform injects `<prefix>_CLIENT_ID`, `<prefix>_CLIENT_SECRET`, and `<prefix>_TOKEN_URL`. Set `ODIP_WORKER_BINDING_PREFIX` to that prefix as non-secret configuration. Rotate the binding at least every 90 days and use the platform's adoption/revocation process.

Provision VEF's separate approved read-only service binding using the shared kit's service-request and approval inputs. VEF owns its credentials and result database. ODIP and VEF never share database access.

The platform owns route-level group authorization for both legacy and versioned APIs. ODIP validates trusted principal context and enforces only dataset permissions, job ownership, and claim tokens; it has no operator/guest group configuration. Grant administration, source/dataset registration, retention administration, and the operator capability route must remain restricted to `dataset-operators` by the platform policy. `manageGrants` in the operator capability response reflects admission to that protected route, not a second group check. Never replace the policy with an all-groups catch-all or expose the backend directly.

In the Publications page, grant the worker READ, INGEST, and VALIDATE on assigned datasets. Grant VEF READ only on the energy dataset. Grant READ and WRITE to permitted publishers, and INGEST when they capture inputs. Catalog registration grants the creator its initial dataset permissions. Operators have no implicit access to other datasets or pipeline runs. For historical datasets, use their known UUIDs with the protected dataset-grant API to assign explicit permissions before they become visible in the catalog/UI. Local grants use the stable principal, so normal client rotation does not change them. Link an unassigned source to a registered dataset before queueing ingestion.

Require platform network isolation that prevents direct backend access, including from another component in the same project. Header validation alone is not authentication. The worker calls ODIP through the protected public HTTPS origin rather than its former private DNS endpoint.

## Render the deployment

Build API/UI and worker images from the repository root:

```bash
docker build --target platform --tag odip-platform:<commit-sha> .
docker build --file workers/data-worker/Dockerfile --tag odip-data-worker:<commit-sha> .
```

The worker installs from its frozen lock and bundles the pinned kit. The API bundles the shared schemas and production UI. Both images run as non-root users.

The root `application.json` declares this installation's protected ODIP origin (`https://web-odip.apps.eseidinger.de`) and the worker's HTTPS egress to ODIP, identity (`identity.eseidinger.de`), and approved reference sources. The token endpoint URL itself comes from the managed worker binding. For another installation, edit `spec.configuration.values.ODIP_API_URL` and the worker's `outbound` DNS rules together; its API and token endpoint hosts must both be allowed. Source registration policy is declared by `ODIP_SOURCE_HOSTS` separately from network egress.

The descriptor sets `ODIP_WORKER_BINDING_PREFIX` to this installation's managed prefix, `ACCESS_BCC37E90DE10`. This is a non-secret reference; client credentials remain in the platform's managed secret. For another installation, use its approved worker binding's `spec.secretPrefix`.

Render the descriptor using the published 40-character commit image tag:

```bash
python scripts/render-integration.py --image-tag <commit-sha>
```

The renderer writes JSON to stdout and does not deploy. It preserves the descriptor's installation configuration, binding prefix, and network rules and pins both images. Use `--file <descriptor-path>` to render an alternative installation descriptor or `--worker-secret-prefix <managed-prefix>` to override the declared prefix. The root `application.json` still needs rendering because its image tags are placeholders. The rendered declaration keeps one public API/UI component and one scheduled worker and declares retained PostgreSQL storage. Supply the PostgreSQL resource and credentials through the platform.

The existing deployment workflow uses this renderer and reads the hostnames and binding prefix from the descriptor; it needs no `ODIP_HOST`, `IDENTITY_HOST`, or `ODIP_WORKER_BINDING_PREFIX` GitHub variables. Keep the control-plane variables `PLATFORM_API_URL` and `PLATFORM_TOKEN_ENDPOINT` and secrets `PLATFORM_CLIENT_ID` and `PLATFORM_CLIENT_SECRET` configured separately. Group IDs are managed in the platform access policy, not injected into application configuration. Applying governance, groups, access policy, and approved service access remains an explicit provisioning step.

After merging a workflow fix, start a new deployment workflow on `main` with an already-published commit image tag, or let a new successful image publication trigger it. Re-running an old failed run uses its old workflow revision and does not pick up the fix.

The API checks source host policy on registration; the worker additionally pins validated public addresses, validates each redirect and TLS hostname, rejects unsupported content and compression, and enforces limits while downloading. Source egress is separate from identity and API egress. DNS rules pin addresses at apply time and must be reapplied when approved addresses change.

## Publish the reference fixtures

Operators can create a draft from a manifest in the Publications page, attach each artifact, and request validation. The scheduled worker claims a permitted job and either finalizes publication or records failure. Failed versions remain unavailable to consumers; corrections use another version. The page exposes artifact checksums, policy results, warnings, and provenance separately from legacy curation status.

The scripted publisher uses an authenticated browser cookie file and same-origin CSRF in deployed mode. Set `ODIP_OPERATOR_COOKIE_FILE` to a protected Netscape cookie file obtained through an approved login; do not commit or print it. Set the worker's managed binding variables for validation. Then, from the repository root:

```bash
uv run --project workers/data-worker --locked python -m odip_worker.fixtures \
  --api-url https://<odip-ingress-host> --fixture all --validate
```

The publisher captures raw inputs through the operator API, derives the energy artifacts from the pinned source, attaches canonical bytes, and records publication lineage. It reuses existing identical drafts on retries. Consumer discovery and downloads use the pinned [read contract](../contracts/vendor/contract-kit-v0.4.0/contract-kit/openapi/odip-publication-v1.yaml); draft and validation operations use the [operator contract](../contracts/openapi/publication-operations.json).

For local development, explicitly set `ODIP_IDENTITY_MODE=development`. The development API accepts synthetic context formats, while production requires the normalized platform formats. Do not configure development bypasses in a deployment.

## Readiness and operations

Readiness includes PostgreSQL; liveness retains process-health semantics. Expired publication claims are released after five minutes with a new claim nonce on the next assignment. Stuck ingestion runs become FAILED after five minutes and retain diagnostics; an operator with INGEST permission queues a fresh run rather than replaying terminal transitions. Operators cannot fail another principal's job or bypass claims. Every ingestion completion, including manually started runs, requires the owning principal, its current INGEST grant, and the returned claim token. Completion retries must retain the same bytes. Atomic reference-input capture uses its server-generated claim internally.

Metrics include publication outcomes, duration, and retrieval count. Application audit records associate dataset/publication actions with stable principals and opaque correlation IDs. Central logs contain only compact platform operational envelopes. Customer details, domain IDs, and credentials do not enter those envelopes.

Supported publications retain their bytes, provenance, reports, and lineage. A protected operator can record a future support-end date at `PUT /api/v1/publication-retention`; expiration is permitted only after the additional one-year grace period. The scheduled cleanup removes expired publication outputs and retains raw inputs. Application audit rows expire after 180 days. Backups are governed separately by platform retention and can contain expired rows until the backup itself expires.

## Deployed handoff and remaining gates

After provisioning and publication, run the read-only deployed verifier with VEF's approved reader binding available in the environment:

```bash
uv run --project workers/data-worker --locked python scripts/verify-deployed-publication.py \
  --api-url https://<odip-ingress-host> --binding-prefix <reader-binding-prefix>
```

It checks authenticated canonical retrieval, ETags, all artifact digests, schema/profile validation, denial of forged identity headers, denial of another dataset, and write denial. It does not provision identities or modify publications.

Record the kit version/checksum, ODIP revision, resolved image digests, fixture digests, endpoint, and sanitized acceptance results for VEF. The deployed gates still require actual token rotation/revocation, direct-backend and unrelated-egress denial, platform outage behavior, retained-log reads, and platform backup restoration. VEF's independent validation, cache, numerical results, and AI release remain its responsibilities. Local verification and container builds do not claim those gates are complete.
