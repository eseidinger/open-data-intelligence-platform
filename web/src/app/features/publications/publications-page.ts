import { ArtifactMigrationComponent } from '../../shared/artifact-migration/artifact-migration';
import { JsonPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { forkJoin } from 'rxjs';
import { Dataset, DatasetApiService } from '../../core/api/dataset-api.service';
import {
  DatasetGrant,
  OperatorCapabilities,
  PublicationApiService,
  PublicationDraft,
} from '../../core/api/publication-api.service';

@Component({
  selector: 'app-publications-page',
  imports: [
    JsonPipe,
    ArtifactMigrationComponent,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
  ],
  templateUrl: './publications-page.html',
  styleUrl: './publications-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PublicationsPageComponent {
  private readonly api = inject(PublicationApiService);
  private readonly catalog = inject(DatasetApiService);
  private readonly fb = inject(NonNullableFormBuilder);
  readonly drafts = signal<readonly PublicationDraft[]>([]);
  readonly datasets = signal<readonly Dataset[]>([]);
  readonly grants = signal<readonly DatasetGrant[]>([]);
  readonly capabilities = signal<OperatorCapabilities>({
    manageGrants: false,
    writableDatasetIds: [],
  });
  readonly writableDatasets = computed(() =>
    this.datasets().filter((d) => this.capabilities().writableDatasetIds.includes(d.id)),
  );
  readonly selected = signal<PublicationDraft | null>(null);
  readonly busy = signal(false);
  readonly error = signal<string | null>(null);
  readonly message = signal<string | null>(null);
  readonly form = this.fb.group({ datasetId: ['', Validators.required] });
  readonly grantForm = this.fb.group({
    datasetId: ['', Validators.required],
    principalId: ['', Validators.required],
    permission: ['READ', Validators.required],
  });
  private manifest: Record<string, unknown> | null = null;
  private draftKey = crypto.randomUUID();
  private readonly publishKeys = new Map<string, string>();

  constructor() {
    this.refresh();
  }
  refresh(): void {
    this.busy.set(true);
    this.error.set(null);
    forkJoin({
      drafts: this.api.drafts(),
      capabilities: this.api.capabilities(),
      datasets: this.catalog.list(),
    }).subscribe({
      next: (result) => {
        this.drafts.set(result.drafts);
        this.capabilities.set(result.capabilities);
        this.datasets.set(result.datasets);
        const selected = this.selected();
        if (selected) this.selected.set(result.drafts.find((d) => d.id === selected.id) ?? null);
        this.busy.set(false);
      },
      error: (error) => this.failed(error),
    });
  }
  canWrite(draft: PublicationDraft): boolean {
    return this.capabilities().writableDatasetIds.includes(draft.datasetId);
  }
  canMigrate(draft: PublicationDraft): boolean {
    const storage = this.capabilities().artifactStorage;
    return storage?.enabled === true && storage.publicationDatasetIds.includes(draft.datasetId);
  }
  select(draft: PublicationDraft): void {
    this.selected.set(draft);
    this.message.set(null);
  }
  async chooseManifest(event: Event): Promise<void> {
    this.manifest = null;
    this.error.set(null);
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (file.size > 1024 * 1024) {
      this.error.set('The manifest must be at most 1 MiB.');
      return;
    }
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
      this.manifest = parsed as Record<string, unknown>;
      this.draftKey = crypto.randomUUID();
    } catch {
      this.error.set('Choose a valid publication manifest JSON file.');
    }
  }
  create(): void {
    if (this.form.invalid || !this.manifest) {
      this.error.set('Select a dataset and a manifest file.');
      return;
    }
    this.busy.set(true);
    this.api.create(this.form.controls.datasetId.value, this.manifest, this.draftKey).subscribe({
      next: (draft) => {
        this.selected.set(draft);
        this.message.set('Draft created. Attach its artifacts before requesting publication.');
        this.refresh();
      },
      error: (error) => this.failed(error),
    });
  }
  upload(draft: PublicationDraft, artifactId: string, event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      this.error.set('Artifacts must be at most 10 MiB.');
      return;
    }
    this.busy.set(true);
    this.api.upload(draft.id, artifactId, file).subscribe({
      next: () => {
        this.message.set('Artifact attached and its checksum verified.');
        this.busy.set(false);
      },
      error: (error) => this.failed(error),
    });
  }
  publish(draft: PublicationDraft): void {
    const key = this.publishKeys.get(draft.id) ?? crypto.randomUUID();
    this.publishKeys.set(draft.id, key);
    this.busy.set(true);
    this.api.publish(draft.id, key).subscribe({
      next: () => {
        this.message.set('Validation queued. Refresh to inspect the result.');
        this.refresh();
      },
      error: (error) => this.failed(error),
    });
  }
  download(draft: PublicationDraft, artifactId: string): void {
    this.api.download(draft.id, artifactId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${artifactId}.json`;
        link.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      },
      error: (error) => this.failed(error),
    });
  }
  loadGrants(): void {
    const dataset = this.grantForm.controls.datasetId.value;
    this.grants.set([]);
    if (dataset)
      this.api.grants(dataset).subscribe({
        next: (grants) => this.grants.set(grants),
        error: (error) => this.failed(error),
      });
  }
  grant(): void {
    if (this.grantForm.invalid) return;
    this.busy.set(true);
    const value = this.grantForm.getRawValue();
    this.api.grant(value.datasetId, value.principalId, value.permission).subscribe({
      next: () => {
        this.loadGrants();
        this.refresh();
      },
      error: (error) => this.failed(error),
    });
  }
  revoke(grant: DatasetGrant): void {
    this.busy.set(true);
    this.api.revoke(this.grantForm.controls.datasetId.value, grant).subscribe({
      next: () => {
        this.loadGrants();
        this.refresh();
      },
      error: (error) => this.failed(error),
    });
  }
  private failed(error: unknown): void {
    const message =
      error instanceof HttpErrorResponse && error.error && typeof error.error.message === 'string'
        ? error.error.message
        : 'The operation failed. Check your access and try again.';
    this.error.set(message);
    this.busy.set(false);
  }
}
