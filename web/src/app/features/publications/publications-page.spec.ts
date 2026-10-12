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

  function create(operator: boolean) {
    const fixture = TestBed.createComponent(PublicationsPageComponent);
    http.expectOne('/api/v1/publication-drafts').flush([]);
    http
      .expectOne('/api/v1/operator-capabilities')
      .flush({ manageGrants: operator, writableDatasetIds: operator ? ['dataset'] : [] });
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
});
