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

The first implementation is intentionally small: a Kotlin/Spring Boot platform API and orchestration layer, Python workers for data and AI work, PostgreSQL for operational metadata and curated serving data, S3-compatible object storage for artifacts, DuckDB for analytics, and an Angular user interface.

Specialized search, graph, vector, document, and streaming technologies are optional adapters. They are introduced only when a product requirement or reproducible experiment justifies them.

## Documentation

The [documentation index](docs/README.md) is the authoritative entry point for the detailed project material.

| Document | Purpose |
| --- | --- |
| [Product scope](docs/product-scope.md) | Users, MVP, reference use case, boundaries, and success measures. |
| [Architecture overview](docs/architecture/overview.md) | Components, logical model, data flow, interfaces, and evolution path. |
| [Architecture decisions](docs/architecture/decisions.md) | Accepted baseline decisions and ADR format. |
| [Development plan](docs/development-plan.md) | Phased delivery plan and exit criteria. |
| [Data lifecycle and governance](docs/data-lifecycle-and-governance.md) | Provenance, quality, licensing, access, and retention policies. |
| [Experiment framework](docs/experiment-framework.md) | Comparable workloads, measurement controls, and evidence requirements. |

## Current status

ODIP is in the foundation/planning stage. The immediate objective is one complete energy-data vertical slice: register a licensed source, capture immutable raw input, validate and curate it, record lineage and quality, then make it available through the API and dataset browser.

## License

ODIP is licensed under the [Apache License 2.0](LICENSE).

## Core principles

1. Keep logical datasets independent from physical storage.
2. Make inputs, transformations, outputs, and quality results observable and reproducible.
3. Prefer a small operable baseline over premature platform complexity.
4. Constrain AI through explicit tools; retain human review of generated engineering artifacts.
5. Use recorded experiments rather than anecdotal benchmarks for architecture decisions.
