// [designed: T72] Production transport/permission/workflow regressions; no model calls.
import './opencode_guard.test.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
const { capture, killOwned, delay, startPrivateServer, privateHome, catalogueFamily } = await import(process.env.T72_TRANSPORT_MODULE || '../tools/harness/lib/opencode-transport.mjs');
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
  const fixture = path.join(scratch, 'leader.mjs'); const pidFile = path.join(scratch, 'descendant.pid');
  fs.writeFileSync(fixture, `import {spawn} from 'node:child_process'; import fs from 'node:fs';
const child=spawn(process.execPath,['-e','setInterval(()=>{},1000)'],{stdio:'inherit'});
fs.writeFileSync(${JSON.stringify(pidFile)},String(child.pid)); child.unref();
process.exit(0);
`);
  const sentinel = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { detached: true, stdio: 'ignore' });
  try {
    const start = Date.now(); const result = await capture({ exe: process.execPath, prefix: [] }, [fixture], { timeoutMs: 100 });
    assert(Date.now() - start < 1000, 'descendant-held pipes must settle within the bounded deadline');
    assert.equal(result.timedOut, true); assert.notEqual(result.code, 0);
    const descendant = Number(fs.readFileSync(pidFile, 'utf8'));
    await delay(25);
    const stat = `/proc/${descendant}/stat`;
    assert(!fs.existsSync(stat) || fs.readFileSync(stat, 'utf8').split(' ')[2] === 'Z', 'owned descendant must terminate even after leader exit');
    assert.equal(sentinel.exitCode, null); process.kill(sentinel.pid, 0);
  } finally {
    killOwned(sentinel);
    if (fs.existsSync(pidFile)) try { process.kill(Number(fs.readFileSync(pidFile, 'utf8')), 'SIGKILL'); } catch {}
    await delay(25);
  }
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

