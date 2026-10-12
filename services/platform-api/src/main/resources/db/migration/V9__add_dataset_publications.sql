CREATE TABLE dataset_public_identity (
    public_dataset_id VARCHAR(100) PRIMARY KEY,
    dataset_id UUID NOT NULL UNIQUE REFERENCES dataset(id)
);
CREATE TABLE dataset_publication (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset(id),
    public_dataset_id VARCHAR(100) NOT NULL,
    version VARCHAR(100) NOT NULL,
    manifest BYTEA NOT NULL,
    manifest_sha256 VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL CHECK (status IN ('DRAFT', 'VALIDATING', 'FAILED', 'PUBLISHED')),
    creator VARCHAR(200) NOT NULL,
    idempotency_key VARCHAR(200) NOT NULL,
    request_sha256 VARCHAR(64) NOT NULL,
    report JSONB,
    failure_code VARCHAR(100),
    validator VARCHAR(200),
    claimed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    UNIQUE(public_dataset_id, version),
    UNIQUE(creator, idempotency_key)
);
CREATE TABLE publication_artifact (
    publication_id UUID NOT NULL REFERENCES dataset_publication(id),
    artifact_id VARCHAR(100) NOT NULL,
    payload BYTEA NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    PRIMARY KEY(publication_id, artifact_id)
);
CREATE TABLE publication_input (
    publication_id UUID NOT NULL REFERENCES dataset_publication(id),
    raw_artifact_id UUID NOT NULL REFERENCES raw_artifact(id),
    PRIMARY KEY(publication_id, raw_artifact_id)
);
CREATE TABLE dataset_grant (
    dataset_id UUID NOT NULL REFERENCES dataset(id),
    principal_id VARCHAR(200) NOT NULL,
    permission VARCHAR(32) NOT NULL CHECK (permission IN ('READ', 'WRITE', 'INGEST', 'VALIDATE')),
    PRIMARY KEY(dataset_id, principal_id, permission)
);
CREATE TABLE publication_audit (
    id UUID PRIMARY KEY,
    principal_id VARCHAR(200) NOT NULL,
    action VARCHAR(100) NOT NULL,
    dataset_id UUID,
    publication_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE publication_request (
    publication_id UUID NOT NULL REFERENCES dataset_publication(id),
    principal_id VARCHAR(200) NOT NULL,
    idempotency_key VARCHAR(200) NOT NULL,
    PRIMARY KEY(principal_id, idempotency_key)
);
CREATE FUNCTION protect_published_publication() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'dataset_publication' THEN
        IF OLD.status = 'PUBLISHED' THEN
            RAISE EXCEPTION 'Published dataset versions are immutable';
        END IF;
    ELSE
        IF EXISTS (SELECT 1 FROM dataset_publication WHERE id = COALESCE(NEW.publication_id, OLD.publication_id) AND status = 'PUBLISHED') THEN
            RAISE EXCEPTION 'Published dataset artifacts and lineage are immutable';
        END IF;
    END IF;
    IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER publication_immutable BEFORE UPDATE OR DELETE ON dataset_publication
    FOR EACH ROW EXECUTE FUNCTION protect_published_publication();
CREATE TRIGGER artifact_immutable BEFORE INSERT OR UPDATE OR DELETE ON publication_artifact
    FOR EACH ROW EXECUTE FUNCTION protect_published_publication();
CREATE TRIGGER input_immutable BEFORE INSERT OR UPDATE OR DELETE ON publication_input
    FOR EACH ROW EXECUTE FUNCTION protect_published_publication();
ALTER TABLE pipeline_run ADD COLUMN owner_principal VARCHAR(200);
