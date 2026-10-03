ALTER TABLE dataset_version ADD COLUMN raw_artifact_id UUID REFERENCES raw_artifact(id);
CREATE UNIQUE INDEX dataset_version_dataset_artifact_idx ON dataset_version (dataset_id, raw_artifact_id) WHERE raw_artifact_id IS NOT NULL;

ALTER TABLE energy_observation ADD COLUMN dataset_version_id UUID REFERENCES dataset_version(id);
CREATE INDEX energy_observation_dataset_version_idx ON energy_observation (dataset_version_id);
