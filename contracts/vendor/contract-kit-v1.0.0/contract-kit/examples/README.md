# Examples

Examples are compact payloads intended for schema and API tests. They are not
the complete reference fixtures and do not represent measurements or commercial
offers.

The `platform-*` examples demonstrate normalized boundary identity headers and
access-error bodies. They are transport contracts, not domain datasets. Header
examples contain synthetic opaque IDs. Deployment and control-plane request
examples are indexed separately under `../platform/`.

`platform-operational-envelope.json` is the only centrally retained application
log shape: event, level, and an optional opaque correlation ID. Domain IDs,
messages, tokens, and customer values are excluded from this emission profile.
The collector strips unknown fields from external producers; kit applications
emit the minimized form directly. See the platform profile for retention and
read-access semantics.
