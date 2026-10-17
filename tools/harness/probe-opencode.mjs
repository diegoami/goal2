#!/usr/bin/env node
// [designed: T72a] Non-billing protocol capture. Only owned empty sessions are mutated.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { spawn, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import assert from 'node:assert/strict';
import { resolveOpenCode } from './lib/opencode.mjs';
const sha = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const arg = process.argv.indexOf('--out');
assert(arg > 0 && process.argv[arg + 1], 'usage: probe-opencode.mjs --out <new-output-directory>');
const out = path.resolve(process.argv[arg + 1]);
fs.mkdirSync(out, { recursive: true });
// [designed: T72a] Never overwrite retained evidence or re-use another probe's database.
const run = fs.mkdtempSync(path.join(out, 'run-'));
const artifacts = {};
function save(name, value) {
  const bytes = typeof value === 'string' ? value : JSON.stringify(value, null, 2) + '\n';
  fs.writeFileSync(path.join(run, name), bytes, { flag: 'wx' });
  artifacts[name] = sha(bytes);
}
const cmd = resolveOpenCode();
assert.equal(cmd.prefix.length, 0, 'probe requires an installed native binary');
const env = { ...process.env };
for (const [key, leaf] of Object.entries({ XDG_DATA_HOME: 'data', XDG_CACHE_HOME: 'cache', XDG_STATE_HOME: 'state' })) {
  env[key] = path.join(run, leaf); fs.mkdirSync(env[key]);
}
function cli(args) {
  const r = spawnSync(cmd.exe, args, { env, cwd: process.cwd(), encoding: 'utf8', timeout: 30000, maxBuffer: 8e6 });
  assert(!r.error, `CLI failed to finish: ${r.error?.code}`);
  return { args, code: r.status, stdout: r.stdout, stderr: r.stderr };
}
const version = cli(['--version']);
assert.equal(version.code, 0); assert.match(version.stdout, /(?:v|^)2\./);
save('version.json', version);
for (const args of [['api', '--help'], ['run', '--help'], ['serve', '--help'], ['session', 'export', '--help'], ['session', 'list', '--help']]) {
  const r = cli(args); assert.equal(r.code, 0); save(`help-${args.slice(0, -1).join('-')}.json`, r);
}
const unrelated = http.createServer((req, res) => res.end('unrelated-server-alive'));
unrelated.listen(0, '127.0.0.1'); await once(unrelated, 'listening');
const unrelatedURL = `http://127.0.0.1:${unrelated.address().port}`;
let child; let exited; let url; let password; let logs = ''; let eventAbort; let eventTask;
const lifecycle = { unrelatedBefore: await (await fetch(unrelatedURL)).text() };
try {
  child = spawn(cmd.exe, ['serve', '--hostname', '127.0.0.1', '--port', '0'], { env, cwd: process.cwd(), stdio: ['ignore', 'pipe', 'pipe'] });
  exited = once(child, 'exit');
  const log = (bytes) => {
    logs += bytes.toString();
    url ||= /server listening on (http:\/\/[^\s]+)/.exec(logs)?.[1];
    password ||= /server password (\S+)/.exec(logs)?.[1];
  };
  child.stdout.on('data', log); child.stderr.on('data', log);
  for (let i = 0; i < 300 && (!url || !password); i++) {
    assert.equal(child.exitCode, null, 'owned server exited before startup'); await sleep(100);
  }
  assert(url && password, 'owned server startup must publish URL and password');
  const headers = { Authorization: `Basic ${Buffer.from(`opencode:${password}`).toString('base64')}` };
  const request = async (route, body) => {
    const r = await fetch(url + route, { headers: { ...headers, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, method: body === undefined ? 'GET' : 'POST', ...(body === undefined ? {} : { body: JSON.stringify(body) }), signal: AbortSignal.timeout(15000) });
    assert.equal(r.status, 200, `HTTP status for ${route}`); return r.json();
  };
  const schemaResponse = await fetch(url + '/openapi.json', { headers, signal: AbortSignal.timeout(15000) });
  assert.equal(schemaResponse.status, 200);
  const schemaText = await schemaResponse.text(); const schema = JSON.parse(schemaText);
  // [designed: T72a] Keep the complete catalogue in bounded shards, never one enormous file.
  const entries = Object.entries(schema.components.schemas);
  for (let n = 0; entries.length; n++) {
    const shard = {};
    while (entries.length && JSON.stringify(shard).length < 24000) { const [key, val] = entries.shift(); shard[key] = val; }
    save(`schema-components-${n}.json`, shard);
  }
  for (const [n, entries] of Object.entries(Object.entries(schema.paths).reduce((chunks, entry, i) => {
    (chunks[Math.floor(i / 5)] ||= []).push(entry); return chunks;
  }, {}))) save(`schema-paths-${n}.json`, Object.fromEntries(entries));
  save('schema-root.json', { ...schema, paths: {}, components: { ...schema.components, schemas: {} } });
  const timeline = []; let agents; let models; let selected;
  const started = Date.now();
  for (let i = 0; i < 150 && Date.now() - started < 30000; i++) {
    agents = await request('/api/agent'); models = await request('/api/model');
    selected = models.data.find((m) => m.providerID === 'minimax' && m.id === 'MiniMax-M3' && m.enabled && m.variants.some((v) => v.id === 'thinking'));
    timeline.push({ elapsedMs: Date.now() - started, agents: agents.data.map((a) => a.id), selectedModelReady: Boolean(selected) });
    if (agents.data.some((a) => a.id === 'reviewer') && selected) break;
    await sleep(200);
  }
  save('readiness.json', timeline);
  assert(selected, 'selected live MiniMax M3 thinking variant must settle without generation');
  const reviewer = agents.data.find((a) => a.id === 'reviewer'); assert(reviewer, 'effective reviewer must settle');
  // [designed: T72a] Whitelist agent metadata: request headers/body can contain secrets.
  save('agents.json', { location: agents.location, data: agents.data.map(({ request, ...a }) => ({ ...a, request: { headers: {}, body: {}, settings: {} } })) });
  const projectModel = (m) => ({ id: m.id, modelID: m.modelID, providerID: m.providerID, family: m.family, enabled: m.enabled, variants: m.variants.map((v) => ({ id: v.id })) });
  save('models.json', { location: models.location, data: models.data.filter((m) => m.providerID === 'minimax').map(projectModel), projection: 'request settings and unrelated providers excluded' });
  save('model-source.json', { sha256: sha(JSON.stringify(models)), projection: 'full response hash only; request fields may contain secrets' });
  save('location.json', await request('/api/location'));
  eventAbort = new AbortController(); const events = [];
  const response = await fetch(url + '/api/event', { headers, signal: eventAbort.signal }); assert.equal(response.status, 200);
  eventTask = (async () => { const decoder = new TextDecoder(); let buffer = '';
    for await (const chunk of response.body) {
      buffer += decoder.decode(chunk, { stream: true });
      let end;
      while ((end = buffer.indexOf('\n\n')) >= 0) { events.push(buffer.slice(0, end)); buffer = buffer.slice(end + 2); }
    }
  })().catch((e) => { if (!eventAbort.signal.aborted) throw e; });
  const model = { id: selected.id, providerID: selected.providerID, variant: 'thinking' };
  const created = await request('/api/session', { title: 'T72a-owned-empty-never-prompted', agent: 'reviewer', model, location: { directory: process.cwd() } });
  const sid = created.data.id; save('session-create.json', created);
  save('session-list-api.json', await request(`/api/session?directory=${encodeURIComponent(process.cwd())}`));
  save('session-export-api.json', await request(`/api/experimental/session/${sid}/export`));
  save('messages.json', await request(`/api/session/${sid}/message`));
  save('permissions.json', await request(`/api/session/${sid}/permission`));
  const interrupted = await request(`/api/session/${sid}/interrupt`, {}); save('interrupt.json', interrupted);
  assert.equal(interrupted.interrupted, false, 'owned idle interruption must be a no-op');
  // [designed: T72a] API remains the source of lifecycle evidence; CLI standalone uses the same private data directory.
  const listed = cli(['session', 'list', '--standalone', '--format', 'json']); save('session-list-cli.json', listed); assert.equal(listed.code, 0);
  const exported = cli(['session', 'export', '--standalone', sid]); save('session-export-cli.json', exported); assert.equal(exported.code, 0);
  const exportRecord = JSON.parse(exported.stdout); assert.equal(exportRecord.info.id, sid); assert.deepEqual(exportRecord.messages, []);
  assert.equal(exportRecord.info.cost, 0); assert.deepEqual(exportRecord.info.tokens, { input: 0, output: 0, reasoning: 0, cache: { read: 0, write: 0 } });
  const oldVariants = cli(['models', 'minimax', '--verbose']); const oldExport = cli(['export', sid]);
  save('old-commands.json', { oldVariants, oldExport });
  assert.notEqual(oldVariants.code, 0, 'v1 variant command must demonstrate real v2 failure');
  assert.notEqual(oldExport.code, 0, 'v1 export command must demonstrate real v2 failure');
  for (let i = 0; i < 30 && !events.some((e) => e.includes(sid)); i++) await sleep(100);
  eventAbort.abort(); await eventTask;
  save('events.sse', events.join('\n\n') + '\n\n'); assert(events.some((e) => e.includes(sid)), 'native events must identify owned empty session');
  lifecycle.sessionID = sid; lifecycle.zeroUsage = true;
  lifecycle.externalDirectoryDefaultGap = !reviewer.permissions.some((p) => p.action === 'external_directory' && p.resource === '*' && p.effect === 'ask');
  lifecycle.schemaSHA256 = sha(schemaText);
} finally {
  eventAbort?.abort(); if (eventTask) await eventTask;
  if (child && child.exitCode === null) { child.kill('SIGTERM'); await Promise.race([exited, sleep(5000)]); }
  if (child && child.exitCode === null && child.signalCode === null) { child.kill('SIGKILL'); await exited; }
  lifecycle.ownedExit = child?.exitCode; lifecycle.ownedSignal = child?.signalCode;
  if (url) {
    try { await fetch(url + '/api/info', { signal: AbortSignal.timeout(1500) }); lifecycle.ownedEndpointUnavailable = false; }
    catch { lifecycle.ownedEndpointUnavailable = true; }
  }
  lifecycle.unrelatedAfter = await (await fetch(unrelatedURL)).text(); unrelated.close();
  save('lifecycle.json', lifecycle);
  // [designed: T72a] Retain only redacted startup logs. Never persist the generated password.
  save('serve-redacted.log', logs.replaceAll(password || '\0', '[REDACTED]'));
  save('manifest.json', { evidence: 'observed non-billing OpenCode2 protocol; no prompt/generate/run', binary: cmd.exe, binarySHA256: sha(fs.readFileSync(cmd.exe)), probeSHA256: sha(fs.readFileSync(new URL(import.meta.url))), artifacts });
}
assert(child?.exitCode !== null || child?.signalCode !== null, 'owned process must exit');
assert(lifecycle.ownedEndpointUnavailable, 'owned endpoint must be unavailable after process shutdown');
assert.equal(lifecycle.unrelatedAfter, lifecycle.unrelatedBefore);
assert(lifecycle.zeroUsage, 'probe must finish its owned zero-usage lifecycle');
console.log(`Protocol probe passed; safe artifacts retained in ${run}`);
