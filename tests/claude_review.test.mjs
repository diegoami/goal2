// [designed: T73] Production policy entrypoints; actual-shaped native projections.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { CLAUDE, sha, claudeEnv, selectClaude, reviewPolicy, claudeArgs, verifySettings, verifyRules } from '../tools/harness/lib/claude-policy.mjs';
const model = { backend: 'claude', id: CLAUDE.model, variant: 'medium', family: 'claude' };
const root = fs.mkdtempSync(path.join(os.tmpdir(), 't73-policy-'));
const cwd = path.join(root, 'review'); fs.mkdirSync(cwd);
const research = path.join(root, 'goal2-archaeology'); fs.mkdirSync(research);
const file = path.join(root, 'trusted.json');
fs.writeFileSync(file, JSON.stringify({ commands: ['git rev-parse HEAD', 'node --test tests/claude_review.test.mjs', 'python3 -I tools/check_premerge.py --expected-head ' + 'a'.repeat(40)], directories: ['/tmp', research] }));
const policy = reviewPolicy(file, cwd);
test('explicit Claude selection and sanitized environment reject provider substitution', () => {
  assert.equal(selectClaude(model).model, CLAUDE.model);
  for (const change of [{ backend: 'opencode' }, { id: 'MiniMax-M3' }, { id: 'sonnet' }, { family: 'openai' }, { variant: 'high' }]) assert.throws(() => selectClaude({ ...model, ...change }), /selection/);
  const env = claudeEnv({ HOME: root, PATH: '/usr/bin', CLAUDE_CODE_OAUTH_TOKEN: 'synthetic-oauth', ANTHROPIC_AUTH_TOKEN: 'synthetic-other-provider', ANTHROPIC_BASE_URL: 'https://proxy.invalid', ANTHROPIC_MODEL: 'MiniMax-M3', CLAUDE_CODE_USE_VERTEX: '1' }, cwd);
  assert.deepEqual(Object.keys(env).sort(), ['CLAUDE_CODE_OAUTH_TOKEN', 'HOME', 'NO_COLOR', 'PATH', 'TMPDIR']);
  assert.equal(env.CLAUDE_CODE_OAUTH_TOKEN, 'synthetic-oauth');
});
test('trusted policy preserves exact isolated-Python grants, research/tmp and native denies', () => {
  assert(policy.settings.permissions.allow.includes('Bash(python3 -I tools/check_premerge.py --expected-head ' + 'a'.repeat(40) + ')'));
  assert(policy.settings.permissions.deny.includes('Bash(git push *)'));
  const compoundFile = path.join(root, 'compound.json'); fs.writeFileSync(compoundFile, JSON.stringify({ commands: ['node --test tests/claude_review.test.mjs && git diff --check'], directories: ['/tmp', research] }));
  assert.deepEqual(reviewPolicy(compoundFile, cwd).settings.permissions.allow.slice(3), ['Bash(node --test tests/claude_review.test.mjs)', 'Bash(git diff --check)']);
  assert.throws(() => reviewPolicy(file, root), /outside reviewed tree/);
  const wide = path.join(root, 'wide.json'); fs.writeFileSync(wide, JSON.stringify({ commands: ['git rev-parse HEAD'], directories: ['/tmp', research, cwd] }));
  assert.throws(() => reviewPolicy(wide, cwd), /research\/tmp grants/);
  const args = claudeArgs(policy, '81688ef6-b3dd-42ab-9680-ae1bd6b824a8');
  assert.equal(args[args.indexOf('--setting-sources') + 1], '');
  assert(args.includes('--restricted')); assert(args.includes('--safe-mode'));
  assert(!args.some(x => /skip-permissions|fallback-model|bypassPermissions/.test(x)));
});
test('native effective settings and live rules fail closed on routing and permission drift', () => {
  const reply = { effective: policy.settings, sources: [{ source: 'flagSettings', settings: policy.settings }], applied: { model: CLAUDE.model, effort: 'medium', advisor: null } };
  assert.equal(verifySettings(reply, policy).model, CLAUDE.model);
  const reordered = structuredClone(reply); reordered.effective = { permissions: { additionalDirectories: policy.settings.permissions.additionalDirectories, deny: policy.settings.permissions.deny, allow: policy.settings.permissions.allow, defaultMode: 'dontAsk' }, effortLevel: 'medium', model: CLAUDE.model };
  assert.equal(verifySettings(reordered, policy).model, CLAUDE.model, 'native settings key order does not change policy');
  for (const mutate of [r => r.effective.env = { ANTHROPIC_BASE_URL: 'https://proxy.invalid' }, r => r.sources.push({ source: 'userSettings', settings: {} }), r => r.applied.model = 'MiniMax-M3', r => r.errors = [{}]]) { const r = structuredClone(reply); mutate(r); assert.throws(() => verifySettings(r, policy)); }
  const rules = [...policy.settings.permissions.allow.map(rule => ({ behavior: 'allow', source: 'flagSettings', rule })), ...policy.settings.permissions.deny.map(rule => ({ behavior: 'deny', source: 'flagSettings', rule }))];
  assert.equal(verifyRules({ state: { rules } }, policy).length, rules.length);
  assert.throws(() => verifyRules({ state: { rules: [...rules, { behavior: 'allow', source: 'policySettings', rule: 'Bash(*)' }] } }, policy), /widened live permission/);
  assert.throws(() => verifyRules({ state: { rules: rules.slice(1) } }, policy), /missing required live permission/);
});

