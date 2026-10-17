// [designed: T72] Owned v2 execution with durable final recovery; verdict parsing stays in review.mjs.
import fs from 'node:fs';
import path from 'node:path';
import { randomBytes } from 'node:crypto';
import { command, normalizeSession } from './opencode-protocol.mjs';
import { privateHome, startPrivateServer, settledCatalogue, spawnOwned, killOwned, delay, hash, OpenCodeInfraError } from './opencode-transport.mjs';
import { reviewerPolicy, trustedReviewEnv, verifyReviewer } from './opencode-policy.mjs';
const json = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
export function finalReviewText(normalized) {
  const last = normalized.messages.filter((m) => m.type === 'assistant').at(-1);
  return last?.parts.filter((p) => p.type === 'text').map((p) => p.text).join('') ?? '';
}
export async function runV2Workflow({ opencode, model, agent = 'reviewer', agentFile, prompt, workDir, title, sessionId, resumeManifest,
  startupTimeoutMs = 180000, totalTimeoutMs = 3600000, idleTimeoutMs = 600000, pollMs = 10000, logDir, env = process.env, log = () => {} }) {
  workDir = fs.realpathSync(workDir);
  const policy = reviewerPolicy(agentFile); let previous;
  if (sessionId) {
    if (!resumeManifest) throw new OpenCodeInfraError('ownership', 'v2 resume requires its retained run manifest');
    previous = JSON.parse(fs.readFileSync(resumeManifest, 'utf8'));
    if (previous.major !== 2 || previous.sessionID !== sessionId || previous.directory !== workDir || previous.agent !== agent || JSON.stringify(previous.model) !== JSON.stringify(model) || previous.phase === 'running') throw new OpenCodeInfraError('ownership', 'resume manifest identity differs from this run');
  }
  const home = privateHome(env, { resumeRoot: previous?.dataRoot });
  const runEnv = trustedReviewEnv(home.env, policy, agent);
  const runTitle = `${title}-${randomBytes(6).toString('hex')}`;
  if (logDir) fs.mkdirSync(path.resolve(logDir), { recursive: true });
  const artifactRoot = logDir ? fs.mkdtempSync(path.join(path.resolve(logDir), `${runTitle}-`)) : path.join(home.root, 'artifacts', runTitle);
  fs.mkdirSync(artifactRoot, { recursive: true });
  const files = Object.fromEntries(['stdout.txt', 'stderr.txt', 'export-response.json', 'export.json', 'final.txt', 'assistant.txt', 'profile.json', 'model.json', 'server.json', 'brief.md', 'run.json'].map((name) => [name, path.join(artifactRoot, name)]));
  const briefFile = path.join(workDir, `.harness-brief-${runTitle}.md`); fs.writeFileSync(briefFile, prompt); fs.writeFileSync(files['brief.md'], prompt);
  const pointer = `Your complete brief is the file ${path.basename(briefFile)} at the root of this worktree. Read it in full first; never edit, commit or delete it.`;
  const start = Date.now(); let server; let client; let clientClosed = false; let exitCode = null; let spawnError; let normalized; let raw; let failure;
  const manifest = { major: 2, title: runTitle, directory: workDir, agent, model, dataRoot: home.root, dataHome: home.env.XDG_DATA_HOME, policySHA256: policy.sourceSHA256, command: { exe: opencode.exe, prefix: opencode.prefix }, binarySHA256: hash(fs.readFileSync(opencode.binary ?? opencode.exe)), sourceSHA256: hash(fs.readFileSync(new URL(import.meta.url))), sources: Object.fromEntries(['opencode.mjs', 'opencode-workflow.mjs', 'opencode-transport.mjs', 'opencode-policy.mjs', 'opencode-protocol.mjs', '../review.mjs'].map((name) => [name, hash(fs.readFileSync(new URL(name, import.meta.url)))])), phase: 'preflight', started: start, files, briefFile };
  const persist = () => {
    json(files['run.json'], manifest);
    // [designed: T72] Per-run receipt index lets bare-SID peek find its own major/data root, without a shared service.
    const index = path.join(home.root, 'receipts'); fs.mkdirSync(index, { recursive: true });
    json(path.join(index, `${runTitle}.json`), { manifest: files['run.json'], sessionID: manifest.sessionID });
  };
  persist(); log(`opencode: manifest ${files['run.json']}`);
  const left = () => Math.max(1, totalTimeoutMs - (Date.now() - start));
  const expected = () => ({ sessionID: manifest.sessionID, directory: workDir, agent, model: { providerID: model.id.split('/')[0], id: model.id.slice(model.id.indexOf('/') + 1), ...(model.variant ? { variant: model.variant } : {}) } });
  const exportFinal = async () => {
    const result = await server.request(`/api/experimental/session/${manifest.sessionID}/export`, { timeoutMs: 5000, outFile: files['export-response.json'] });
    raw = result.data; json(files['export.json'], raw);
    normalized = normalizeSession(2, raw, expected());
    fs.writeFileSync(files['assistant.txt'], normalized.assistantText);
    fs.writeFileSync(files['final.txt'], finalReviewText(normalized));
    manifest.usage = { cost: normalized.cost, tokens: normalized.tokens }; manifest.completed = normalized.completed; manifest.rejected = normalized.rejected;
  };
  try {
    server = await startPrivateServer(opencode, { env: runEnv, cwd: workDir, timeoutMs: Math.min(startupTimeoutMs, totalTimeoutMs), log });
    const found = await settledCatalogue(server, { timeoutMs: Math.min(startupTimeoutMs - (Date.now() - start), left()), model, agent, verifyAgent: (profile) => verifyReviewer(profile, policy, agent) });
    json(files['profile.json'], { id: found.profile.id, mode: found.profile.mode, hidden: found.profile.hidden, system: found.profile.system, permissions: found.profile.permissions });
    json(files['model.json'], { id: found.selected.id, modelID: found.selected.modelID, providerID: found.selected.providerID, family: found.selected.family, variants: found.selected.variants.map((v) => v.id), enabled: found.selected.enabled });
    let info;
    if (sessionId) {
      info = (await server.request(`/api/session/${sessionId}`, { timeoutMs: left() })).data;
      manifest.sessionID = sessionId;
    } else {
      const before = await server.request('/api/session', { timeoutMs: left() });
      const occupied = new Set(before.data.map((s) => s.id));
      info = (await server.request('/api/session', { body: { title: runTitle, agent, model: expected().model, location: { directory: workDir } }, timeoutMs: left() })).data;
      if (!info || occupied.has(info.id) || info.title !== runTitle || info.time?.created < start - 1000) throw new OpenCodeInfraError('ownership', 'new session is not unique to this invocation');
      manifest.sessionID = info.id;
    }
    // [designed: T72] Stored selection is checked only after independently verifying the effective profile.
    normalizeSession(2, { info, messages: [] }, expected());
    if (Date.now() - start >= totalTimeoutMs) throw new OpenCodeInfraError('total-timeout', 'total deadline before generation');
    persist(); log(`opencode: session ${manifest.sessionID} started; manifest ${files['run.json']}`);
    const args = command(2, 'run', { directory: workDir, agent, model: expected().model, sessionID: manifest.sessionID, prompt: pointer }).args;
    args.splice(1, 1, '--server', server.url);
    const out = fs.openSync(files['stdout.txt'], 'w'); const err = fs.openSync(files['stderr.txt'], 'w');
    try { client = spawnOwned(opencode, args, { cwd: workDir, env: server.clientEnv, stdio: ['ignore', out, err] }); }
    finally { fs.closeSync(out); fs.closeSync(err); }
    client.on('error', (e) => { spawnError = e; clientClosed = true; });
    client.on('close', (code, signal) => { exitCode = code ?? (signal ? 128 : 1); clientClosed = true; });
    manifest.phase = 'running'; manifest.clientPID = client.pid; manifest.serverPID = server.child.pid; persist();
    let updated = Math.max(info.time.updated, Date.now());
    while (!clientClosed) {
      await delay(Math.max(1, Math.min(pollMs, idleTimeoutMs > 0 ? Math.max(10, idleTimeoutMs / 5) : pollMs, left())));
      if (Date.now() - start >= totalTimeoutMs) throw new OpenCodeInfraError('total-timeout', 'total deadline; cancelling owned session');
      if (clientClosed) break;
      if (!server.isAlive()) throw new OpenCodeInfraError('server-exit', 'owned execution server exited');
      const state = (await server.request(`/api/session/${manifest.sessionID}`, { timeoutMs: Math.min(5000, left()) })).data;
      normalizeSession(2, { info: state, messages: [] }, expected());
      if (state.time.updated > updated) { updated = state.time.updated; log(`opencode: session ${manifest.sessionID} progress`); }
      if (idleTimeoutMs > 0 && Date.now() - updated >= idleTimeoutMs) throw new OpenCodeInfraError('idle', 'session idle; cancelling owned session');
    }
    if (spawnError) throw new OpenCodeInfraError('spawn', `could not start private client: ${spawnError.message}`);
    await exportFinal();
    if (exitCode !== 0) throw new OpenCodeInfraError('non-zero-exit', `exit ${exitCode}`);
    if (!normalized.completed) throw new OpenCodeInfraError('incomplete', 'export has no complete final assistant outcome');
    if (normalized.rejected) throw new OpenCodeInfraError('permission-rejected', 'permission rejected in complete session export');
    manifest.phase = 'complete';
  } catch (error) {
    failure = Date.now() - start >= totalTimeoutMs ? new OpenCodeInfraError('total-timeout', 'total deadline; cancelling owned session')
      : error instanceof OpenCodeInfraError ? error : new OpenCodeInfraError('protocol', error.message);
    manifest.phase = 'failed'; manifest.failure = { reason: failure.reason, message: failure.message };
    // [designed: T72] Interrupt only this session at this owned endpoint, then recover before closing its lease.
    if (server?.isAlive() && manifest.sessionID) {
      try { manifest.interrupt = await server.request(`/api/session/${manifest.sessionID}/interrupt`, { body: {}, timeoutMs: 2000 }); } catch (e) { manifest.interruptError = e.message; }
      if (!raw) try { await exportFinal(); } catch (e) { manifest.exportError = e.message; }
    }
  } finally {
    if (server) try { json(files['server.json'], await server.stop()); } catch (e) { manifest.shutdownError = e.message; failure ||= e; }
    if (client && !clientClosed) {
      for (let i = 0; i < 20 && !clientClosed; i++) await delay(25);
      if (!clientClosed) { killOwned(client); for (let i = 0; i < 20 && !clientClosed; i++) await delay(25); }
      if (!clientClosed) { failure ||= new OpenCodeInfraError('shutdown', 'owned client did not exit'); manifest.phase = 'failed'; }
    }
    if (client) { killOwned(client); await delay(25); }
    // [designed: T72] Generated transport nonce is excluded even if a child echoes it in split chunks.
    if (server) for (const file of [files['stdout.txt'], files['stderr.txt']]) if (fs.existsSync(file)) fs.writeFileSync(file, server.redact(fs.readFileSync(file, 'utf8')));
    manifest.exitCode = exitCode; manifest.finished = Date.now(); manifest.durationMs = manifest.finished - start;
    manifest.artifactSHA256 = Object.fromEntries(Object.values(files).filter((f) => f !== files['run.json'] && fs.existsSync(f)).map((f) => [path.basename(f), hash(fs.readFileSync(f))]));
    persist();
  }
  if (failure) throw Object.assign(failure, { sessionId: manifest.sessionID, manifest: files['run.json'], files: Object.values(files).filter((f) => fs.existsSync(f)) });
  const stdout = fs.readFileSync(files['stdout.txt'], 'utf8'); const stderr = fs.readFileSync(files['stderr.txt'], 'utf8');
  return { stdout, stderr, output: `${stdout}\n${stderr}`, reviewText: finalReviewText(normalized), exitCode, sessionId: manifest.sessionID, title: runTitle, agentFallback: false, sessionAgent: normalized.agent, permissionRejected: null, permissionHint: null, files: Object.values(files).filter((f) => fs.existsSync(f)), briefFile, manifest: files['run.json'], normalized, seconds: manifest.durationMs / 1000 };
}
