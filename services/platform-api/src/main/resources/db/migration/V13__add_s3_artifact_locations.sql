-- Keep original immutable bytes during migration. External storage references are
-- separate from publication bytes and lineage, so existing guards stay intact.
ALTER TABLE publication_artifact ALTER COLUMN payload DROP NOT NULL;
ALTER TABLE publication_artifact ADD COLUMN content_length BIGINT;
-- Existing published rows must not be updated: immutable triggers stay active.
-- Their length is derived from the retained payload when content_length is NULL.
ALTER TABLE publication_artifact ADD CHECK (content_length >= 0);
ALTER TABLE publication_artifact ADD CHECK (payload IS NOT NULL OR content_length IS NOT NULL);

CREATE TABLE artifact_object (
    storage_id VARCHAR(250) PRIMARY KEY,
    raw_artifact_id UUID UNIQUE REFERENCES raw_artifact(id) ON DELETE CASCADE,
    publication_id UUID,
    artifact_id VARCHAR(100),
    bucket VARCHAR(200) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    version_id VARCHAR(1000) NOT NULL CHECK (version_id <> '' AND version_id <> 'null'),
    sha256 VARCHAR(64) NOT NULL,
    content_length BIGINT NOT NULL CHECK (content_length >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(publication_id,artifact_id) REFERENCES publication_artifact(publication_id,artifact_id) ON DELETE CASCADE,
    UNIQUE(publication_id,artifact_id),
    CHECK ((raw_artifact_id IS NOT NULL AND publication_id IS NULL AND artifact_id IS NULL)
        OR (raw_artifact_id IS NULL AND publication_id IS NOT NULL AND artifact_id IS NOT NULL))
);

-- Object deletion follows the metadata transaction and retries after failures.
CREATE TABLE artifact_object_deletion (
    id UUID PRIMARY KEY,
    bucket VARCHAR(200) NOT NULL,
    object_key VARCHAR(500) NOT NULL,
    version_id VARCHAR(1000) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE FUNCTION queue_artifact_object_deletion() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO artifact_object_deletion VALUES (gen_random_uuid(),OLD.bucket,OLD.object_key,OLD.version_id,CURRENT_TIMESTAMP);
    RETURN OLD;
END $$;
CREATE TRIGGER artifact_object_deleted AFTER DELETE ON artifact_object
    FOR EACH ROW EXECUTE FUNCTION queue_artifact_object_deletion();