test('policy guard deletion controls fail intended production assertions', () => {
  const file = new URL('../tools/harness/lib/claude-policy.mjs', import.meta.url);
  const original = fs.readFileSync(file, 'utf8');
  const cases = [
    { name: 'selection', before: "demand(model?.backend === 'claude' && model.id === CLAUDE.model && model.variant === CLAUDE.effort && model.family === 'claude', 'selection');", after: '', pattern: 'explicit Claude selection', assertion: /Missing expected exception/ },
    { name: 'routing', before: "demand(reply && !reply.errors?.length && isDeepStrictEqual(reply.effective, policy.settings), 'effective settings');", after: '', pattern: 'native effective settings', assertion: /Missing expected exception/ },
    { name: 'permission', before: "demand(r.source === 'flagSettings' && expected.delete(r.rule), 'widened live permission');", after: 'expected.delete(r.rule);', pattern: 'native effective settings', assertion: /Missing expected exception/ },
  ];
  const results = [];
  try {
    for (const c of cases) {
      assert(original.includes(c.before), c.name + ' applies');
      fs.writeFileSync(file, original.replace(c.before, c.after));
      const env = { ...process.env }; delete env.NODE_TEST_CONTEXT;
      const r = spawnSync(process.execPath, ['--test', '--test-name-pattern', c.pattern, 'tests/claude_review.test.mjs'], { env, encoding: 'utf8', timeout: 15000 });
      assert(!r.error, c.name + ' executes'); assert.equal(r.status, 1, c.name); assert.match(r.stdout + r.stderr, c.assertion);
      assert.doesNotMatch(r.stdout + r.stderr, /SyntaxError|MODULE_NOT_FOUND/);
      results.push({ control: c.name, baselineSHA256: sha(original), mutantSHA256: sha(fs.readFileSync(file)), exit: r.status, stdout: r.stdout, stderr: r.stderr });
    }
  } finally { fs.writeFileSync(file, original); }
  if (process.env.T73_CONTROL_OUT) fs.writeFileSync(process.env.T73_CONTROL_OUT, JSON.stringify(results, null, 2) + '\n', { flag: 'wx' });
});