const { runOpenCodeWatched } = await import(process.env.T72_TEST_MODULE || '../tools/harness/lib/opencode.mjs');
const stub = fileURLToPath(new URL('./helpers/opencode-stub.mjs', import.meta.url));
const selection = { id: 'minimax/MiniMax-M3', family: 'minimax', variant: 'thinking' };
function workflowOptions(mode = 'complete') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-workflow-'));
  return { args: ['run'], model: selection, agent: 'reviewer', agentFile,
    opencode: { exe: process.execPath, prefix: [stub] }, prompt: 'Synthetic nonbilling brief', workDir: dir, title: 'stub',
    startupTimeoutMs: mode === 'startup' ? 700 : 2500, totalTimeoutMs: 5000, idleTimeoutMs: 350, pollMs: 20,
    env: { ...process.env, HARNESS_OPENCODE_HOME: path.join(dir, 'runtime'), STUB_MODE: mode, STUB_TRACE: path.join(dir, 'trace.jsonl') } };
}
test('production major dispatch recovers complete export, usage and receipt; same owned session resumes', async () => {
  const options = workflowOptions(); const logs = []; options.log = (line) => logs.push(line);
  const result = await runOpenCodeWatched(options);
  assert.equal(result.reviewText, 'Complete recovered final\nFinal pass done\napprove\n');
  assert.doesNotMatch(result.stdout, /Complete recovered final/);
  const noEffort = await runOpenCodeWatched({ ...options, model: { id: selection.id, family: selection.family } });
  assert.equal(noEffort.normalized.model.variant, undefined, 'absent effort stays absent instead of selecting a fallback variant');
  assert.equal(result.normalized.tokens.input, 10); assert.equal(result.normalized.cost, .002);
  assert.equal(result.normalized.messages[0].parts.filter((p) => p.type === 'tool').length, 1);
  assert(fs.existsSync(result.manifest)); assert(fs.existsSync(result.briefFile));
  const receipt = JSON.parse(fs.readFileSync(result.manifest)); assert.equal(receipt.phase, 'complete'); assert.equal(receipt.completed, true);
  assert(receipt.guard?.sourceSHA256, 'native operand guard must be pinned before generation');
  assert.equal(receipt.binarySHA256.length, 64); assert.equal(receipt.policySHA256.length, 64);
  assert(logs.some((line) => line.includes(`session ${result.sessionId} started`)));
  const independent = await runOpenCodeWatched(options);
  assert.notEqual(independent.sessionId, result.sessionId);
  assert.equal(JSON.parse(fs.readFileSync(independent.manifest)).dataHome, receipt.dataHome, 'one native v2 provider DB survives distinct owned executions');
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

import { findReceipt, peekRecord, renderPeek } from '../tools/harness/lib/opencode-peek.mjs';
import { spawnSync } from 'node:child_process';
test('peek reads retained complete receipts and live standalone private exports without legacy DB access', async () => {
  const options = workflowOptions(); const result = await runOpenCodeWatched(options);
  const cmd = options.opencode; const receipt = findReceipt(result.sessionId, options.env);
  assert.equal(receipt.manifest, result.manifest);
  const record = await peekRecord(cmd, receipt, { env: options.env });
  assert.match(renderPeek(record, 2), /Complete recovered final/);
  const live = { ...receipt, record: { ...receipt.record, phase: 'running' } };
  assert.deepEqual(await peekRecord(cmd, live, { env: options.env }), record);
  const cli = spawnSync(process.execPath, [fileURLToPath(new URL('../tools/harness/peek.mjs', import.meta.url)), result.manifest], { env: { ...options.env, HARNESS_OPENCODE_EXE: stub }, encoding: 'utf8' });
  assert.equal(cli.status, 0, cli.stderr); assert.match(cli.stdout, /tool shell \[completed\]/);
  await assert.rejects(() => peekRecord(cmd, { record: { ...receipt.record, sessionID: 'ses_foreign' } }, { env: options.env }), /session mismatch/);
  assert.throws(() => findReceipt('not-a-session', options.env), /valid session/);
  const traces = fs.readFileSync(options.env.STUB_TRACE, 'utf8').trim().split('\n').map(JSON.parse);
  assert(traces.filter((x) => x.dataHome).every((x) => x.dataHome.includes('/v2/data')), 'v2 commands never open legacy data');
});
test('explicit v1 commands retain actual-shaped step records and complete recovered text without deleting receipts', async () => {
  const options = workflowOptions(); const dir = options.workDir;
  options.env.STUB_VERSION = '1.18.34'; options.env.STUB_V1_DIR = dir;
  options.args = ['run', '--dir', dir, '--agent', 'reviewer', '--model', selection.id, '--variant', selection.variant];
  options.logDir = path.join(dir, 'retained');
  const result = await runOpenCodeWatched(options);
  assert.match(result.reviewText, /Final pass done/); assert.doesNotMatch(result.stdout, /Final pass done/);
  assert(result.normalized.messages[0].parts.some((p) => p.type === 'step-start'));
  assert(result.normalized.messages[0].parts.some((p) => p.type === 'step-finish'));
  assert(result.files.some((file) => file.endsWith('.export.json')));
  assert(result.files.every((file) => fs.existsSync(file)));
  const resumed = await runOpenCodeWatched({ ...options, sessionId: result.sessionId }); assert.equal(resumed.sessionId, result.sessionId);
  const bad = workflowOptions('wrong-model'); bad.env.STUB_VERSION = '1.18.34'; bad.env.STUB_V1_DIR = bad.workDir; bad.args = [...options.args]; bad.args[bad.args.indexOf('--dir') + 1] = bad.workDir;
  await assert.rejects(() => runOpenCodeWatched(bad), /model mismatch/);
  const rejected = await runOpenCodeWatched({ ...options, env: { ...options.env, STUB_MODE: 'rejected' } });
  assert.match(rejected.permissionRejected, /complete session export/);
});

test('spawn errors are explicit infrastructure failures before any generation', async () => {
  const cmd = { exe: '/missing/T72-opencode', prefix: [] };
  const result = await capture(cmd, ['--version'], { timeoutMs: 300 });
  assert.equal(result.code, null); assert.match(result.error, /ENOENT/); assert.equal(result.timedOut, false);
  await assert.rejects(() => startPrivateServer(cmd, { env: process.env, cwd: os.tmpdir(), timeoutMs: 300 }), (e) => {
    assert.equal(e.reason, 'startup'); assert.match(e.message, /ENOENT/); return true;
  });
});
test('production workflow identity and rejection deletion controls fail the intended assertions', () => {
  const root = new URL('../tools/harness/lib/', import.meta.url);
  for (const [name, file, before, after, pattern = 'full export identity', failure = 'Missing expected rejection'] of [
    ['session identity', 'opencode-protocol.mjs', "equal(sessionID, string(expected.sessionID, 'expected session id'), 'session');", ''],
    ['rejection', 'opencode-workflow.mjs', 'if (normalized.rejected) throw', 'if (false) throw'],
    ['owned descendants', 'opencode-transport.mjs', 'if (!child?.pid) return;', 'if (!child?.pid || child.exitCode !== null || child.signalCode !== null) return;', 'capture deadline', 'owned descendant must terminate'],
    ['old run command', 'opencode-workflow.mjs', "args.splice(1, 1, '--server', server.url);", '', 'production major dispatch', 'exit 2'],
    ['own nonce returned text', 'opencode-workflow.mjs', 'raw = JSON.parse(server.redact(JSON.stringify(result.data)));', 'raw = result.data;', 'known owned transport nonce', 'returned records must not expose own nonce'],
    ['complete final recovery', '../review.mjs', 'readReview(run.reviewText, header)', 'readReview(run.stdout, header)', 'review CLI uses', 'No review from'],
  ]) {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-workflow-mutant-'));
    const dir = path.join(scratch, 'lib'); fs.mkdirSync(dir);
    for (const item of fs.readdirSync(root)) if (item.endsWith('.mjs')) fs.copyFileSync(new URL(item, root), path.join(dir, item));
    // [designed: T72] Workflow identity receipts hash this public entrypoint too.
    fs.copyFileSync(new URL('../tools/harness/review.mjs', import.meta.url), path.join(dir, '../review.mjs'));
    fs.cpSync(new URL('../tools/harness/opencode-guard/', import.meta.url), path.join(scratch, 'opencode-guard'), { recursive: true });
    const target = path.join(dir, file); const source = fs.readFileSync(target, 'utf8'); assert(source.includes(before)); fs.writeFileSync(target, source.replace(before, after));
    const testEnv = { ...process.env }; delete testEnv.NODE_TEST_CONTEXT;
    const result = spawnSync(process.execPath, ['--test', '--test-name-pattern=' + pattern, fileURLToPath(new URL('./opencode_workflow.test.mjs', import.meta.url))], { env: { ...testEnv, T72_TRANSPORT_MODULE: pathToFileURL(path.join(dir, 'opencode-transport.mjs')).href, T72_REVIEW_SCRIPT: path.join(scratch, 'review.mjs'), T72_TEST_MODULE: pathToFileURL(path.join(dir, 'opencode.mjs')).href }, encoding: 'utf8', timeout: 20000 });
    assert.equal(result.status, 1, `${name}: ${result.stderr}`);
    assert.match(result.stdout + result.stderr, new RegExp(failure), name);
    assert.doesNotMatch(result.stdout + result.stderr, /MODULE_NOT_FOUND|ERR_MODULE_NOT_FOUND|timed out/, name);
  }
});

test('review CLI uses exact fetched head, trusted profile and complete export while retaining its worktree', () => {
  // [designed: T72] Actual git worktrees stay under the task cache, never /tmp, and are retained.
  const cache = fileURLToPath(new URL('../.cache/workflow-review-tests/', import.meta.url)); fs.mkdirSync(cache, { recursive: true });
  const fixture = fs.mkdtempSync(path.join(cache, 'run-')); const repo = path.join(fixture, 'repo'); fs.mkdirSync(repo);
  const git = (...args) => { const r = spawnSync('git', args, { cwd: repo, encoding: 'utf8' }); assert.equal(r.status, 0, r.stderr); return r.stdout.trim(); };
  git('init', '-q'); git('config', 'user.email', 't72@example.invalid'); git('config', 'user.name', 'T72 nonbilling stub');
  const cfg = { worktreeRoot: path.join(fixture, 'trees'), reviewer: { agent: 'reviewer', startupTimeoutSec: 2, idleTimeoutSec: 2, totalTimeoutSec: 4 }, models: { m3: selection }, blocked: [] };
  fs.writeFileSync(path.join(repo, 'harness.json'), JSON.stringify(cfg)); fs.mkdirSync(path.join(repo, '.opencode/agents'), { recursive: true }); fs.copyFileSync(agentFile, path.join(repo, '.opencode/agents/reviewer.md'));
  git('add', '.'); git('commit', '-qm', 'Synthetic CLI workflow'); const head = git('rev-parse', 'HEAD'); git('update-ref', 'refs/pull/1/head', head); git('remote', 'add', 'origin', repo);
  const gh = path.join(fixture, 'gh.mjs'); fs.writeFileSync(gh, `if(process.argv.includes('--version')) console.log('gh stub'); else if(process.argv.includes('headRefOid')) console.log(process.env.STUB_HEAD); else if(!process.argv.includes('labels')) process.exit(9);`);
  const brief = path.join(fixture, 'brief.md'); fs.writeFileSync(brief, 'T72 stub review (M3)\nSynthetic read-only review.\n');
  const env = { ...process.env, HARNESS_CLIENT: 'codex', HARNESS_GH_EXE: gh, HARNESS_OPENCODE_EXE: stub, HARNESS_OPENCODE_HOME: path.join(fixture, 'runtime'), STUB_HEAD: head, STUB_FINAL: 'T72 stub review (M3)\napprove\nDW1: ran stub → pass\nFinal pass done\napprove\n' };
  delete env.HARNESS_SESSION_FAMILY; delete env.STUB_VERSION;
  const result = spawnSync(process.execPath, [process.env.T72_REVIEW_SCRIPT || fileURLToPath(new URL('../tools/harness/review.mjs', import.meta.url)), '--pr', '1', '--brief', brief, '--reviewer', 'm3', '--done-when', '1', '--dry-run'], { cwd: repo, env, encoding: 'utf8', timeout: 12000 });
  assert.equal(result.status, 0, result.stderr + result.stdout);
  assert.match(result.stdout, /dry run: would post the above/); assert.match(result.stdout, /DW1: ran stub/);
  const runManifest = result.stdout.match(/manifest (.+run\.json)/)?.[1]; assert(runManifest);
  assert.equal(JSON.parse(fs.readFileSync(runManifest)).reviewedHead, head);
  assert.equal(JSON.parse(fs.readFileSync(runManifest)).reviewPR, '1');
  assert.doesNotMatch(result.stdout, /no review|volatile output/i);
  const trees = fs.readdirSync(cfg.worktreeRoot); assert.equal(trees.length, 1);
  const tree = path.join(cfg.worktreeRoot, trees[0]); assert(fs.existsSync(tree));
  assert(runManifest.startsWith(path.join(tree, '.cache/harness-reviews') + path.sep), 'safe run/profile/source receipts must be inside the reviewer worktree grants');
  const receipt = JSON.parse(fs.readFileSync(runManifest));
  assert(fs.existsSync(receipt.files['profile.json'])); assert(fs.existsSync(receipt.files['model.json']));
  assert(!receipt.dataHome.startsWith(tree), 'provider DB stays outside reviewer artifact grants');
  assert.equal(spawnSync('git', ['rev-parse', 'HEAD'], { cwd: tree, encoding: 'utf8' }).stdout.trim(), head);
  const stale = path.join(fixture, 'stale.md'); fs.writeFileSync(stale, 'T72 stub review (M3)\nHEAD is '+ 'a'.repeat(40)+'\n');
  const refused = spawnSync(process.execPath, [process.env.T72_REVIEW_SCRIPT || fileURLToPath(new URL('../tools/harness/review.mjs', import.meta.url)), '--pr', '1', '--brief', stale, '--reviewer', 'm3', '--dry-run'], { cwd: repo, env, encoding: 'utf8', timeout: 12000 });
  assert.equal(refused.status, 2, refused.stderr); assert.match(refused.stderr, /brief names/);
  assert.equal(fs.readdirSync(cfg.worktreeRoot).length, 1, 'stale head must not launch another worktree');
});

test('progress advances and active owned-server descendants terminate on cancellation', async () => {
  const options = workflowOptions('progress'); const logs = []; options.log = (line) => logs.push(line);
  await runOpenCodeWatched(options); assert(logs.some((line) => /session .* progress/.test(line)), 'native updated time drives progress');
  const active = workflowOptions('active'); let receipt;
  const otherHome = privateHome(active.env);
  const unrelated = await startPrivateServer(active.opencode, { env: { ...otherHome.env, OPENCODE_CONFIG_CONTENT: '{}' }, cwd: active.workDir, timeoutMs: 700 });
  const other = await unrelated.request('/api/session', { body: { title: 'unrelated', agent: 'reviewer', model: { providerID: 'minimax', id: 'MiniMax-M3', variant: 'thinking' }, location: { directory: active.workDir } } });
  let worker;
  try {
  await assert.rejects(() => runOpenCodeWatched(active), (error) => { assert.equal(error.reason, 'idle'); receipt = JSON.parse(fs.readFileSync(error.manifest)); return true; });
  assert.equal(receipt.completed, false); assert.equal(receipt.phase, 'failed'); assert.deepEqual(receipt.interrupt, { interrupted: true });
  const trace = fs.readFileSync(active.env.STUB_TRACE, 'utf8').trim().split('\n').map(JSON.parse);
  assert(trace.some((entry) => entry.interrupt === receipt.sessionID), 'only the own selected session is interrupted');
  worker = trace.find((entry) => entry.workerPID)?.workerPID; assert(worker);
  assert.deepEqual((await unrelated.request(`/api/session/${other.data.id}`)).data, other.data, 'unrelated same-v2-DB session and service survive');
  const stat = `/proc/${worker}/stat`;
  assert(!fs.existsSync(stat) || fs.readFileSync(stat, 'utf8').split(' ')[2] === 'Z', 'owned generation descendant must terminate');
  } finally {
    await unrelated.stop();
    if (worker) try { process.kill(worker, 'SIGKILL'); } catch {}
  }
});

test('reviewer frontmatter rejects unknown roots, malformed permission sections and late deny overrides', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-policy-roots-')); const file = path.join(dir, 'reviewer.md');
  const original = fs.readFileSync(agentFile, 'utf8');
  for (const changed of [original.replace('permission:', 'permit:'), original.replace('mode: all', 'mode: all\nwebfetch deny:'), original.replace('mode: all', 'mode: primary'), original.replace('permission:', 'permission:\npermission:'), original.replace('    "gh issue comment *": deny', '    "gh issue comment *": deny\n    "*": allow')]) {
    fs.writeFileSync(file, changed); assert.throws(() => reviewerPolicy(file), /unsupported reviewer frontmatter root|exact ordered permission contract/);
  }
});
test('resume rejects missing/wrong major markers as ownership errors before opening a database', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-ownership-')); const env = { ...process.env, HARNESS_OPENCODE_HOME: dir };
  const missing = path.join(dir, 'missing');
  assert.throws(() => privateHome(env, { resumeRoot: missing }), (e) => e.reason === 'ownership');
  const home = privateHome(env);
  fs.writeFileSync(path.join(home.root, 'data-home'), path.join(dir, 'data'));
  assert.throws(() => privateHome(env, { resumeRoot: home.root }), (e) => e.reason === 'ownership');
  fs.writeFileSync(path.join(home.root, 'protocol-major'), '1\n');
  assert.throws(() => privateHome(env, { resumeRoot: home.root }), (e) => e.reason === 'ownership');
});
test('peek renders schema-shaped streaming/running tool states and refuses malformed missing input', () => {
  const schema = JSON.parse(fs.readFileSync(new URL('../measurements/T72/peek-tool-state-schemas.json', import.meta.url)));
  const stream = schema.schemas['Session.Message.ToolState.Streaming']; assert(stream.required.includes('input')); assert.equal(stream.properties.input.type, 'string');
  const running = schema.schemas['Session.Message.ToolState.Running']; assert(running.required.includes('input')); assert.equal(running.properties.input.type, 'object');
  // [designed: T72] Synthetic values from the pinned live schema; no generation evidence.
  const record = { info: { title: 'synthetic', location: { directory: '/synthetic' } }, messages: [{ type: 'assistant', content: [
    { type: 'tool', id: 'stream', name: 'shell', state: { status: 'streaming', input: '{"command":' }, time: { created: 1 } },
    { type: 'tool', id: 'run', name: 'shell', state: { status: 'running', input: { command: 'pwd' }, metadata: {} }, time: { created: 1 } },
  ] }] };
  assert.match(renderPeek(record, 2), /tool shell \[streaming\]/); assert.match(renderPeek(record, 2), /tool shell \[running\]/);
  delete record.messages[0].content[1].state.input;
  assert.throws(() => renderPeek(record, 2), /malformed native tool state\/input/);
});

