# Development Plan

Delivery is organized around working vertical slices. A phase is complete only when its exit criteria are met, not merely when its components exist.

## Phase 0 — Foundations

Set up repository conventions, local containerized dependencies, configuration/secrets handling, CI checks, schema migrations, observability conventions, and a minimal API/UI/worker skeleton.

Exit criteria: a new contributor can start the stack locally, run automated checks, and see a health signal for each component.

## Phase 1 — Data foundation

Implement source and dataset catalog APIs; PostgreSQL and object-storage adapters; a Python batch worker; raw capture; validation, normalization, and curated storage; pipeline-run records; and an Angular dataset browser. Deliver one energy source end to end.

Exit criteria: a licensed source is registered, ingested, versioned, browsable, and traceable from a curated record back to its raw artifact and pipeline run.

## Phase 2 — Quality and analytics

Add profiling, expectations, reject workflows, freshness reporting, Parquet publication, DuckDB queries, historical data loading, and basic charts/questions for the energy use case.

Exit criteria: users can inspect quality/freshness and answer the documented reference questions from curated data; the same analytical query can run reproducibly over its specified representation.

## Phase 3 — Experimentation

Implement experiment definitions, workload fixtures, environment capture, metric collection, and result comparison. Begin with PostgreSQL versus DuckDB/Parquet for a defined analytical workload.

Exit criteria: a third party can rerun a recorded experiment and compare stored results, including dataset version and configuration.

## Phase 4 — Intelligence

Add embeddings, semantic catalog search, retrieval over approved artifacts, constrained natural-language analytics, and tool/MCP interfaces. Keep human review and auditability in the loop.

Exit criteria: an AI interaction identifies its datasets and query evidence; unauthorized, unbounded, or write operations are rejected.

## Phase 5 — AI-assisted data engineering

Add draft metadata, semantic-type suggestions, schema-drift detection, quality suggestions, relationship discovery, and reviewable pipeline configuration proposals.

Exit criteria: every AI-generated artifact has provenance, a review status, and a deterministic path to acceptance or rejection.

## Cross-cutting work in every phase

- Unit, integration, contract, and representative end-to-end tests.
- Structured logs, metrics, traces, and correlation IDs for API and pipeline runs.
- Least-privilege access, secret management, dependency scanning, and license capture.
- Versioned schemas, migrations, documentation, and sample data that can be safely shared.
- Clear cleanup/retention policy for raw data, rejects, derived artifacts, and exports.

## Suggested first milestones

1. Repository bootstrap and local developer experience.
2. Catalog with source and dataset registration.
3. One raw-to-curated energy pipeline with run history.
4. Dataset browser with lineage and quality summary.
5. Parquet/DuckDB analytical comparison with a published result.
