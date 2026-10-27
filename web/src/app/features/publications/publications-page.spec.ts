import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { PublicationsPageComponent } from './publications-page';
import { PublicationDraft } from '../../core/api/publication-api.service';

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
    http.expectOne('/api/v1/operator-capabilities').flush({
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

  function published(): PublicationDraft {
    return {
      id: 'original',
      datasetId: 'dataset',
      status: 'PUBLISHED',
      manifestSha256: 'a'.repeat(64),
      report: null,
      failureCode: null,
      inputArtifacts: [
        {
          rawArtifactId: 'raw-one',
          pipelineRunId: 'run-one',
          sha256: 'b'.repeat(64),
          capturedAt: '2026-10-27T00:00:00Z',
        },
      ],
      manifest: {
        datasetId: 'energy',
        version: '1.0.0',
        schemaRef: 'energy:v1',
        metadata: {},
        artifacts: [],
        quality: { status: 'PASS', policyRef: 'quality:v1', warnings: [] },
        provenance: [],
      },
    };
  }

  async function chooseNextManifest(component: PublicationsPageComponent): Promise<void> {
    await component.chooseManifest({
      target: { files: [{ size: 30, text: async () => '{"version":"1.0.1"}' }] },
    } as unknown as Event);
  }

  it('creates a new draft with the selected published input lineage and preserves the original', async () => {
    const fixture = create(true);
    const original = published();
    const before = JSON.stringify(original);
    fixture.componentInstance.reuseInputs(original);
    fixture.detectChanges();
    expect(fixture.componentInstance.form.controls.datasetId.value).toBe('dataset');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Linking 1 captured inputs',
    );
    await chooseNextManifest(fixture.componentInstance);
    fixture.componentInstance.create();
    const post = http.expectOne(
      (request) => request.method === 'POST' && request.url === '/api/v1/publication-drafts',
    );
    expect(post.request.body.rawArtifactIds).toEqual(['raw-one']);
    expect(post.request.body.manifest.version).toBe('1.0.1');
    expect(JSON.stringify(original)).toBe(before);
    post.flush({ ...original, id: 'new', status: 'DRAFT' });
    http.expectOne('/api/v1/publication-drafts').flush([]);
    http
      .expectOne('/api/v1/operator-capabilities')
      .flush({ manageGrants: true, writableDatasetIds: ['dataset'] });
    http.expectOne('/api/datasets').flush([]);
  });

  it('clears captured input selection when the dataset changes', () => {
    const fixture = create(true);
    fixture.componentInstance.reuseInputs(published());
    fixture.componentInstance.form.controls.datasetId.setValue('another-dataset');
    expect(fixture.componentInstance.draftSource()).toBeNull();
    http.expectNone((request) => request.method === 'POST');
  });

  it('requires a permitted published version with captured inputs', () => {
    const fixture = create(false);
    fixture.componentInstance.reuseInputs(published());
    expect(fixture.componentInstance.draftSource()).toBeNull();
    fixture.componentInstance.capabilities.set({
      manageGrants: true,
      writableDatasetIds: ['dataset'],
    });
    fixture.componentInstance.reuseInputs({ ...published(), status: 'DRAFT' });
    expect(fixture.componentInstance.draftSource()).toBeNull();
    fixture.componentInstance.reuseInputs({ ...published(), inputArtifacts: [] });
    expect(fixture.componentInstance.draftSource()).toBeNull();
    http.expectNone((request) => request.method === 'POST');
  });

  it('keeps retries idempotent and changes the key when source inputs are cleared', async () => {
    const fixture = create(true);
    const component = fixture.componentInstance;
    component.reuseInputs(published());
    await chooseNextManifest(component);
    component.create();
    const first = http.expectOne((request) => request.method === 'POST');
    const key = first.request.headers.get('Idempotency-Key');
    first.flush({}, { status: 503, statusText: 'Unavailable' });
    component.create();
    const retry = http.expectOne((request) => request.method === 'POST');
    expect(retry.request.headers.get('Idempotency-Key')).toBe(key);
    expect(retry.request.body.rawArtifactIds).toEqual(['raw-one']);
    retry.flush({}, { status: 503, statusText: 'Unavailable' });
    component.clearDraftSource();
    component.create();
    const cleared = http.expectOne((request) => request.method === 'POST');
    expect(cleared.request.headers.get('Idempotency-Key')).not.toBe(key);
    expect(cleared.request.body.rawArtifactIds).toEqual([]);
    cleared.flush({}, { status: 503, statusText: 'Unavailable' });
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
