import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export type ArtifactMigrationTarget =
  { kind: 'raw'; id: string } | { kind: 'publication'; publicationId: string; artifactId: string };

export interface ArtifactMigrationResult {
  status: 'ready' | 'migrated' | 'already_migrated';
  sha256: string;
  contentLength: number;
  postgresCopyRetained: boolean;
}

@Injectable({ providedIn: 'root' })
export class ArtifactStorageApiService {
  private readonly http = inject(HttpClient);

  migrate(target: ArtifactMigrationTarget, apply: boolean) {
    const path =
      target.kind === 'raw'
        ? `raw/${encodeURIComponent(target.id)}`
        : `publications/${encodeURIComponent(target.publicationId)}/artifacts/${encodeURIComponent(target.artifactId)}`;
    return this.http.post<ArtifactMigrationResult>(`/api/v1/artifact-storage/${path}/migrate`, {
      apply,
    });
  }
}
