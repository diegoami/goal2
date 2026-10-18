// [designed: T73] Production policy entrypoints; actual-shaped native projections.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { CLAUDE, claudeEnv, selectClaude, reviewPolicy, claudeArgs, verifySettings, verifyRules } from '../tools/harness/lib/claude-policy.mjs';
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
  assert.throws(() => reviewPolicy(file, root), /outside reviewed tree/);
  const args = claudeArgs(policy, '81688ef6-b3dd-42ab-9680-ae1bd6b824a8');
  assert.equal(args[args.indexOf('--setting-sources') + 1], '');
  assert(args.includes('--restricted')); assert(args.includes('--safe-mode'));
  assert(!args.some(x => /skip-permissions|fallback-model|bypassPermissions/.test(x)));
});
test('native effective settings and live rules fail closed on routing and permission drift', () => {
  const reply = { effective: policy.settings, sources: [{ source: 'flagSettings', settings: policy.settings }], applied: { model: CLAUDE.model, effort: 'medium', advisor: null } };
  assert.equal(verifySettings(reply, policy).model, CLAUDE.model);
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
    { name: 'routing', before: "demand(reply && !reply.errors?.length && JSON.stringify(reply.effective) === JSON.stringify(policy.settings), 'effective settings');", after: '', pattern: 'native effective settings', assertion: /Missing expected exception/ },
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
      results.push({ control: c.name, exit: r.status, stdout: r.stdout, stderr: r.stderr });
    }
  } finally { fs.writeFileSync(file, original); }
  if (process.env.T73_CONTROL_OUT) fs.writeFileSync(process.env.T73_CONTROL_OUT, JSON.stringify(results, null, 2) + '\n', { flag: 'wx' });
});
