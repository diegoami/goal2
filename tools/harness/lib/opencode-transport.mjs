// [designed: T72; confirmed: measurements/T72] Private stdio lease, never managed service discovery.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawn, spawnSync } from 'node:child_process';
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
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (process.platform === 'win32') spawnSync('taskkill', ['/T', '/F', '/PID', String(child.pid)], { stdio: 'ignore' });
    else process.kill(-child.pid, signal);
  } catch { /* owned process already exited */ }
}
export function capture(cmd, args, { env, cwd, timeoutMs = 30000, outFile } = {}) {
  return new Promise((resolve) => {
    const fd = outFile ? fs.openSync(outFile, 'w') : null;
    let child;
    try { child = spawnOwned(cmd, args, { env, cwd, stdio: ['ignore', fd ?? 'pipe', 'pipe'] }); }
    catch (error) { resolve({ code: null, error: error.message, stdout: '', stderr: '' }); return; }
    finally { if (fd !== null) fs.closeSync(fd); }
    const out = []; const err = [];
    child.stdout?.on('data', (b) => out.push(b)); child.stderr.on('data', (b) => err.push(b));
    const timer = setTimeout(() => { killOwned(child); }, Math.max(1, timeoutMs));
    child.on('error', (error) => { clearTimeout(timer); resolve({ code: null, error: error.message, stdout: '', stderr: '' }); });
    child.on('close', (code, signal) => { clearTimeout(timer); resolve({ code: signal ? 128 : code, signal, stdout: outFile ? fs.readFileSync(outFile, 'utf8') : Buffer.concat(out).toString('utf8'), stderr: Buffer.concat(err).toString('utf8') }); });
  });
}
// [designed: T72] Never migrate/open the retained legacy v1 database with a v2 process.
export function privateHome(env, { resumeRoot } = {}) {
  const base = path.resolve(env.HARNESS_OPENCODE_HOME || path.join(env.HOME || os.homedir(), '.local/share/harness-opencode'));
  const runs = path.join(base, 'v2', 'runs'); fs.mkdirSync(runs, { recursive: true });
  const root = resumeRoot ? fs.realpathSync(resumeRoot) : fs.mkdtempSync(path.join(runs, 'run-'));
  const marker = path.join(root, 'protocol-major');
  if (resumeRoot) {
    if (fs.readFileSync(marker, 'utf8').trim() !== '2') throw new OpenCodeInfraError('ownership', 'resume root is not a retained v2 run');
  } else fs.writeFileSync(marker, '2\n', { flag: 'wx' });
  const dirs = { XDG_DATA_HOME: path.join(root, 'data'), XDG_CACHE_HOME: path.join(root, 'cache'), XDG_STATE_HOME: path.join(root, 'state') };
  for (const dir of Object.values(dirs)) fs.mkdirSync(dir, { recursive: true });
  return { root, env: { ...env, ...dirs } };
}
export async function startPrivateServer(cmd, { env, cwd, timeoutMs = 30000, log = () => {} } = {}) {
  const password = randomBytes(32).toString('base64url');
  const child = spawnOwned(cmd, ['serve', '--stdio', '--hostname', '127.0.0.1', '--port', '0'], { env: { ...env, OPENCODE_PASSWORD: password }, cwd, stdio: ['pipe', 'pipe', 'pipe'] });
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
  child.stderr.on('data', (b) => { stderr += String(b).replaceAll(password, '[REDACTED]'); });
  const stop = async () => {
    child.stdin.end();
    await Promise.race([exited, delay(3000)]);
    if (!closed) { killOwned(child, 'SIGTERM'); await Promise.race([exited, delay(1000)]); }
    if (!closed) { killOwned(child); await Promise.race([exited, delay(1000)]); }
    if (!closed) throw new OpenCodeInfraError('shutdown', 'owned server did not exit');
    return { pid: child.pid, exitCode: child.exitCode, signal: child.signalCode, stdout: output.replaceAll(password, '[REDACTED]'), stderr };
  };
  const started = Date.now();
  while (!url && !closed && !startupError && Date.now() - started < timeoutMs) await delay(Math.min(25, timeoutMs));
  if (!url || startupError || !/^http:\/\/127\.0\.0\.1:\d+$/.test(url)) {
    await stop(); throw new OpenCodeInfraError('startup', `private server failed before billing: ${startupError?.message || stderr || 'readiness deadline'}`);
  }
  const request = async (route, { body, timeoutMs: requestMs = 15000 } = {}) => {
    if (closed) throw new OpenCodeInfraError('server-exit', 'owned server exited');
    const response = await fetch(url + route, { method: body === undefined ? 'GET' : 'POST', headers: { Authorization: `Basic ${Buffer.from(`opencode:${password}`).toString('base64')}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(Math.max(1, requestMs)) });
    if (!response.ok) throw new OpenCodeInfraError('api', `${route}: HTTP ${response.status}`);
    return response.json();
  };
  log(`opencode: private server pid ${child.pid}`);
  return { child, url, request, stop, isAlive: () => !closed, clientEnv: { ...env, OPENCODE_PASSWORD: password } };
}
export async function settledCatalogue(server, { timeoutMs = 30000, model, agent, verifyAgent } = {}) {
  const started = Date.now(); let last = 'registry not settled';
  while (Date.now() - started < timeoutMs) {
    const remaining = Math.max(1, timeoutMs - (Date.now() - started));
    try {
      const catalogue = await server.request('/api/model', { timeoutMs: remaining });
      const selected = catalogue.data?.filter((m) => `${m.providerID}/${m.id}` === model.id);
      if (selected?.length !== 1 || selected[0].enabled !== true) throw new Error('selected model missing, disabled or ambiguous');
      if (model.variant && !selected[0].variants.some((v) => v.id === model.variant)) throw new Error('selected effort not advertised');
      if (model.family && String(selected[0].family).toLowerCase() !== String(model.family).toLowerCase()) throw new Error('selected model family mismatch');
      let profile;
      if (agent) {
        const agents = await server.request('/api/agent', { timeoutMs: Math.max(1, timeoutMs - (Date.now() - started)) });
        profile = agents.data?.find((a) => a.id === agent);
        if (!profile) throw new Error('selected agent not loaded');
        verifyAgent(profile);
      }
      return { catalogue, selected: selected[0], profile };
    } catch (error) { last = error.message; }
    await delay(Math.min(100, Math.max(0, timeoutMs - (Date.now() - started))));
  }
  throw new OpenCodeInfraError('preflight', `refused before billing: ${last}`);
}
