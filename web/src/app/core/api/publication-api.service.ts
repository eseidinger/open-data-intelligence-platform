import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface Publication {
  datasetId: string;
  version: string;
  schemaRef: string;
  metadata: Record<string, unknown>;
  artifacts: readonly {
    artifactId: string;
    role: string;
    mediaType: string;
    sha256: string;
    unit?: string;
  }[];
  quality: {
    status: string;
    policyRef: string;
    warnings: readonly { code: string; message: string }[];
  };
  provenance: readonly {
    sourceId: string;
    sourceOwner: string;
    license: string;
    retrievedAt: string;
    transformationVersion: string;
  }[];
}
export interface PublicationDraft {
  id: string;
  datasetId: string;
  status: 'DRAFT' | 'VALIDATING' | 'FAILED' | 'PUBLISHED';
  manifestSha256: string;
  manifest: Publication;
  report: { checks: Record<string, string> } | null;
  failureCode: string | null;
  inputArtifacts?: readonly {
    rawArtifactId: string;
    pipelineRunId: string;
    sha256: string;
    capturedAt: string;
  }[];
}
export interface DatasetGrant {
  principalId: string;
  permission: string;
}
export interface OperatorCapabilities {
  manageGrants: boolean;
  writableDatasetIds: readonly string[];
}

@Injectable({ providedIn: 'root' })
export class PublicationApiService {
  private readonly http = inject(HttpClient);
  drafts() {
    return this.http.get<readonly PublicationDraft[]>('/api/v1/publication-drafts');
  }
  capabilities() {
    return this.http.get<OperatorCapabilities>('/api/v1/operator-capabilities');
  }
  create(datasetId: string, manifest: Record<string, unknown>, key: string) {
    return this.http.post<PublicationDraft>(
      '/api/v1/publication-drafts',
      { datasetId, manifest },
      { headers: { 'Idempotency-Key': key } },
    );
  }
  upload(id: string, artifactId: string, file: File) {
    return this.http.put<void>(`/api/v1/publication-drafts/${id}/artifacts/${artifactId}`, file, {
      headers: { 'Content-Type': 'application/octet-stream' },
    });
  }
  publish(id: string, key: string) {
    return this.http.post<PublicationDraft>(
      `/api/v1/publication-drafts/${id}/publish`,
      {},
      { headers: { 'Idempotency-Key': key } },
    );
  }
  download(id: string, artifactId: string) {
    return this.http.get(`/api/v1/publication-drafts/${id}/artifacts/${artifactId}`, {
      responseType: 'blob',
    });
  }
  grants(datasetId: string) {
    return this.http.get<readonly DatasetGrant[]>(`/api/v1/dataset-grants/${datasetId}`);
  }
  grant(datasetId: string, principalId: string, permission: string) {
    return this.http.put<void>(`/api/v1/dataset-grants/${datasetId}`, { principalId, permission });
  }
  revoke(datasetId: string, grant: DatasetGrant) {
    return this.http.delete<void>(`/api/v1/dataset-grants/${datasetId}`, {
      params: { principalId: grant.principalId, permission: grant.permission },
    });
  }
}
