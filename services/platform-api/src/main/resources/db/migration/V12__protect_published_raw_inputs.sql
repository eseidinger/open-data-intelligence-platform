CREATE FUNCTION protect_published_raw_input() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS(SELECT 1 FROM publication_input i JOIN dataset_publication p ON p.id=i.publication_id
              WHERE i.raw_artifact_id=OLD.id AND p.status='PUBLISHED') THEN
        IF TG_OP='DELETE' OR NEW.payload IS DISTINCT FROM OLD.payload
           OR NEW.checksum_sha256 IS DISTINCT FROM OLD.checksum_sha256
           OR NEW.content_length IS DISTINCT FROM OLD.content_length
           OR NEW.source_id IS DISTINCT FROM OLD.source_id
           OR NEW.pipeline_run_id IS DISTINCT FROM OLD.pipeline_run_id
           OR NEW.retrieved_at IS DISTINCT FROM OLD.retrieved_at
           OR NEW.source_version IS DISTINCT FROM OLD.source_version THEN
            RAISE EXCEPTION 'Published raw input bytes and provenance are immutable';
        END IF;
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER published_raw_input_immutable BEFORE UPDATE OR DELETE ON raw_artifact
    FOR EACH ROW EXECUTE FUNCTION protect_published_raw_input();
