# JSON Schemas

Every schema uses JSON Schema 2020-12, has a stable `$id`, rejects unknown
properties, and is versioned independently. Domain payloads carry a `schemaVersion` value;
platform principal-header objects, operational envelopes, and boundary error bodies describe the actual
transport and do not add version fields to upstream requests or responses.
Semantic checks that JSON Schema cannot express—such as interval completeness,
chronological ordering, digest matching, and cross-artifact consistency—belong
in the shared validation runner.
