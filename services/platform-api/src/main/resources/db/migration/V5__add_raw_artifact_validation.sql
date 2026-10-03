CREATE TABLE raw_artifact_validation (
    id UUID PRIMARY KEY,
    raw_artifact_id UUID NOT NULL UNIQUE REFERENCES raw_artifact(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL,
    detected_format VARCHAR(64),
    record_count BIGINT,
    schema_fingerprint VARCHAR(64),
    failure_reason TEXT,
    validated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX raw_artifact_validation_status_idx ON raw_artifact_validation (status);
