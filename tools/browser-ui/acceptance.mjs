#!/usr/bin/env node
// [designed: T35, T37] Real Chromium acceptance against the Python-owned live session.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { setTimeout as delay } from 'node:timers/promises';
import path from 'node:path';

const args = process.argv.slice(2);
const valueAfter = flag => { const at = args.indexOf(flag); return at >= 0 ? args[at + 1] : undefined; };
const scenario = valueAfter('--scenario');
assert(args.includes('--scenario') && ['countries', 'management', 'friendlies', 'persistence'].includes(scenario), 'use --scenario countries|management|friendlies|persistence');
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
let saveDirectory;
let savePath;
if (scenario === 'persistence') {
  saveDirectory = await mkdtemp(path.join('/tmp', 'goal2-browser-save-'));
  savePath = path.join(saveDirectory, 'session.g2save');
}
async function startServer(resume = false) {
  child = spawn(process.env.PYTHON || 'python3', resume
    ? ['-m', 'goal2.web', '--resume', savePath, goaldat, '--host', '127.0.0.1', '--port', '0']
    : ['-m', 'goal2.web', savestate, goaldat, ...(savePath ? ['--save', savePath] : []), '--host', '127.0.0.1', '--port', '0'], {
    cwd, env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' }, stdio: ['ignore', 'pipe', 'pipe'],
  });
  let stdout = '';
  let stderr = '';
  child.stdout.setEncoding('utf8').on('data', chunk => { stdout += chunk; });
  child.stderr.setEncoding('utf8').on('data', chunk => { stderr += chunk; });
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const match = stdout.match(/http:\/\/127\.0\.0\.1:(\d+)\//);
    if (match) { base = `http://127.0.0.1:${match[1]}`; return; }
    if (child.exitCode !== null) throw new Error(`Python server exited: ${stdout}\n${stderr}`);
    await delay(50);
  }
  throw new Error(`Python server did not report its address: ${stderr}`);
}
async function stopServer() {
  if (child && child.exitCode === null) {
    child.kill('SIGTERM');
    await new Promise(resolve => child.once('exit', resolve));
  }
  child = null;
}
if (!base) {
  await startServer();
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
  if (scenario === 'management') {
    const initial = await getSession();
    const countries = await getCountries();
    const choice = countries.countries.find(country => country.id !== initial.country.id && country.name !== 'Denmark');
    assert(choice, 'a non-Denmark country is available');
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    const pageErrors = [];
    let managementPosts = 0;
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('request', request => { if (request.url().endsWith('/api/management')) managementPosts += 1; });
    await page.goto(`${base}/`, { waitUntil: 'networkidle' });
    await page.locator('#club-country').waitFor({ state: 'visible' });
    await page.locator('[data-page="squad"]').click();

    // A draft from the prior country is discarded when Python supplies a new squad.
    const beforeCountryDraft = await getSession();
    await page.locator('[data-select="' + beforeCountryDraft.players[11].id + '"]').check();
    await page.locator('[data-tactic-bit="0"]').setChecked(!Boolean(beforeCountryDraft.confirmed.tactics & 1));
    await page.locator('#country-select').selectOption(String(choice.id));
    await page.waitForFunction(expected => document.querySelector('#club-country')?.textContent === expected, choice.name);
    let current = await getSession();
    assert.equal(current.country.id, choice.id, 'Python owns the selected country');
    assert.equal(await page.locator('.player-check:checked').count(), 11, 'new country starts from its confirmed eleven');
    assert.deepEqual(await page.locator('.player-check:checked').evaluateAll(inputs => inputs.map(input => Number(input.dataset.select))), current.confirmed.starting_eleven, 'previous country lineup draft does not carry into the new squad');
    assert.equal(await page.locator('#captain-select').inputValue(), String(current.confirmed.captain || current.confirmed.starting_eleven[0]), 'previous country captain draft does not carry into the new squad');
    assert.equal(await page.locator('[data-tactic-bit="0"]').isChecked(), Boolean(current.confirmed.tactics & 1), 'new country starts from its stored tactics');

    const tacticControl = page.locator('[data-tactic-bit="0"]');
    await tacticControl.focus();
    await tacticControl.press('Space');
    assert.equal(await page.locator('[data-tactic-bit="0"]').evaluate(el => el === document.activeElement), true, 'keyboard tactic edit retains focus');
    await page.locator(`[data-select="${current.confirmed.starting_eleven[0]}"]`).uncheck();
    await page.locator('[data-tactic-bit="1"]').setChecked(!Boolean(current.confirmed.tactics & 2));
    await page.locator('#reset-button').click();
    assert.deepEqual(await page.locator('.player-check:checked').evaluateAll(inputs => inputs.map(input => Number(input.dataset.select))), current.confirmed.starting_eleven, 'reset restores the confirmed eleven');
    assert.equal(await page.locator('#captain-select').inputValue(), String(current.confirmed.captain || current.confirmed.starting_eleven[0]), 'reset restores the confirmed captain');
    for (let bit = 0; bit < 8; bit += 1) assert.equal(await page.locator(`[data-tactic-bit="${bit}"]`).isChecked(), Boolean(current.confirmed.tactics & (1 << bit)), `reset restores tactic bit ${bit}`);

    await page.locator('[data-page="squad"]').click();
    const target = current.players.slice(1, 12).map(player => player.id);
    for (const player of current.players) {
      const shouldSelect = target.includes(player.id);
      const control = page.locator('[data-select="' + player.id + '"]');
      if (await control.isChecked() !== shouldSelect) await control.setChecked(shouldSelect);
    }
    assert.equal(await page.locator('#selection-count').textContent(), '11 of 11 selected');
    assert.equal(await page.locator('#confirm-button').isEnabled(), true, 'valid lineup enables confirmation');
    await page.locator('#captain-select').selectOption(String(target[10]));
    const desiredTactics = 0xA5;
    for (let bit = 0; bit < 8; bit += 1) {
      await page.locator(`[data-tactic-bit="${bit}"]`).setChecked(Boolean(desiredTactics & (1 << bit)));
    }
    await page.locator('[data-select="' + target[0] + '"]').focus();
    await page.locator('[data-select="' + target[0] + '"]').press('Space');
    assert.equal(await page.locator('#confirm-button').isDisabled(), true, 'invalid count disables confirmation');
    assert.match(await page.locator('#management-feedback').innerText(), /Choose 1 more player/);
    assert.equal(await page.locator('[data-select="' + target[0] + '"]').evaluate(el => el === document.activeElement), true, 'keyboard edit retains focus');
    await page.locator('[data-select="' + target[0] + '"]').press('Space');
    await page.locator('#confirm-button').click();
    await page.waitForFunction(() => document.querySelector('#management-feedback')?.textContent.includes('Team confirmed'));
    current = await getSession();
    assert.deepEqual(current.confirmed.starting_eleven, target, 'Python confirms the exact selected eleven');
    assert.equal(current.confirmed.captain, target[10], 'Python confirms the captain');
    assert.equal(current.confirmed.tactics, desiredTactics, 'Python confirms all selected tactic bits');
    assert.equal(await page.locator('#confirmed-eleven').textContent(), target.map(id => current.players.find(player => player.id === id).name).join(', '), 'preview names the confirmed eleven');
    assert.equal(await page.locator('#confirmed-captain').textContent(), current.players.find(player => player.id === target[10]).name, 'preview names the confirmed captain');
    assert.equal(await page.locator('#confirmed-tactics').textContent(), current.tactics_options.map(option => `${desiredTactics & (1 << (option.element - 1)) ? option.set : option.clear} (element ${option.element})`).join(' · '), 'preview displays every tactic element');
    await page.locator('[data-page="dashboard"]').click();
    if (screenshotDir) {
      await mkdir(screenshotDir, { recursive: true });
      await page.screenshot({ path: path.join(screenshotDir, 'management-desktop-dashboard.png'), fullPage: true });
    }

    // Force the normal form submission to receive a server validation error;
    // its visible feedback must explain the rejection without changing state.
    await page.locator('[data-page="squad"]').click();
    let rejectNextConfirm = true;
    await page.route('**/api/management', async route => {
      if (!rejectNextConfirm || route.request().method() !== 'POST') return route.continue();
      rejectNextConfirm = false;
      const body = JSON.parse(route.request().postData());
      body.captain = 999999;
      await route.continue({ postData: JSON.stringify(body) });
    });
    await page.locator('[data-select="' + target[0] + '"]').uncheck();
    await page.locator('[data-select="' + target[0] + '"]').check();
    await page.locator('#confirm-button').click();
    await page.waitForFunction(() => document.querySelector('#management-feedback')?.textContent.includes('Team was not confirmed'));
    assert.match(await page.locator('#management-feedback').innerText(), /captain must be one of the starting eleven/, 'server validation error is visible');
    assert.deepEqual((await getSession()).confirmed, current.confirmed, 'server rejection preserves confirmed state');
    await page.unroute('**/api/management');
    const postsAfterConfirm = managementPosts;
    await page.reload({ waitUntil: 'networkidle' });
    assert.deepEqual((await getSession()).confirmed, current.confirmed, 'Python retains confirmed choices after browser reload');
    assert.equal(await page.locator('#confirmed-captain').textContent(), current.players.find(player => player.id === target[10]).name, 'reload shows the confirmed captain');

    // Cancellation restores the authoritative snapshot and sends no confirmation request.
    await page.locator('[data-page="squad"]').click();
    if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'management-desktop-squad.png'), fullPage: true });
    const cancelId = current.confirmed.starting_eleven[0];
    await page.locator(`[data-select="${cancelId}"]`).uncheck();
    await page.locator('[data-tactic-bit="1"]').setChecked(!(current.confirmed.tactics & 2));
    await page.locator('#cancel-button').click();
    assert.equal(managementPosts, postsAfterConfirm, 'cancel makes no management POST');
    assert.deepEqual((await getSession()).confirmed, current.confirmed, 'cancel leaves Python-confirmed state untouched');
    assert.equal(await page.locator(`[data-select="${cancelId}"]`).isChecked(), true, 'cancel restores the confirmed eleven');

    const invalidPayloads = [
      { ...current.confirmed, country: current.country.id, starting_eleven: current.confirmed.starting_eleven.slice(1) },
      { ...current.confirmed, country: current.country.id, starting_eleven: Array(11).fill(target[0]) },
      { ...current.confirmed, country: current.country.id, starting_eleven: [...target.slice(0, 10), 999999] },
      { ...current.confirmed, country: current.country.id, captain: 999999 },
      { ...current.confirmed, country: current.country.id, tactics: 256 },
    ];
    for (const [index, payload] of invalidPayloads.entries()) {
      const response = await page.evaluate(async body => {
        const result = await fetch('/api/management', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        return { status: result.status, data: await result.json() };
      }, payload);
      assert.equal(response.status, 400, `invalid state ${index} receives visible API rejection`);
      assert.deepEqual((await getSession()).confirmed, current.confirmed, `invalid state ${index} leaves confirmed state unchanged`);
    }
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, '390px management layout has no page overflow');
    if (screenshotDir) await page.screenshot({ path: path.join(screenshotDir, 'management-mobile-squad.png'), fullPage: true });
    assert.deepEqual(pageErrors, [], 'management browser has no page errors');
    await context.close();
    console.log(`PASS management: ${choice.name}, confirmed eleven/captain/all tactic bits, reload, cancel, invalid states, keyboard and mobile layout`);
  } else if (scenario === 'persistence') {
    const initial = await getSession();
    const countries = await getCountries();
    const country = countries.countries.find(item => item.id !== initial.country.id && item.name !== 'Denmark');
    assert(country, 'a non-Denmark management choice exists');
    browser = await chromium.launch({ headless: true });
    let context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    let page = await context.newPage();
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(`${base}/`, { waitUntil: 'networkidle' });
    await page.locator('#club-country').waitFor({ state: 'visible' });
    await page.locator('#country-select').selectOption(String(country.id));
    await page.waitForFunction(expected => document.querySelector('#club-country')?.textContent === expected, country.name);
    let current = await getSession();
    const target = current.players.slice(1, 12).map(player => player.id);
    await page.locator('[data-page="squad"]').click();
    for (const player of current.players) {
      const shouldSelect = target.includes(player.id);
      const control = page.locator(`[data-select="${player.id}"]`);
      if (await control.isChecked() !== shouldSelect) await control.setChecked(shouldSelect);
    }
    await page.locator('#captain-select').selectOption(String(target[10]));
    const tactics = 0xA5;
    for (let bit = 0; bit < 8; bit += 1) await page.locator(`[data-tactic-bit="${bit}"]`).setChecked(Boolean(tactics & (1 << bit)));
    await page.locator('#confirm-button').click();
    await page.waitForFunction(() => document.querySelector('#management-feedback')?.textContent.includes('Team confirmed'));
    current = await getSession();
    assert.deepEqual(current.confirmed.starting_eleven, target);
    assert.equal(current.confirmed.captain, target[10]);
    assert.equal(current.confirmed.tactics, tactics);
    await page.locator('[data-page="dashboard"]').click();
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#match-tag')?.textContent === 'MATCH 1');
    const beforeSave = await getSession();
    await page.locator('#save-session-button').click();
    await page.waitForFunction(() => document.querySelector('#save-feedback')?.textContent.includes('Session saved'));
    const savedBytes = await readFile(savePath);
    assert(savedBytes.includes(Buffer.from('goal2-session')), 'saved bytes use the existing rebuild session format');

    // An invalid candidate must be visible and leave the active live state intact.
    try {
      await writeFile(savePath, Buffer.from('{"format":"goal2-session","version":999}'));
      await page.locator('#load-session-button').click();
      await page.waitForFunction(() => document.querySelector('#save-feedback')?.textContent.includes('Load failed'));
      assert.match(await page.locator('#save-feedback').innerText(), /unsupported session save version/);
      assert.equal((await getSession()).match_count, beforeSave.match_count, 'invalid load keeps current game state');
      assert.equal((await getSession()).country.id, beforeSave.country.id, 'invalid load keeps current country');
    } finally {
      await writeFile(savePath, savedBytes);
    }
    assert.deepEqual(await getSession(), beforeSave, 'invalid load left the complete active state unchanged');

    await context.close();
    await stopServer();
    await startServer(true);
    context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    page = await context.newPage();
    page.on('pageerror', error => pageErrors.push(error.message));
    await page.goto(`${base}/`, { waitUntil: 'networkidle' });
    await page.locator('#club-country').waitFor({ state: 'visible' });
    const resumed = await getSession();
    assert.equal(resumed.country.id, country.id, 'fresh server resumes the saved managed country');
    assert.deepEqual(resumed.confirmed.starting_eleven, target, 'fresh server resumes the complete custom eleven');
    assert.equal(resumed.confirmed.captain, target[10], 'fresh server retains a full captain ID');
    assert.equal(resumed.confirmed.tactics, tactics, 'fresh server retains all tactics bits');
    assert.equal(resumed.match_count, 1, 'resuming does not simulate a match');
    assert.deepEqual(resumed.last_match.score, beforeSave.last_match.score, 'fresh browser shows the retained result');
    assert.deepEqual(resumed.last_match.seeds, beforeSave.last_match.seeds, 'fresh browser shows retained seeds');
    assert.equal(await page.locator('#match-tag').textContent(), 'MATCH 1', 'dashboard displays saved result');
    assert.equal(await page.locator('#match-score').textContent(), `${beforeSave.last_match.score[0]} – ${beforeSave.last_match.score[1]}`);
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#match-tag')?.textContent === 'MATCH 2');
    assert.equal((await getSession()).match_count, 2, 'explicit Play advances the resumed session');
    assert.deepEqual(pageErrors, [], 'persistence browser has no page errors');
    await context.close();
    console.log(`PASS persistence: ${country.name}, save after friendly, invalid-load preservation, fresh-server resume, explicit next friendly`);
  } else if (scenario === 'friendlies') {
    const initial = await getSession();
    const choices = await getCountries();
    const country = choices.countries.find(item => item.id !== initial.country.id && item.name !== 'Denmark');
    assert(country, 'a non-Denmark management choice exists');
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await context.newPage();
    const pageErrors = [];
    let playPosts = 0;
    page.on('pageerror', error => pageErrors.push(error.message));
    page.on('request', request => { if (request.url().endsWith('/api/play')) playPosts += 1; });
    await page.goto(`${base}/`, { waitUntil: 'networkidle' });
    await page.locator('#club-country').waitFor({ state: 'visible' });
    await page.locator('#country-select').selectOption(String(country.id));
    await page.waitForFunction(expected => document.querySelector('#club-country')?.textContent === expected, country.name);
    await page.locator('[data-page="squad"]').click();
    let current = await getSession();
    const target = current.players.slice(2, 13).map(player => player.id);
    for (const player of current.players) {
      const checkbox = page.locator(`[data-select="${player.id}"]`);
      if (await checkbox.isChecked() !== target.includes(player.id)) await checkbox.setChecked(target.includes(player.id));
    }
    await page.locator('#captain-select').selectOption(String(target[4]));
    const tactics = 0x5A;
    for (let bit = 0; bit < 8; bit += 1) await page.locator(`[data-tactic-bit="${bit}"]`).setChecked(Boolean(tactics & (1 << bit)));
    await page.locator('#confirm-button').click();
    await page.waitForFunction(() => document.querySelector('#management-feedback')?.textContent.includes('Team confirmed'));
    current = await getSession();
    assert.deepEqual(current.confirmed.starting_eleven, target, 'custom eleven is confirmed before Play');
    assert.equal(current.confirmed.captain, target[4], 'custom captain is confirmed before Play');
    assert.equal(current.confirmed.tactics, tactics, 'custom tactics are confirmed before Play');
    await page.locator('[data-page="dashboard"]').click();
    assert.equal(await page.locator('#match-score').textContent(), 'VS', 'preview does not simulate a match');
    assert.equal(await page.locator('#play-button').isEnabled(), true, 'explicit Play is available for the resolved matchup');
    const beforeFailure = await getSession();
    await page.route('**/api/play', async route => {
      const payload = JSON.parse(route.request().postData());
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({
        error: 'synthetic browser refusal', play_token: payload.play_token,
      }) });
      await page.unroute('**/api/play');
    });
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#match-feedback')?.textContent.includes('Friendly failed: synthetic browser refusal'));
    assert.equal((await getSession()).match_count, beforeFailure.match_count, 'failed browser request leaves authoritative match count unchanged');
    assert.equal(await page.locator('#play-button').isEnabled(), true, 'visible failure leaves explicit Play usable');
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#match-tag')?.textContent.startsWith('MATCH '));
    let completed = await getSession();
    assert.equal(completed.match_count, 1, 'one explicit click completes one match');
    assert.equal(completed.last_match.match_count, 1);
    assert.equal(completed.last_match.teams[completed.last_match.managed_side].id, country.id, 'result uses selected managed country');
    assert.equal(await page.locator('#home-team').textContent(), completed.last_match.teams[0].name, 'first engine team is shown first');
    assert.equal(await page.locator('#away-team').textContent(), completed.last_match.teams[1].name, 'second engine team is shown second');
    assert.equal(await page.locator('#home-side').textContent(), completed.last_match.managed_side === 0 ? 'MANAGED TEAM · TEAM A' : 'TEAM A', 'managed side is identified in ordered result');
    assert.match(await page.locator('#match-score').textContent(), /^\d+ – \d+$/, 'full-time ordered score is visible');
    assert.match(await page.locator('#match-status').textContent(), /Half-time/, 'half-time score is visible');
    const eventRows = await page.locator('#goal-events li').allTextContents();
    if (completed.last_match.goals.length) {
      assert.equal(eventRows.length, completed.last_match.goals.length, 'every engine goal event is shown');
      for (const goal of completed.last_match.goals) assert(eventRows.some(row => row.includes(goal.player_name) && row.includes(goal.team_name)), 'goal scorer and team are named');
    } else assert.deepEqual(eventRows, ['No goals'], 'a scoreless match says there were no goals');
    assert((await page.locator('#result-detail').textContent()).includes(completed.last_match.seeds.join(' / ')), 'both retained seeds are visible');
    assert.equal(playPosts, 2, 'failed request and explicit retry are separate browser submissions');
    assert.equal(await page.locator('#play-button').isEnabled(), true, 'Play is re-enabled after the match finishes');
    await page.reload({ waitUntil: 'networkidle' });
    completed = await getSession();
    assert.equal(completed.match_count, 1, 'reload does not simulate another match');
    assert.equal(playPosts, 2, 'reload does not submit a match request');
    assert.equal(await page.locator('#match-tag').textContent(), 'MATCH 1', 'reload displays the retained result');
    await page.locator('#another-button').click();
    assert.equal(await page.locator('#topbar-page').textContent(), 'Squad', 'another friendly returns to team management');
    const retained = await getSession();
    assert.equal(retained.country.id, country.id, 'management remains on the same country');
    assert.deepEqual(retained.confirmed.starting_eleven, target, 'confirmed lineup is carried into repeat management');
    assert.equal(retained.confirmed.captain, target[4]);
    assert.equal(retained.confirmed.tactics, tactics);
    assert.equal(await page.locator(`[data-select="${target[0]}"]`).isEnabled(), true, 'management roster is usable after returning');
    assert.equal(await page.locator('[data-tactic-bit="0"]').isEnabled(), true, 'management tactics are usable after returning');
    for (const player of retained.players) {
      assert.equal(await page.locator(`[data-select="${player.id}"]`).isChecked(), target.includes(player.id), 'management shows the retained eleven');
      assert.equal((await page.locator(`[data-select="${player.id}"]`).locator('xpath=ancestor::tr').locator('.energy-value').textContent()).trim(), String(player.energy), 'management energy reflects retained player records');
    }
    await page.locator('[data-page="dashboard"]').click();
    await page.locator('#play-button').click();
    await page.waitForFunction(() => document.querySelector('#match-tag')?.textContent === 'MATCH 2');
    assert.equal((await getSession()).match_count, 2, 'a second explicit Play advances the retained session');
    assert.equal(playPosts, 3, 'two successful explicit clicks produce two matches');
    assert.deepEqual(pageErrors, [], 'friendly browser has no page errors');
    await context.close();
    console.log(`PASS friendlies: ${country.name}, confirmed custom team/tactics, explicit play, named result, reload, management return and repeat`);
  } else {
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
  }
} finally {
  if (browser) await browser.close();
  if (child && child.exitCode === null) { child.kill('SIGTERM'); await new Promise(resolve => child.once('exit', resolve)); }
  if (saveDirectory) await rm(saveDirectory, { recursive: true, force: true });
}
