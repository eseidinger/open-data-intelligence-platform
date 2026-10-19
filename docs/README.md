# ODIP Documentation

This documentation turns the project vision in the root [README](../README.md) into an implementable reference set. The README remains the project overview; these documents define how to build and evolve it.

## Start here

- [Product scope](product-scope.md) — the problem, users, outcomes, and first reference use case.
- [Architecture overview](architecture/overview.md) — system boundaries, components, data flow, and design principles.
- [Architecture decisions](architecture/decisions.md) — baseline choices and the rules for introducing alternatives.
- [Development plan](development-plan.md) — phased delivery plan, milestones, and exit criteria.
- [Energy configuration integration plan](energy-configuration-integration-plan.md) — next delivery milestone: immutable publications, the energy adapter, scoped access, and the VEF handoff.

The ODIP publication implementation is available locally. Use the [integration runbook](energy-configuration-integration-runbook.md) for verification, provisioning, and deployment; the deployed VEF handoff remains the next integration gate.

## Operating the platform

- [Bootstrap environments](bootstrap.md) — complete first deployment of test and production, including storage, access and worker setup.

- [Data lifecycle and governance](data-lifecycle-and-governance.md) — data states, provenance, quality, retention, and access controls.
- [Experiment framework](experiment-framework.md) — how technology comparisons become reproducible evidence.
- [Deployment setup](energy-configuration-integration-runbook.md#deployment-descriptors-and-automatic-releases) — production and test descriptors, storage provisioning and automatic releases.

## Documentation conventions

Architecture decisions are recorded as **accepted**, **proposed**, or **experiment**. An experiment may change a decision only when its workload, configuration, source data version, measurements, and result are recorded.

When implementation begins, add runbooks, API contracts, and decision records next to the relevant document rather than allowing operational knowledge to live only in code or tickets.
