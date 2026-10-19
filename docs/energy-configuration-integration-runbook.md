# Energy Configuration Integration Runbook

ODIP consumes contract kit 0.5.0, which preserves the accepted 0.4.0 publication contract and fixtures while adding VEF AI-assistance contracts. The reference fixture is Wasserburg am Inn, region `DE-BY-09187182`, with 8,784 hourly UTC intervals on the 2024 calendar. Its PV profile derives from pinned PVGIS 2023 data; the leap day, tariffs, load shape, and catalog follow the shared decisions. It is a regional demonstration rather than observed 2024 building production or a commercial offer.

For a new test or production installation, start with [Bootstrap environments](bootstrap.md). It covers the web-only first deployment, shared setup scripts and CI prerequisites in dependency order.

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
devplat profiles create odip-lab --api-url https://platform.eseidinger.de \
  --issuer https://identity.eseidinger.de/realms/platform --project odip
devplat --profile odip-lab auth login
```

If `odip-lab` already exists, inspect it with `devplat profiles show odip-lab` and reuse it rather than recreating it. Human login uses the CLI's device flow and secure OS keyring. Clear `PLATFORM_ACCESS_TOKEN`, `PLATFORM_TOKEN_ENDPOINT`, `PLATFORM_CLIENT_ID`, and `PLATFORM_CLIENT_SECRET` when using profile login: environment authentication takes precedence. On headless systems without a secure keyring, securely supply a short-lived administrator token in `PLATFORM_ACCESS_TOKEN` and set `PLATFORM_API_URL`. Tokens and credentials never belong in command-line arguments or source control. A deployment credential or hosted ODIP token cannot administer access policy.

#### Supply an administrator access token

Use this alternative on a headless host without a secure keyring. Obtain a short-lived Platform API access token for a human administrator of project `odip` through your installation's approved authentication process. For a manual session, you can copy it from your own authenticated Developer Platform portal: open browser developer tools, select the Network panel, and inspect a successful Platform API request, such as `GET /v1/projects/odip/application-access-context`. Copy only the token after `Bearer ` in its `Authorization` request header. Do not copy an ODIP application token, browser cookie, ID token, refresh token, or deployment client secret.

In an interactive Bash or WSL terminal, disable shell tracing and enter the token at a hidden prompt rather than putting its literal value in an `export` command:

```bash
set +x
unset PLATFORM_ACCESS_TOKEN PLATFORM_TOKEN_ENDPOINT PLATFORM_CLIENT_ID PLATFORM_CLIENT_SECRET
export PLATFORM_API_URL="https://platform.eseidinger.de"
read -r -s -p 'Platform administrator access token: ' PLATFORM_ACCESS_TOKEN
printf '\n'
: "${PLATFORM_ACCESS_TOKEN:?An administrator access token is required}"
export PLATFORM_ACCESS_TOKEN

devplat --output json auth status
devplat --output json access context --project odip
```

The authentication source should be `access-token-environment`. `auth status` reports the selected source without validating the token against the server; `access context` makes an authenticated read and lets you check project eligibility and access-policy administration permissions. If the token has expired, obtain a fresh one and repeat the hidden prompt. Supplying an environment token does not create a renewable keyring session. For non-interactive automation, have the approved secret mechanism inject `PLATFORM_ACCESS_TOKEN` and `PLATFORM_API_URL` into the process environment instead of using the prompt.

The hidden Bash prompt has the same terminal line-length limit described in [cookie file setup](#create-the-operator-cookie-file). For a token of 4,095 characters or more, use approved secret injection instead of pasting into that prompt. In WSL, another option is to run the following commands, copy only the fresh token from the browser while the prompt waits, and then press Enter without pasting. Keep shell tracing disabled:

```bash
set +x
read -r -s -p 'Copy the Platform API token now, then press Enter without pasting: '
printf '\n'
PLATFORM_ACCESS_TOKEN="$(powershell.exe -NoProfile -NonInteractive -Command 'Get-Clipboard -Raw' | tr -d '\r\n')"
: "${PLATFORM_ACCESS_TOKEN:?An administrator access token is required}"
export PLATFORM_ACCESS_TOKEN
devplat --output json auth status
devplat --output json access context --project odip
```

For the preview and apply commands below, replace `--profile odip-lab` with `--platform-url "$PLATFORM_API_URL"`. No CLI profile or `auth login` is required for this token path. For example, the read-only preview is:

```bash
python3 scripts/configure-access-policy.py \
  --platform-url "$PLATFORM_API_URL" --project odip
