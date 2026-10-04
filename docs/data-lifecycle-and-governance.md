# Data Lifecycle and Governance

## Lifecycle states

| State | Purpose | Mutability | Minimum metadata |
| --- | --- | --- | --- |
| Registered | Source or dataset is known to the catalog. | Metadata versioned | Owner, license, access method, refresh cadence |
| Raw | Exact acquired input. | Immutable | URI, checksum, retrieved time, source version, run ID |
| Validated | Input assessed against declared rules. | Derived | Ruleset version, counts, failures, rejects URI |
| Normalized | Source shape mapped to canonical fields. | Derived/versioned | Mapping version, schema version, run ID |
| Curated | Approved dataset version for use. | Immutable/versioned | Quality report, lineage, retention/classification |
| Projected | Search, graph, vector, or analytical representation. | Rebuildable | Parent curated version, adapter/configuration version |
| Archived/deleted | Retention policy applied. | Controlled | Decision, actor, time, legal basis |

## Provenance and reproducibility

Every curated version must point to its source inputs, code or image revision, pipeline configuration, schema version, transformation versions, and quality outcome. Use checksums for artifacts and stable IDs for sources, versions, runs, and representations. Do not overwrite an artifact that is referenced by a successful run.

## Quality policy

Quality rules are declared with the dataset, versioned, and run before curation. At minimum capture row counts, null rates for key fields, uniqueness where applicable, schema conformance, freshness, and rejected-record samples. A failed rule produces a visible run state and preserves diagnostic artifacts; promotion to curated is policy-controlled.

## Licensing, privacy, and access

Record the source license and attribution requirements before ingestion. Classify data on registration; do not assume public availability means unrestricted reuse. Access policies apply consistently to raw artifacts, curated records, exports, and AI tools. Secrets stay outside source definitions and are never included in run logs or prompts.

## Retention and deletion

Dataset owners define retention for raw inputs, rejects, curated versions, and exports. Retention actions must preserve the minimum lineage required for audit, subject to legal and license obligations. Derived projections can be rebuilt and should reference their parent version rather than duplicate governance metadata.

## Storage evolution

Phase 1 stores bounded raw artifacts in PostgreSQL. Phase 2 moves raw artifacts and stores Parquet publications in S3-compatible object storage through the platform storage abstraction. Moving an artifact between backends must preserve its stable identity, checksum, source and run lineage, classification, retention policy, and audit history. The original copy must not be removed until the migrated copy has been verified and references have been updated transactionally.