test('missing or malformed chosen model agent and effort fail before generation without defaults', async () => {
  for (const [change, message] of [
    [{ agent: undefined }, 'selected agent'],
    [{ agentFile: undefined }, 'explicit trusted agentFile'],
    [{ model: undefined }, 'selected provider/model'],
    [{ model: { id: selection.id } }, 'selected policy family'],
    [{ model: { ...selection, variant: '' } }, 'valid explicit effort'],
    [{ model: { ...selection, variant: 3 } }, 'valid explicit effort'],
    [{ args: ['run', '--model'] }, 'explicit value'],
    [{ args: ['run', '--agent'] }, 'explicit value'],
    [{ args: ['run', '--variant'] }, 'explicit value'],
  ]) {
    const options = { ...workflowOptions(), ...change };
    await assert.rejects(() => runOpenCodeWatched(options), (e) => { assert.equal(e.reason, 'selection'); assert.match(e.message, new RegExp(message)); return true; });
    assert.doesNotMatch(fs.readFileSync(options.env.STUB_TRACE, 'utf8'), /generation|serve/, 'no selected identity means no execution server');
  }
});
test('native series-family metadata maps through policy lineage without accepting another family', async () => {
  for (const [native, policy] of [['glm-flash','glm'], ['gpt-luna','openai'], ['gpt-sol','openai'], ['o','openai'], ['o-pro','openai'], ['kimi-k2','kimi'], ['claude-sonnet','claude'], ['minimax-m3','minimax'], ['mimo-v2.5','mimo'], ['Hy','hunyuan']]) assert.equal(catalogueFamily(native), policy, native);
  const options = workflowOptions(); options.env.STUB_FAMILY = 'minimax-m3';
  const result = await runOpenCodeWatched(options); assert.equal(result.normalized.model.id, 'MiniMax-M3');
  assert.equal(JSON.parse(fs.readFileSync(JSON.parse(fs.readFileSync(result.manifest)).files['model.json'])).family, 'minimax-m3', 'raw advertised family stays in the receipt');
  await assert.rejects(() => runOpenCodeWatched(workflowOptions('family')), /selected model family mismatch/);
});

