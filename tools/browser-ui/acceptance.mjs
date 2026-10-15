#!/usr/bin/env node
// [designed: T35] Real Chromium acceptance against the Python-owned live session.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { setTimeout as delay } from 'node:timers/promises';
import path from 'node:path';

const args = process.argv.slice(2);
const valueAfter = flag => { const at = args.indexOf(flag); return at >= 0 ? args[at + 1] : undefined; };
assert(args.includes('--scenario') && valueAfter('--scenario') === 'countries', 'use --scenario countries');
const modulePath = process.env.PLAYWRIGHT_MODULE;
assert(modulePath, 'set PLAYWRIGHT_MODULE to the installed Playwright entrypoint');
const require = createRequire(import.meta.url);
const { chromium } = require(path.resolve(modulePath));
const cwd = process.cwd();
const savestate = valueAfter('--savestate') || '.cache/e010-r0001-halftime.sav';
const goaldat = valueAfter('--goaldat') || '.cache/GOAL.DAT';
const screenshotDir = process.env.SCREENSHOT_DIR;
let child;
let base = valueAfter('--url');
if (!base) {
  child = spawn(process.env.PYTHON || 'python3', ['-m', 'goal2.web', savestate, goaldat, '--host', '127.0.0.1', '--port', '0'], {
    cwd, env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk; });
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const match = stdout.match(/http:\/\/127\.0\.0\.1:(\d+)\//);
    if (match) { base = `http://127.0.0.1:${match[1]}`; break; }
    if (child.exitCode !== null) throw new Error(`Python server exited: ${stdout}\n${stderr}`);
    await delay(50);
  }
  assert(base, `Python server did not report its address: ${stderr}`);
}
const getSession = async () => {
  const response = await fetch(`${base}/api/session`);
  assert.equal(response.status, 200, 'Python session endpoint is available');
  return response.json();
};
const getCountries = async () => {
  const response = await fetch(`${base}/api/countries`);
  assert.equal(response.status, 200, 'Python countries endpoint is available');
  return response.json();
};

let browser;
try {
  const initial = await getSession();
  const countryView = await getCountries();
  assert.equal(countryView.countries.length, 128, 'Python supplies all countries');
  const candidates = countryView.countries.filter(country => country.id !== initial.country.id && country.name !== 'Denmark').slice(0, 2);
  assert.equal(candidates.length, 2, 'two non-current country choices exist');
  assert(candidates.every(country => country.name !== 'Denmark'), 'both choices are non-Denmark countries');
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await page.goto(`${base}/`, { waitUntil: 'networkidle' });
  await page.locator('#club-country').waitFor({ state: 'visible' });
  assert.equal(await page.locator('#club-country').textContent(), initial.country.name);
  assert.equal(await page.locator('#squad-rows tr').count(), 20);

  for (const choice of candidates) {
    await page.locator('#country-select').selectOption(String(choice.id));
    await page.waitForFunction(expected => document.querySelector('#club-country')?.textContent === expected, choice.name);
    const expected = await getSession();
    assert.equal(expected.country.id, choice.id, 'Python owns the selected country');
    assert.equal(await page.locator('#club-country').textContent(), expected.country.name);
    assert.equal(await page.locator('#dashboard-roster-size').textContent(), String(expected.players.length));
    assert.equal(await page.locator('#squad-rows tr').count(), expected.players.length);
    await page.locator('[data-page="squad"]').click();
    for (let index = 0; index < expected.players.length; index += 1) {
      const row = page.locator('#squad-rows tr').nth(index);
      const player = expected.players[index];
      assert.equal(await row.locator('[data-select]').getAttribute('data-select'), String(player.id), 'roster player ID is the Python runtime ID');
      assert((await row.locator('.player-name').innerText()).startsWith(player.name), `roster name ${player.name}`);
      assert.equal((await row.locator('.rating-value').textContent()).trim(), String(player.ability), 'ability is record byte +4');
      assert.equal((await row.locator('.energy-value').textContent()).trim(), String(player.energy), 'energy is record byte +0xE');
      assert((await row.locator('.position-cell').innerText()).includes(`code ${player.position}`), 'position is source code +7');
    }
    await page.locator('[data-page="dashboard"]').click();
    if (expected.matchup.available) {
      assert.equal(await page.locator('#away-team').textContent(), expected.matchup.opponent.name, 'opponent matches Python resolver');
    } else {
      assert.equal(await page.locator('#away-team').textContent(), 'Unavailable');
      assert((await page.locator('#match-status').textContent()).includes('unavailable'));
    }
  }
  const selected = await getSession();
  await page.reload({ waitUntil: 'networkidle' });
  assert.equal(await page.locator('#club-country').textContent(), selected.country.name, 'reload keeps server country choice');
  assert.equal(await page.locator('#away-team').textContent(), selected.matchup.available ? selected.matchup.opponent.name : 'Unavailable');
  const pageText = await page.locator('body').innerText();
  for (const sample of ['Mikkel Madsen', 'SAMPLE PREVIEW', 'Scandinavian test', 'fictional sample data']) {
    assert(!pageText.includes(sample), `live page excludes prototype sample: ${sample}`);
  }
  if (screenshotDir) await mkdir(screenshotDir, { recursive: true });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '1280px dashboard has no page overflow');
  if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'countries-desktop-dashboard.png'), fullPage: true });
  await page.locator('[data-page="squad"]').click();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '1280px squad has no page overflow');
  if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'countries-desktop-squad.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(100);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '390px layout has no page overflow');
  await page.locator('[data-page="dashboard"]').click();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '390px dashboard has no page overflow');
  if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'countries-mobile-dashboard.png'), fullPage: true });
  await page.locator('[data-page="squad"]').click();
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, '390px squad layout has no page overflow');
  assert((await page.locator('.table-wrap').evaluate(el => el.scrollWidth)) >=
         (await page.locator('.table-wrap').evaluate(el => el.clientWidth)), '390px roster remains inside the table scroll region');
  if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'countries-mobile-squad.png'), fullPage: true });
  assert.deepEqual(pageErrors, [], 'browser has no page errors');
  await context.close();
  console.log(`PASS countries: ${candidates.map(country => `${country.name} (${country.id})`).join(', ')}`);
} finally {
  if (browser) await browser.close();
  if (child && child.exitCode === null) { child.kill('SIGTERM'); await new Promise(resolve => child.once('exit', resolve)); }
}
