# Product Scope

## Purpose

Open Data Intelligence Platform (ODIP) is a domain-independent platform for turning heterogeneous public data into reliable, searchable, analyzable, and AI-accessible datasets. It is both a usable data product and a controlled environment for evaluating data-architecture choices.

## Primary users

| User | Primary need |
| --- | --- |
| Data engineer | Register sources, run observable pipelines, and diagnose quality issues. |
| Data analyst | Discover curated datasets and run reproducible analyses. |
| Architecture experimenter | Compare storage or query implementations against the same workload. |
| AI-enabled analyst | Explore approved datasets through constrained tools and traceable answers. |

## First reference use case: energy intelligence

The first end-to-end implementation combines public electricity generation, renewable generation, prices, weather, and consumption data. It should support time-series correlation, anomaly investigation, and discovery of similar historical events. This is a demonstrator, not a core domain model.

## MVP outcome

An operator can register one licensed public source, execute a repeatable pipeline, inspect its quality and lineage, browse the resulting dataset, and query or visualize it through the UI and API.

## In scope for the MVP

- Dataset and source catalog, including owner, license, refresh cadence, schema, and provenance.
- Batch ingestion from a public API or file source.
- Immutable raw capture, validation, normalization, and curated relational storage.
- Pipeline-run metadata, data-quality metrics, and rejected-record handling.
- PostgreSQL, a Kotlin/Spring API, Python worker, and Angular UI.
- One energy-data vertical slice from source to UI.

## Deliberately out of scope for the MVP

- Streaming infrastructure and a broad microservice landscape.
- Mandatory specialized stores (search, graph, document, or vector databases).
- Autonomous writes or unrestricted database access by an LLM.
- Multiple unrelated domains, production-scale distributed processing, and a generic marketplace.

## Planned after the data-foundation MVP

Phase 2 adds S3-compatible object storage for large immutable raw artifacts and Parquet analytical representations. It is not required for the Phase 1 PostgreSQL deployment, but it is a required component of the Phase 2 architecture.

## Success measures

- A pipeline run can be reproduced using its recorded source version and configuration.
- Every curated dataset exposes source, schema, freshness, quality, and lineage information.
- The reference use case answers at least three documented analytical questions.
- At least one baseline analytical workload has a captured, repeatable result.
