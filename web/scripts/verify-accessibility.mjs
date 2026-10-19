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
    const result = path === '/api/v1/operator-capabilities' ? { manageGrants: operator, writableDatasetIds: operator ? [dataset.id] : [] } :
      path === '/api/v1/publication-drafts' ? (operator ? [draft] : []) :
      path === '/api/datasets' ? [dataset] : [];
    return route.fulfill({ status: 200, json: result });
  });
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
      await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
      const result = await page.evaluate(async () => window.axe.run(document));
      if (result.violations.length) throw new Error(JSON.stringify(result.violations.map(v => ({ id: v.id, targets: v.nodes.map(n => n.target) }))));
    }
  }
  console.log('PASS: browser accessibility checks for operator and read-only publication views at desktop and mobile widths');
} finally {
  if (browser) await browser.close();
  await new Promise(done => server.close(done));
}
