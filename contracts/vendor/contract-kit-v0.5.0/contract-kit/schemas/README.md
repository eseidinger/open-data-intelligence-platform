# JSON Schemas

Every schema uses JSON Schema 2020-12, has a stable `$id`, rejects unknown
properties, and is versioned independently. Domain payloads carry a `schemaVersion` value;
platform principal-header objects, operational envelopes, and boundary error bodies describe the actual
transport and do not add version fields to upstream requests or responses.
Semantic checks that JSON Schema cannot express—such as interval completeness,
chronological ordering, digest matching, and cross-artifact consistency—belong
in the shared validation runner.

The AI request-proposal schema wraps the existing optimization request and
requires user confirmation; clarification proposals cannot contain a submittable
request. The AI explanation schema carries classified claims with JSON Pointer
citations. Citation `value` intentionally accepts any JSON value copied from
approved evidence. Cross-document citation integrity is checked by
`contractkit.ai`, and workflow obligations are defined in the
[AI profile](../ai/README.md).
