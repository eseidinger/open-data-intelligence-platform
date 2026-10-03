# Implementation Layout

The repository is a monorepo organized around the ODIP baseline architecture. Components communicate through versioned contracts and infrastructure adapters; business logic must not depend directly on a particular optional data-store implementation.

| Path | Responsibility |
| --- | --- |
| `services/platform-api` | Kotlin/Spring Boot catalog, orchestration, API, and authorization service. |
| `workers/data-worker` | Python ingestion, transformation, profiling, analytics, and AI jobs. |
| `web` | Angular/TypeScript dataset browser and operator interface. |
| `contracts` | Versioned API and data-contract definitions shared across components. |
| `infrastructure` | Local development, database migrations, object-storage setup, and deployment/observability assets. |
| `experiments` | Reproducible workload fixtures and experiment definitions. |
| `scripts` | Repository-level developer and automation scripts. |

Build files, component configuration, and executable code should be added as each vertical slice is implemented. Generated artifacts, credentials, local datasets, and experiment measurements belong outside version control unless explicitly selected as safe fixtures or published evidence.