import { runClaudeReview } from '../tools/harness/lib/claude-workflow.mjs';
import { parseClaude } from '../tools/harness/lib/claude-protocol.mjs';
import { pinnedScope, preparedClaudeWorktree } from '../tools/harness/lib/claude-scope.mjs';
const stub = path.resolve('tests/helpers/claude-stub.mjs');
function fixtureOptions(mode = 'ok') {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 't73-workflow-')); const cwd = path.join(dir, 'repo'); fs.mkdirSync(cwd);
  const git = args => { const r = spawnSync('git', args, { cwd, encoding: 'utf8' }); assert.equal(r.status, 0, 'fixture git succeeds'); return r.stdout.trim(); };
  git(['init', '-q']); git(['config', 'user.email', 'fixture@example.invalid']); git(['config', 'user.name', 'Fixture']);
  fs.writeFileSync(path.join(cwd, 'source.txt'), 'before\n'); git(['add', 'source.txt']); git(['commit', '-qm', 'base']); const base = git(['rev-parse', 'HEAD']);
  fs.writeFileSync(path.join(cwd, 'source.txt'), 'after\n'); git(['add', 'source.txt']); git(['commit', '-qm', 'head']); const head = git(['rev-parse', 'HEAD']);
  const policyFile = path.join(dir, 'trusted.json'); const research = path.join(dir, 'goal2-archaeology'); fs.mkdirSync(research);
  const commands = ['git rev-parse HEAD', 'git diff --check', 'node --test tests/negative.test.mjs && git diff --check']; const negativeControl = commands.at(-1);
  fs.writeFileSync(policyFile, JSON.stringify({ commands, directories: ['/tmp', research] }));
  const scope = { base, head, pr: 186, header: 'T73 review (Sonnet)', inventory: [{ id: 'F001' }], negativeControl, commands };
  const stubScope = path.join(dir, 'scope.json'); fs.writeFileSync(stubScope, JSON.stringify(scope));
  return { model, policyFile, workDir: cwd, reviewedHead: head, reviewBase: base, reviewPR: scope.pr, header: scope.header, doneWhen: 1, negativeControl, prompt: 'Synthetic trusted review brief', startupTimeoutMs: 800, idleTimeoutMs: 600, totalTimeoutMs: 3000,
    command: { exe: process.execPath, prefix: [stub], simulator: true }, env: { ...process.env, T73_STUB_MODE: mode, T73_STUB_SCOPE: stubScope, T73_STUB_TRACE: path.join(dir, 'trace.jsonl') } };
}
test('production runner recovers full native final, exact scope, usage and sanitized projection', async () => {
  const options = fixtureOptions(); const result = await runClaudeReview(options);
  assert.match(result.reviewText, /COVER F001: audited/); assert.equal(result.modelUsage[CLAUDE.model].provider, 'firstParty');
  const receipt = JSON.parse(fs.readFileSync(result.manifest)); assert.equal(receipt.phase, 'complete'); assert.equal(receipt.owned.stdin, 'DEVNULL');
  const projection = fs.readFileSync(receipt.files.projection, 'utf8'); assert.doesNotMatch(projection, /SYNTHETIC-SECRET/);
  assert.match(projection, /owned pipe lease/); assert(fs.existsSync(path.join(path.dirname(result.manifest), 'scope.json')));
  const frames = fs.readFileSync(receipt.files.stdout, 'utf8'); assert.equal(JSON.parse(frames.trimEnd().split('\n').at(-1)).result, result.reviewText);
  assert.equal(result.init.model, CLAUDE.model);
  const cliBrief = path.join(path.dirname(options.policyFile), 'brief.md'); fs.writeFileSync(cliBrief, 'T73 review (Sonnet)\nNo model call permitted.\n');
  const gh = path.join(path.dirname(options.policyFile), 'gh.mjs'); fs.writeFileSync(gh, "process.stdout.write(process.argv.includes('--version') ? 'fixture' : '')");
  const cli = spawnSync(process.execPath, [path.resolve('tools/harness/review.mjs'), '--pr', '1', '--brief', cliBrief, '--reviewer', 'claude-sonnet'], { env: { ...process.env, HARNESS_CLIENT: 'codex', HARNESS_GH_EXE: gh }, encoding: 'utf8' });
  assert.equal(cli.status, 2); assert.match(cli.stderr, /requires --backend claude/);
});
test('production discovery refuses routing/provider/widening before generation without raw config retention', async () => {
  for (const mode of ['provider', 'routing', 'permissions']) {
    const options = fixtureOptions(mode);
    await assert.rejects(() => runClaudeReview(options), e => { assert(e.manifest); const r = JSON.parse(fs.readFileSync(e.manifest)); assert.equal(r.phase, 'failed'); assert.doesNotMatch(JSON.stringify(r), /SYNTHETIC-SECRET/); assert(!fs.existsSync(r.files.stdout)); return true; });
    assert.doesNotMatch(fs.readFileSync(options.env.T73_STUB_TRACE, 'utf8'), /generation/);
  }
});
test('production exact identity, required denials, final and coverage guards reject approval-looking streams', async () => {
  const cases = { 'read-malformed-error': 'tool result identity', 'read-failed': 'required tool denied', 'malformed-init': 'init toolset', 'duplicate-init': 'missing/duplicate init', 'bad-usage': 'native token/cost accounting', 'wrong-head': 'executed head identity', 'wrong-model': 'init identity', 'wrong-cwd': 'init identity', toolset: 'init toolset', 'wrong-session': 'frame session', 'wrong-pr': 'PR/head/base', denied: 'required tool denied', 'missing-check': 'required command coverage', dw: 'Done-when coverage', scope: 'changed-file scope coverage', control: 'substantive control accounting', 'provider-final': 'final model/provider', 'missing-init': 'missing/duplicate init', 'missing-final': 'missing/duplicate final', 'final-mismatch': 'complete final recovery', malformed: 'malformed native stream', truncated: 'truncated stream', nonzero: 'nonzero review exit' };
  for (const [mode, reason] of Object.entries(cases)) {
    await assert.rejects(() => runClaudeReview(fixtureOptions(mode)), e => { assert.match(e.message, new RegExp(reason), mode); assert.equal(JSON.parse(fs.readFileSync(e.manifest)).phase, 'failed'); return true; });
  }
});
test('production owned startup idle total and cancellation leave unrelated process alive', async () => {
  const unrelated = spawnSync(process.execPath, ['-e', 'process.exit(0)']); assert.equal(unrelated.status, 0);
  const { spawn } = await import('node:child_process'); const sentinel = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'ignore' });
  try {
    for (const [mode, reason] of [['startup', 'startup deadline'], ['idle', 'idle deadline'], ['total', 'total deadline'], ['cancel-descendant', 'cancelled']]) {
      const options = fixtureOptions(mode); options.startupTimeoutMs = 200; options.idleTimeoutMs = 220; options.totalTimeoutMs = 420;
      let timer;
      if (mode === 'cancel-descendant') { const controller = new AbortController(); options.signal = controller.signal; timer = setInterval(() => { if (fs.existsSync(options.env.T73_STUB_TRACE + '.child')) controller.abort(); }, 20); }
      try { await assert.rejects(() => runClaudeReview(options), e => { assert.match(e.message, new RegExp(reason)); assert(e.manifest); return true; }); }
      finally { clearInterval(timer); }
      assert.doesNotThrow(() => process.kill(sentinel.pid, 0), 'unrelated sentinel survives every owned cancellation');
      if (mode === 'cancel-descendant') {
        const pid = Number(fs.readFileSync(options.env.T73_STUB_TRACE + '.child', 'utf8'));
        let live = true; try { live = fs.readFileSync(`/proc/${pid}/stat`, 'utf8').split(' ')[2] !== 'Z'; } catch { live = false; }
        assert.equal(live, false, 'owned descendant no longer runs');
      }
    }
  } finally { sentinel.kill(); await new Promise(r => sentinel.on('close', r)); }
});
test('complete inventory retains rename source and destination and bounded full diff chunks', () => {
  const options = fixtureOptions(); const cwd = options.workDir;
  const g = args => { const r = spawnSync('git', args, { cwd, encoding: 'utf8' }); assert.equal(r.status, 0); return r.stdout.trim(); };
  g(['mv', 'source.txt', 'renamed.txt']); g(['commit', '-qm', 'rename']);
  const head = g(['rev-parse', 'HEAD']); const directory = fs.mkdtempSync(path.join(os.tmpdir(), 't73-scope-'));
  const scope = pinnedScope({ cwd, base: options.reviewedHead, head, pr: 186, directory });
  assert.deepEqual(scope.inventory[0].paths, ['source.txt', 'renamed.txt']); assert.equal(scope.inventory[0].status, 'R100');
  // An unrelated base tip must not silently contribute reverse changes to the inventory.
  const side = g(['commit-tree', g(['rev-parse', head + '^{tree}']), '-p', options.reviewBase, '-m', 'independent base tip']);
  assert.throws(() => pinnedScope({ cwd, base: side, head, pr: 186, directory }), /pinned PR merge base/);
  assert(scope.chunks.every(c => fs.readFileSync(path.join(directory, c.name)).length <= 24000));
});

