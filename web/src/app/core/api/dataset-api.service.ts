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

@Injectable({ providedIn: 'root' })
export class DatasetApiService {
  private readonly http = inject(HttpClient);

  list() {
    return this.http.get<readonly Dataset[]>('/api/datasets');
  }

  create(request: CreateDatasetRequest) {
    return this.http.post<Dataset>('/api/datasets', request);
  }
}
