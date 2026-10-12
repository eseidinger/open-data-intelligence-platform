CREATE TABLE publication_support (
    schema_ref VARCHAR(200) PRIMARY KEY,
    support_ends_at TIMESTAMPTZ NOT NULL
);
ALTER TABLE publication_audit ADD COLUMN correlation_id VARCHAR(36);

CREATE FUNCTION publication_expired(publication UUID) RETURNS boolean LANGUAGE sql STABLE AS $$
    SELECT EXISTS(SELECT 1 FROM dataset_publication p JOIN publication_support s
        ON s.schema_ref=convert_from(p.manifest,'UTF8')::jsonb->>'schemaRef'
        WHERE p.id=publication AND s.support_ends_at < CURRENT_TIMESTAMP - INTERVAL '1 year');
$$;
CREATE OR REPLACE FUNCTION protect_published_publication() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent UUID;
BEGIN
    IF TG_TABLE_NAME='dataset_publication' THEN
        IF OLD.status='PUBLISHED' THEN
            IF TG_OP='DELETE' AND publication_expired(OLD.id) THEN RETURN OLD; END IF;
            RAISE EXCEPTION 'Published dataset versions are immutable';
        END IF;
    ELSE
        parent := COALESCE(NEW.publication_id,OLD.publication_id);
        IF EXISTS(SELECT 1 FROM dataset_publication WHERE id=parent AND status='PUBLISHED') THEN
            IF TG_OP='DELETE' AND publication_expired(parent) THEN RETURN OLD; END IF;
            RAISE EXCEPTION 'Published dataset artifacts and lineage are immutable';
        END IF;
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
