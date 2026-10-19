# OpenAPI contracts

- `odip-publication-v1.yaml` describes domain-neutral dataset discovery,
  immutable manifest retrieval, and artifact retrieval through platform bearer
  authentication. Service access uses a managed binding and approved reader
  group; OAuth scopes and fixed provider client IDs are not application inputs.
- `vef-optimization-v1.yaml` describes optimization submission, run status,
  ranked candidates, and limits through platform browser-session authentication.
  First login requires approval. Mutations require a same-origin header and
  platform CSRF token. Browser login redirects and access-layer errors are
  explicitly documented.

Both use OpenAPI 3.1 and the JSON Schema 2020-12 files in `../schemas/`.
Externally presented credentials terminate at the platform boundary. Backends
consume trusted normalized principal headers and enforce finer dataset/run
permissions. Platform `application_access_*` errors differ from application
`error/v1`; clients must accept both envelopes where documented and treat access
unavailability as a dependency failure.

Illustrative server names are derived from component/project names and replaced
with installation-specific HTTPS origins. No realm, audience, OAuth role, or
client secret is fixed by these API descriptions. A bearer VEF automation API
would require distinct non-overlapping routes and a separately reviewed policy;
it cannot share the browser routes' authentication mode.

The input policies and compatibility/acceptance limits are shipped in
[the platform profile](../platform/README.md). Application APIs remain proposed
extensions; pinning the platform does not claim ODIP or VEF implements them.
