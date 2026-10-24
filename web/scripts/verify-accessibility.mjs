import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { dirname, resolve, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { chromium } from 'playwright';

const require = createRequire(import.meta.url);
const web = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const output = resolve(web, 'dist/odip-web/browser');
const manifest = JSON.parse(readFileSync(resolve(web, '../contracts/vendor/contract-kit-v0.5.0/contract-kit/fixtures/energy-reference-wasserburg-am-inn-2024/manifest.json')));
const dataset = { id: 'd4a050bb-15a4-4022-b9f9-5300e8bb46fc', name: 'Reference energy data', classification: 'PUBLIC', sources: [], owner: 'ODIP' };
const draft = { id: '88fc1c6e-3c4f-460e-9cfa-144b4c719514', datasetId: dataset.id, status: 'DRAFT', manifestSha256: 'a'.repeat(64), manifest, report: null, failureCode: null };
const sourceId = '6b9f9d08-af69-44fe-8578-259f0e686900';
const run = { id: 'ef3229f6-735c-47ba-b214-b0639b7b9400', sourceId, sourceName: 'Reference energy source', status: 'SUCCEEDED', requestedAt: '2026-10-24T09:00:00Z', completedAt: '2026-10-24T09:01:00Z' };
const raw = { id: '549081e8-2b3b-4616-8fc8-a67f42452bab', storageUri: 'postgres://raw-artifacts/fixture', contentType: 'application/json', contentLength: 10, checksumSha256: 'b'.repeat(64), sourceVersion: 'fixture-v1', retrievedAt: '2026-10-24T09:00:00Z', validation: null };
const server = createServer((request, response) => {
  try {
    const pathname = new URL(request.url, 'http://localhost').pathname;
    const file = pathname.startsWith('/ui/') ? resolve(output, pathname.slice(4)) : resolve(output, 'index.html');
    if (!file.startsWith(output + '/')) throw new Error('Invalid asset path');
    response.setHeader('Content-Type', ({ '.js': 'application/javascript', '.css': 'text/css', '.html': 'text/html', '.ico': 'image/x-icon' })[extname(file)] ?? 'application/octet-stream');
    response.end(readFileSync(file));
  } catch { response.statusCode = 404; response.end(); }
});
await new Promise(done => server.listen(0, '127.0.0.1', done));
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  let operator = false;
  await page.route('**/api/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith('/api/v1/artifact-storage/')) {
      const isRaw = path.includes('/raw/');
      const artifact = manifest.artifacts.find(value => path.includes('/artifacts/' + value.artifactId + '/'));
      if (!operator || (!isRaw && !artifact)) return route.fulfill({ status: 403, json: {} });
      return route.fulfill({ status: 200, json: { status: route.request().postDataJSON().apply ? 'migrated' : 'ready', sha256: isRaw ? raw.checksumSha256 : artifact.sha256, contentLength: 10, postgresCopyRetained: true } });
    }
    const result = path === '/api/v1/operator-capabilities' ? { manageGrants: operator, writableDatasetIds: operator ? [dataset.id] : [], artifactStorage: { enabled: true, publicationDatasetIds: operator ? [dataset.id] : [], sourceIds: operator ? [sourceId] : [] } } :
      path === '/api/v1/publication-drafts' ? (operator ? [draft] : []) :
      path === '/api/datasets' ? [dataset] :
      path === '/api/v1/operator-pipeline-runs' ? [run] :
      path === `/api/v1/operator-pipeline-runs/${run.id}/artifacts` ? [raw] : [];
    return route.fulfill({ status: 200, json: result });
  });
  async function checkAccessibility() {
    await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
    const result = await page.evaluate(async () => window.axe.run(document));
    if (result.violations.length) throw new Error(JSON.stringify(result.violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) }))));
  }
  async function migrateArtifact(label) {
    const preview = page.getByRole('button', { name: 'Check S3 migration for ' + label, exact: true });
    const apply = page.getByRole('button', { name: 'Migrate ' + label + ' to S3', exact: true });
    if (await apply.count()) throw new Error('Migration can start without a preview');
    await preview.focus();
    await page.keyboard.press('Enter');
    await apply.waitFor();
    await checkAccessibility();
    await page.waitForFunction(() => document.activeElement?.textContent.includes('Check S3 migration'));
    await page.keyboard.press('Tab');
    if (!(await apply.evaluate(element => element === document.activeElement))) throw new Error('Migration confirmation is not next in keyboard order');
    await page.keyboard.press('Enter');
    await page.getByText('Migration completed and verified.', { exact: true }).waitFor();
    await page.waitForFunction(() => document.activeElement?.textContent.includes('Check S3 migration'));
    await checkAccessibility();
  }
  const origin = 'http://127.0.0.1:' + server.address().port;
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: 900 });
    for (operator of [false, true]) {
      await page.goto(origin + '/publications');
      await page.getByRole('heading', { name: 'Dataset publications', exact: true }).waitFor();
      await page.waitForFunction(() => !document.querySelector('p[role=status]'));
      if (operator) {
        await page.getByRole('button', { name: manifest.datasetId + ' / 1.0.0', exact: true }).click();
        await page.getByRole('heading', { name: 'Provenance', exact: true }).waitFor();
      } else {
        if (await page.getByRole('heading', { name: 'Create a draft', exact: true }).count()) throw new Error('Read-only identity sees write controls');
      }
      await checkAccessibility();
      if (operator) await migrateArtifact(manifest.artifacts[0].artifactId);
      await page.goto(origin + '/pipeline-runs');
      await page.getByRole('button', { name: 'View artifacts', exact: true }).click();
      await page.getByRole('heading', { name: run.sourceName, exact: true }).waitFor();
      await checkAccessibility();
      if (operator) await migrateArtifact(raw.id);
      else if (await page.getByRole('button', { name: /Check S3 migration/ }).count()) throw new Error('Read-only identity sees raw migration controls');
    }
  }
  console.log('PASS: accessible publication and raw migration previews, keyboard operation, completion focus, and read-only views at desktop and mobile widths');
} finally {
  if (browser) await browser.close();
  await new Promise(done => server.close(done));
}
