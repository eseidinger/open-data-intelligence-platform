import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ArtifactMigrationComponent } from './artifact-migration';

const checksum = 'a'.repeat(64);
const path = '/api/v1/artifact-storage/raw/raw-one/migrate';
const ready = { status: 'ready', sha256: checksum, contentLength: 10, postgresCopyRetained: true };

describe('Artifact migration', () => {
  let http: HttpTestingController;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ArtifactMigrationComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  function create() {
    const fixture = TestBed.createComponent(ArtifactMigrationComponent);
    fixture.componentRef.setInput('target', { kind: 'raw', id: 'raw-one' });
    fixture.componentRef.setInput('label', 'raw-one');
    fixture.componentRef.setInput('checksum', checksum);
    fixture.componentRef.setInput('contentLength', 10);
    fixture.detectChanges();
    return fixture;
  }

  it('requires a verified preview before applying and prevents duplicate submissions', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.migrate();
    http.expectNone(path);
    component.check();
    component.check();
    const preview = http.expectOne(path);
    expect(preview.request.body).toEqual({ apply: false });
    preview.flush(ready);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('10 bytes');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(checksum);
    component.migrate();
    component.migrate();
    const apply = http.expectOne(path);
    expect(apply.request.body).toEqual({ apply: true });
    apply.flush({ ...ready, status: 'migrated' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain(
      'Migration completed and verified.',
    );
  });

  it('does not allow migration when checksum or size differs from the artifact', () => {
    const fixture = create();
    for (const response of [
      { ...ready, sha256: 'b'.repeat(64) },
      { ...ready, contentLength: 11 },
    ]) {
      fixture.componentInstance.check();
      http.expectOne(path).flush(response);
      expect(fixture.componentInstance.error()).toContain('does not match');
      fixture.componentInstance.migrate();
      http.expectNone(path);
    }
  });

  it('invalidates previews and cancels pending checks when the selected artifact changes', () => {
    const fixture = create();
    fixture.componentInstance.check();
    const pending = http.expectOne(path);
    fixture.componentRef.setInput('target', { kind: 'raw', id: 'raw-two' });
    fixture.detectChanges();
    expect(pending.cancelled).toBe(true);
    expect(fixture.componentInstance.busy()).toBeNull();
    fixture.componentInstance.migrate();
    http.expectNone('/api/v1/artifact-storage/raw/raw-two/migrate');
    fixture.componentInstance.check();
    http.expectOne('/api/v1/artifact-storage/raw/raw-two/migrate').flush(ready);
  });

  it('requires a fresh preview after an inconclusive apply and hides raw error details', () => {
    const fixture = create();
    fixture.componentInstance.check();
    http.expectOne(path).flush(ready);
    fixture.componentInstance.migrate();
    http
      .expectOne(path)
      .flush(
        { message: 'sensitive-token response payload' },
        { status: 503, statusText: 'Unavailable' },
      );
    fixture.detectChanges();
    expect(fixture.componentInstance.error()).toContain('storage connection');
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('sensitive-token');
    fixture.componentInstance.migrate();
    http.expectNone(path);
    fixture.componentInstance.check();
    http.expectOne(path).flush({ ...ready, status: 'already_migrated' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('already stored in S3');
  });

  it('uses the publication endpoint and reports access denial without showing backend details', () => {
    const fixture = create();
    fixture.componentRef.setInput('target', {
      kind: 'publication',
      publicationId: 'publication',
      artifactId: 'hourly-counts',
    });
    fixture.detectChanges();
    fixture.componentInstance.check();
    http
      .expectOne(
        '/api/v1/artifact-storage/publications/publication/artifacts/hourly-counts/migrate',
      )
      .flush({ message: 'private error' }, { status: 403, statusText: 'Forbidden' });
    expect(fixture.componentInstance.error()).toContain('permissions');
    expect(fixture.componentInstance.error()).not.toContain('private error');
  });
});
