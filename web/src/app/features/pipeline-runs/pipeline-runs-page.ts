import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { PipelineRun, PipelineRunApiService, RawArtifact } from '../../core/api/pipeline-run-api.service';

@Component({ selector: 'app-pipeline-runs-page', imports: [MatButtonModule, MatCardModule, MatProgressSpinnerModule, MatTableModule], templateUrl: './pipeline-runs-page.html', styleUrl: './pipeline-runs-page.scss', changeDetection: ChangeDetectionStrategy.OnPush })
export class PipelineRunsPageComponent {
  private readonly api = inject(PipelineRunApiService);
  readonly runs = signal<readonly PipelineRun[]>([]);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly selectedRunId = signal<string | null>(null);
  readonly artifacts = signal<readonly RawArtifact[]>([]);
  readonly artifactsLoading = signal(false);
  readonly artifactsError = signal<string | null>(null);
  readonly selectedRun = computed(() => this.runs().find((run) => run.id === this.selectedRunId()) ?? null);
  readonly displayedColumns = ['sourceName', 'status', 'requestedAt', 'completedAt', 'artifacts'];
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(null); this.api.list().subscribe({ next: (runs) => { this.runs.set(runs); this.loading.set(false); }, error: () => { this.error.set('Pipeline runs could not be loaded.'); this.loading.set(false); } }); }
  selectRun(runId: string): void {
    this.selectedRunId.set(runId);
    this.artifacts.set([]);
    this.artifactsError.set(null);
    this.artifactsLoading.set(true);
    this.api.listArtifacts(runId).subscribe({
      next: (artifacts) => { this.artifacts.set(artifacts); this.artifactsLoading.set(false); },
      error: () => { this.artifactsError.set('Artifacts could not be loaded.'); this.artifactsLoading.set(false); },
    });
  }
}
