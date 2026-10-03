import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { forkJoin } from 'rxjs';
import { DataSource, DataSourceApiService } from '../../core/api/data-source-api.service';
import {
  Dataset,
  DatasetApiService,
  DatasetClassification,
  DatasetSummary,
  EnergyObservation,
  datasetClassifications,
} from '../../core/api/dataset-api.service';

@Component({
  selector: 'app-datasets-page',
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
  templateUrl: './datasets-page.html',
  styleUrl: './datasets-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DatasetsPageComponent {
  private readonly formBuilder = inject(NonNullableFormBuilder);
  private readonly datasetApi = inject(DatasetApiService);
  private readonly dataSourceApi = inject(DataSourceApiService);

  readonly classifications = datasetClassifications;
  readonly displayedColumns = ['name', 'classification', 'sources', 'owner', 'observations'];
  readonly datasets = signal<readonly Dataset[]>([]);
  readonly sourceOptions = signal<readonly DataSource[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedDataset = signal<Dataset | null>(null);
  readonly observations = signal<readonly EnergyObservation[]>([]);
  readonly observationsLoading = signal(false);
  readonly observationsError = signal<string | null>(null);
  readonly summary = signal<DatasetSummary | null>(null);

  readonly form = this.formBuilder.group({
    name: ['', [Validators.required, Validators.maxLength(255)]],
    description: ['', Validators.maxLength(10_000)],
    owner: ['', Validators.maxLength(255)],
    classification: ['PUBLIC' as DatasetClassification, Validators.required],
    sourceIds: this.formBuilder.control<string[]>([], Validators.required),
  });

  constructor() {
    this.loadCatalog();
  }

  loadCatalog(): void {
    this.loading.set(true);
    this.error.set(null);
    forkJoin({ datasets: this.datasetApi.list(), sources: this.dataSourceApi.list() }).subscribe({
      next: ({ datasets, sources }) => {
        this.datasets.set(datasets);
        this.sourceOptions.set(sources);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Datasets could not be loaded. Confirm that the platform API is running.');
        this.loading.set(false);
      },
    });
  }

  sourceNames(dataset: Dataset): string {
    return dataset.sources.map((source) => source.name).join(', ');
  }

  showObservations(dataset: Dataset): void {
    this.selectedDataset.set(dataset);
    this.observations.set([]);
    this.observationsError.set(null);
    this.summary.set(null);
    this.observationsLoading.set(true);
    this.datasetApi.listEnergyObservations(dataset.id).subscribe({
      next: (observations) => {
        this.observations.set(observations);
        this.observationsLoading.set(false);
      },
      error: () => {
        this.observationsError.set('Curated energy observations could not be loaded.');
        this.observationsLoading.set(false);
      },
    });
    this.datasetApi.getSummary(dataset.id).subscribe({
      next: (summary) => this.summary.set(summary),
      error: () => this.observationsError.set('Dataset quality and freshness could not be loaded.'),
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.error.set(null);
    this.datasetApi.create(this.form.getRawValue()).subscribe({
      next: (dataset) => {
        this.datasets.update((datasets) => [...datasets, dataset].sort((left, right) => left.name.localeCompare(right.name)));
        this.form.reset({ classification: 'PUBLIC', sourceIds: [] });
        this.saving.set(false);
      },
      error: () => {
        this.error.set('Dataset could not be saved. Choose one or more registered sources and use a unique name.');
        this.saving.set(false);
      },
    });
  }
}
