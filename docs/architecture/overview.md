# Architecture Overview

## Design principles

1. Keep the logical dataset model independent of physical storage.
2. Preserve immutable raw inputs and make every transformation observable.
3. Start with a small, operable baseline; add technology only to meet a demonstrated workload.
4. Treat AI output as reviewable artifacts and constrain AI access through explicit tools.
5. Make architectural comparisons reproducible experiments, not anecdotes.

## System context

```text
Public APIs / files / databases
             |
             v
    Ingestion and transformation
             |
             v
 Object storage + PostgreSQL catalog/data <--- Python worker
             |
             v
       Kotlin / Spring API
             |
             +-------------------+
             v                   v
        Angular UI       Approved AI tools / MCP (later)
```

External sources remain outside the trust boundary. The platform records their license, owner, access method, refresh policy, source version, and retrieval time.

## Baseline components

| Component | Responsibility | Baseline technology |
| --- | --- | --- |
| Catalog service | Sources, datasets, schemas, lineage, pipeline and experiment metadata | Kotlin / Spring Boot + PostgreSQL |
| Pipeline orchestration | Starts runs, records state, retries approved work, exposes results | Kotlin / Spring Boot |
| Data worker | Extraction, profiling, validation, transformation, enrichment, analytical jobs | Python |
| Operational store | Catalog metadata and normalized/curated serving data | PostgreSQL |
| Artifact store | Immutable raw inputs, Parquet outputs, exports, run artifacts | S3-compatible object storage |
| Analytical engine | Local/worker analytical queries over Parquet and PostgreSQL | DuckDB |
| Web client | Dataset browsing, pipeline monitoring, quality, experiments, analysis | Angular / TypeScript |

## Data flow and states

```text
Registered source
  -> extracted artifact (raw, immutable)
  -> validated records + rejects
  -> normalized records
  -> enriched and curated dataset version
  -> optional projections: Parquet, search, graph, vector
```

Each transition is associated with a pipeline run. A run records input artifacts, configuration and code version, timestamps, counts, quality results, and output dataset versions. Optional projections are derived representations; they do not replace the curated canonical dataset.

## Logical model

- **DataSource**: external provider and access metadata.
- **Dataset**: logical collection, owner, semantic description, schema, and lifecycle policy.
- **DatasetVersion**: immutable identifiable result of a successful curation run.
- **PhysicalRepresentation**: a version in a particular storage and format, such as PostgreSQL tables or Parquet.
- **Pipeline**: declared transformation definition.
- **PipelineRun**: one execution and its observability record.
- **QualityReport**: assertions, metrics, samples of rejects, and outcome for a dataset version.
- **Experiment**: workload and comparable implementation results.

## Boundaries and interfaces

The API owns catalog and orchestration operations. Workers receive a declared run specification and return artifacts plus structured outcomes; they must not silently mutate catalog state. Storage and query adapters hide vendor-specific behavior behind capabilities, so callers request a supported operation rather than depend on a specific database.

AI clients use narrow, read-oriented tools such as `listDatasets`, `describeDataset`, `getDatasetSchema`, `queryDataset`, `executeAnalytics`, `getDataQualityReport`, and `getDatasetLineage`. Tool policies enforce dataset authorization, parameter constraints, row/scan limits, and audit logging.

## Evolution path

Search, graph, vector, document, and streaming systems are optional adapters. Introduce one only with an experiment or product requirement that cannot be met by the baseline. Kafka or another broker is deferred until asynchronous/streaming needs justify its operational cost.
