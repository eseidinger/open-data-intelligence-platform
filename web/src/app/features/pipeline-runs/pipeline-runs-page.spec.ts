import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PipelineRunsPageComponent } from './pipeline-runs-page';

describe('Raw artifact migration controls', () => {
  let http: HttpTestingController;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PipelineRunsPageComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('shows migration only for source permissions advertised by the API', () => {
    const fixture = TestBed.createComponent(PipelineRunsPageComponent);
    http
      .expectOne('/api/v1/operator-pipeline-runs')
      .flush([
        {
          id: 'run',
          sourceId: 'source',
          sourceName: 'Energy',
          status: 'SUCCEEDED',
          requestedAt: '2026-10-24',
          completedAt: '2026-10-24',
        },
      ]);
    http
      .expectOne('/api/v1/operator-capabilities')
      .flush({
        manageGrants: false,
        writableDatasetIds: [],
        artifactStorage: { enabled: true, publicationDatasetIds: [], sourceIds: ['source'] },
      });
    fixture.componentInstance.selectRun('run');
    http
      .expectOne('/api/v1/operator-pipeline-runs/run/artifacts')
      .flush([
        {
          id: 'raw',
          storageUri: 'postgres://raw',
          contentType: 'application/json',
          contentLength: 2,
          checksumSha256: 'a'.repeat(64),
          sourceVersion: null,
          retrievedAt: '2026-10-24',
          validation: null,
        },
      ]);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Check S3 migration for raw',
    );
    fixture.componentInstance.capabilities.set({
      manageGrants: false,
      writableDatasetIds: [],
      artifactStorage: { enabled: true, publicationDatasetIds: [], sourceIds: [] },
    });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Check S3 migration');
  });

  it('keeps monitoring available when operator capabilities cannot be loaded', () => {
    const fixture = TestBed.createComponent(PipelineRunsPageComponent);
    http.expectOne('/api/v1/operator-pipeline-runs').flush([]);
    http
      .expectOne('/api/v1/operator-capabilities')
      .flush({}, { status: 403, statusText: 'Forbidden' });
    fixture.detectChanges();
    expect(fixture.componentInstance.loading()).toBe(false);
    expect(fixture.componentInstance.error()).toBeNull();
    expect(fixture.componentInstance.canMigrate('source')).toBe(false);
  });
});
