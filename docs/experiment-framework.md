# Experiment Framework

## Objective

An experiment evaluates alternative implementations against the same declared workload. It does not declare a universal winner; it records evidence for a specific dataset, configuration, and environment.

## Experiment contract

```yaml
name: postgres-vs-duckdb-parquet-analytics-v1
dataset_version: energy-curated:2026-01-01
workload:
  query_set: energy-analytics-v1
  warmup_runs: 1
  measured_runs: 5
implementations:
  - name: postgres
    representation: postgres-normalized
  - name: duckdb-parquet
    representation: parquet-curated
metrics:
  - wall_clock_ms
  - cpu_time_ms
  - peak_memory_mb
  - bytes_scanned
  - storage_bytes
  - ingestion_duration_ms
environment:
  capture: runtime-version, host-shape, configuration, image-digest
```

## Required controls

- Pin the dataset version, query set, adapter version, and configuration.
- Use equivalent semantic queries and document unavoidable differences.
- Run warmups separately from measured runs; report distributions, not only a fastest result.
- Capture failures, resource limits, environment details, and storage/ingestion costs.
- Store raw measurements and a human-readable conclusion with limitations.

## Result interpretation

Results are valid only within the captured conditions. A conclusion should state the workload characteristics it supports, the trade-offs observed, and the follow-up decision: retain the baseline, run another experiment, or promote an adapter under a documented operational plan.

## First experiment

Compare PostgreSQL with DuckDB over curated Parquet for a fixed set of energy time-series aggregation, filtering, and join queries. Measure ingestion time, storage footprint, repeated query latency, memory, and scan volume. Publish the query fixture, dataset version, and all measured runs alongside the summary.
