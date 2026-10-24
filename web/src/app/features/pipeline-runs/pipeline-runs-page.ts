import { forkJoin, catchError, of } from 'rxjs';
import { ArtifactMigrationComponent } from '../../shared/artifact-migration/artifact-migration';
import {
  OperatorCapabilities,
  PublicationApiService,
} from '../../core/api/publication-api.service';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import {
  PipelineRun,
  PipelineRunApiService,
  RawArtifact,
} from '../../core/api/pipeline-run-api.service';

@Component({
  selector: 'app-pipeline-runs-page',
  imports: [
    ArtifactMigrationComponent,
    MatButtonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    MatTableModule,
  ],
  templateUrl: './pipeline-runs-page.html',
  styleUrl: './pipeline-runs-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PipelineRunsPageComponent {
  private readonly api = inject(PipelineRunApiService);
  private readonly publications = inject(PublicationApiService);
  readonly capabilities = signal<OperatorCapabilities | null>(null);
  readonly runs = signal<readonly PipelineRun[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly selectedRunId = signal<string | null>(null);
  readonly artifacts = signal<readonly RawArtifact[]>([]);
  readonly artifactsLoading = signal(false);
  readonly artifactsError = signal<string | null>(null);
  readonly selectedRun = computed(
    () => this.runs().find((run) => run.id === this.selectedRunId()) ?? null,
  );
  readonly displayedColumns = ['sourceName', 'status', 'requestedAt', 'completedAt', 'artifacts'];
  constructor() {
    this.load();
  }
  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.capabilities.set(null);
    forkJoin({
      runs: this.api.list(),
      capabilities: this.publications.capabilities().pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ runs, capabilities }) => {
        this.runs.set(runs);
        this.capabilities.set(capabilities);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Pipeline runs could not be loaded.');
        this.loading.set(false);
      },
    });
  }
  canMigrate(sourceId: string): boolean {
    const storage = this.capabilities()?.artifactStorage;
    return storage?.enabled === true && storage.sourceIds.includes(sourceId);
  }
  selectRun(runId: string): void {
    this.selectedRunId.set(runId);
    this.artifacts.set([]);
    this.artifactsError.set(null);
    this.artifactsLoading.set(true);
    this.api.listArtifacts(runId).subscribe({
      next: (artifacts) => {
        if (this.selectedRunId() !== runId) return;
        this.artifacts.set(artifacts);
        this.artifactsLoading.set(false);
      },
      error: () => {
        if (this.selectedRunId() !== runId) return;
        this.artifactsError.set('Artifacts could not be loaded.');
        this.artifactsLoading.set(false);
      },
    });
  }
}
