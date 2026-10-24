# Artifact storage

ODIP supports PostgreSQL and Developer Platform S3 bindings for raw inputs and
publication artifacts. PostgreSQL remains the authoritative catalog, manifest,
checksum, lineage, access-grant and retention database. Only the API component
(`web`) receives a store binding; workers and VEF continue using the application
API. Consumer URLs, canonical bytes, SHA-256 ETags and dataset permissions stay
unchanged. Parquet generation and DuckDB execution are subsequent Phase 2 work.

## Developer Platform setup

The platform provisions a named, versioned RustFS-backed S3 bucket, scoped
credentials, private native access and credential rotation. Use a read-write
binding for `web`, alongside its existing PostgreSQL binding, with an empty
`envPrefix`. The binding injects:

| Variable | Purpose |
| --- | --- |
| `S3_BUCKET` | Resource-owned bucket, not an operator-selected shared bucket. |
| `AWS_ENDPOINT_URL_S3` | Private platform relay endpoint. Path-style addressing is required. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Managed resource credentials; never put them in descriptors. |
| `AWS_DEFAULT_REGION` | S3 signing region. |
| `ODIP_ARTIFACT_STORAGE_BACKEND=s3` | Application setting enabling new S3 writes and migrations. Defaults to `postgres`. |

Preview and provision through the existing CLI workflow:

```bash
python scripts/setup-storage.py --profile lab --project odip-test --provider s3
python scripts/setup-storage.py --profile lab --project odip-test --provider s3 \
  --apply --update-descriptor infrastructure/deployments/application-test.json
```

For production use project `odip` and `application.json`. For a local Developer
Platform installation use profile `odip-local`, project `odip-test-local` and
`application-test-local.json`. The selected platform must advertise provider `s3`.
The [resource template](../infrastructure/integration/odip-s3.json) requests 1 GiB;
`--quota-bytes` can select another allocation on creation. Existing quotas and
bindings must match; the script does not change them or deploy the application.
It preserves existing descriptor bindings and adds the S3 binding and backend
setting. Review the updated descriptor and apply the updated access policy
before deployment, using the [bootstrap workflow](bootstrap.md). Commit the updated
project descriptors together with the S3 implementation and deployment workflow.
A push to `main` publishes `latest` images and deploys `odip-test`; a new version
tag publishes release images and deploys `odip`. The deployment guard requires
one unprefixed PostgreSQL binding in PostgreSQL mode, or two distinct unprefixed
bindings (PostgreSQL plus S3) when `ODIP_ARTIFACT_STORAGE_BACKEND=s3`. Repeated setup
reuses matching resources. Do not replace the PostgreSQL binding with S3.

Keep the platform-managed secret names unprefixed. On platform credential rotation
the component restarts and the SDK reloads the new binding environment. Use the
platform's private endpoint directly; do not add unrestricted external egress or
operator credentials. Transport encryption, at-rest encryption and off-host
backup are installation responsibilities. Confirm the platform's private relay
boundary and encrypted bucket/catalog backup policy before production activation.

Readiness includes `artifactStorage`: in S3 mode it verifies bucket access and
enabled versioning, with a fixed safe error code on failure. Liveness remains
independent of S3. No successful health polls are logged at INFO.

## Local RustFS

The optional Compose profile uses the same pinned RustFS 1.0.2 image as Developer
Platform, with a persistent volume and loopback-only S3/console ports:

```bash
docker compose --file infrastructure/compose/docker-compose.yml --profile s3 up --detach --wait
export AWS_ENDPOINT_URL_S3=http://localhost:9000
export AWS_ACCESS_KEY_ID=odip-local-access
export AWS_SECRET_ACCESS_KEY=odip-local-secret-only
export AWS_DEFAULT_REGION=us-east-1
export S3_BUCKET=odip-artifacts
export ODIP_ARTIFACT_STORAGE_BACKEND=s3
```

These are disposable local development credentials. For local application use,
create the bucket and enable versioning with an installed AWS CLI:

```bash
aws --endpoint-url "$AWS_ENDPOINT_URL_S3" s3api create-bucket --bucket "$S3_BUCKET"
aws --endpoint-url "$AWS_ENDPOINT_URL_S3" s3api put-bucket-versioning \
  --bucket "$S3_BUCKET" --versioning-configuration Status=Enabled
```

Alternatively create the bucket and enable versioning in the local RustFS console
at `http://localhost:9001`. For an existing bucket, verify its versioning rather
than recreating it. Start the API normally from this environment. This direct
Compose endpoint is for local application tests; a deployed local Developer
Platform installation still uses its scoped binding and private relay.

