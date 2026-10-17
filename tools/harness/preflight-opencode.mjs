#!/usr/bin/env node
// [designed: T72] Non-billing production transport preflight; never invokes run/prompt/generate.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { resolveOpenCode } from './lib/opencode.mjs';
import { privateHome, startPrivateServer, settledCatalogue, capture, hash } from './lib/opencode-transport.mjs';
import { reviewerPolicy, trustedReviewEnv, verifyReviewer } from './lib/opencode-policy.mjs';
const outIndex = process.argv.indexOf('--out');
assert(outIndex > 0 && process.argv[outIndex + 1], '--out is required');
const out = path.resolve(process.argv[outIndex + 1]); fs.mkdirSync(out, { recursive: true });
const dest = fs.mkdtempSync(path.join(out, 'preflight-'));
const save = (name, value) => fs.writeFileSync(path.join(dest, name), JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
const cmd = resolveOpenCode(); const policy = reviewerPolicy(path.resolve('.opencode/agents/reviewer.md'));
const home = privateHome({ ...process.env, HARNESS_OPENCODE_HOME: path.join(dest, 'runtime') });
const env = trustedReviewEnv(home.env, policy);
const version = await capture(cmd, ['--version'], { env, cwd: process.cwd() });
assert.equal(version.code, 0); assert.match(version.stdout, /(?:^|v)2\./);
save('identity.json', { version: version.stdout.trim(), binary: cmd.exe, binarySHA256: hash(fs.readFileSync(cmd.exe)), sourceSHA256: hash(fs.readFileSync(new URL(import.meta.url))), policySHA256: policy.sourceSHA256, root: home.root, directory: process.cwd() });
let server;
try {
  server = await startPrivateServer(cmd, { env, cwd: process.cwd() });
  const found = await settledCatalogue(server, { model: { id: 'minimax/MiniMax-M3', variant: 'thinking', family: 'minimax' }, agent: 'reviewer', verifyAgent: (profile) => verifyReviewer(profile, policy, 'reviewer') });
  save('profile.json', { id: found.profile.id, mode: found.profile.mode, system: found.profile.system, permissions: found.profile.permissions });
  save('selected-model.json', { id: found.selected.id, providerID: found.selected.providerID, family: found.selected.family, variants: found.selected.variants.map((v) => v.id), enabled: found.selected.enabled });
  const model = { id: 'MiniMax-M3', providerID: 'minimax', variant: 'thinking' };
  const session = await server.request('/api/session', { body: { title: 'T72-owned-empty-preflight', agent: 'reviewer', model, location: { directory: process.cwd() } } });
  const record = await server.request(`/api/experimental/session/${session.data.id}/export`);
  assert.equal(record.data.info.location.directory, process.cwd()); assert.equal(record.data.info.agent, 'reviewer'); assert.deepEqual(record.data.info.model, model);
  assert.equal(record.data.info.cost, 0); assert.deepEqual(record.data.info.tokens, { input: 0, output: 0, reasoning: 0, cache: { read: 0, write: 0 } }); assert.deepEqual(record.data.messages, []);
  save('empty-export.json', record.data);
  save('session-list.json', await server.request(`/api/session?directory=${encodeURIComponent(process.cwd())}`));
  save('idle-interrupt.json', await server.request(`/api/session/${session.data.id}/interrupt`, { body: {} }));
} finally { if (server) save('shutdown.json', await server.stop()); }
console.log(`Non-billing reviewer preflight passed: ${dest}`);
