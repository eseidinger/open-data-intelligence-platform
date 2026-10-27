# Energy Configuration Integration Plan

Current acceptance scope: the maintainer accepts the other listed non-AI points without further testing under [DEC-11](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-11-current-release-non-ai-acceptance-exceptions.md). They are ACCEPTED_EXCEPTION, not demonstrated passes. Hosted AI-05/06 and AI-08/11 pass within recorded evidence limits. A private hosted VEF AI-10 probe passes ten verifier/client/optimizer checks against synthetic ODIP fixtures; the complete unchanged deployed Gate 5 suite remains unrecorded as one run. AI-10 and final Gate 6 stay open. This supersedes older non-AI release-check prerequisites and chronological case counts below.

Subsequent protected VEF runs on AI-enabled revision 45 pass both full original
and corrected 252-candidate oracles. ODIP's non-energy publication matches its
pinned manifest hash. The energy source is linked to its dataset, but an energy
pipeline attempt failed with `NewConnectionError`; the registered source URL is
a GitHub release page rather than the pinned PVGIS raw JSON. No successful raw
artifact or publication input link is inferred. See the
[current-image report](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/evidence/2026-10-27-ai10-current-image-oracles.json).

The isolated synthetic dataset `energy-ai10-lineage-20261027/1.0.0` then passed
protected capture of the pinned PVGIS JSON, worker validation/publication,
raw-byte readback and all five artifact digests. The temporary worker grants
were removed after publication by operator confirmation. This does not add
raw-input links to immutable reference versions or fix the catalog URL's
scheduled download. The [sanitized lineage record](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/evidence/2026-10-27-ai10-isolated-lineage.json)
keeps the evidence and limits; AI-10's full suite stays open.

Historical DEC-10 scope (additional non-AI checks subsequently excepted by DEC-11): the maintainer accepts this release without the isolated joint database/S3 restore test under [DEC-10](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-10-current-release-recovery-test-exception.md). Restore-execution acceptance clauses below are excepted for this release, not passed. Backup/storage/security duties and other open Gate 6 cases remain; recovery VM provisioning is not required.

Status: ODIP's energy configuration integration handoff is complete by maintainer confirmation on October 19, 2026, for ODIP 0.5.0 and contract kit 0.5.0. The deterministic 0.4.0 workflow was accepted upstream at Gate 5 on October 17, 2026. VEF AI assistance is implemented; Gate 6 acceptance and the final cross-project release remain open for AI-10. AI-05/06 pass hosted citation/semantic review, AI-08/11 pass the hosted private validation boundary, and the listed non-AI checks have accepted exceptions. Decisions are recorded in [ADR0001](architecture/adr/0001-energy-configuration-integration.md); verification and deployment are described in the [runbook](energy-configuration-integration-runbook.md).
Updated: 2026-10-27. See the [cross-project review](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-implementation-and-acceptance-review.md) and
[gap analysis](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-gap-analysis.md) for the reconciled baseline and closure evidence.

ODIP publishes complete, validated dataset versions that the Variability Engineering Framework (VEF) retrieves and verifies through an application API. The implemented publication path uses the Kotlin API, Python worker, PostgreSQL storage, and Angular operator interface. The next cross-project milestone is acceptance of the implemented VEF AI-assistance increment, with the deterministic publication path retained as its regression baseline.