Run real-provider tests with PostgreSQL and RustFS running:

```bash
cd services/platform-api
ODIP_S3_INTEGRATION_TEST=true ./gradlew ktlintCheck test
```

Retain the AWS environment above. The test suite creates a uniquely named bucket,
enables versioning and removes only that owned bucket and its versions. It does
not use or delete the configured application bucket. CI runs the same tests with
an isolated RustFS service. Both PostgreSQL and S3 write paths are tested.

## Controlled migration

In the operator UI, open **Publications**, select a version, and use **Check S3
migration** on an artifact. For raw inputs open **Pipeline runs**, choose **View
artifacts**, and use the same action. Review size and SHA-256, then choose
**Migrate … to S3**. The UI reports completion or that an artifact is already in
S3. Original PostgreSQL copies remain retained. Controls are shown only when S3
is enabled and the identity has the required dataset/source permissions. Backend
permission checks apply again to every preview and migration. An inconclusive
request requires a fresh check before another migration can be submitted.

Deploy the schema and adapter with a verified S3 binding first. Migration is
explicit, per artifact, idempotent and available only through the operator API.
Apply the new `operator-artifact-storage` platform route, which requires the
operator browser session and CSRF boundary. ODIP additionally requires READ and
INGEST on a contributing dataset for raw inputs, or READ and WRITE on the
publication's dataset. Reader/worker service routes do not grant migration access.

| POST route | Identifier |
| --- | --- |
| `/api/v1/artifact-storage/raw/{id}/migrate` | Internal raw artifact UUID. |
| `/api/v1/artifact-storage/publications/{id}/artifacts/{artifact}/migrate` | Internal publication UUID and declared artifact ID. |

Send JSON `{}` or `{"apply":false}` to preview. The result `ready` means the
existing bytes pass their recorded checksum/length and the configured bucket is
accessible with versioning enabled; no object or storage reference is written.
Send `{"apply":true}` for the reviewed artifact to migrate it. Use the existing
operator session/Origin/CSRF workflow, not a worker token. See the
[operator OpenAPI](../contracts/openapi/publication-operations.json).

The implementation locks the source record, verifies the captured bytes, writes
a new UUID object key, requires a non-null S3 version ID, retrieves that exact
version, verifies length and SHA-256, and inserts the storage reference in the
same database transaction. It does not alter the manifest, published artifact,
raw provenance, validation report or grants. Results are `migrated`, or
`already_migrated` on a verified repeat. Responses contain checksums, lengths and
whether a PostgreSQL copy is retained; they expose no storage credentials.

Existing PostgreSQL bytes remain as a recovery copy. This migration changes the
active retrieval backend; it does **not** reclaim the original database space or
relax database immutability guards. New S3-mode uploads store only metadata in
PostgreSQL and bytes in S3. Current API limits remain: 10 MiB per S3 artifact and
50 MiB per publication. Larger streaming/multipart ingestion is future work.

A failed upload, version check or readback leaves the original bytes and active
reference unchanged. A database rollback also rolls back the new reference.
There is no silent fallback after an active S3 version is lost or corrupted:
reads fail with a sanitized `503` so an outage cannot hide missing evidence.
Disabling S3 configuration is not a rollback after any external references exist.

S3 and PostgreSQL cannot share a transaction. A crash or failed database commit
after upload can leave an unreferenced object. Do not configure blanket age-based
bucket expiry: supported publications and raw evidence must remain available.
After quiescing writes and reconciling all retained database references and
backups, an authorized operator may identify and remove orphaned UUID versions.
Automatic orphan reclamation and removal of retained PostgreSQL copies are not
part of this migration.

## Retention and recovery

The existing support-end policy and additional one-year grace period govern
publication expiry. Deleting expired metadata enqueues the exact S3 versions in a
transactional deletion outbox. A scheduled worker retries these deletions; a store
outage keeps the pending rows and does not undo the metadata transaction. It never
deletes another version at the same key. Monitor
`SELECT count(*) FROM artifact_object_deletion` for a growing backlog. Raw inputs
remain retained under the existing policy.

Back up PostgreSQL references **and** the retained bucket versions. Restore both
under quarantine, reconcile grants, revoked credentials and fresh bindings, then
verify manifests, artifact checksums, raw lineage and authorized consumer reads
before reopening access. PostgreSQL-only restoration cannot recover new S3-only
uploads. The real RustFS tests establish version pinning and metadata rereads;
a deployed platform backup/restore drill remains separate evidence.
