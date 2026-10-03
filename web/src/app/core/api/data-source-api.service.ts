import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export const dataSourceTypes = ['API', 'FILE', 'DATABASE', 'STREAM', 'DOCUMENT'] as const;

export type DataSourceType = (typeof dataSourceTypes)[number];

export interface DataSource {
  id: string;
  name: string;
  sourceType: DataSourceType;
  location: string;
  owner: string | null;
  license: string | null;
  refreshCadence: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateDataSourceRequest {
  name: string;
  sourceType: DataSourceType;
  location: string;
  owner: string;
  license: string;
  refreshCadence: string;
}

@Injectable({ providedIn: 'root' })
export class DataSourceApiService {
  private readonly http = inject(HttpClient);

  list() {
    return this.http.get<readonly DataSource[]>('/api/data-sources');
  }

  create(request: CreateDataSourceRequest) {
    return this.http.post<DataSource>('/api/data-sources', request);
  }
}
