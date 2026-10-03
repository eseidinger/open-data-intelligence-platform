CREATE TABLE data_source (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    source_type VARCHAR(64) NOT NULL,
    location TEXT NOT NULL,
    owner VARCHAR(255),
    license TEXT,
    refresh_cadence VARCHAR(255),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dataset (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    owner VARCHAR(255),
    classification VARCHAR(64) NOT NULL DEFAULT 'PUBLIC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dataset_version (
    id UUID PRIMARY KEY,
    dataset_id UUID NOT NULL REFERENCES dataset(id),
    version_number BIGINT NOT NULL,
    status VARCHAR(32) NOT NULL,
    schema_definition JSONB NOT NULL DEFAULT '{}'::jsonb,
    quality_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (dataset_id, version_number)
);

CREATE TABLE pipeline_run (
    id UUID PRIMARY KEY,
    pipeline_name VARCHAR(255) NOT NULL,
    source_id UUID REFERENCES data_source(id),
    dataset_id UUID REFERENCES dataset(id),
    output_dataset_version_id UUID REFERENCES dataset_version(id),
    status VARCHAR(32) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX pipeline_run_dataset_id_started_at_idx ON pipeline_run (dataset_id, started_at DESC);