```

Keep using the same terminal for the reviewed apply. Do not print the token, store it in a profile or `.env` file, commit it, or share it in chat. Keep shell tracing disabled while it is in use, and clear it with `unset PLATFORM_ACCESS_TOKEN` after completing policy configuration or before switching back to profile login. Clear the copied token from your clipboard as well.

#### Preview and apply the policy

Preview the complete policy for the disposable installation:

```bash
python3 scripts/configure-access-policy.py \
  --profile odip-lab --project odip
```

The script checks the CLI version and authentication source, then uses `devplat access context`, `access groups list`, and `access policy get` with JSON output to validate eligibility and preview the policy. The preview lists missing groups under `groupsToCreate` without creating them; policy group references remain names until all stable IDs exist. With `--apply`, it creates missing `dataset-operators`, `dataset-readers`, and `ingestion-workers` groups from `infrastructure/integration/groups.json`, using project-specific idempotency keys, then reads back their active IDs before applying the policy. Existing active groups are reused; duplicate, inactive or malformed groups stop the operation. Group creation failures stop policy application and are never automatically retried. Select either `--project odip` or `--project odip-test`. `--platform-url` overrides the CLI profile's API origin when needed; otherwise the active or selected profile supplies it. HTTPS is required, and the script never requests insecure TLS. The CLI honors `PLATFORM_CA_BUNDLE` or the profile's CA bundle.

Review the preview, then apply it:

```bash
python3 scripts/configure-access-policy.py \
  --profile odip-lab --project odip --apply
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
python scripts/setup-storage.py --profile odip-lab --project odip
python scripts/setup-storage.py --profile odip-lab --project odip --apply \
  --update-descriptor infrastructure/deployments/application.json
```

The template `infrastructure/integration/odip-postgresql.json` requests a 1 GiB
resource named `database`. Use the same `--quota-bytes` allocation for preview and
apply. Existing resource configuration and bindings must match; the script never
changes quotas, migrates data or retries a failed write. `--update-descriptor`
saves the approved binding UUID in `web.bindings` with an empty `envPrefix`.
For test storage, use the same shared script with the test project and descriptor:

```bash
python scripts/setup-storage.py --profile odip-lab --project odip-test --apply \
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
devplat --profile odip-lab deploy apply --project odip-test --file infrastructure/deployments/application-test.json --wait
python scripts/render-release.py --version v0.4.1 > /tmp/odip-release.json
devplat --profile odip-lab deploy apply --project odip --file /tmp/odip-release.json --wait
```

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

python3 - <<'PY'
import os
import subprocess
from getpass import getpass
from http.cookies import SimpleCookie
from urllib.parse import urlsplit

getpass("Copy the fresh browser Cookie value now, then press Enter without pasting: ")
try:
    raw = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive",
         "-Command", "Get-Clipboard -Raw"],
        text=True, stderr=subprocess.DEVNULL,
    ).strip()
except (OSError, subprocess.CalledProcessError):
    raise SystemExit("Windows clipboard access failed. Check WSL PowerShell availability.") from None
if any(character in raw for character in "\r\n\t"):
    raise SystemExit("Clipboard must contain only the single-line Cookie header value.")
cookies = SimpleCookie()
cookies.load(raw)
required = {
    "__Host-platform-session",
    "__Host-platform-activity",
    "__Host-platform-csrf",
}
if not required.issubset(cookies) or any(not cookies[name].value for name in required):
    raise SystemExit("Missing platform cookies. Copy from an authenticated ODIP request.")

host = urlsplit(os.environ["ODIP_API_URL"]).hostname
lines = ["# Netscape HTTP Cookie File"]
for name, cookie in cookies.items():
    if name.startswith("__Host-platform-"):
        lines.append("\t".join(
            (host, "FALSE", "/", "TRUE", "", name, cookie.coded_value)
        ))

with open(os.environ["ODIP_OPERATOR_COOKIE_FILE"], "w", encoding="utf-8") as output:
    output.write("\n".join(lines) + "\n")
print("Cookie file created; captured header bytes:", len(raw.encode("utf-8")))
PY
```

`mktemp` creates an owner-only file with mode `600`. The empty expiry column represents session cookies; it does not extend the platform's session lifetime. Only the header length is displayed, not its contents. Keep using the same terminal so the environment variables remain available, and clear the copied cookie value from your clipboard after creating the file.

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

Supported publications retain their bytes, provenance, reports, and lineage. A protected operator can record a future support-end date at `PUT /api/v1/publication-retention`; expiration is permitted only after the additional one-year grace period. The scheduled cleanup removes expired publication outputs and retains raw inputs. Application audit rows expire after 180 days. Backups are governed separately by platform retention and can contain expired rows until the backup itself expires.

## Deployed handoff and remaining gates

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

### Remaining deployed acceptance gates

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
