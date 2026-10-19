# ADR0001 Energy Configuration Integration Boundaries

Status: accepted
Date: 2026-10-12

## Context

The [integration plan](../../energy-configuration-integration-plan.md) adds governed publication to the existing ingestion and curation foundation. Shared contract kit 0.4.0 resolves the reference data, simulation, connectivity, identity, limits, retention, and contract ownership. Its platform identity boundary replaces the earlier application-managed JWT assumptions.

## Decision

Implement and verify the ODIP repository, including deployment and acceptance tooling. Live deployment, identity provisioning, and cross-project acceptance are separate operational steps.

Use the released `contract-kit-v0.4.0` archive with SHA-256 `884e3590614328c2adafa457153e11575dc1be09b9f53d7b0f53704fe39d02b0`. Vendor the archive and exact extracted contents and verify them in CI. Preserve the kit's attribution and licenses.

Retain UUID catalog keys and numeric curated versions. Bind a public dataset slug to one catalog UUID and use semantic publication versions. Publication has a separate `DRAFT -> VALIDATING -> PUBLISHED` lifecycle with a final `FAILED` outcome. Operators prepare drafts and request asynchronous publication; an approved worker supplies the named validation evidence. PostgreSQL locks, uniqueness constraints, and triggers enforce idempotency and immutability. Claimed work carries a nonce to reject stale callbacks.

Store local dataset grants by stable platform principal ID. Application operators manage grants through a protected API and UI. Creator grants are seeded when registering a dataset. VEF receives only READ for the accepted energy reference dataset; the worker receives READ, INGEST, and VALIDATE on its assigned datasets. Publication preparation requires WRITE.

Use the Developer Platform's managed access boundary for both VEF and worker HTTP calls. Applications require normalized principal context and finer dataset grants; they do not validate JWTs or repeat platform route checks. Production context follows the kit's ID/header formats. Development supports explicit synthetic identities.

The authorization implementation was aligned with this boundary on 2026-10-13. All API routes, including legacy routes, rely on platform group authorization. Protected administrative endpoints do not perform a second operator-group check. Catalog and pipeline visibility, source ingestion, publication operations, and raw retrieval require explicit dataset grants even for operators. Ownership and current claim tokens remain mandatory; atomic input capture supplies its own token internally. Only explicit local/test mode may bypass dataset grants.

Keep one deployment descriptor and project with a combined API/UI component and a scheduled worker. Remove the duplicate private API instance so there is one protected backend. Serve production assets under `/ui/` to permit disjoint browser and bearer route policies. Worker credentials remain project-wide, which means other ODIP components may receive them. This accepts the current platform boundary without claiming component credential isolation.

Use the accepted 1 MiB manifest, 10 MiB artifact, and 50 MiB bundle limits. Record an explicit support-end timestamp before publication retention can expire; active publications remain retained. Purge published outputs only after the one-year grace period, retain raw inputs, and expire application audit rows after 180 days.

## Consequences

The canonical consumer API remains stable across a future storage migration. The energy adapter contains profile interpretation and source mapping; the core handles registered schemas and named policy evidence.

Platform policies, application groups, service bindings, and governance are separate resources from the application descriptor. Operators must provision them and inject binding configuration before deployment. Stable group IDs belong to platform policies, not application configuration. Production renders `__VERSION__` image placeholders in `infrastructure/deployments/application.json` from the release tag; `infrastructure/deployments/application-test.json` uses `latest` images for `odip-test`. After publication, CI applies the test declaration directly on `main` and the rendered production declaration on version tags. Administrative API and UI access depends on the active platform policy and enforced backend isolation; there is no duplicate application role configuration as a fallback.

Local tests establish publication, authorization logic, concurrency, semantic quality, restart, and actual PostgreSQL restore. Live platform isolation, rotation, egress, and the VEF numerical workflow require the target installation. Their absence does not become an accepted release claim.

## Evidence

See the [integration runbook](../../energy-configuration-integration-runbook.md), pinned shared [decisions](https://github.com/eseidinger/energy-system-configuration/tree/contract-kit-v0.4.0/decisions), and API/worker tests.

## Contract kit 0.5.0 adoption

On October 19, 2026, upgrade the consumer pin to the released
`contract-kit-v0.5.0` archive, SHA-256
`ae4edaf6799d4b57510d14d2004c5b65ff6b05f3b225e96bbd5971b30ce8832b`.
This supersedes the archive pin above while preserving the accepted 0.4.0 domain
and identity decisions. The additive release includes VEF AI proposal/explanation
schemas and semantic citation checks; ODIP APIs, energy fixtures and numerical
oracles are unchanged. Vendor the exact published archive and verify it against
the lock in CI. Gate 6 implementation/acceptance remains separate from this pin
upgrade; no application AI feature is introduced in ODIP.
