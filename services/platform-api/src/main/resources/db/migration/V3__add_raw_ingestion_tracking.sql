ALTER TABLE pipeline_run ALTER COLUMN started_at DROP NOT NULL;
ALTER TABLE pipeline_run ADD COLUMN requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE pipeline_run ADD COLUMN failure_reason TEXT;

CREATE TABLE raw_artifact (
    id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL UNIQUE REFERENCES pipeline_run(id),
    source_id UUID NOT NULL REFERENCES data_source(id),
    storage_uri TEXT NOT NULL UNIQUE,
    content_type VARCHAR(255),
    content_length BIGINT NOT NULL,
    checksum_sha256 CHAR(64) NOT NULL,
    source_version VARCHAR(1024),
    retrieved_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX pipeline_run_source_id_requested_at_idx ON pipeline_run (source_id, requested_at DESC);
