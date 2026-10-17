// [designed: T72; confirmed: measurements/T72] Private stdio lease, never managed service discovery.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
import { normalizeModels } from './opencode-protocol.mjs';
import { randomBytes, createHash } from 'node:crypto';
export const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
export const delay = (ms) => new Promise((r) => setTimeout(r, Math.max(0, ms)));
export class OpenCodeInfraError extends Error {
  constructor(reason, message) { super(message); this.name = 'OpenCodeInfraError'; this.reason = reason; }
}
export function spawnOwned(cmd, args, options) {
  return spawn(cmd.exe, [...cmd.prefix, ...args], { ...options, detached: process.platform !== 'win32', windowsHide: true });
}
export function killOwned(child, signal = 'SIGKILL') {
  if (!child?.pid) return;
  try {
    if (process.platform === 'win32') {
      if (child.exitCode === null && child.signalCode === null) spawnSync('taskkill', ['/T', '/F', '/PID', String(child.pid)], { stdio: 'ignore' });
      return;
    }
    process.kill(-child.pid, signal);
  } catch { /* owned process already exited */ }
}
export function capture(cmd, args, { env, cwd, timeoutMs = 30000, outFile } = {}) {
  return new Promise((resolve) => {
    const fd = outFile ? fs.openSync(outFile, 'w') : null;
    let child;
    try { child = spawnOwned(cmd, args, { env, cwd, stdio: ['ignore', fd ?? 'pipe', 'pipe'] }); }
    catch (error) { resolve({ code: null, error: error.message, stdout: '', stderr: '' }); return; }
    finally { if (fd !== null) fs.closeSync(fd); }
    const out = []; const err = []; let done = false; let timedOut = false; let forced;
    child.stdout?.on('data', (b) => out.push(b)); child.stderr.on('data', (b) => err.push(b));
    const finish = (value) => {
      if (done) return; done = true; clearTimeout(timer); clearTimeout(forced);
      resolve({ ...value, timedOut, stdout: outFile ? fs.readFileSync(outFile, 'utf8') : Buffer.concat(out).toString('utf8'), stderr: Buffer.concat(err).toString('utf8') });
    };
    const timer = setTimeout(() => {
      timedOut = true; killOwned(child);
      // [designed: T72; regression] A dead leader's descendant can hold pipes; timeout must still settle.
      forced = setTimeout(() => { child.stdout?.destroy(); child.stderr.destroy(); finish({ code: 128, error: 'command deadline' }); }, 250);
    }, Math.max(1, timeoutMs));
    child.on('error', (error) => finish({ code: null, error: error.message }));
    child.on('close', (code, signal) => { killOwned(child); finish({ code: timedOut || signal ? 128 : code, signal }); });
  });
}
// [designed: T72] Never migrate/open the retained legacy v1 database with a v2 process.
export function privateHome(env, { resumeRoot } = {}) {
  const base = path.resolve(env.HARNESS_OPENCODE_HOME || path.join(env.HOME || os.homedir(), '.local/share/harness-opencode'));
  const runs = path.join(base, 'v2', 'runs'); fs.mkdirSync(runs, { recursive: true });
  let root;
  const marker = (dir) => path.join(dir, 'protocol-major');
  if (resumeRoot) {
    try {
      root = fs.realpathSync(resumeRoot);
      if (!root.startsWith(fs.realpathSync(runs) + path.sep) || fs.readFileSync(marker(root), 'utf8').trim() !== '2') throw new Error('not owned v2 root');
    } catch { throw new OpenCodeInfraError('ownership', 'resume root is not a retained v2 run'); }
  } else {
    root = fs.mkdtempSync(path.join(runs, 'run-')); fs.writeFileSync(marker(root), '2\n', { flag: 'wx' });
  }
  // [confirmed: v2.0.28 Credential/Database primary source; measurements/T72] Native logins and sessions share one DB.
  // [designed: T72] Persist v2-only provider/session storage; execution lease, cache, state and receipts remain per-run.
  const pointer = path.join(root, 'data-home');
  const dataHome = resumeRoot ? fs.existsSync(pointer) ? fs.readFileSync(pointer, 'utf8').trim() : path.join(root, 'data') : path.join(base, 'v2', 'data');
  if (![path.join(base, 'v2', 'data'), path.join(root, 'data')].includes(path.resolve(dataHome))) throw new OpenCodeInfraError('ownership', 'v2 data pointer is outside version-isolated storage');
  if (!resumeRoot) fs.writeFileSync(pointer, dataHome + '\n', { flag: 'wx' });
  const dirs = { XDG_DATA_HOME: dataHome, XDG_CACHE_HOME: path.join(root, 'cache'), XDG_STATE_HOME: path.join(root, 'state') };
  for (const dir of Object.values(dirs)) fs.mkdirSync(dir, { recursive: true });
  return { root, env: { ...env, ...dirs, OPENCODE_DB: path.join(dataHome, 'opencode', 'opencode.db') } };
}
export async function startPrivateServer(cmd, { env, cwd, timeoutMs = 30000, log = () => {} } = {}) {
  const password = randomBytes(32).toString('base64url');
  const child = spawnOwned(cmd, ['serve', '--stdio', '--hostname', '127.0.0.1', '--port', '0'], { env: { ...env, OPENCODE_PASSWORD: password }, cwd, stdio: ['pipe', 'pipe', 'pipe'] });
  child.stdin.on('error', () => {});
  let output = ''; let stderr = ''; let url; let startupError;
  let closed = false;
  const exited = new Promise((resolve) => {
    child.on('error', (e) => { startupError = e; closed = true; resolve(); });
    child.on('close', () => { closed = true; resolve(); });
  });
  child.stdout.on('data', (bytes) => {
    output += bytes;
    const first = output.split(/\r?\n/)[0];
    if (!url && output.includes('\n')) {
      try { url = JSON.parse(first).url; } catch { startupError = new Error('invalid owned server readiness JSON'); }
    }
  });
  child.stderr.on('data', (b) => { stderr += String(b); });
  const boundedExit = async (ms) => {
    let timer;
    try { await Promise.race([exited, new Promise((resolve) => { timer = setTimeout(resolve, ms); })]); }
    finally { clearTimeout(timer); }
  };
  const stop = async () => {
    child.stdin.end();
    await boundedExit(3000);
    // [designed: T72] Signal the owned group once per stage, including descendants after leader exit.
    killOwned(child, 'SIGTERM');
    if (!closed) await boundedExit(1000); else await delay(25);
    killOwned(child);
    if (!closed) await boundedExit(1000);
    if (!closed) {
      child.stdout.destroy(); child.stderr.destroy(); child.stdin.destroy();
      throw new OpenCodeInfraError('shutdown', 'owned server did not settle within shutdown deadline');
    }
    if (url) {
      let reachable = false;
      try { await fetch(url, { signal: AbortSignal.timeout(500) }); reachable = true; } catch {}
      if (reachable) throw new OpenCodeInfraError('shutdown', 'owned endpoint remains available after lease shutdown');
    }
    return { pid: child.pid, exitCode: child.exitCode, signal: child.signalCode, stdout: output.replaceAll(password, '[REDACTED]'), stderr: stderr.replaceAll(password, '[REDACTED]') };
  };
  const started = Date.now();
  while (!url && !closed && !startupError && Date.now() - started < timeoutMs) await delay(Math.min(25, timeoutMs));
  if (!url || startupError || !/^http:\/\/127\.0\.0\.1:\d+$/.test(url)) {
    await stop(); throw new OpenCodeInfraError('startup', `private server failed before billing: ${String(startupError?.message || stderr || 'readiness deadline').replaceAll(password, '[REDACTED]')}`);
  }
  const request = async (route, { body, timeoutMs: requestMs = 15000, outFile } = {}) => {
    if (closed) throw new OpenCodeInfraError('server-exit', 'owned server exited');
    const response = await fetch(url + route, { method: body === undefined ? 'GET' : 'POST', headers: { Authorization: `Basic ${Buffer.from(`opencode:${password}`).toString('base64')}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(Math.max(1, requestMs)) });
    const text = await response.text();
    if (outFile) fs.writeFileSync(outFile, text.replaceAll(password, '[REDACTED]'));
    if (!response.ok) throw new OpenCodeInfraError('api', `${route}: HTTP ${response.status}`);
    try { return JSON.parse(text); } catch { throw new OpenCodeInfraError('api-json', `invalid JSON from owned endpoint ${route}`); }
  };
  log(`opencode: private server pid ${child.pid}`);
  return { child, url, directory: fs.realpathSync(cwd), request, stop, redact: (text) => String(text).replaceAll(password, '[REDACTED]'), isAlive: () => !closed, clientEnv: { ...env, OPENCODE_PASSWORD: password } };
}
export async function settledCatalogue(server, { timeoutMs = 30000, model, agent, verifyAgent } = {}) {
  const started = Date.now(); let last = 'registry not settled';
  while (Date.now() - started < timeoutMs) {
    const remaining = Math.max(1, timeoutMs - (Date.now() - started));
    try {
      const catalogue = await server.request('/api/model', { timeoutMs: remaining });
      normalizeModels(2, catalogue, { directory: server.directory, providerID: model.id.split('/')[0], id: model.id.slice(model.id.indexOf('/') + 1), ...(model.variant ? { variant: model.variant } : {}) });
      const selected = catalogue.data?.filter((m) => `${m.providerID}/${m.id}` === model.id);
      if (selected?.length !== 1 || selected[0].enabled !== true) throw new Error('selected model missing, disabled or ambiguous');
      if (model.variant && !selected[0].variants.some((v) => v.id === model.variant)) throw new Error('selected effort not advertised');
      if (model.family && String(selected[0].family).toLowerCase() !== String(model.family).toLowerCase()) throw new Error('selected model family mismatch');
      let profile;
      if (agent) {
        const agents = await server.request('/api/agent', { timeoutMs: Math.max(1, timeoutMs - (Date.now() - started)) });
        if (agents.location?.directory !== server.directory) throw new Error('agent registry directory mismatch');
        const matches = agents.data?.filter((a) => a.id === agent);
        if (matches?.length !== 1) throw new Error('selected agent missing or ambiguous');
        profile = matches[0];
        if (!profile) throw new Error('selected agent not loaded');
        verifyAgent(profile);
      }
      return { catalogue, selected: selected[0], profile };
    } catch (error) { last = error.message; }
    await delay(Math.min(100, Math.max(0, timeoutMs - (Date.now() - started))));
  }
  throw new OpenCodeInfraError('preflight', `refused before billing: ${last}`);
}
