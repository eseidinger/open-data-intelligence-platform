# ODIP Contracts

The consumer publication API, publication manifest, energy schemas, fixtures, and numerical oracles are supplied by the immutable [contract kit](vendor/contract-kit-v0.4.0/contract-kit/README.md). Its version and archive checksum are recorded in [contract-kit.lock.json](contract-kit.lock.json). Run `python scripts/verify-contract-kit.py` from the repository root to verify both the archive and every extracted file.

Do not edit vendored files. Upgrade by accepting a new released archive and checksum, updating the lock, and rerunning the shared suite and consumer tests.

- [Consumer publication API](vendor/contract-kit-v0.4.0/contract-kit/openapi/odip-publication-v1.yaml) defines discovery, manifests, artifact retrieval, ETags, and errors.
- [Publication manifest schema](vendor/contract-kit-v0.4.0/contract-kit/schemas/dataset-publication-v1.schema.json) defines the bytes exchanged with VEF.
- [Operator and worker API](openapi/publication-operations.json) defines draft preparation, publication jobs, dataset grants, and retention.
- [Legacy ingestion API](openapi/ingestions.yaml) remains available for the annual observation adapter and raw ingestion.

JSON artifacts and manifests use RFC 8785 canonical UTF-8 bytes without a trailing newline. Schema references are resolved through the pinned local registry, never through arbitrary network locations. The Kotlin API bundles the pinned schemas; the Python worker bundles the kit's validation and reference transformation utilities.

The generic API uses a profile registry in `services/platform-api/src/main/resources/publication-policies.json`. A new profile requires registered artifact schemas, an approved validation policy, and an adapter implementation. Energy and mobility currently traverse the same publication service and storage interface. The local mobility schema adds validation for the non-energy fixture whose artifact schema is not included in the shared kit.
