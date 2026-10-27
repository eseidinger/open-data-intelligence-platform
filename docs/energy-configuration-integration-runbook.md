# Energy Configuration Integration Runbook

ODIP consumes contract kit 0.5.0, which preserves the accepted 0.4.0 publication contract and fixtures while adding VEF AI-assistance contracts. The reference fixture is Wasserburg am Inn, region `DE-BY-09187182`, with 8,784 hourly UTC intervals on the 2024 calendar. Its PV profile derives from pinned PVGIS 2023 data; the leap day, tariffs, load shape, and catalog follow the shared decisions. It is a regional demonstration rather than observed 2024 building production or a commercial offer.

For a new test or production installation, start with [Bootstrap environments](bootstrap.md). It covers the web-only first deployment, shared setup scripts and CI prerequisites in dependency order.

## Current-release acceptance scope

Use requests for new installations with `existingComponentIds: []`, following
[DEC-07](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-07-new-equipment-release-scope.md). Existing-equipment planning is deferred. Include an explicit VEF HTTP 422 /
`existing_equipment_not_supported` and no-created-run check for a non-empty list
in the deployed negative regression. Original dataset 1.0.0 and the synthetic
corrected-version drill remain unchanged.

Under [DEC-08](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-08-complete-calendar-year.md), energy optimization uses January 1 at 00:00 UTC through the following
January 1, with 8,760 or 8,784 complete hourly intervals. The energy worker
checks this before passing publication validation, while VEF checks it
independently. Reject partial/rolling/shifted periods in the deployed regression.
Existing immutable publications are never rewritten; historical shorter profiles
are unsupported for new annual optimizations.

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
cd contracts/vendor/contract-kit-v0.5.0/contract-kit
uv run --frozen pytest
```

The API tests require an isolated PostgreSQL database. Point `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, and `SPRING_DATASOURCE_PASSWORD` to it before running `./gradlew --no-daemon test bootJar` in `services/platform-api`. Publication integration tests enable principal enforcement; production header-format checks have separate tests.

From `web`, run `npm ci`, `npm test -- --watch=false`, `npm run build`, `npx playwright install chromium`, and `npm run test:a11y`. The browser check exercises operator and read-only views at desktop and mobile widths.

After building the API jar, execute the local acceptance harness from the repository root:

```bash
uv run --project workers/data-worker --locked python scripts/local-publication-acceptance.py
```

The harness creates its own PostgreSQL container and temporary files. It ingests fixture bytes, derives the energy outputs, publishes both domains, verifies digests and conditional reads, rejects a missing-hour version, preserves earlier versions, restarts the API, and performs a real dump/restore into another database. It binds the API only to loopback and uses explicit development mode. It removes its own container and temporary backup afterward. This is local durability evidence, not deployed platform authentication evidence.

### Corrected-version regression boundary

The October 27 follow-up harness uses failed draft `1.0.99` and valid corrected
`1.0.1` in its disposable local database. It adds exactly EUR 0.01/kWh to every
hourly import tariff and advances the catalog version. The pinned `1.0.0` bytes
and released oracle stay unchanged. This is a synthetic regression fixture,
not a newly accepted commercial tariff or replacement of the released oracle.

Export the bytes read after restart and actual PostgreSQL restore, together with
an independent Python contract-kit oracle, to a new evidence directory:

```bash
uv run --project workers/data-worker --locked python scripts/local-publication-acceptance.py \
  --evidence-dir /tmp/odip-corrected-energy
```

