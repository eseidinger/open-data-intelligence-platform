import { DOCUMENT } from '@angular/common';
import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  Injector,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DestroyRef } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { Subscription } from 'rxjs';
import {
  ArtifactMigrationResult,
  ArtifactMigrationTarget,
  ArtifactStorageApiService,
} from '../../core/api/artifact-storage-api.service';

@Component({
  selector: 'app-artifact-migration',
  imports: [MatButtonModule],
  templateUrl: './artifact-migration.html',
  styles: `
    :host {
      display: block;
      margin-block: 1rem;
    }
    .checksum {
      overflow-wrap: anywhere;
    }
    dt {
      font-weight: 600;
    }
    dd {
      margin-inline-start: 0;
      margin-block-end: 0.5rem;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactMigrationComponent {
  readonly target = input.required<ArtifactMigrationTarget>();
  readonly label = input.required<string>();
  readonly checksum = input.required<string>();
  readonly contentLength = input<number>();
  readonly result = signal<ArtifactMigrationResult | null>(null);
  readonly busy = signal<'checking' | 'migrating' | null>(null);
  readonly error = signal<string | null>(null);
  private readonly api = inject(ArtifactStorageApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly injector = inject(Injector);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly document = inject(DOCUMENT);
  private readonly checkButton = viewChild<ElementRef<HTMLButtonElement>>('checkButton');
  private readonly identity = computed(() =>
    JSON.stringify([this.target(), this.checksum(), this.contentLength()]),
  );
  private checkedIdentity: string | null = null;
  private request?: Subscription;

  constructor() {
    effect(() => {
      this.identity();
      this.request?.unsubscribe();
      this.checkedIdentity = null;
      this.result.set(null);
      this.error.set(null);
      this.busy.set(null);
    });
  }

  check(): void {
    this.run(false);
  }

  migrate(): void {
    if (this.result()?.status !== 'ready' || this.checkedIdentity !== this.identity()) return;
    this.run(true);
  }

  private run(apply: boolean): void {
    if (this.busy()) return;
    const identity = this.identity();
    this.busy.set(apply ? 'migrating' : 'checking');
    this.error.set(null);
    this.result.set(null);
    this.checkedIdentity = null;
    this.request = this.api
      .migrate(this.target(), apply)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if (identity !== this.identity()) return;
          this.busy.set(null);
          if (
            result.sha256 !== this.checksum() ||
            (this.contentLength() !== undefined && result.contentLength !== this.contentLength()) ||
            (apply && result.status === 'ready') ||
            (!apply && result.status === 'migrated')
          ) {
            this.error.set(
              'The migration result does not match this artifact. Refresh the artifact before trying again.',
            );
          } else {
            this.result.set(result);
            this.checkedIdentity = identity;
          }
          this.restoreFocus();
        },
        error: (error: unknown) => {
          if (identity !== this.identity()) return;
          this.busy.set(null);
          const status = error instanceof HttpErrorResponse ? error.status : 0;
          this.error.set(
            status === 403
              ? 'Migration access was denied. Ask a dataset administrator to check your permissions.'
              : status === 503
                ? 'S3 migration is unavailable. Ask an administrator to check the storage connection, then check the migration again.'
                : status === 404
                  ? 'This artifact is unavailable. Refresh the artifact list before trying again.'
                  : 'The migration could not be confirmed. Check the migration again before retrying.',
          );
          this.restoreFocus();
        },
      });
  }

  private restoreFocus(): void {
    afterNextRender(
      () => {
        const active = this.document.activeElement;
        if (active === this.document.body || this.host.nativeElement.contains(active)) {
          this.checkButton()?.nativeElement.focus();
        }
      },
      { injector: this.injector },
    );
  }
}