test('native planned forbidden canaries remain distinct from required-check denials', async () => {
  const options = fixtureOptions(); options.deniedCanaries = ['git push --dry-run'];
  const scope = JSON.parse(fs.readFileSync(options.env.T73_STUB_SCOPE)); scope.deniedCanaries = options.deniedCanaries;
  fs.writeFileSync(options.env.T73_STUB_SCOPE, JSON.stringify(scope));
  const result = await runClaudeReview(options);
  assert.equal(result.denials.length, 1); assert.equal(result.denials[0].tool_input.command, 'git push --dry-run');
});
test('protocol identity rejection and scope deletion controls fail intended assertions', () => {
  const file = new URL('../tools/harness/lib/claude-protocol.mjs', import.meta.url);
  const original = fs.readFileSync(file, 'utf8');
  const cases = [
    { name: 'native-read-optional-error', before: "(c.is_error === undefined || typeof c.is_error === 'boolean')", after: "typeof c.is_error === 'boolean'", pattern: 'native successful Read', assertion: /tool result identity/ },
    { name: 'init-identity', before: "demand(frame.session_id === expected.sessionID && frame.cwd === expected.cwd && frame.model === CLAUDE.model && frame.claude_code_version === CLAUDE.version, 'init identity');", after: '' },
    { name: 'required-rejection', before: "else demand(!outcome.is_error && !outcome.interrupted && !rejection, 'required tool denied/failed');", after: 'else { /* deleted required-check rejection */ }', second: ["demand(denied.every(d => calls.has(d.tool_use_id) && calls.get(d.tool_use_id).name === 'Bash' && planned.has(calls.get(d.tool_use_id).input?.command)), 'unaccounted permission denial');", ''] },
    { name: 'scope-coverage', before: "demand(expected.inventory.length > 0 && expected.inventory.every(item => final.result.split('\\n').some(line => line.startsWith(`COVER ${item.id}: audited `) && line.slice(`COVER ${item.id}: audited `.length).trim())), 'changed-file scope coverage');", after: '' },
  ];
  const results = [];
  try {
    for (const c of cases) {
      assert(original.includes(c.before), c.name + ' applies'); let mutant = original.replace(c.before, c.after);
      if (c.second) { assert(mutant.includes(c.second[0])); mutant = mutant.replace(...c.second); }
      fs.writeFileSync(file, mutant);
      const env = { ...process.env }; delete env.NODE_TEST_CONTEXT;
      const r = spawnSync(process.execPath, ['--test', '--test-name-pattern', c.pattern ?? 'production exact identity', 'tests/claude_review.test.mjs'], { env, encoding: 'utf8', timeout: 20000 });
      assert(!r.error, c.name + ' executes'); assert.equal(r.status, 1, c.name); assert.match(r.stdout + r.stderr, c.assertion ?? /Missing expected rejection/);
      assert.doesNotMatch(r.stdout + r.stderr, /SyntaxError|MODULE_NOT_FOUND/); results.push({ control: c.name, baselineSHA256: sha(original), mutantSHA256: sha(fs.readFileSync(file)), exit: r.status, stdout: r.stdout, stderr: r.stderr });
    }
  } finally { fs.writeFileSync(file, original); }
  if (process.env.T73_PROTOCOL_CONTROL_OUT) fs.writeFileSync(process.env.T73_PROTOCOL_CONTROL_OUT, JSON.stringify(results, null, 2) + '\n', { flag: 'wx' });
});

