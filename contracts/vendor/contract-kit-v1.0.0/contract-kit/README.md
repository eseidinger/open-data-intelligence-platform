# Energy System Configuration Contract Kit

Version `1.0.0` is the first Gate 6 contract release for the bounded energy
configuration workflow accepted under DEC-13. It retains the `0.5.0` AI assistance contract,
schemas, examples, semantic citation validation and consumer acceptance cases.
ODIP APIs, numerical fixtures and expected results remain unchanged. The
[release compatibility notes](RELEASE-NOTES-1.0.0.md) state the accepted
new-equipment and complete-calendar-year deployment scope. The
[versioned release page](https://github.com/eseidinger/energy-system-configuration/releases/tag/contract-kit-v1.0.0)
records the archive and checksum. Consumers adopt the released archive and
checksum through a coordinated handoff.

The accepted `0.4.0` baseline reconciles the integration contract with Developer
Platform revision `b360ddee34444748c95705c597aa7b17491cd05b`. It retains the
`0.3.0` identity changes and adds the platform operational log emission profile
and component-monitoring semantics. Energy schemas, fixtures, and numerical oracles
remain unchanged. See [platform compatibility notes](platform/README.md). ODIP and VEF consume released archives of this directory and pin both
the version and archive checksum.

## Contents

- `schemas/` contains JSON Schema 2020-12 contracts.
- `openapi/` contains OpenAPI 3.1 service descriptions.
- `examples/` contains small valid payload examples.
- `fixtures/` contains the complete energy and non-energy reference inputs.
- `expected-results/` contains reviewed simulation and optimization outputs.
- `platform/` contains the pinned upstream input-schema snapshot and deployment,
  access-policy, service-request, governance, and observability compatibility notes.
- `ai/` contains the normative VEF AI profile, approved-evidence example, and
  workflow acceptance cases to execute in VEF.
- `contractkit/` contains the repository-neutral validation utilities.
- `tests/` validates schemas, APIs, examples, canonical serialization, and
  fixture integrity.

## Validate

Install the pinned environment and execute the suite:

```text
uv sync --frozen
uv run --frozen pytest
```

Canonicalize a JSON document and print its SHA-256 digest:

```text
uv run python -m contractkit.canonical path/to/document.json
```

The semantic validator checks the energy publication as one unit after JSON
Schema validation. It enforces the five required roles, canonical artifact
digests, aligned and complete hourly intervals, load-shape normalization, and
catalog identity and model-count rules.

After validating AI envelopes with JSON Schema, call
`contractkit.ai.validate_explanation(explanation, sources)` against VEF's trusted
evidence snapshot. It checks citation resolution, copied values, classification,
and required evidence coverage. Free-text claim accuracy, confirmation enforcement,
and prompt-injection resistance require the VEF acceptance tests; they are not
established by this static kit suite.

Build the deterministic release archive and `SHA256SUMS` file under `dist/`:

```text
uv run --frozen python -m tools.build_release
```

## Licensing

Schemas, OpenAPI definitions, runner code, and tests use Apache-2.0. Examples,
fixtures, and expected results authored in this repository use CC BY 4.0.
Third-party source material retains its source terms and attribution as stated
in the repository `NOTICE` and artifact provenance.
