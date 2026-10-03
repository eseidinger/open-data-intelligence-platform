import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { DataSourceType } from './data-source-api.service';

export const datasetClassifications = ['PUBLIC', 'INTERNAL', 'RESTRICTED'] as const;

export type DatasetClassification = (typeof datasetClassifications)[number];

export interface SourceSummary {
  id: string;
  name: string;
  sourceType: DataSourceType;
}

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  owner: string | null;
  classification: DatasetClassification;
  sources: readonly SourceSummary[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateDatasetRequest {
  name: string;
  description: string;
  owner: string;
  classification: DatasetClassification;
  sourceIds: readonly string[];
}

export interface EnergyObservation {
  id: string;
  datasetId: string;
  datasetVersionId: string | null;
  datasetVersionNumber: number | null;
  rawArtifactId: string;
  indicatorCode: string;
  geoCode: string;
  observationYear: number;
  unitCode: string;
  observationValue: number;
  createdAt: string;
}

export interface DatasetSummary {
  datasetId: string;
  latestVersionNumber: number | null;
  retrievedAt: string | null;
  freshnessStatus: 'FRESH' | 'STALE' | 'UNKNOWN';
  freshnessDueAt: string | null;
  validationStatus: 'VALID' | 'INVALID' | 'UNSUPPORTED' | 'NOT_RECORDED';
  recordCount: number | null;
}

@Injectable({ providedIn: 'root' })
export class DatasetApiService {
  private readonly http = inject(HttpClient);

  list() {
    return this.http.get<readonly Dataset[]>('/api/datasets');
  }

  create(request: CreateDatasetRequest) {
    return this.http.post<Dataset>('/api/datasets', request);
  }

  listEnergyObservations(datasetId: string) {
    return this.http.get<readonly EnergyObservation[]>(`/api/datasets/${datasetId}/energy-observations`);
  }

  getSummary(datasetId: string) {
    return this.http.get<DatasetSummary>(`/api/datasets/${datasetId}/summary`);
  }
}
