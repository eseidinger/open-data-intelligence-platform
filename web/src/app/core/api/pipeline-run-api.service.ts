import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export interface PipelineRun {
  id: string;
  sourceId: string;
  sourceName: string;
  status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED';
  requestedAt: string;
  startedAt: string | null;
  completedAt: string | null;
}

@Injectable({ providedIn: 'root' })
export class PipelineRunApiService {
  private readonly http = inject(HttpClient);
  list() { return this.http.get<readonly PipelineRun[]>('/api/pipeline-runs'); }
}
