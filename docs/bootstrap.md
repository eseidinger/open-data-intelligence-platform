# Bootstrap ODIP environments

Bootstrap `odip-test` and `odip` independently. Each project needs its own PostgreSQL
resource, application groups, access policy, worker service identity and CI
deployment credential. The first deployment runs only `web`: the platform needs
that application before it can configure access policy and issue worker credentials.
After worker access is active, deploy the complete application through GitHub Actions.

Run commands from the repository root. The examples use profile `odip-lab`, which
must have administrator access to the selected project. For an existing environment,
inspect its resources and skip completed steps; do not bootstrap an application that
already declares its worker.

## Environment mapping

| Setting | Test | Production |
| --- | --- | --- |
| Project | `odip-test` | `odip` |
| Descriptor | `infrastructure/deployments/application-test.json` | `infrastructure/deployments/application.json` |
| Images | `latest` | `__VERSION__`, rendered from a release tag |
| Public origin | `https://web-odip-test.apps.eseidinger.de` | `https://web-odip.apps.eseidinger.de` |
| GitHub environment | `test` | `production` |
| Deployment trigger | Push to `main` | Push a version tag such as `v0.4.1` |
| CI client ID secret | `PLATFORM_CLIENT_ID_TEST` | `PLATFORM_CLIENT_ID` |
| CI client secret | `PLATFORM_CLIENT_SECRET_TEST` | `PLATFORM_CLIENT_SECRET` |

The descriptors carry installation-owned non-secret binding references. An ID
already in Git is not proof that a binding exists in a new installation. Run storage
and worker setup against the actual project to obtain its own references. Never
copy production credentials or bindings to the test project.

## Prepare tools and authentication

Use Python 3.12 or newer and Developer Platform CLI 0.3.0. Upgrade the Python
environment that owns your existing `devplat` executable:

```bash
bash scripts/upgrade-devplat.sh /path/to/venv/bin/python
devplat --version
```

Create a profile if it does not exist, then authenticate:

```bash
devplat profiles create odip-lab --api-url https://platform.eseidinger.de \
  --issuer https://identity.eseidinger.de/realms/platform --project odip-test
devplat --profile odip-lab auth login
```

