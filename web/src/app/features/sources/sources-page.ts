import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ReactiveFormsModule, Validators, NonNullableFormBuilder } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import {
  dataSourceTypes,
  DataSource,
  DataSourceApiService,
  DataSourceType,
} from '../../core/api/data-source-api.service';

@Component({
  selector: 'app-sources-page',
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTableModule,
  ],
  templateUrl: './sources-page.html',
  styleUrl: './sources-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SourcesPageComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly dataSourceApi = inject(DataSourceApiService);

  readonly sourceTypes = dataSourceTypes;
  readonly displayedColumns = ['name', 'sourceType', 'owner', 'refreshCadence', 'actions'];
  readonly sources = signal<readonly DataSource[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly queueingSourceId = signal<string | null>(null);
  readonly error = signal<string | null>(null);

  readonly form = this.formBuilder.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    sourceType: ['API' as DataSourceType, Validators.required],
    location: [
      '',
      [
        Validators.required,
        Validators.maxLength(2048),
        Validators.pattern(/^[a-zA-Z][a-zA-Z0-9+.-]*:.+/),
      ],
    ],
    owner: ['', Validators.maxLength(255)],
    license: ['', Validators.maxLength(2048)],
    refreshCadence: ['', Validators.maxLength(255)],
  });

  constructor() {
    this.loadSources();
  }

  loadSources(): void {
    this.loading.set(true);
    this.error.set(null);
    this.dataSourceApi.list().subscribe({
      next: (sources) => {
        this.sources.set(sources);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Sources could not be loaded. Confirm that the platform API is running.');
        this.loading.set(false);
      },
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.error.set(null);
    this.dataSourceApi.create(this.form.getRawValue()).subscribe({
      next: (source) => {
        this.sources.update((sources) => [...sources, source].sort((left, right) => left.name.localeCompare(right.name)));
        this.form.reset({ sourceType: 'API' });
        this.saving.set(false);
      },
      error: () => {
        this.error.set('Source could not be saved. Names must be unique and locations must be valid URIs.');
        this.saving.set(false);
      },
    });
  }

  queueIngestion(source: DataSource): void {
    this.queueingSourceId.set(source.id);
    this.error.set(null);
    this.dataSourceApi.queueIngestion(source.id).subscribe({
      next: () => this.queueingSourceId.set(null),
      error: () => {
        this.error.set('Ingestion could not be queued.');
        this.queueingSourceId.set(null);
      },
    });
  }
}
