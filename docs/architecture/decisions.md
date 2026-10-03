# Architecture Decisions

The following are initial decisions derived from the project vision. They are intentionally small and reversible. Record a dated ADR when implementation makes a decision more specific.

| ID | Status | Decision | Rationale | Revisit when |
| --- | --- | --- | --- | --- |
| AD-001 | Accepted | Use a modular monolith for platform APIs and orchestration. | Delivers an end-to-end slice without distributed-systems overhead. | Independent deployment/scaling or team boundaries are demonstrated. |
| AD-002 | Accepted | PostgreSQL is the operational baseline. | It supports catalog metadata, normalized data, JSONB, and a credible comparison point. | A workload exceeds documented baseline limits. |
| AD-003 | Accepted | Store raw and analytical artifacts in S3-compatible object storage. | Supports immutable provenance and Parquet analytics without a large lakehouse stack. | Retention, scale, or governance needs require another implementation. |
| AD-004 | Accepted | Use DuckDB for analytical execution over Parquet and comparative workloads. | It provides a lightweight analytical baseline. | A workload needs distributed execution or a managed analytical engine. |
| AD-005 | Accepted | Separate Kotlin platform services, Python data/AI workers, and TypeScript UI. | Aligns each responsibility with an appropriate ecosystem while keeping boundaries explicit. | A measured integration cost outweighs the benefit. |
| AD-006 | Accepted | AI accesses data only through governed tools. | Enables authorization, limits, auditability, and reproducible evidence. | Never relax to unrestricted production database access. |
| AD-007 | Experiment | Add specialized stores through adapters, never as implicit core dependencies. | Keeps comparisons fair and avoids premature platform complexity. | An experiment and operational plan justify promotion. |

## Required ADR template

Create `docs/architecture/adr/NNNN-short-title.md` for consequential changes.

```markdown
# ADR-NNNN: Title

Status: proposed | accepted | superseded
Date: YYYY-MM-DD

## Context

## Decision

## Consequences

## Evidence / experiment link
```
