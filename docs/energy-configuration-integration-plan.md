# Energy Configuration Integration Plan

Status: Implemented and verified locally. Deployed cross-project acceptance remains open. Decisions are recorded in [ADR0001](architecture/adr/0001-energy-configuration-integration.md); verification and deployment are described in the [runbook](energy-configuration-integration-runbook.md).
Date: 2026-10-12

ODIP will publish complete, validated dataset versions that the Variability Engineering Framework (VEF) can retrieve and verify through an application API. The next milestone is a working publication path using the existing Kotlin API, Python worker, PostgreSQL storage, and Angular operator interface.

ODIP supplies reference data and provenance. VEF owns customer inputs, component compatibility, simulation, optimization, and AI explanations. The Developer Platform provides deployment, identity facilities, routing, and application databases. The first integration uses a bounded reference region, calendar year, and component catalog; synthetic fixtures can establish the initial flow. These boundaries follow the proposed [energy configuration use case](https://github.com/eseidinger/energy-system-configuration/blob/main/energy-configuration-use-case.md).

## Relationship to the roadmap

Complete this publication milestone after the existing ingestion and curation foundation and before the Parquet/DuckDB analytical comparison. It closes publication, quality, and authorization gaps needed by an external consumer without requiring the full analytics platform.

Use bounded PostgreSQL storage for the first publication fixture behind an artifact storage interface. Phase 2 still introduces S3-compatible storage and Parquet as specified in the [development plan](development-plan.md) and [architecture decisions](architecture/decisions.md). Publication access must remain stable when storage changes.

The implementation pins released contract kit 0.4.0 and its [reconciled integration contract](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.4.0/energy-configuration-integration-contract.md), dated 2026-10-11. The shared decisions are resolved in that release. The [integration plan](https://github.com/eseidinger/energy-system-configuration/blob/contract-kit-v0.4.0/energy-configuration-integration-plan.md) defines the remaining deployed gates. Local verification does not itself accept the cross-project contract.

## Current implementation and gaps

The baseline is repository revision `912ed42794af552965ab055d6e9bc18735ffe74c`. Source registration, ingestion jobs, PostgreSQL raw payload storage, checksum verification, validation metadata, energy curation, dataset version listing, and the dataset browser already exist.

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
| DEC-06 Contract ownership | The shared repository owns the released kit; ODIP pins version 0.4.0 and its archive checksum. |

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

The next ODIP milestone is complete when a clean client can retrieve and verify an authorized, complete publication using only the pinned contract. Both energy and non-energy fixtures must pass, failed drafts must remain unavailable, and correcting a dataset must preserve earlier publication bytes. Restart and backup restoration must retain manifests, artifacts, validation evidence, and lineage.

Record the contract-kit release, ODIP revision, images, fixture digests, configuration, and acceptance results with the handoff. Update this plan and the development roadmap when those conditions are met. Broader analytics and the Phase 2 storage migration then proceed against the established publication interface.