test('relative explicit executable resolves once to a real absolute file before changing the run cwd', async () => {
  const { resolveOpenCode } = await import('../tools/harness/lib/opencode.mjs');
  const options = workflowOptions();
  const cmd = resolveOpenCode({ ...options.env, HARNESS_OPENCODE_EXE: path.relative(process.cwd(), stub) });
  assert.equal(cmd.prefix[0], fs.realpathSync(stub));
  assert(path.isAbsolute(cmd.exe));
  const result = await runOpenCodeWatched({ ...options, opencode: cmd }); assert.equal(result.exitCode, 0);
});

// [designed: T72 rework1] Only the harness-generated short-lived transport nonce is redacted; no credential store is read.
test('known owned transport nonce is redacted from exports final returned text and hashes after split echoes', async () => {
  for (const mode of ['nonce', 'nonce-nonzero']) {
    const options = workflowOptions(mode);
    options.totalTimeoutMs = 5000;
    let result;
    let failure;
    try { result = await runOpenCodeWatched(options); }
    catch (error) { failure = error; }
    if (mode === 'nonce-nonzero') assert.equal(failure?.reason, 'non-zero-exit');
    else assert(result);
    const receipt = JSON.parse(fs.readFileSync((result ?? failure).manifest));
    assert(receipt.redactions.some(value => value.includes('owned-server transport nonce')));
    const safe = text => !/CONTROLLED_NONCE:[A-Za-z0-9_-]{43}/.test(text);
    if (result) {
      assert(safe(result.stdout) && safe(result.stderr) && safe(result.reviewText) && safe(result.normalized.assistantText), 'returned records must not expose own nonce');
      assert(result.reviewText.includes('CONTROLLED_NONCE:[REDACTED]'));
    }
    const { createHash } = await import('node:crypto');
    for (const file of [...Object.values(receipt.files), receipt.briefFile]) {
      if (!fs.existsSync(file)) continue;
      const text = fs.readFileSync(file, 'utf8');
      assert(safe(text), 'every retained textual artifact must redact the known own nonce');
      if (receipt.artifactSHA256[path.basename(file)]) assert.equal(createHash('sha256').update(text).digest('hex'), receipt.artifactSHA256[path.basename(file)]);
    }
  }
});
