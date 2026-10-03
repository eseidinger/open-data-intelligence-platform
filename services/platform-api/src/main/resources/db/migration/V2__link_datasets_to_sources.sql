CREATE TABLE dataset_source (
    dataset_id UUID NOT NULL REFERENCES dataset(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_source(id) ON DELETE RESTRICT,
    PRIMARY KEY (dataset_id, source_id)
);

CREATE INDEX dataset_source_source_id_idx ON dataset_source (source_id);