ODIP supplies reference data and provenance. VEF owns customer inputs, component compatibility, simulation, optimization, and AI explanations. The Developer Platform provides deployment, identity facilities, routing, and application databases. The first integration uses a bounded reference region, calendar year, and component catalog; synthetic fixtures can establish the initial flow. These boundaries follow the proposed [energy configuration use case](https://github.com/eseidinger/energy-system-configuration/blob/main/energy-configuration-use-case.md).

## Current-release scope

The maintainer selected new installations for the current release on October 27
in shared [DEC-07](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-07-new-equipment-release-scope.md). Existing-equipment support is deferred; VEF requires an empty
`existingComponentIds` list and rejects non-empty inputs before run creation.
ODIP continues publishing the same domain-neutral manifests and energy catalog;
no customer equipment data or new publication endpoint is required. GAP-06 is
closed by scope decision, while shared-kit release packaging remains under GAP-10.
Released kit 0.5.0 and its vendored bytes remain immutable; the next shared-kit
release must carry the new scope decision before final acceptance. The maintainer
also accepted [DEC-08](https://github.com/eseidinger/energy-system-configuration/blob/main/decisions/DEC-08-complete-calendar-year.md): the energy adapter now requires a complete UTC calendar year with exactly
8,760 or 8,784 aligned hours. This closes the local annual-period validation
deficiency; deployed negative regression and final acceptance remain open.

## Relationship to the roadmap

This publication milestone follows the ingestion and curation foundation and precedes the Parquet/DuckDB analytical comparison. It closes publication, quality, and authorization gaps needed by an external consumer without requiring the full analytics platform.

The accepted first publication fixture uses bounded PostgreSQL storage behind an artifact storage interface. The subsequent S3 adapter and controlled migration are implemented; Parquet/DuckDB remain planned. See the [development plan](development-plan.md) and [storage runbook](artifact-storage.md). Publication access remains stable across storage backends; installation-specific S3 activation/recovery is separate evidence.

The implementation pins released contract kit 0.5.0 and its [reconciled integration contract](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.5.0/energy-configuration-integration-contract.md), dated 2026-10-11. Kit 0.5.0 adds VEF AI-assistance contracts without changing ODIP publication APIs, fixtures or numerical results. The shared decisions remain resolved. The [integration plan](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.5.0/energy-configuration-integration-plan.md) records Gate 5 acceptance and the Gate 6 AI milestone. Acceptance by maintainer direction does not constitute a new execution of the suite; retain the historical local evidence and rerun deployed regression for the AI increment.

## Current implementation and acceptance boundaries

| Area | Implemented at the reviewed source revision | Remaining shared evidence |
| --- | --- | --- |
| Publication | Generic immutable manifest/artifacts, validation lifecycle, ETags, conditional reads, energy and non-energy adapters. A private hosted VEF probe passes exact-version, cache and invalid-content checks with in-memory ODIP transport. | Complete unchanged deployed Gate 5 regression for AI-10; the private job does not prove a mutated live ODIP read response. |
| Access and lineage | Stable-principal dataset grants, worker claims, source restrictions, raw inputs and publication lineage. | Release-specific denied/allowed boundary, rotation/revocation and retained correlation evidence. |
| Durability | PostgreSQL persistence, local restart/dump/restore harness; October 19 maintainer-confirmed ODIP handoff. | ODIP restart and exact artifact readback now pass. Joint restoration is excepted under DEC-10; remaining observability assertions stay open. |
| Version isolation | DEC-09 correction now published in odip-test; the original and corrected owned VEF runs pass full independent comparisons of all 252 candidates, metrics, ranking and provenance. Original 1.0.0 readback is unchanged. See the [guided acceptance](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-guided-release-acceptance.md). | Retain final deployment/evidence pins. Joint restore is excepted under DEC-10; other remaining AI-10 assertions stay open. |
| Artifact storage | PostgreSQL default plus optional S3 exact-version storage, V13 references/deletion outbox, operator migration. | Installation activation and joint bucket/database restore when S3 is enabled. Parquet/DuckDB remain later work. |

These evidence gaps do not revoke the accepted October 19 ODIP milestone.
The shared gap IDs GAP-03/04/05/09/10/13 define the remaining ODIP contributions.

## Historical pre-implementation baseline

The table below records the original implementation baseline and required changes, delivered by the accepted deterministic workflow. The original baseline is repository revision `912ed42794af552965ab055d6e9bc18735ffe74c`. Source registration, ingestion jobs, PostgreSQL raw payload storage, checksum verification, validation metadata, energy curation, dataset version listing, and the dataset browser already exist.

| Area | Current behavior | Required change |
| --- | --- | --- |
| Version model | `DatasetVersionEntity` uses a numeric version and a single raw-artifact relationship. | Add a publication identity and immutable bundle that can reference several outputs and inputs. |
| Publication | `EnergyCurationService` creates a version with default status `PUBLISHED`; validation may be missing or unsuccessful. Additional observations can join that version. | Separate mutable preparation from publication and enforce validation before freezing outputs. |
| Retrieval | Catalog routes use `/api/datasets`; versions expose summaries rather than complete immutable artifacts. | Add a versioned consumer API while preserving existing operator routes during migration. |
| Domain boundary | `IngestionService` and its completion request directly reference energy curation. The Python normalizer supports one annual Eurostat observation. | Introduce a generic transformation interface and isolate energy profile processing in an adapter. |
| Authorization | Principal headers and user/guest groups control broad API access. | Authenticate the caller and enforce dataset and operation grants. |
| Source retrieval | The worker downloads configured URLs and buffers responses before the API checks payload limits. | Validate destinations and redirects, and stop oversized downloads before buffering or uploading them. |
| Deployment | Separate production and test declarations use explicit release versions and `latest`, respectively, with approved source egress. | Pin release images and declare the selected data sources and consumer route. |

## Accepted integration decisions

These decisions were resolved by the shared release and the user's accepted recommendations recorded in ADR0001. The table preserves their traceability. Publication operations now have an [OpenAPI contract](../contracts/openapi/publication-operations.json).
ADR0001 records the local workflow and deployment choices. The shared release records the owners and accepted resolutions of DEC-01 through DEC-06.

| Decision | Accepted resolution |
| --- | --- |
| DEC-01 Reference data | Wasserburg am Inn, 2024 calendar, pinned PVGIS 2023 source, and the released synthetic profiles and catalog. |
| DEC-02 Simulation assumptions | Shared bounded-demonstration review and unchanged numerical oracle; VEF owns simulation. |
| DEC-03 Connectivity | Public HTTPS through the managed access boundary and explicitly declared egress. |
| DEC-04 Identity | Platform-managed clients and project-wide bindings; normalized context and local stable-principal grants. |
| DEC-05 Limits and retention | 1 MiB manifest, 10 MiB artifact, 50 MiB bundle; five-minute claims; support lifetime plus one year and 180-day application audit. |
| DEC-06 Contract ownership | The shared repository owns the released kit; ODIP pins version 0.5.0 and its archive checksum. |

Public dataset slugs bind to existing catalog UUIDs, and publication versions use semantic version labels. Numeric curated versions remain intact. Legacy data becomes a publication only through explicit draft preparation and validation; unsupported profiles produce structured errors.

The operator API is an ODIP extension to the shared read contract. It implements draft preparation, artifact attachment, an idempotent publication request, and worker validation evidence. Its payloads and permissions are defined in the local OpenAPI contract; the immutable shared kit is unchanged.

## Ordered implementation work

### 1 Establish schemas and fixtures

Work package: SHARED-01, with ODIP owning its generic publication contract.

Consume the generic manifest schema and read API from `contracts/vendor/`; define operator extensions under `contracts/openapi/`. Use the pinned shared release containing energy and non-energy fixtures, serialization rules, and expected digests. Use one complete calendar year for the reference fixture. Schema and digest checks must run in both API and worker CI.

Define byte serialization before hashing, including timestamp and number representation. Tests must compare the bytes exchanged through HTTP, not independently reconstructed JSON objects. Define safe relative artifact paths and machine-readable error payloads.

Acceptance: an independent client validates both fixture manifests and reproduces their recorded digests. The contract kit has a stable release reference and no unresolved field shape.

### 2 Add atomic generic publication

Work package: ODIP-01.

Create a `publication` module in `services/platform-api` with its own services, persistence, and response types. Add Flyway migrations after the existing migrations for publication records, output artifacts, input lineage, validation reports, and unique public dataset/version keys. Preserve existing version and raw-artifact records.

Propose `DRAFT -> VALIDATING -> PUBLISHED` with a failed validation state retaining diagnostics. Store manifest bytes and the server-computed digest at publication. Snapshot source attribution and transformation metadata so later catalog edits do not alter historical evidence. Link each output to its input artifacts and pipeline runs.

The publication service checks artifact availability, lengths and hashes, schema conformance, provenance, permissions, and required policy results before committing the final state. A parseable JSON file alone is insufficient validation. Prevent changes to published manifests, artifacts, and lineage; corrections produce another version. Use transaction boundaries and database constraints to handle concurrent requests, and make retried preparation/finalization safe.

Place artifact persistence behind a storage interface with a bounded PostgreSQL implementation. Separate immutable output bytes from raw input bytes even when their content happens to match. Validate request limits before expensive decoding and database writes.

Acceptance: failed checks and interrupted preparation expose no published bundle. Concurrent publication cannot create duplicate versions. Published bytes remain identical after catalog metadata changes. Historical curated data is preserved and requires explicit validation before promotion.

### 3 Serve the consumer API

Work package: ODIP-02.

Implement the proposed contract routes:

```text
GET /api/v1/datasets?status=PUBLISHED&schemaRef={schemaRef}
GET /api/v1/datasets/{datasetId}/versions/{version}
GET /api/v1/datasets/{datasetId}/versions/{version}/artifacts/{artifactId}
```

The manifest carries schema references, multiple artifact descriptors, quality-policy evidence, and provenance. Return SHA-256 ETags and support `If-None-Match`; distinguish missing versions, unpublished versions, and unauthorized callers with the specified errors. These obligations come from the [proposed publication contract](https://github.com/eseidinger/energy-system-configuration/blob/main/energy-configuration-integration-contract.md#31-publication-and-retrieval).

Serve stored bytes rather than regenerating manifests on reads. Resolve artifact IDs within the selected publication and never expose storage credentials or database URIs in consumer responses. Bound discovery responses and apply authorization before returning entries. Define pagination in the agreed API schema.

Keep the current operator APIs available during migration. Add publication-specific response types instead of changing existing version-summary payloads in place.

Acceptance: a clean client discovers a fixture, downloads it, verifies digests, and obtains conditional responses. Artifact IDs cannot cross publication boundaries. All routes produce consistent errors.

### 4 Implement the energy adapter

Work package: ENERGY-01.

Add an isolated energy package under `workers/data-worker/src/odip_worker/` with source mappings and profile validation. Produce the five profile outputs: PV yield, import tariff, export tariff, reference load shape, and component catalog. Validate intervals, units, numeric ranges, catalog attributes and identity, and usage rights against the versioned policy. The [energy profile](https://github.com/eseidinger/energy-system-configuration/blob/main/energy-configuration-integration-contract.md#32-energy-profile-semantics) specifies their semantics.

Replace the generic ingestion service's direct energy dependency with a declared transformation identifier and result interface. Move energy normalizer selection out of the core enum. Preserve the current annual-observation path as a legacy adapter during migration; it does not substitute for the hourly configuration profile.

Prepare bundles using explicit input artifact IDs across source runs, since one source run may not supply every output. Record mapping version and configuration with each transformation. The adapter returns structured validation evidence; only the publication service can finalize a version. Restrict accepted policy identifiers and which worker identities can submit their reports.

Acceptance: the adapter reproduces the pinned fixture. Invalid inputs remain diagnosable and cannot publish. A non-energy adapter uses the same core workflow without energy branches in core DTOs, services, or consumer routes.

### 5 Enforce permissions and source restrictions

Work package: ODIP-03. Resolve the identity design in step 1 and enforce it before the publication milestone is complete.

Introduce dataset grants and operation permissions covering discovery, reads, draft preparation, publication, and ingestion. Give VEF read access to selected publications; separate that identity from the worker and publisher. Apply grants to both new publication routes and existing raw/curated routes to avoid bypasses.

Production accepts normalized principal headers only through the platform's trusted access boundary. The platform validates credentials; ODIP validates context shape and object permissions. Application grants must be distinct from Developer Platform administration groups. Remove the worker's reliance on a broadly privileged default group and inject its scoped identity through the supported secret mechanism.

Add source destination policy in registration and worker retrieval. Validate resolved addresses and every redirect, restrict protocols and ports, and block private, link-local, and metadata destinations for external sources. Keep internal API access separately configured. Stream downloads with byte limits and bounded timeouts, and redact sensitive locations from error messages.

Acceptance: API integration tests with authorization enabled reject forged identities, prohibited datasets, and unauthorized writes. Retrieval tests reject unsafe destinations, redirects, and oversized responses. VEF can download the permitted fixture but cannot prepare or publish data.

### 6 Update the operator interface and runtime

Extend `web/src/app/core/api/` and the dataset page with publication history, schema, artifacts, quality results, and provenance. Separate curated observations from published versions, expose validation failures, and restrict publication actions to permitted operators. Display source metadata as untrusted text.

Update `infrastructure/deployments/application.json`, deployment documentation, and image workflows to pin release versions, declare approved source egress, and support the agreed consumer connection. Verify that database unavailability removes the API from readiness while liveness retains its process-health purpose.

Use the current database job queue and scheduled worker. Add ownership and idempotency for publication preparation and define recovery for runs abandoned after a worker crash. A reconciliation process must not blindly repeat terminal callbacks. Add publication duration/failure and retrieval metrics, audit events, and correlation by dataset, version, and pipeline run. Preserve a consumer run correlation ID when supplied without collecting customer inputs or tokens.

Acceptance: the operator can inspect a published fixture and its diagnostics. Restart retains publication state; an interrupted worker can be reconciled safely. API and worker resource limits accommodate the supported bundle, and backup restoration preserves its bytes and lineage.

### 7 Verify the deployed VEF handoff

Work package: INT-01, shared with VEF and Developer Platform.

Run the upstream [integration gates](https://github.com/eseidinger/energy-system-configuration/blob/main/energy-configuration-integration-plan.md#4-ordered-integration-steps) against pinned releases. Publish energy and non-energy fixtures through the same API; exercise invalid data, access denial, version isolation, restart, and restoration. Hand off the published dataset/version, manifest digest, endpoint, and test identity configuration to VEF.

ODIP's exit condition is verified retrieval from the deployed application with retained evidence. VEF and the cross-project suite establish numerical recommendations, cached-input behavior, and later AI acceptance. Track those results separately so successful ODIP tests do not imply complete integration.

## Pull request sequence

1. Contract schemas, pinned fixtures, decision records, and CI validation.
2. Publication persistence, lifecycle, storage interface, and migration coverage.
3. Consumer retrieval, errors, conditional requests, and scoped authorization.
4. Generic transformation boundary, energy adapter, and complete fixture publication.
5. Operator interface, source restrictions, job recovery, and deployment configuration.
6. Automated deployed handoff and recovery evidence.

Introduce source restrictions as soon as retrieval is changed; their final deployed verification belongs to step 5. Every pull request should include the checks that establish its own acceptance conditions. Run PostgreSQL integration tests for lifecycle, concurrency, and migrations; worker tests for profile validation and retrieval limits; UI checks for operator changes; and the shared schema/digest checks in CI. Authorization tests must override the existing test profile that disables principal enforcement.

## Completion criteria

On October 19, 2026, the maintainer confirmed all remaining ODIP handoff items: production publication and grants, deployed VEF retrieval and checksum verification, access denials, captured raw inputs and pipeline lineage, restart and actual backup restoration, resolution of the worker telemetry issue with Developer Platform, and the handoff record. This records the maintainer's acceptance; no new automated execution, deployment inspection, image digests, final publication version, or external test reports were supplied with that confirmation.

The accepted criteria are that a clean client can retrieve and verify an authorized, complete publication using only the pinned contract. Both energy and non-energy fixtures must pass, failed drafts must remain unavailable, and correcting a dataset must preserve earlier publication bytes. Restart and backup restoration must retain manifests, artifacts, validation evidence, and lineage. These criteria remain the regression baseline for subsequent releases.

Record the contract-kit release, ODIP revision, images, fixture digests, configuration, and acceptance results with the handoff. Update this plan and the development roadmap when those conditions are met. Broader analytics and the Phase 2 storage migration then proceed against the established publication interface.