The VEF `EnergyCorrectedPublicationTest` consumes that directory through
`ENERGY_CORRECTED_FIXTURE_DIRECTORY`, validates all bytes and compares all 252
candidates, feasibility, ranking, recommendation and metrics. It also recomputes
unchanged `1.0.0`. The October 27 local execution passed; see the
[VEF verification record](https://github.com/eseidinger/variability-engineering-framework/blob/main/docs/04-development/energy-gap-closure-verification.md).

This closes the local unchanged-content test deficiency. The deployed comparison of the maintainer-approved [DEC-09 correction](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-09-corrected-tariff-acceptance-case.md) and integrated application
restore remain open in [GAP-03/05](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-gap-analysis.md).
Never overwrite an existing published version; use an isolated namespace when
an installation already occupies `1.0.1`.

The [October 27 review](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-implementation-and-acceptance-review.md) records the accepted ODIP handoff separately
from the remaining joint AI-10 regression and recovery evidence.

### Create corrected 1.0.1 while retaining original input lineage

For the approved DEC-09 scenario, prepare the checksum-verified 1.0.1 manifest
and five artifacts with the local acceptance harness's `--evidence-dir` option.
Keep the original published version and its captured raw-input links intact.

In the signed-in ODIP test application, select published version 1.0.0 under
Publications. Under Raw input lineage, choose **Use these inputs for a new draft**.
The dataset is selected automatically, the captured-input count appears above
the creation form, and focus moves to the manifest chooser. Select the prepared
1.0.1 `manifest.json` and create the draft. The existing operator API receives
the selected raw-input IDs together with the manifest; backend ownership and
source-membership checks still apply. Changing datasets clears the selection.
Only permitted published versions with captured inputs expose this action.

Select the new 1.0.1 draft, attach its five checksum-matching artifact files,
and request validation/publication through the existing UI and worker. Record
the draft ID, manifest checksum, preserved input count and final validation
status. If the original has no captured inputs, investigate its lineage before
proceeding. A console script or cookie export is not required for this workflow.

## Prepare platform resources

Use [ADR0001](architecture/adr/0001-energy-configuration-integration.md) and the shared DEC-01 through DEC-06 as the accepted implementation decisions.

The [integration inputs](../infrastructure/integration/) include application groups, a disjoint access policy, governance, and the ODIP worker service request and approval. The policy configuration script creates missing groups and resolves their stable IDs before applying the policy to the `web` component. Approve human operator membership explicitly. The consumer reader group has only bearer GET access; operator routes use browser sessions and CSRF; worker job routes use bearer authentication. No anonymous or combined session/bearer route is declared.

### Configure the access policy

After deploying an eligible application with public component `web`, use the [policy configuration script](../scripts/configure-access-policy.py). It invokes the reviewed [Developer Platform CLI v0.3.0](https://github.com/eseidinger/developer-platform/tree/cli-v0.3.0) for every platform operation; it has no HTTP client or token prompt. Install that release with Python 3.12 or newer and put `devplat` on PATH:

```bash
uv tool install --python 3.12 \
  'git+https://github.com/eseidinger/developer-platform.git@cli-v0.3.0#subdirectory=platform/cli'
devplat --version
```

Create a CLI profile and sign in as a project administrator. Confirm the installation's issuer before creating the profile; the commands below use `https://identity.eseidinger.de/realms/platform`:

```bash
devplat profiles create lab --api-url https://platform.eseidinger.de \
  --issuer https://identity.eseidinger.de/realms/platform --project odip
devplat --profile lab auth login
```

If `lab` already exists, inspect it with `devplat profiles show lab` and reuse it rather than recreating it. Human login uses the CLI's device flow and secure OS keyring. Run the commands from a desktop terminal with access to the OS keyring. Follow the verification URL and user code printed by `auth login` and sign in as a project administrator.

Environment authentication takes precedence over profile login. Clear stale authentication variables and API overrides before signing in with the selected profile:

```bash
unset PLATFORM_ACCESS_TOKEN PLATFORM_TOKEN_ENDPOINT PLATFORM_CLIENT_ID PLATFORM_CLIENT_SECRET PLATFORM_API_URL

devplat --profile lab auth login
devplat --profile lab --output json auth status
devplat --profile lab --output json access context --project odip
```

The authentication source should be `human-profile-session`. `auth status` reports the selected source without validating the session against the server; `access context` makes an authenticated read and lets you check project eligibility and access-policy administration permissions. If authentication fails, run `devplat --profile lab auth login` again. A deployment credential or hosted ODIP session cannot administer platform access policy.

For the local Developer Platform, follow the [local authentication and network
notes](bootstrap.md#prepare-tools-and-authentication). Substitute profile
`odip-local` and project `odip-test-local` in policy, service-access and permission
checks below. Continue using `devplat auth login` with the local profile.

#### Preview and apply the policy

Preview the complete policy for the disposable installation:

```bash
python3 scripts/configure-access-policy.py \
  --profile lab --project odip
```

The script checks the CLI version and authentication source, then uses `devplat access context`, `access groups list`, and `access policy get` with JSON output to validate eligibility and preview the policy. The preview lists missing groups under `groupsToCreate` without creating them; policy group references remain names until all stable IDs exist. With `--apply`, it creates missing `dataset-operators`, `dataset-readers`, and `ingestion-workers` groups from `infrastructure/integration/groups.json`, using project-specific idempotency keys, then reads back their active IDs before applying the policy. Existing active groups are reused; duplicate, inactive or malformed groups stop the operation. Group creation failures stop policy application and are never automatically retried. Select either `--project odip` or `--project odip-test`. `--platform-url` overrides the CLI profile's API origin when needed; otherwise the active or selected profile supplies it. HTTPS is required, and the script never requests insecure TLS. The CLI honors `PLATFORM_CA_BUNDLE` or the profile's CA bundle.

Review the preview, then apply it:

```bash
python3 scripts/configure-access-policy.py \
  --profile lab --project odip --apply
```

`--apply` creates missing groups and creates or **replaces the entire access policy**, including any manually added rules. It sends non-secret policy JSON through stdin to `devplat access policy apply --file - --wait`. Existing-policy updates pass the exact quoted CLI ETag through `--if-match`; initial creation uses CLI v0.3.0's native version handling because that release rejects the zero-version ETag. Do not run concurrent initial policy creation from another administrator or automation. The CLI owns HTTPS transport, redirect rejection, authentication, and operation watching. The wrapper does not print raw CLI errors or credentials, preserves CLI failure exit codes, and never retries a write. It does not change existing groups, governance, membership, service approval, or dataset grants.

CLI v0.3.0 redacts the entire `authorization` block of each policy rule, including its non-secret group assignments. The preview reports `currentGroupsRedacted`; it cannot establish equality with the desired policy from that incomplete response. An explicit apply therefore replaces a redacted policy even when its other fields look unchanged. After the CLI confirms operation success and activation, the script checks the visible fields and reports that independent group read-back is unavailable. Verify group selections in the portal and through allowed/denied access tests. A fully readable, identical active policy would cause no write.

The activation timeout defaults to 120 seconds; `--wait-seconds` accepts 1–600 and is passed to the CLI's `--timeout`, with bounded subprocess overhead. An already pending, unchanged policy is observed through CLI reads without resubmission. A timeout or interrupted run does not cancel a submitted operation. Inspect **Application access → Policy / Operations** or rerun the preview before proceeding. A failed, unchanged policy requires an explicit operation retry through the platform. Once active, open ODIP, sign in, and approve the pending human request with `dataset-operators`; creating groups and applying policy does not grant membership.

### Configure service bindings and dataset grants

The worker requests service access to ODIP from the ODIP project itself. Its approved `ingestion-workers` binding is project-wide. Record the binding's stable principal and managed prefix; the platform injects `<prefix>_CLIENT_ID`, `<prefix>_CLIENT_SECRET`, and `<prefix>_TOKEN_URL`. Set `ODIP_WORKER_BINDING_PREFIX` to that prefix as non-secret configuration. Rotate the binding at least every 90 days and use the platform's adoption/revocation process.

Provision VEF's separate approved read-only service binding using the shared kit's service-request and approval inputs. VEF owns its credentials and result database. ODIP and VEF never share database access.

The platform owns route-level group authorization for both legacy and versioned APIs. ODIP validates trusted principal context and enforces only dataset permissions, job ownership, and claim tokens; it has no operator/guest group configuration. Grant administration, source/dataset registration, retention administration, and the operator capability route must remain restricted to `dataset-operators` by the platform policy. `manageGrants` in the operator capability response reflects admission to that protected route, not a second group check. Never replace the policy with an all-groups catch-all or expose the backend directly.

In the Publications page, grant the worker READ, INGEST, and VALIDATE on assigned datasets. Grant VEF READ only on the energy dataset. Grant READ and WRITE to permitted publishers, and INGEST when they capture inputs. Catalog registration grants the creator its initial dataset permissions. Operators have no implicit access to other datasets or pipeline runs. For historical datasets, use their known UUIDs with the protected dataset-grant API to assign explicit permissions before they become visible in the catalog/UI. Local grants use the stable principal, so normal client rotation does not change them. Link an unassigned source to a registered dataset before queueing ingestion.

Require platform network isolation that prevents direct backend access, including from another component in the same project. Header validation alone is not authentication. The worker calls ODIP through the protected public HTTPS origin rather than its former private DNS endpoint.

## Deployment descriptors and automatic releases

Two checked-in descriptors define the applications:

| Descriptor | Project | Image tags | Deployment trigger |
| --- | --- | --- | --- |
| `infrastructure/deployments/application-test.json` | `odip-test` | `latest` for both images | Successful build and publication on `main` |
| `infrastructure/deployments/application.json` | `odip` | `__VERSION__` placeholders filled from the release tag | Successful build and publication on matching `v*` tags |

`infrastructure/deployments/application-test.json` is deployed directly. Production uses the
`__VERSION__` image-tag placeholder in `infrastructure/deployments/application.json`.
`scripts/render-release.py --version v0.4.1` replaces that placeholder in both
images with `0.4.1`, writes JSON to stdout, and leaves the template unchanged.
The version-tag workflow validates the template before publishing, then renders
it to a temporary file and deploys that file after publication. No per-release
version edits to the template are needed. The renderer accepts release versions
with an optional leading `v` and optional prerelease suffix; floating tags and
build metadata are rejected. Release builds do not update `latest`.
The build workflow calls the reusable deployment workflow after both images have
published. A manual build on `main` or a version tag follows the same routing.

Configure the GitHub environments `test` and `production` separately. Each needs
variables `PLATFORM_API_URL` and `PLATFORM_TOKEN_ENDPOINT`. Test uses secrets
`PLATFORM_CLIENT_ID_TEST` and `PLATFORM_CLIENT_SECRET_TEST`; production uses
`PLATFORM_CLIENT_ID` and `PLATFORM_CLIENT_SECRET`. Test never falls back to the
production secrets. The test deployment credential
must target `odip-test`, and the production credential must target `odip`.
The build uses repository secret `DOCKERHUB_TOKEN`. PostgreSQL binding UUIDs and
worker managed prefixes are non-secret installation configuration in the
descriptors, rather than GitHub variables. Provision them before enabling automatic
deployment and commit the updated descriptor. The workflow rejects an empty
PostgreSQL binding or a missing worker prefix.

## Provision application storage

The platform rejects legacy `spec.resources` / `shared-dev` / `retain` declarations.
Provision the independently managed PostgreSQL resource and its read-write binding
for component `web` before deploying `odip`:

```bash
# Upgrade the Python environment that owns devplat, if needed.
bash scripts/upgrade-devplat.sh /path/to/venv/bin/python
python scripts/setup-storage.py --profile lab --project odip
python scripts/setup-storage.py --profile lab --project odip --apply \
  --update-descriptor infrastructure/deployments/application.json
```

The template `infrastructure/integration/odip-postgresql.json` requests a 1 GiB
resource named `database`. Use the same `--quota-bytes` allocation for preview and
apply. Existing resource configuration and bindings must match; the script never
changes quotas, migrates data or retries a failed write. `--update-descriptor`
saves the approved binding UUID in `web.bindings` with an empty `envPrefix`.
For test storage, use the same shared script with the test project and descriptor:

```bash
python scripts/setup-storage.py --profile lab --project odip-test --apply \
  --update-descriptor infrastructure/deployments/application-test.json
```

The selected project must already exist. Provision its groups, access policy and
worker service binding through the earlier CLI workflow, selecting `odip-test`
for test resources. Save the test worker's own managed prefix in the test
descriptor. Review and commit the descriptor changes before automatic deployment.

Only `web` receives injected `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and
`PGPASSWORD` variables and private database egress. Spring's production
configuration already consumes them. Remove stale `ODIP_DATABASE_*` overrides
when switching to managed storage. The worker must have no database binding.
Provision its separate service identity and set `ODIP_WORKER_BINDING_PREFIX` in
the production descriptor. Access policy, groups and governance use the earlier
provisioning workflow. Existing database data needs an explicitly verified
migration before switching to a new resource.

For manual deployment after provisioning, apply the test descriptor directly or render the production release first:

```bash
devplat --profile lab deploy apply --project odip-test --file infrastructure/deployments/application-test.json --wait
python scripts/render-release.py --version v0.4.1 > /tmp/odip-release.json
devplat --profile lab deploy apply --project odip --file /tmp/odip-release.json --wait
```

For local deployment, use `--profile odip-local --project odip-test-local` and
`--file infrastructure/deployments/application-test-local.json` in the manual
apply command. See [local descriptor setup](bootstrap.md#provision-postgresql)
for project-specific descriptor selection and installation-owned bindings.
The remote descriptors and release workflow above continue to target the remote
Developer Platform.

The API checks source host policy on registration; the worker additionally pins validated public addresses, validates each redirect and TLS hostname, rejects unsupported content and compression, and enforces limits while downloading. Source egress is separate from identity and API egress. DNS rules pin addresses at apply time and must be reapplied when approved addresses change.

## Publish the reference fixtures

Operators can create a draft from a manifest in the Publications page, attach each artifact, and request validation. The scheduled worker claims a permitted job and either finalizes publication or records failure. Failed versions remain unavailable to consumers; corrections use another version. The page exposes artifact checksums, policy results, warnings, and provenance separately from legacy curation status.

The scripted publisher uses an authenticated operator browser session and same-origin CSRF in deployed mode. Create its Netscape-format cookie file and check authentication before publishing. The platform CLI login and worker service credentials do not replace this operator session.

### Create the operator cookie file

In WSL, use Windows clipboard access through `powershell.exe` to transfer the complete header without displaying it. Keep the cookie file outside the repository: it grants access as your signed-in operator and must not be committed, uploaded, printed, or shared in chat. On another Linux host, use an approved Netscape-format cookie export into an owner-only file outside the repository, set `ODIP_OPERATOR_COOKIE_FILE` to that path and `ODIP_API_URL` to the protected origin, and continue with [Check the operator session](#check-the-operator-session).

Do not paste a complete cookie header into `getpass()` or `read -s`. Linux canonical terminal input discards characters after 4,095 characters on a single line. A long header can therefore be truncated while retaining all three cookie names, causing a login redirect. Reading the clipboard directly avoids that input limit. See the [Linux terminal documentation](https://man7.org/linux/man-pages/man3/termios.3.html).

1. Sign into `https://web-odip.apps.eseidinger.de` with an account approved for `dataset-operators`.
2. Open `https://web-odip.apps.eseidinger.de/api/datasets` in that browser. Confirm it returns JSON, rather than a login redirect or access denial.
3. Open browser developer tools and select the Network panel. Reload the API URL and select its successful request. Locate the value of `Cookie` under Request Headers. Copy from the ODIP hostname, not the identity or platform hostname. Preserve the complete value without URL decoding or truncation. Do not use `document.cookie`: it omits HttpOnly authentication cookies.
4. Start the following commands in WSL. While the confirmation prompt waits, copy only the browser's Cookie header value to the Windows clipboard. Return to the terminal and press Enter without pasting. Copying after starting the script prevents its own code from occupying the clipboard when it reads the header. The cookie values are not echoed or entered as shell command arguments. For another installation, replace the ODIP origin before running the commands.

```bash
export ODIP_API_URL="https://web-odip.apps.eseidinger.de"
export ODIP_IDENTITY_MODE=platform
export ODIP_OPERATOR_COOKIE_FILE="$(mktemp /tmp/odip-operator-cookies.XXXXXX)"

python3 scripts/capture-operator-session.py
```

Run these commands from the repository root. The [capture script](../scripts/capture-operator-session.py) reads the Windows clipboard through `powershell.exe`, validates the three required platform cookies and the publisher's cookie-file format, and saves the file with owner-only permissions (`600`). It never prints cookie values. The empty expiry column represents session cookies; it does not extend the platform's session lifetime. Keep using the same terminal so the environment variables remain available, and clear the copied cookie value from your clipboard after creating the file.

For the local Developer Platform installation, use `https://web-odip-test-local.apps.localhost` for both browser URLs above and set the following variables before capturing the session:

```bash
export ODIP_API_URL="https://web-odip-test-local.apps.localhost"
export REQUESTS_CA_BUNDLE="$HOME/dev/developer-platform/.runtime/trust/local-ca.pem"
```

Adjust the CA path to your Developer Platform checkout. Retain `ODIP_IDENTITY_MODE=platform` for this deployed local installation. If the session expires, rerun the capture script with fresh browser cookies, then repeat the session check below.

### Check the operator session

From the repository root, run this read-only probe. It reports only the identity mode, sent cookie names, HTTP status, and redirect path, never the cookie values or full redirect URL:

```bash
uv run --project workers/data-worker --locked python - <<'PY'
import os
import requests
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
from odip_worker.fixtures import operator_session

base = os.environ["ODIP_API_URL"].rstrip("/")
session = operator_session(base)
request = session.prepare_request(requests.Request("GET", base + "/api/datasets"))
print("Identity mode:", os.getenv("ODIP_IDENTITY_MODE", "platform"))
print("Sent cookie names:", sorted(SimpleCookie(request.headers.get("Cookie", ""))))
response = session.send(request, timeout=(10, 30), allow_redirects=False)
print("HTTP:", response.status_code)
print("Redirect path:", urlsplit(response.headers.get("Location", "")).path)
PY
```

Proceed only after `HTTP: 200`. A `302` redirect to `/oauth2/start` means the platform did not accept the browser session, even if all three cookie names were sent. Sessions expire after 30 minutes of inactivity or eight hours overall; a change to the policy's session epoch also invalidates them. Sign out and back in, confirm the browser API request succeeds, and recreate the file from that fresh request. If the browser returns JSON but the probe still redirects, investigate the export rather than enabling development mode or following redirects automatically. An HTTP `403` requires checking operator approval and route access before proceeding.

### Run the fixture publisher

From the same terminal and repository root, use the deployed scheduled worker for validation:

```bash
uv run --project workers/data-worker --locked python -m odip_worker.fixtures \
  --api-url "$ODIP_API_URL" --fixture all
```

The publisher captures raw inputs through the operator API, derives the energy artifacts from the pinned source, attaches canonical bytes, and records publication lineage. It reuses existing identical drafts on retries. Consumer discovery and downloads use the pinned [read contract](../contracts/vendor/contract-kit-v0.5.0/contract-kit/openapi/odip-publication-v1.yaml); draft and validation operations use the [operator contract](../contracts/openapi/publication-operations.json).

Use `--fixture energy` to publish only the energy reference dataset. The publisher
uses bundled pinned source bytes and registers their GitHub provenance URL;
`github.com` must be included in `ODIP_SOURCE_HOSTS`. This fixture upload does not
require the worker to download the PVGIS source over the network. External
outbound entries still undergo platform policy validation when declared.

For local worker grants, inspect `devplat --profile odip-local --output json access
services list --project odip-test-local`, find `odip-test-local-worker`, and use its
`spec.principalId` in Publications → Dataset access. The service request ID and
managed secret prefix are separate values.

For a new catalog, the publisher registers both datasets before queueing validation. In Publications, grant the approved worker principal READ, INGEST, and VALIDATE on those datasets so the scheduled worker can process them. The optional `--validate` flag instead consumes validation jobs locally and requires the worker's managed binding variables on that host; it is not needed for the deployed-worker path above.

When setup is complete, remove the temporary credential file and unset its reference:

```bash
rm -- "$ODIP_OPERATOR_COOKIE_FILE"
unset ODIP_OPERATOR_COOKIE_FILE
```

For local development, explicitly set `ODIP_IDENTITY_MODE=development`. The development API accepts synthetic context formats, while production requires the normalized platform formats. Do not configure development bypasses in a deployment.

## Readiness and operations

Readiness includes PostgreSQL; liveness retains process-health semantics. Expired publication claims are released after five minutes with a new claim nonce on the next assignment. Stuck ingestion runs become FAILED after five minutes and retain diagnostics; an operator with INGEST permission queues a fresh run rather than replaying terminal transitions. Operators cannot fail another principal's job or bypass claims. Every ingestion completion, including manually started runs, requires the owning principal, its current INGEST grant, and the returned claim token. Completion retries must retain the same bytes. Atomic reference-input capture uses its server-generated claim internally.

Metrics include publication outcomes, duration, and retrieval count. Application audit records associate dataset/publication actions with stable principals and opaque correlation IDs. Central logs contain only compact platform operational envelopes. Customer details, domain IDs, and credentials do not enter those envelopes.

The API console uses Spring Boot's Logstash JSON format, with the text startup banner disabled. Existing request envelopes retain their minimized JSON shape for platform collection. The ingestion worker emits one JSON object per log line, including library messages and job lifecycle events. Worker failures report the exception type and a fixed diagnostic without exception messages or raw tracebacks. The image passes its temporary-directory JVM option directly to Java to avoid the plain-text `JAVA_TOOL_OPTIONS` startup announcement.

Supported publications retain their bytes, provenance, reports, and lineage. A protected operator can record a future support-end date at `PUT /api/v1/publication-retention`; expiration is permitted only after the additional one-year grace period. The scheduled cleanup removes expired publication outputs and retains raw inputs. Application audit rows expire after 180 days. Backups are governed separately by platform retention and can contain expired rows until the backup itself expires.

## Deployed handoff and regression gates

The maintainer confirmed all remaining ODIP handoff items complete on October 19, 2026, for ODIP 0.5.0 and contract kit 0.5.0. See the [completion record](energy-configuration-integration-plan.md#completion-criteria) for the acceptance scope and evidence limits. The instructions and checks below remain applicable to new installations and release regression; Gate 6 AI acceptance remains separate.

After both reference versions are `PUBLISHED`, confirm that VEF's separate service-access request is active and grant its stable principal `READ` on the energy dataset alone. VEF must exercise authenticated retrieval, integrity checks, and denial of the non-energy dataset through its own deployed integration tests; publication and grants alone do not establish those results.

### Handoff values for VEF

Record these values from the **deployed revision and published data**. The pinned fixture values below provide an exact comparison target; do not substitute the repository's current `HEAD` for the revision actually running.

| Field | Value or source |
| --- | --- |
| Contract kit | `0.5.0`; SHA-256 of `contracts/vendor/contract-kit-v0.5.0.tar.gz`: `ae4edaf6799d4b57510d14d2004c5b65ff6b05f3b225e96bbd5971b30ce8832b`, as pinned in `scripts/verify-contract-kit.py`. |
| ODIP application revision and images | Record the deployed 40-character Git revision and the **resolved OCI digests** for both `docker.io/eseidinger/odip-platform` and `docker.io/eseidinger/odip-data-worker` from the active deployment/registry; a mutable tag alone is insufficient. |
| Consumer endpoint and identity | `https://web-odip.apps.eseidinger.de`; record VEF's approved service-access resource, stable principal ID, reader group ID, and non-secret binding prefix. Keep client ID/secret, token, and operator cookies out of the handoff. |
| Energy publication | Public dataset ID `energy-reference-wasserburg-am-inn-2024`, version `1.0.0`, `schemaRef` `urn:portfolio:energy-configuration-input:v1`, manifest SHA-256 `252b90b18b594a764a2744ba133a8db56b233e9e375301befc7616e9c18c1715`. The five artifact IDs and digests are in its pinned manifest; record or link that manifest as the authoritative list. |
| Reference input | Pinned PVGIS source-byte SHA-256 `d82aff39f867cb3cd77f7f355ec164b2d43c19d27bb86b13e87306885d082f29`; deployed raw-artifact ID and run ID come from the actual publication lineage. |
| Domain-neutral control | Non-energy dataset `non-energy-mobility-counts-2024`, version `1.0.0`, manifest SHA-256 `f0d4f6b882c1a05154fb43283166953fda7a0dba7f2ed435dd7f46088663bbff`. VEF's reader identity must receive `403` for it. |
| Acceptance evidence | Record UTC timestamps, the deployed revisions, and links/IDs for VEF's authenticated retrieval, integrity, dataset-scope, and write-denial tests and the separate gate evidence below. Leave unrun checks open; record failures without credential-bearing request/response bodies. |

The two manifest digests and the raw-source digest are pinned in [the fixture index](../contracts/vendor/contract-kit-v0.5.0/contract-kit/fixtures/index.json). The manifest and its artifact digests are the data contract VEF consumes; the internal dataset UUID and raw-artifact UUID are lineage evidence, not substitutes for the public ID/version.

### Deployed acceptance regression gates

Gate 5 was accepted by maintainer direction on October 17, 2026 in the [upstream acceptance record](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.5.0/reviews/2026-10-17-gate-5-acceptance.md). That decision did not add new deployment digests or test reports. The following checks remain the regression/evidence checklist for new deployments and the Gate 6 AI increment; they do not reopen that accepted progression.

These are deployed acceptance checks from [the pinned integration plan](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.5.0/energy-configuration-integration-plan.md#4-ordered-integration-steps), especially Gates 4 and 5. Record a result and evidence reference for each; leave an unrun check open.

| Gate | Responsible boundary | Passing evidence |
| --- | --- | --- |
| Service identity lifecycle | Developer Platform and VEF | Exercise a real replacement reader binding, confirm VEF adopts it without changing its stable dataset grant, and verify the old client loses access after confirmation or revocation. Normal overlap is at most 24 hours; include an emergency revocation case, issued-token denial, and an owner for the at-least-every-90-days rotation schedule. |
| Network and backend isolation | Developer Platform | VEF reaches ODIP only through approved HTTPS and its token endpoint; a direct request to ODIP's private backend, including from another same-project component, and an unrelated outbound destination are denied. Record the applied DNS/address pins and any reapply after DNS changes. |
| Access dependency failure | Developer Platform, ODIP, and VEF | Verify protected routes fail closed during platform authorization unavailability; distinguish a boundary `503` from ODIP readiness or an application error. VEF may reuse only a previously verified cached version when ODIP is unavailable. |
| Monitoring and retained logs | Developer Platform and application owners | Observe the protected boundary probe separately from Kubernetes readiness; emit an opaque correlation ID, read its minimized event through project-authorized retained-log access, deny a foreign-project read, and verify retained readback after pod retirement/restart. Treat `state: unavailable` as failure even if the log API returns HTTP `200`; seven-day expiry and compactor behavior need elapsed evidence. |
| Restart and actual restoration | ODIP, VEF, and Developer Platform | After restart and a real platform backup restore, retrieve identical manifest/artifact bytes and lineage, restore VEF's verified input/result, and reconcile access catalog, service credentials, grants, and revocation state before protected routes reopen. A local dump/restore or pod restart alone is not this gate. |
| Cross-project use-case suite | ODIP and VEF | Run the shared energy and non-energy fixtures through deployed ODIP, then verify VEF's independent import/cache, exact feasible set and numerical results, tamper/unit/missing-hour/unsupported-schema denials, `1.0.0` versus corrected `1.0.1` isolation, and reproducibility after outage and restore. VEF's later AI proposal and explanation acceptance belongs to Gate 6. |

The handoff values, local verification, and container builds do not close these deployed gates.

## October 27 guided test result

The operator additionally confirmed that isolated partial-calendar version
1.0.90 is FAILED with `profile_validation_failed`; see the cross-project
guided record below for its manifest digest and 4,368-hour construction.
Reading an existing non-published version returns contract-defined HTTP 409.
VEF initially misclassified this as 503; correction `561887e` passed CI and
deployment in run `40502827158`. The operator's hosted retest returned 422
`publication_not_published`, with no run ID in the supplied error envelope.
This completes the partial-calendar publication/state rejection scenario;
it does not prove independent VEF validation of invalid published bytes.

The operator subsequently reported missing-hour version 1.0.99 as FAILED after
the guided upload/validate steps. Its schema-valid, digest-matching PV series has
8,783 values in the 8,784-hour 2024 period. Hosted publication-status rejection
passes; the worker failure code/report was not separately captured. The guided
record below retains its digest. Wrong-unit version 1.0.91 was subsequently
rejected at upload with 422 `schema_validation_failed`, "Document fails schema
energy-import-tariff-v1". An earlier 422 `missing_artifact` prevented validation
before every upload succeeded. The wrong-unit upload rejection passes; the
earlier expected worker FAILED result was incorrect because upload schema
validation intervenes first. No worker report or FAILED status is claimed for
1.0.91. The subsequent upload of checksum-mismatch version 1.0.92 returned
422 `checksum_mismatch`,
"Artifact digest does not match the manifest". Hosted upload integrity rejection
therefore passes. Version 1.0.93 with unsupported energy publication schema v99
then returned 422 `unsupported_schema`, "Publication schema is not supported",
at draft creation. This hosted boundary check passes. The guided record links
the consolidated sanitized negative-case summary with hashes and capture limits.
Independent hosted VEF invalid-content validation remains open.

The [guided acceptance record](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-guided-release-acceptance.md) records successful publication and full VEF oracle comparisons for 1.0.0 and
corrected 1.0.1, plus unchanged original-run readback. The fixture has manifest
provenance but no captured raw-input links or matching ingestion run were
observed in this installation. Ordinary draft creation was used; do not claim
hosted raw capture or rewrite immutable 1.0.0. Remaining regression/recovery
and final deployment inventory remain open.

### Operational snapshot after renewed login

The [shared operational snapshot](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/evidence/2026-10-27-operational-checks.json)
records ready ODIP revision 10, both OCI sources `31c4602`, web image
`sha256:bf4648d452a4542cf18fda6d1d5b5b0b3b8a2fd600ce460e5594df988fd6ebef`
and worker image
`sha256:6acce327d1b15fc0223dddeb7a0f5e1e0f397f3b71a9a7dfbb2ca357465eca02`.
Service restart `2b197f8a-f634-4456-b357-bd496ecf5f8c` succeeded with one
ready replica, unchanged web image and replacement of the old web pod. The
scheduled worker remained active. The subsequent VEF corrected-version run
`run-36002a86-73ce-4445-bd66-aff03c7621f9` succeeded with the same recommendation,
194 feasible of 252, EUR 365.64 annualized cost, EUR 8,240 investment,
self-sufficiency 0.889509006, expected manifest digest and PROVEN_OPTIMAL.
The reported summary matches the independent corrected oracle; the functional
summary check passes. The operator then downloaded all five published artifacts
through ODIP's Download buttons. All five match the approved 1.0.1 manifest
digests and corrected-reference bytes exactly; the guided record links the
machine-readable verification and private evidence archive hash. The operator
artifact-readback check passes. Complete new candidate-page exports and consumer
manifest/ETag capture remain absent. S3 is enabled, but these reads alone do not
prove each artifact lacks a legacy database payload fallback.

HTTP metrics, current resource usage and retained logs are readable. Retired-pod
log envelopes and recent request correlation metadata were observed. Actual
elapsed log expiry and collector/compactor health remain open. The deployed
backend is S3 with active PostgreSQL and S3 bindings; joint database/object-version
restore is required for this installation. The installed tenant CLI only exposes
an operator-assistance request for recovery. No request was sent and no data
was restored. The final platform/source/image inventory must be pinned again
at release acceptance because test CI continues deploying automatically.
Read-only recovery preflight found the configured VM port 127.0.0.1:2222
unavailable, no local recovery VM directory and no /dev/kvm on this controller.
An isolated target and explicit verified snapshot must be selected before the
remaining database/bucket restore. No restore or new backup has been performed.
