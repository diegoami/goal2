import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root = resolve(fileURLToPath(new URL('.', import.meta.url)));
const require = createRequire(import.meta.url);
assert.ok(process.env.PLAYWRIGHT_MODULE, 'Set PLAYWRIGHT_MODULE to the installed Playwright module path.');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE);
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8' };
const server = createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const requested = resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    assert.ok(requested === root || requested.startsWith(root + sep), 'Path must stay inside the preview directory.');
    const body = await readFile(requested);
    res.writeHead(200, { 'content-type': mime[extname(requested)] ?? 'application/octet-stream' });
    res.end(body);
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(resolveListen => server.listen(0, '127.0.0.1', resolveListen));
let browser;
try {
  const launchOptions = { headless: true };
  if (process.env.CHROMIUM_EXECUTABLE) launchOptions.executablePath = process.env.CHROMIUM_EXECUTABLE;
  browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
  const screenshotDir = process.env.SCREENSHOT_DIR;
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  const capture = async name => {
    if (screenshotDir) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: join(screenshotDir, name), fullPage: true, timeout: 10_000 });
    }
  };
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const base = 'http://127.0.0.1:' + server.address().port;
  await page.goto(base, { waitUntil: 'networkidle' });
  assert.match(await page.locator('.notice').first().innerText(), /Sample preview/, 'preview notice is visible');
  assert.equal(await page.locator('#selection-count').innerText(), '11 of 11 selected');
  await capture('desktop-dashboard.png');
  await page.locator('[data-page="squad"]').click();
  assert.equal(await page.locator('#squad-page').isVisible(), true, 'squad navigation opens squad');
  await page.locator('[data-select="krogh"]').focus();
  await page.locator('[data-select="krogh"]').press('Space');
  assert.equal(await page.locator('#selection-count').innerText(), '12 of 11 selected');
  assert.match(await page.locator('#selection-guidance').innerText(), /1 fewer player/);
  assert.equal(await page.locator('[data-select="krogh"]').evaluate(el => el === document.activeElement), true, 'keyboard selection keeps focus on the changed row');
  await page.locator('[data-select="krogh"]').press('Space');
  assert.equal(await page.locator('#selection-count').innerText(), '11 of 11 selected');
  await page.locator('#captain-select').selectOption('bro');
  assert.equal(await page.locator('[data-captain="bro"]').isChecked(), true, 'captain dropdown syncs with roster control');
  assert.equal(await page.locator('.captain-mark').innerText(), 'C', 'captain badge follows selected captain');
  await page.locator('[data-captain="lund"]').focus();
  await page.locator('[data-captain="lund"]').press('Space');
  assert.equal(await page.locator('#captain-select').inputValue(), 'lund', 'roster captain control syncs to dropdown');
  assert.equal(await page.locator('[data-captain="lund"]').evaluate(el => el === document.activeElement), true, 'keyboard captain change keeps focus on the control');
  await page.locator('[data-select="lund"]').uncheck();
  assert.notEqual(await page.locator('#captain-select').inputValue(), 'lund', 'removing captain assigns another selected player');
  const currentCaptain = await page.locator('#captain-select').inputValue();
  assert.equal(await page.locator('#captain-select option[value="' + currentCaptain + '"]').count(), 1);
  const selectedIds = await page.locator('.player-check:checked').evaluateAll(inputs => inputs.map(input => input.dataset.select));
  for (const id of selectedIds) await page.locator('[data-select="' + id + '"]').uncheck();
  assert.equal(await page.locator('#selection-count').innerText(), '0 of 11 selected');
  assert.equal(await page.locator('#captain-select').isDisabled(), true, 'captain control is unavailable with no selected players');
  assert.equal(await page.locator('#captain-select option').innerText(), 'No selected players');
  await page.locator('[data-select="madsen"]').check();
  assert.equal(await page.locator('#captain-select').inputValue(), 'madsen', 'first selected player becomes an eligible captain');
  await page.locator('#reset-button').click();
  assert.equal(await page.locator('#selection-count').innerText(), '11 of 11 selected');
  assert.equal(await page.locator('#captain-select').inputValue(), 'skov');
  assert.equal(await page.locator('[data-captain="skov"]').isChecked(), true);
  assert.equal(await page.locator('#summary-captain').innerText(), 'Lasse Skov');
  await capture('desktop-squad.png');
  await page.locator('[data-page="dashboard"]').click();
  assert.equal(await page.locator('#dashboard-page').isVisible(), true, 'overview navigation returns to dashboard');
  await page.setViewportSize({ width: 390, height: 844 });
  await capture('mobile-dashboard.png');
  const mobileDimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth }));
  assert.ok(mobileDimensions.document <= mobileDimensions.viewport, '390px viewport has horizontal page overflow: ' + JSON.stringify(mobileDimensions));
  await page.locator('[data-page="squad"]').click();
  const squadDimensions = await page.evaluate(() => ({ viewport: innerWidth, document: document.documentElement.scrollWidth, table: document.querySelector('.table-wrap').scrollWidth, tableClient: document.querySelector('.table-wrap').clientWidth }));
  assert.ok(squadDimensions.document <= squadDimensions.viewport, 'mobile squad page has horizontal page overflow: ' + JSON.stringify(squadDimensions));
  assert.ok(squadDimensions.table >= squadDimensions.tableClient, 'roster table remains contained in its horizontal scroll region');
  await capture('mobile-squad.png');
  await page.locator('.brand').click();
  assert.equal(await page.locator('#dashboard-page').isVisible(), true, 'goal2 brand returns to the overview');
  assert.deepEqual(pageErrors, [], 'browser page errors: ' + pageErrors.join('; '));
  console.log('PASS Chromium dashboard/squad navigation, selection feedback, captain synchronization, reset, sample label, 1280×900 and 390×844 layout; no page errors.');
  if (screenshotDir) console.log('Screenshots saved in ' + screenshotDir);
} finally {
  if (browser) await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
