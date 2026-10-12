# Developer Platform compatibility profile

Kit `0.4.0` was reconciled on 2026-10-11 against the current GitHub default
branch, revision
[`b360ddee34444748c95705c597aa7b17491cd05b`](https://github.com/eseidinger/developer-platform/tree/b360ddee34444748c95705c597aa7b17491cd05b).
`baseline.json` records source-file checksums (UTF-8 with LF line endings,
independent of Git checkout newline conversion) and the bounded upstream acceptance
evidence. This is a source compatibility pin, not a claim about the version of
an installation's running control plane.

## Breaking changes from `0.2.0`

| Earlier integration assumption | Reconciled implementation contract |
| --- | --- |
| Dedicated `energy-system` realm; fixed `odip-api`/`vef-odip-reader` clients and `dataset.read` OAuth role/scope | Environment realm, platform-derived clients/audience, provider-approved application groups; no application OAuth scopes. |
| ODIP validates JWTs and retrieves Keycloak JWKS | Platform boundary validates tokens and route groups; ODIP receives trusted normalized headers and applies finer dataset authorization. |
| VEF user API uses direct OIDC bearer authentication | Browser-session routes with explicit human approval, CSRF token, and same-origin mutations. Machine access requires separate routes. |
| Secrets isolated to an individual component | Managed service binding is project-wide; every component in the consumer project may receive it. |
| Every API failure uses domain `error/v1` | Access layer returns its own `application_access_*` body; browser login redirects, and access dependency failures may return `503`. |
| Blanket encrypted application transport | Public cross-project HTTPS is encrypted; application PostgreSQL transport has no TLS in the lab profile. |
| 30-day logs and backups, universal 180-day audit expiry | Minimized central envelopes with seven-day configured storage; deployed and elapsed-retention acceptance remain open. Tiered backups and append-only platform audit without automatic expiry. Applications retain ownership of domain-row cleanup. |

Energy schema majors, artifact bytes and digests, canonicalization, simulations,
optimization results, and the reviewed `0.2.0` numerical oracle are unchanged.
Consumers must upgrade the security/deployment integration when pinning the new
kit. Existing tags or release artifacts must not be overwritten. Kit `0.4.0`
still needs maintainer review, immutable publication, and consumer CI pins.

## Additions since `0.3.0`

Upstream commit `b360dde` implements component-aware monitoring, minimized
central workload logs, and authorized retained-log reads. Kit `0.4.0` adds a
log-emission schema/example and reconciles those operational obligations; it is
an additive minor release under DEC-06. Deployment, access-policy, governance,
and rotation input schemas remain byte-identical to the previous pin. Hosted
identity behavior and the domain API descriptions are unchanged.

The `baseline.json` acceptance record still describes historical EV-45 at
runner `e8f74fd`, not acceptance of the new monitoring/logging implementation.
Its nine deferred checks remain open. The separate `observability` entry records
source implementation and configured retention with no claimed deployed or
elapsed-retention acceptance.

## Executable files

`upstream-inputs.schema.json` is a generated, self-contained projection of only
the consumed input schemas and their transitive references from the producer's
`docs/api/openapi.json`. `examples.json` indexes request bodies by upstream model
name. No platform Python, Kubernetes, identity provider, or network dependency
is needed to validate their shapes in the normal kit test runner.

The snapshot does **not** encode Pydantic runtime checks such as route overlap,
cron parsing, one public component, configuration-name restrictions, readiness
port selection, DNS resolution/operator allow-lists, or aggregate quota/surge
admission. The platform must also accept a rendered declaration in the target
installation. Kit tests check cross-contract route coverage and selected
unsupported inputs; they are not deployed isolation or authorization evidence.

To regenerate or check the snapshot from an exact local checkout, run from
`contract-kit/`:

```text
uv run --frozen python -m tools.build_platform_snapshot /path/to/developer-platform
uv run --frozen python -m tools.build_platform_snapshot /path/to/developer-platform --check
```

The tool rejects another revision or modified reviewed source files. A future
platform reconciliation updates the pin and checksums through review before
regeneration. The builder rewrites only the snapshot; it does not edit domain
fixtures or expected numerical results.

`../schemas/platform-principal-headers-v1.schema.json` checks the canonicalized
identity-header object emitted by this pinned implementation. Only the selected
reserved identity headers belong in that object; HTTP names are case-insensitive
and adapters must reject duplicate values before canonicalizing. Shape checks
alone do not establish trust. Direct backend access must be denied by the
platform, including from another same-project component. Required stable context
includes principal ID/kind, issuer, subject, and space-delimited group IDs; a
service additionally needs client ID. Optional name/email are disabled here.

## Render and apply

The JSON files are illustrative control-plane inputs. Image tags denote required
application-owned deliverables, not existing images. Replace them with actual
publicly pullable OCI images and record resolved digests. Replace reserved
`example.invalid` hosts with the installation's platform-owned origins. Source
hostnames are not supplied by publications. Use runtime entrypoints/commands and
readiness endpoints that the actual images implement. A scheduled ODIP worker
must exit after each bounded run; if the real worker is long-lived, declare it as
a private service instead.

1. Apply `odip-application.json` to `PUT /projects/odip` and
   `vef-application.json` to `PUT /projects/vef`. ODIP API and worker share one
   project/database; VEF has a separate project/database. Each has one public
   `api` component and uses `platform.example/v1alpha2`. Readiness is private,
   schedules do not wait for service readiness, and jobs retry transient errors.
2. Submit each `*-governance.json` to `PUT /v1/projects/{project}/governance`.
   Governance, deployment, and access policy are separate resources. Updates to
   governance/access resources use the returned ETag in `If-Match`; application
   deployment revisions use their own concurrency contract.
3. Create groups using `POST /v1/projects/{project}/application-groups` with
   the matching `*-group.json` and a caller-chosen `Idempotency-Key`. Record
   returned stable group IDs. Policies and approval bodies may resolve group
   names during provisioning, as the examples do; runtime authorization and
   domain grants use stable IDs. Renaming a display attribute must not change
   authority. The writer group is provisioned for future write workflows but is
   not assigned to VEF or exposed by this reader policy.
4. Apply `*-access-policy.json` to
   `PUT /v1/projects/{project}/applications/{project}/access-policy` and wait for
   the returned access operation to succeed and the policy to be active.
   ODIP exposes only bearer-authenticated GET dataset routes; no anonymous or
   write route exists in this profile. VEF exposes browser-authenticated runs,
   capabilities, the root UI entry, and UI assets under `/ui`. Add further UI or
   administration paths explicitly with non-overlapping method/path matches.
   `HEAD` follows `GET`; `OPTIONS` is denied unless explicitly declared.
5. Submit `vef-odip-service-request.json` to
   `POST /v1/projects/vef/service-access-requests` with `Idempotency-Key`.
   As ODIP project administrator, approve its returned resource ID using
   `POST /v1/projects/odip/service-access-requests/{id}/approve`,
   `odip-service-approval.json`, and the request's current ETag in `If-Match`.
   Wait for active service access before using the credential. Ordinary reads
   contain safe metadata, not secret values.
6. Configure VEF to read the resource's managed `secretPrefix` binding:
   `<prefix>_CLIENT_ID`, `<prefix>_CLIENT_SECRET`, and `<prefix>_TOKEN_URL`.
   These names are platform-generated, not normal readable configuration values.
   Configure ODIP's local read-only dataset grant for the resource's stable
   principal ID. The platform has no energy-dataset authorization store.
7. Enroll VEF humans by first browser login and explicit administrator approval
   of pending requests. A platform administrator receives no automatic
   application membership. Use stable principal ID for run ownership and
   idempotency scope. For mutations, send the managed `__Host-platform-csrf`
   cookie value as `X-Platform-CSRF-Token` and the exact application's HTTPS
   `Origin`. Do not create application-owned session credentials.
8. Exercise service rotation with `normal-rotation.json` at
   `POST /v1/projects/vef/service-access-requests/{id}/rotate`; consume the new
   binding and call the same resource's `/confirm` endpoint with its current
   `If-Match`. Normal overlap is at most 24 hours; emergency rotation sets
   `emergency: true` and revokes without overlap. Arrange the integration's
   at-least-90-day rotation schedule separately.

VEF declares only ODIP and the token host on TCP 443. Operators approve every
resolved address and port. DNS egress pins addresses at apply time; changed
addresses require reapply. No ODIP-side identity-provider exception is necessary
for inbound authentication. Real ingestion source destinations are declared on
the worker separately; the synthetic/local reference publication needs none.

Per-component limits and replica counts must fit the installation's aggregate
quota including rollout surge. Restricted workloads have a read-only root,
non-root UID, and bounded ephemeral `/tmp`; the current profile offers no
application PVC. Store immutable ODIP artifact bytes in backed-up PostgreSQL or
separately provision supported durable storage. Do not treat a pod filesystem
as retained publication storage.

## Component monitoring and central operational logs

Public `v1alpha2` probes use the component hostname and declared readiness path.
Private services and scheduled components have no public probe. A protected
probe carries no credential, never follows login redirects, and treats only
`302`, `401`, or `403` as boundary reachability success; backend `200` and
policy-unavailable `503` fail that probe. Success therefore proves routing/TLS
and a protected boundary, not backend readiness or an authorized dataset fetch.
Kubernetes readiness and `ApplicationComponentNotReady` supply a separate health
signal. Add no anonymous health policy or implicit monitoring membership.

Applications emit the schema in
`../schemas/platform-operational-envelope-v1.schema.json` as compact JSON on
stdout/stderr, within the collector's 4 KB line limit:

```json
{"event":"request.completed","level":"info","correlationId":"0123456789abcdef0123456789abcdef"}
```

Events use `application`, `request`, or `job` plus `.started`, `.ready`,
`.completed`, or `.failed`. Levels are `debug`, `info`, `warning`, or `error`.
Correlation is absent, empty, lowercase 32-hex, or a lowercase UUID-shaped
identifier. It is opaque and application-owned, classified Internal in the
reference governance. Propagate it between VEF and ODIP and record its association
with dataset/version/run in application-owned evidence; the platform neither
interprets those domain IDs nor retains them as central envelope fields.
Do not encode customer identifiers, payloads, or credentials in correlation.

Alloy reads attributed project pod logs using a dedicated read-only Kubernetes
credential, not a provisioner credential or application token. Unknown fields
are stripped; malformed JSON, invalid envelopes, oversized lines, and free text
are dropped from central workload storage. This kit's stricter **emission**
schema rejects extra fields so applications emit the minimized form directly;
it does not claim the upstream collector rejects every unknown field.
Arbitrary application text remains best-effort kubelet diagnostics. Collection
or write outages may lose entries; retention does not guarantee delivery.

New/restarted workloads carry platform-derived revision/operation annotations.
These become non-indexed log metadata; existing pods need reapply/restart to
acquire them. Correlation/operation IDs are not metric or stream-index labels.
Project/application/component/pod attribution is supplied by the collector,
not by business payloads or new ApplicationSpec fields. Workload usage scrapes,
application-specific request metrics, and distributed tracing remain separate
work; central logs do not implement them.

Read retained entries through authenticated control-plane
`GET /projects/{name}/retained-logs`, requiring project `view` authority. This
is a Platform API route, not an ODIP/VEF application route or service-group
permission. Shared Loki/Grafana remain operator-only. The API fixes the project
and namespace selector, revalidates backend streams/envelopes, and audits reads;
it accepts no user LogQL or backend URL. Supported query parameters are `tail`
(default 200, range 1–1000), `since_seconds` (default 604800, range 1–604800), `component`,
`instance` (pod name), `after`, and `before`. Time filters are bounded to the
retention window; `after` may use the returned nanosecond `next_cursor` and is
exclusive. Unknown projects return `404`, undeployed projects `409`, and invalid
queries `422`; ordinary control-plane authentication/permission checks also apply.

Read success returns `lines`, `truncated`, `next_cursor`, `observed_at`, and a
retention object with `source: loki`, `seconds: 604800`,
`format: operational-envelope-v1`, and `state: configured`. State `ok` means
entries were returned; `no_output` means a successful empty read. **Backend
failure also returns HTTP `200`, but with `state: unavailable`,
`reason: CentralLogUnavailable`, and no entries.** Consumers must inspect that
state and not interpret it as a successful empty result. No raw backend error
or unsafe original line is returned.

The upstream hosted-access harness adds `--monitoring` checks for component
probes, Kubernetes readiness, and provider/consumer retained correlation. It
requires deploying the new source and publishing a new envelope-emitting fixture
digest; the EV-45 fixture is insufficient. Even successful immediate ingestion
keeps monitoring/retention deferred: deployed readback after retirement/restart,
seven-day expiry, and compactor deletion delay still need recorded evidence.

## Evidence and remaining gates

The pinned source preserves the historical 2026-10-11 neutral hosted-access run with 39 named
checks passing and `gateClosed: false`. Its runner revision was
`e8f74fdd522ab18bd06ffed06073525494a90345`; the report does not identify the
deployed control-plane source revision. The test covered core browser/service
approval, identity stripping, IPv4 backend/egress isolation, restart persistence,
policy rollback, rotation, token expiry, and revocation. IPv6 address pins alone
do not prove IPv6 enforcement. These are upstream-reported observations, not
checks rerun by this kit reconciliation.

Nine checks remain deferred in that evidence: real backup restore, full browser
idle/absolute expiry, the 24-hour adoption timeout, 30/90-day access retention,
component monitoring/centralized logs, control-plane outage, DNS-change reapply,
recovery reconciliation, and the external use-case suite. Gate 4/5 must supply
the applicable deployed evidence and the real energy workflow. Do not infer
application images, domain permissions, artifact durability, restore success,
or completed energy acceptance from a source schema or a neutral fixture.

Applications enforce ODIP supported-lifetime-plus-one-year and VEF 180-day row
retention. Platform retirement retains databases until an authorized purge;
backups retain the latest verified snapshot plus 14 daily, 8 weekly, and 6
monthly points. Domain-row deletion therefore does not immediately delete backup
copies. Minimized central workload logs have seven-day retention configured,
with deployed ingestion and elapsed-retention acceptance still open; platform
audit is append-only with no automatic expiry. Recovery
must reconcile catalog, clients, groups, credentials, and denial state before
reopening protected routes and invalidate restored browser sessions.

Sources: [operational log implementation](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/platform/app/retained_logs.py),
[monitoring/logging contract](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/infrastructure/monitoring/README.md),
[application declaration](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/platform/app/spec.py),
[access intent](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/platform/app/access_contract.py),
[header enforcement](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/platform/app/access_gateway.py),
[ADR-020](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/docs/architecture/decisions/ADR-020-generic-hosted-application-integration.md),
[recorded acceptance](https://github.com/eseidinger/developer-platform/blob/b360ddee34444748c95705c597aa7b17491cd05b/docs/operators/validation/access-and-authorization.md).