An existing profile can be reused for both projects: every setup command below
passes `--project` explicitly. Environment authentication takes precedence over a
profile login. Unset stale `PLATFORM_ACCESS_TOKEN`, `PLATFORM_TOKEN_ENDPOINT`,
`PLATFORM_CLIENT_ID` and `PLATFORM_CLIENT_SECRET` variables when using human login.
Headless sessions can use a securely supplied administrator `PLATFORM_ACCESS_TOKEN`
and `PLATFORM_API_URL`; see [administrator token setup](energy-configuration-integration-runbook.md#supply-an-administrator-access-token).
CI deployment credentials cannot administer groups, policies or worker access.

The platform operator must enable named PostgreSQL resources, provide sufficient
capacity, and permit the HTTPS destinations in each descriptor: its application
origin, identity endpoint and approved data sources. The API and worker images
must be public and already published before bootstrap. Test uses both `latest`
images; production uses both images at the same chosen release version.
The [container build guide](container-builds.md) describes manual image builds.
An initial CI run can publish images and then fail deployment while installation
bindings are incomplete; finish bootstrap before retrying that deployment.

## Create the projects

Inspect accessible projects, then create only those that are missing:

```bash
devplat --profile odip-lab projects list --output json
devplat --profile odip-lab projects create --project odip-test
devplat --profile odip-lab projects create --project odip
```

Project creation requires platform-administrator authority. Once the projects
exist, their administrators can perform the remaining setup. Existing projects
must not be retired. Run the following sequence for test first, then production.

## Provision PostgreSQL

Preview and apply test storage, saving its binding to the test descriptor:

```bash
python scripts/setup-storage.py --profile odip-lab --project odip-test
python scripts/setup-storage.py --profile odip-lab --project odip-test --apply \
  --update-descriptor infrastructure/deployments/application-test.json
```

Repeat for production:

```bash
python scripts/setup-storage.py --profile odip-lab --project odip
python scripts/setup-storage.py --profile odip-lab --project odip --apply \
  --update-descriptor infrastructure/deployments/application.json
```

The script creates or reuses a project-owned `database` resource and an active
read-write binding for `web`. The default logical allocation is 1 GiB; select a
reviewed allocation with `--quota-bytes` on both preview and apply. Existing name,
provider, quota, extensions and access must match; the script does not modify
quotas or migrate existing data. It waits for observed activation and saves an
unprefixed binding in `web.bindings`.

Only `web` receives `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` and `PGPASSWORD`.
The production Spring profile consumes these variables directly. Remove stale
`ODIP_DATABASE_*` overrides, which would take precedence. The worker receives no
PostgreSQL binding or credentials. Do not add database credentials to GitHub or Git.

## Bootstrap the web component

Previewing writes the web-only declaration to stdout without contacting the
platform. Apply deploys it and waits for readiness:

```bash
python scripts/bootstrap-deployment.py --project odip-test
python scripts/bootstrap-deployment.py --profile odip-lab --project odip-test --apply
```

For production, specify an already published release version. Replace `v0.4.1`
with the release you intend to deploy:

```bash
python scripts/bootstrap-deployment.py --project odip --version v0.4.1
python scripts/bootstrap-deployment.py --profile odip-lab --project odip \
  --version v0.4.1 --apply
```

The helper uses the saved database binding, excludes the scheduled worker and
removes worker-prefix configuration from the submitted declaration. It never
changes the checked-in descriptor. Readiness includes PostgreSQL and migrations.
Public access remains denied until policy and user membership are configured.
If the platform already declares `ingestion-worker`, the helper stops before any
write; use normal full deployment for that environment instead.

## Configure groups and route policy

Preview and apply the policy independently for each deployed application:

```bash
python scripts/configure-access-policy.py --profile odip-lab --project odip-test
python scripts/configure-access-policy.py --profile odip-lab --project odip-test --apply

python scripts/configure-access-policy.py --profile odip-lab --project odip
python scripts/configure-access-policy.py --profile odip-lab --project odip --apply
```

Apply creates missing `dataset-operators`, `dataset-readers` and `ingestion-workers`
groups, resolves their active IDs and saves the complete reviewed route policy.
Existing active groups are reused. Preview lists missing groups without creating
them. Applying can replace manually added policy rules. Group creation and policy
configuration do not approve a human or worker identity.

Review and record each project's governance using the installation's policy:

```bash
devplat --profile odip-lab governance replace --project odip-test \
  --file infrastructure/integration/odip-governance.json
devplat --profile odip-lab governance replace --project odip \
  --file infrastructure/integration/odip-governance.json
```

The supplied governance template declares Internal classification, no personal
data, and domain retention/recovery ownership. Review these values before applying
them. The access policy does not release email attributes by default.

## Configure the worker identities

Preview and apply worker access for each project:

```bash
python scripts/configure-worker-access.py --profile odip-lab --project odip-test
python scripts/configure-worker-access.py --profile odip-lab --project odip-test --apply

python scripts/configure-worker-access.py --profile odip-lab --project odip
python scripts/configure-worker-access.py --profile odip-lab --project odip --apply
```

This helper requests a project-wide service identity named `<project>-worker`
targeting that same project, approves it only for `ingestion-workers`, waits for
activation and saves its `spec.secretPrefix` as `ODIP_WORKER_BINDING_PREFIX` in
the appropriate descriptor. Repeat runs reuse matching active requests and can
resume pending/provisioning requests. Inactive, conflicting or overprivileged
requests stop setup for review. Preview performs authenticated reads without
creating or approving access or changing files.

The platform injects `<prefix>_CLIENT_ID`, `<prefix>_CLIENT_SECRET` and
`<prefix>_TOKEN_URL`. The worker uses them to obtain a short-lived application
token. Output contains only non-secret IDs and the managed prefix; the helper
never retrieves credential values. It does not deploy the worker. Test and
production must have different worker identities and prefixes.

## Configure CI and deploy the full application

Create separate project-scoped deployment credentials in the platform portal,
one for each project, and save their returned client IDs/secrets under the names
in the environment table. Configure GitHub environments `test` and `production`
with `PLATFORM_API_URL` and `PLATFORM_TOKEN_ENDPOINT` variables. Both use the same
platform endpoints in this installation. Add repository secret `DOCKERHUB_TOKEN`
for image publication. Rotate expiring deployment credentials through the platform;
do not use the worker credentials or an administrator's token for CI.

Review and commit the bootstrap documentation/scripts, workflow changes, and each
descriptor's saved non-secret PostgreSQL binding and worker prefix. In a new
installation these changes must include the actual installation's own references.

- Push to `main` to build/publish both `latest` images and deploy `odip-test`.
- Push a version tag, such as `v0.4.1`, to build/publish versioned images and deploy
  `odip`. The release renderer fills both `:__VERSION__` placeholders in a temporary
  production declaration. Keep the placeholders in Git. Release builds leave
  `latest` unchanged.

If the images are already published, full manual deployment is also available:

```bash
devplat --profile odip-lab deploy apply --project odip-test \
  --file infrastructure/deployments/application-test.json --wait
python scripts/render-release.py --version v0.4.1 > /tmp/odip-release.json
devplat --profile odip-lab deploy apply --project odip --file /tmp/odip-release.json --wait
```

## Approve humans and verify ingestion

Open the selected application's public origin and complete first login. An
administrator must approve that request with `dataset-operators`; a platform
role alone does not grant application access. Inspect pending requests and approve
the appropriate ID for each environment:

```bash
devplat --profile odip-lab access human-requests list --project odip-test --output json
devplat --profile odip-lab access human-requests approve REQUEST_ID \
  --project odip-test --group dataset-operators --wait
```

Use `--project odip` for production. Confirm that the approved operator can access
the UI and that unauthorized identities remain denied. Register test data and
grant the environment's worker principal READ, INGEST and VALIDATE on its assigned
datasets through the Publications UI. The worker setup output includes its stable
`principal_id`. Dataset grants remain separate from platform group membership;
without them, an authenticated worker still cannot process those datasets.

Inspect readiness, scheduled runs and bounded logs:

```bash
devplat --profile odip-lab components list --project odip-test --output json
devplat --profile odip-lab logs --project odip-test --component web --tail 50
devplat --profile odip-lab logs --project odip-test --component ingestion-worker --tail 50
```

Repeat for `odip`. Verify a representative claim, ingestion and publication in test
before using production data. Follow the [integration runbook](energy-configuration-integration-runbook.md)
for dataset grants, publication verification and the VEF handoff.

## Recover interrupted setup

Exit code 3 means authentication failed: sign in again, or replace/unset an expired
`PLATFORM_ACCESS_TOKEN`. Exit code 4 means the selected identity lacks permission.
A timeout does not cancel an accepted platform operation. Inspect operations and
resource state before rerunning; helpers never automatically retry uncertain
writes. Storage and worker setup discover matching resources on the next run.
Their `--wait-seconds` options accept 1–600 seconds.

If storage was created without `--update-descriptor`, rerun with that option to
save its existing binding. If a policy is missing, bootstrap `web` before configuring
access. If a worker prefix is missing, apply worker access and commit the updated
descriptor before retrying CI. Removing an application does not purge its named
PostgreSQL data; retirement, purge, credential rotation, and database migration are
separate operations.
