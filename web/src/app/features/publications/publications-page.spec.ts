import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PublicationsPageComponent } from './publications-page';

describe('Publication operator access', () => {
  let http: HttpTestingController;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PublicationsPageComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  function create(operator: boolean, enabled = true) {
    const fixture = TestBed.createComponent(PublicationsPageComponent);
    http.expectOne('/api/v1/publication-drafts').flush([]);
    http
      .expectOne('/api/v1/operator-capabilities')
      .flush({
        manageGrants: operator,
        writableDatasetIds: operator ? ['dataset'] : [],
        artifactStorage: {
          enabled,
          publicationDatasetIds: operator ? ['dataset'] : [],
          sourceIds: [],
        },
      });
    http
      .expectOne('/api/datasets')
      .flush([{ id: 'dataset', name: 'Reference', sources: [], classification: 'PUBLIC' }]);
    fixture.detectChanges();
    return fixture;
  }

  it('hides grant administration and publication controls for read-only identities', () => {
    const fixture = create(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Create a draft');
    expect(text).not.toContain('Grant access');
  });

  it('exposes grant management and draft preparation to permitted operators', () => {
    const fixture = create(true);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Create a draft');
    expect(text).toContain('Grant access');
  });

  it('rejects malformed manifest files before sending a request', async () => {
    const fixture = create(true);
    const event = { target: { files: [{ size: 2, text: async () => '[]' }] } } as unknown as Event;
    await fixture.componentInstance.chooseManifest(event);
    expect(fixture.componentInstance.error()).toContain('valid publication manifest');
    http.expectNone('/api/v1/publication-drafts', 'No write should be sent');
  });
  it('shows migration for permitted published artifacts and hides it when S3 is disabled', () => {
    const fixture = create(true);
    const draft = {
      id: 'publication',
      datasetId: 'dataset',
      status: 'PUBLISHED' as const,
      manifestSha256: 'a'.repeat(64),
      report: null,
      failureCode: null,
      manifest: {
        datasetId: 'energy',
        version: '1.0.0',
        schemaRef: 'energy:v1',
        metadata: {},
        artifacts: [
          {
            artifactId: 'hourly-counts',
            role: 'counts',
            mediaType: 'application/json',
            sha256: 'b'.repeat(64),
          },
        ],
        quality: { status: 'PASS', policyRef: 'quality:v1', warnings: [] },
        provenance: [],
      },
    };
    fixture.componentInstance.select(draft);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Check S3 migration for hourly-counts',
    );
    fixture.componentInstance.capabilities.set({
      manageGrants: true,
      writableDatasetIds: ['dataset'],
      artifactStorage: { enabled: false, publicationDatasetIds: [], sourceIds: [] },
    });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Check S3 migration');
  });
});
