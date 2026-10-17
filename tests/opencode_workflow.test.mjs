// [designed: T72] Production transport/permission/workflow regressions; no model calls.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { capture, killOwned, delay, startPrivateServer } from '../tools/harness/lib/opencode-transport.mjs';
import { reviewerPolicy, trustedReviewEnv, verifyReviewer } from '../tools/harness/lib/opencode-policy.mjs';
const agentFile = new URL('../.opencode/agents/reviewer.md', import.meta.url);
test('trusted reviewer freezes exact deny rules and legacy external boundary without replacing globals', () => {
  const policy = reviewerPolicy(agentFile);
  assert(policy.profile.permissions.some((r) => r.action === 'external_directory' && r.resource === '*' && r.effect === 'ask'));
  const env = trustedReviewEnv({ OPENCODE_CONFIG_DIR: '/untrusted', OPENCODE_CONFIG: '/untrusted', OPENCODE_CONFIG_CONTENT: 'untrusted', KEEP: 'yes' }, policy);
  assert.equal(env.OPENCODE_CONFIG_DIR, undefined); assert.equal(env.OPENCODE_CONFIG, undefined); assert.equal(env.OPENCODE_DISABLE_PROJECT_CONFIG, '1'); assert.equal(env.KEEP, 'yes');
  const profile = { id: 'reviewer', ...policy.profile };
  verifyReviewer(profile, policy, 'reviewer');
  verifyReviewer({ ...profile, permissions: [...profile.permissions, profile.permissions.at(-1)] }, policy, 'reviewer');
  assert.throws(() => verifyReviewer({ ...profile, permissions: [...profile.permissions, { action: 'edit', resource: '*', effect: 'allow' }] }, policy, 'reviewer'), /effective reviewer/);
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-policy-'));
  const file = path.join(scratch, 'reviewer.md'); const original = fs.readFileSync(agentFile, 'utf8');
  fs.writeFileSync(file, original.replaceAll('\n', '\r\n'));
  assert.deepEqual(reviewerPolicy(file).profile, policy.profile, 'CRLF preserves the effective policy');
  for (const [before, after] of [['    "*": ask\n', ''], ['  edit: deny', '  edit: allow'], ['"git push *": deny', '"git push *": allow'], ['"/tmp/*": allow', '"/home/*": allow']]) {
    fs.writeFileSync(file, original.replace(before, after)); assert.throws(() => reviewerPolicy(file), /reviewer must preserve|exact research/);
  }
});

test('capture deadline kills an exited leaders owned descendants while unrelated process survives', async () => {
  if (process.platform === 'win32') return;
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-pipes-'));
  const fixture = path.join(scratch, 'leader.mjs');
  fs.writeFileSync(fixture, `import {spawn} from 'node:child_process';
spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'inherit'}).unref();
process.exit(0);
`);
  const sentinel = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { detached: true, stdio: 'ignore' });
  try {
    const start = Date.now(); const result = await capture({ exe: process.execPath, prefix: [] }, [fixture], { timeoutMs: 100 });
    assert(Date.now() - start < 1000, 'descendant-held pipes must settle within the bounded deadline');
    assert.equal(result.timedOut, true); assert.notEqual(result.code, 0);
    assert.equal(sentinel.exitCode, null); process.kill(sentinel.pid, 0);
  } finally { killOwned(sentinel); await delay(25); }
});

test('owned lease nonce split across chunks is redacted at return and startup-error boundaries', async () => {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-redaction-'));
  const fixture = path.join(scratch, 'server.mjs');
  fs.writeFileSync(fixture, `const key=process.env.OPENCODE_PASSWORD;
if(!process.env.NO_READY) console.log(JSON.stringify({url:'http://127.0.0.1:4321'}));
process.stderr.write('NONCE='+key.slice(0,20));
if(!process.env.NO_READY) process.stdout.write(key.slice(0,20));
setTimeout(()=>{process.stderr.write(key.slice(20));if(!process.env.NO_READY)process.stdout.write(key.slice(20));},70);
process.stdin.resume();process.stdin.on('end',()=>setTimeout(()=>process.exit(0),100));
`);
  const cmd = { exe: process.execPath, prefix: [fixture] };
  const server = await startPrivateServer(cmd, { env: process.env, cwd: scratch, timeoutMs: 500 });
  const nonce = server.clientEnv.OPENCODE_PASSWORD; await delay(100);
  const stopped = await server.stop();
  assert.equal(stopped.stdout.includes(nonce), false, 'stdout must not expose split generated nonce');
  assert.equal(stopped.stderr.includes(nonce), false, 'stderr must not expose split generated nonce');
  assert.equal(stopped.stderr.includes('NONCE=[REDACTED]'), true);
  await assert.rejects(() => startPrivateServer(cmd, { env: { ...process.env, NO_READY: '1' }, cwd: scratch, timeoutMs: 200 }), (error) => {
    assert.equal(error.message.includes('NONCE=[REDACTED]'), true, 'startup error must redact complete generated nonce');
    return true;
  });
});

