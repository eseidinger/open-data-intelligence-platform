import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { PipelineRun, PipelineRunApiService } from '../../core/api/pipeline-run-api.service';

@Component({ selector: 'app-pipeline-runs-page', imports: [MatButtonModule, MatCardModule, MatProgressSpinnerModule, MatTableModule], templateUrl: './pipeline-runs-page.html', styleUrl: './pipeline-runs-page.scss', changeDetection: ChangeDetectionStrategy.OnPush })
export class PipelineRunsPageComponent {
  private readonly api = inject(PipelineRunApiService);
  readonly runs = signal<readonly PipelineRun[]>([]); readonly loading = signal(true); readonly error = signal<string | null>(null);
  readonly displayedColumns = ['sourceName', 'status', 'requestedAt', 'completedAt'];
  constructor() { this.load(); }
  load(): void { this.loading.set(true); this.error.set(null); this.api.list().subscribe({ next: (runs) => { this.runs.set(runs); this.loading.set(false); }, error: () => { this.error.set('Pipeline runs could not be loaded.'); this.loading.set(false); } }); }
}