test('native successful Read omits optional error flag and retains full review', async () => {
  const result = await runClaudeReview(fixtureOptions('read-optional-error'));
  assert(result.calls.some(c => c.name === 'Read'));
  assert.match(result.reviewText, /Final pass done/);
});

test('prepared worktree validates isolation repository exact head and cleanliness before billing', () => {
  const options = fixtureOptions(); const directory = options.workDir; const top = path.dirname(directory);
  const commonDir = path.join(directory, '.git'); const args = { directory, top, workRoot: top, commonDir, head: options.reviewedHead };
  assert.throws(() => preparedClaudeWorktree(args), /prepared review worktree identity/, 'author branch is not a staged detached review');
  const detached = spawnSync('git', ['switch', '--detach', 'HEAD'], { cwd: directory, encoding: 'utf8' }); assert.equal(detached.status, 0);
  assert.equal(preparedClaudeWorktree(args), fs.realpathSync(directory));
  for (const change of [{ top: directory }, { workRoot: directory }, { commonDir: '/other/.git' }, { head: 'f'.repeat(40) }]) assert.throws(() => preparedClaudeWorktree({ ...args, ...change }), /prepared review worktree identity/);
  const file = path.join(directory, 'source.txt'); const original = fs.readFileSync(file);
  try { fs.writeFileSync(file, 'dirty'); assert.throws(() => preparedClaudeWorktree(args), /prepared review worktree identity/); }
  finally { fs.writeFileSync(file, original); }
});