import { runOpenCodeWatched } from '../tools/harness/lib/opencode.mjs';
const stub = new URL('./helpers/opencode-stub.mjs', import.meta.url).pathname;
const selection = { id: 'minimax/MiniMax-M3', family: 'minimax', variant: 'thinking' };
function workflowOptions(mode = 'complete') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-workflow-'));
  return { args: ['run'], model: selection, agent: 'reviewer', agentFile,
    opencode: { exe: process.execPath, prefix: [stub] }, prompt: 'Synthetic nonbilling brief', workDir: dir, title: 'stub',
    startupTimeoutMs: 700, totalTimeoutMs: 1800, idleTimeoutMs: 350, pollMs: 20,
    env: { ...process.env, HARNESS_OPENCODE_HOME: path.join(dir, 'runtime'), STUB_MODE: mode, STUB_TRACE: path.join(dir, 'trace.jsonl') } };
}
test('production major dispatch recovers complete export, usage and receipt; same owned session resumes', async () => {
  const options = workflowOptions(); const logs = []; options.log = (line) => logs.push(line);
  const result = await runOpenCodeWatched(options);
  assert.equal(result.reviewText, 'Complete recovered final\nFinal pass done\napprove\n');
  assert.doesNotMatch(result.stdout, /Complete recovered final/);
  assert.equal(result.normalized.tokens.input, 10); assert.equal(result.normalized.cost, .002);
  assert.equal(result.normalized.messages[0].parts.filter((p) => p.type === 'tool').length, 1);
  assert(fs.existsSync(result.manifest)); assert(fs.existsSync(result.briefFile));
  const receipt = JSON.parse(fs.readFileSync(result.manifest)); assert.equal(receipt.phase, 'complete'); assert.equal(receipt.completed, true);
  assert.equal(receipt.binarySHA256.length, 64); assert.equal(receipt.policySHA256.length, 64);
  assert(logs.some((line) => line.includes(`session ${result.sessionId} started`)));
  const resumed = await runOpenCodeWatched({ ...options, sessionId: result.sessionId, resumeManifest: result.manifest });
  assert.equal(resumed.sessionId, result.sessionId); assert.notEqual(resumed.manifest, result.manifest);
  assert.equal(JSON.parse(fs.readFileSync(resumed.manifest)).dataRoot, receipt.dataRoot);
  await assert.rejects(() => runOpenCodeWatched({ ...options, sessionId: result.sessionId }), /retained run manifest/);
  await assert.rejects(() => runOpenCodeWatched({ ...options, sessionId: result.sessionId, resumeManifest: result.manifest, model: { ...selection, variant: 'none' } }), /resume manifest identity/);
});
test('discovery fails before generation on chosen family/effort/agent/effective policy mismatch', async () => {
  for (const mode of ['family', 'effort', 'agent', 'policy']) {
    const options = workflowOptions(mode);
    await assert.rejects(() => runOpenCodeWatched(options), (e) => { assert.equal(e.reason, 'preflight', mode); return true; });
    assert.doesNotMatch(fs.readFileSync(options.env.STUB_TRACE, 'utf8'), /generation/, mode);
  }
});
test('full export identity, rejection, completion and JSON guards reject approval-looking outcomes', async () => {
  const cases = { 'wrong-session': 'session mismatch', 'wrong-directory': 'directory mismatch', 'wrong-model': 'model mismatch', 'wrong-agent': 'agent mismatch', 'wrong-effort': 'effort mismatch', malformed: 'malformed assistant text', truncated: 'invalid JSON', partial: 'complete final', pending: 'complete final', rejected: 'permission rejected', nonzero: 'exit 7' };
  for (const [mode, expected] of Object.entries(cases)) {
    await assert.rejects(() => runOpenCodeWatched(workflowOptions(mode)), (e) => {
      assert.match(e.message, new RegExp(expected), mode); assert(fs.existsSync(e.manifest), mode);
      const receipt = JSON.parse(fs.readFileSync(e.manifest)); assert.equal(receipt.phase, 'failed');
      assert(fs.existsSync(receipt.files['export-response.json'])); return true;
    });
  }
});
test('owned startup/idle/total timeouts settle with failure receipt and unrelated service survives', async () => {
  const sentinel = await startPrivateServer({ exe: process.execPath, prefix: [stub] }, { env: { ...process.env, XDG_DATA_HOME: fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-sentinel-')), OPENCODE_CONFIG_CONTENT: '{}' }, cwd: os.tmpdir(), timeoutMs: 700 });
  try {
    for (const [mode, reason] of [['startup','startup'], ['idle','idle'], ['total','total-timeout']]) {
      const options = workflowOptions(mode); if (mode === 'total') { options.totalTimeoutMs = 450; options.idleTimeoutMs = 0; }
      await assert.rejects(() => runOpenCodeWatched(options), (e) => { assert.equal(e.reason, reason, e.message); assert(fs.existsSync(e.manifest)); return true; });
      assert.deepEqual((await sentinel.request('/api/session')).data, []);
    }
  } finally { await sentinel.stop(); }
});
