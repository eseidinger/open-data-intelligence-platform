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

export interface RawArtifact {
  id: string;
  storageUri: string;
  contentType: string | null;
  contentLength: number;
  checksumSha256: string;
  sourceVersion: string | null;
  retrievedAt: string;
  validation: RawArtifactValidation | null;
}

export interface RawArtifactValidation {
  status: 'VALID' | 'INVALID' | 'UNSUPPORTED';
  detectedFormat: string | null;
  recordCount: number | null;
  schemaFingerprint: string | null;
  failureReason: string | null;
  validatedAt: string;
}

@Injectable({ providedIn: 'root' })
export class PipelineRunApiService {
  private readonly http = inject(HttpClient);
  list() { return this.http.get<readonly PipelineRun[]>('/api/pipeline-runs'); }
  listArtifacts(runId: string) { return this.http.get<readonly RawArtifact[]>(`/api/pipeline-runs/${runId}/artifacts`); }
}
