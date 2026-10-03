ALTER TABLE data_source ADD COLUMN normalizer VARCHAR(64);

UPDATE data_source
SET normalizer = 'EUROSTAT_RENEWABLE_SHARE'
WHERE location LIKE '%/nrg_ind_ren?%';

CREATE TABLE energy_observation (
    id UUID PRIMARY KEY,
    raw_artifact_id UUID NOT NULL REFERENCES raw_artifact(id),
    dataset_id UUID NOT NULL REFERENCES dataset(id),
    indicator_code VARCHAR(128) NOT NULL,
    geo_code VARCHAR(32) NOT NULL,
    observation_year INTEGER NOT NULL CHECK (observation_year BETWEEN 1900 AND 2200),
    unit_code VARCHAR(32) NOT NULL,
    observation_value NUMERIC(18, 6) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (raw_artifact_id, indicator_code, geo_code, observation_year, unit_code)
);

CREATE INDEX energy_observation_dataset_year_idx ON energy_observation (dataset_id, observation_year DESC);
