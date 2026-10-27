# Open Data Intelligence Platform

Open Data Intelligence Platform (ODIP) is an experimental platform for ingesting, transforming, storing, analyzing, and exploring heterogeneous public datasets. It combines data engineering, data-architecture experiments, and governed AI-assisted analytics without binding the core platform to one provider, data store, or domain.

The first reference implementation is **energy intelligence**: public electricity generation, renewable generation, prices, weather, and consumption data combined into an analyzable, traceable dataset.

## What ODIP provides

- Reproducible pipelines from external sources to curated dataset versions.
- A catalog with source metadata, schemas, lineage, freshness, quality, ownership, and licensing.
- Multiple physical representations of the same logical dataset, such as PostgreSQL and Parquet.
- A controlled environment for evidence-based comparisons of data stores and query engines.
- Explicit, audited AI tools for dataset discovery and analysis.

## Baseline architecture

The first implementation is intentionally small: a Kotlin/Spring Boot platform API and orchestration layer, Python workers for data and AI work, PostgreSQL for operational metadata, raw artifacts, and curated serving data, DuckDB for analytics, and an Angular user interface.

The S3-compatible artifact adapter and controlled migration are implemented as the first Phase 2 increment. PostgreSQL remains the default artifact backend; S3 activation and joint database/bucket recovery require installation-specific verification. Parquet generation and DuckDB analytics remain planned.

Specialized search, graph, vector, document, and streaming technologies are optional adapters. They are introduced only when a product requirement or reproducible experiment justifies them.

## Documentation

The [documentation index](docs/README.md) is the authoritative entry point for the detailed project material. To deploy a new test or production installation, follow the [bootstrap runbook](docs/bootstrap.md).

| Document | Purpose |
| --- | --- |
| [Product scope](docs/product-scope.md) | Users, MVP, reference use case, boundaries, and success measures. |
| [Architecture overview](docs/architecture/overview.md) | Components, logical model, data flow, interfaces, and evolution path. |
| [Architecture decisions](docs/architecture/decisions.md) | Accepted baseline decisions and ADR format. |
| [Development plan](docs/development-plan.md) | Phased delivery plan and exit criteria. |
| [Energy configuration integration plan](docs/energy-configuration-integration-plan.md) | Accepted publication milestone and VEF integration handoff; regression baseline for subsequent releases. |
| [Data lifecycle and governance](docs/data-lifecycle-and-governance.md) | Provenance, quality, licensing, access, and retention policies. |
| [Experiment framework](docs/experiment-framework.md) | Comparable workloads, measurement controls, and evidence requirements. |

## Current status

ODIP implements catalog and ingestion, energy curation, and generic immutable dataset publication with scoped access and an operator interface. The [energy configuration integration](docs/energy-configuration-integration-plan.md#completion-criteria) was accepted by maintainer confirmation on October 19, 2026, for ODIP 0.5.0 and contract kit 0.5.0; the completion record distinguishes acceptance from retained execution evidence. Phase 2 is in progress: S3 storage and controlled migration are implemented; broader quality workflows, Parquet and DuckDB remain planned. The [storage runbook](docs/artifact-storage.md) describes the S3 adapter and controlled migration; the [integration runbook](docs/energy-configuration-integration-runbook.md) remains the deployment and regression baseline. VEF AI assistance is implemented, but Gate 6 acceptance remains open for AI-05/06/08/10/11. The [cross-project review](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-implementation-and-acceptance-review.md) and [gap analysis](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-gap-analysis.md) distinguish accepted ODIP delivery from remaining joint regression and release evidence.

## License

ODIP is licensed under the [Apache License 2.0](LICENSE).

## Core principles

1. Keep logical datasets independent from physical storage.
2. Make inputs, transformations, outputs, and quality results observable and reproducible.
3. Prefer a small operable baseline over premature platform complexity.
4. Constrain AI through explicit tools; retain human review of generated engineering artifacts.
5. Use recorded experiments rather than anecdotal benchmarks for architecture decisions.

## Linting and logging

Run these checks before submitting changes:

```sh
# services/platform-api
./gradlew ktlintCheck
# web
npm run lint
# workers/data-worker (also checks repository Python scripts)
uv sync --locked
uv run --locked ruff check src tests ../../scripts
```

Use `./gradlew ktlintFormat`, `npm run lint:fix`, or Ruff's `--fix` option for safe fixes, then review the changes. Python formatting is available with `uv run --locked ruff format src tests ../../scripts`. CI runs all three linters; vendored contract kits are excluded.

API request envelopes include correlation ID, status, severity, and elapsed milliseconds. Correlation is also available to downstream API logs through MDC and is restored after each request. Worker ingestion and publication validation events include opaque run/publication IDs and elapsed milliseconds; logs emitted in an active trace include trace and span IDs. Payloads, credentials, source URLs, and raw exception details must stay out of logs. See [AGENTS.md](AGENTS.md) for contribution rules.
