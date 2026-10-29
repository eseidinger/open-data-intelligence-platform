# ODIP Documentation

This documentation turns the project vision in the root [README](../README.md) into an implementable reference set. The README remains the project overview; these documents define how to build and evolve it.

## Start here

- [Product scope](product-scope.md) — the problem, users, outcomes, and first reference use case.
- [Architecture overview](architecture/overview.md) — system boundaries, components, data flow, and design principles.
- [Architecture decisions](architecture/decisions.md) — baseline choices and the rules for introducing alternatives.
- [Development plan](development-plan.md) — phased delivery plan, milestones, and exit criteria.
- [Energy configuration integration plan](energy-configuration-integration-plan.md) — accepted milestone: immutable publications, the energy adapter, scoped access, and the VEF handoff.

The ODIP publication and deployed VEF handoff were accepted by maintainer confirmation on October 19, 2026, using ODIP 0.5.0 and contract kit 0.5.0. ODIP now pins kit 1.0.0 and application v1.0.0 is ready in production. The bounded cross-project [Gate 6 is closed with limitations](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-29-gate-6-closure.md). See the [completion record](energy-configuration-integration-plan.md#completion-criteria) for evidence limits. Phase 2 is in progress: the S3 adapter and controlled migration are implemented; Parquet/DuckDB analytics and broader quality workflows remain planned. The [integration runbook](energy-configuration-integration-runbook.md) remains the installation and regression baseline.

The [October 27 cross-project review](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-implementation-and-acceptance-review.md) consolidates implementation,
acceptance and executed checks. The [shared gap register](https://github.com/eseidinger/energy-system-configuration/blob/main/reviews/2026-10-27-gap-analysis.md) tracks corrected
dataset isolation, joint regression/recovery and final release evidence without
reopening the accepted ODIP handoff.

## Operating the platform

- [Artifact storage](artifact-storage.md) — Developer Platform S3 bindings, local RustFS, verified migration, retention, and recovery.

- [Bootstrap environments](bootstrap.md) — complete first deployment of test and production, including storage, access and worker setup.

- [Data lifecycle and governance](data-lifecycle-and-governance.md) — data states, provenance, quality, retention, and access controls.
- [Experiment framework](experiment-framework.md) — how technology comparisons become reproducible evidence.
- [Deployment setup](energy-configuration-integration-runbook.md#deployment-descriptors-and-automatic-releases) — production and test descriptors, storage provisioning and automatic releases.

## Documentation conventions

Architecture decisions are recorded as **accepted**, **proposed**, or **experiment**. An experiment may change a decision only when its workload, configuration, source data version, measurements, and result are recorded.

When implementation begins, add runbooks, API contracts, and decision records next to the relevant document rather than allowing operational knowledge to live only in code or tickets.
