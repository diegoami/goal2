// [designed: T24] Exercise the Codex/Claude family boundary and CLI against isolated config.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import * as common from '../tools/harness/lib/common.mjs';
import * as switches from '../tools/harness/lib/switch.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const config = () => ({
  implementer: { default: 'sonnet', defaultsByClient: { codex: 'session' } },
  reviewer: { default: 'luna' }, blocked: [],
  models: { luna: { id: 'openai/gpt-5.6-luna', family: 'openai', variant: 'high' } },
});
const cleanEnv = (extra = {}) => {
  const env = { ...process.env };
  for (const key of ['HARNESS_CLIENT', 'HARNESS_SESSION_FAMILY', 'CODEX_THREAD_ID',
    'CODEX_SESSION_ID', 'ANTHROPIC_BASE_URL', 'HARNESS_GH_EXE', 'HARNESS_OPENCODE_EXE']) delete env[key];
  return { ...env, ...extra };
};
function fixture(run) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-client-test-'));
  try {
    const git = spawnSync('git', ['init', '-q'], { cwd: dir });
    assert.equal(git.status, 0);
    fs.writeFileSync(path.join(dir, 'harness.json'), JSON.stringify(config()));
    return run(dir);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}
const cli = (script, args, cwd, env) => spawnSync(process.execPath,
  [path.join(root, 'tools/harness', script), ...args], { cwd, env: cleanEnv(env), encoding: 'utf8', timeout: 15000 });

test('Codex markers override stale Anthropic settings; installation paths do not identify a session', () => {
  for (const marker of ['CODEX_THREAD_ID', 'CODEX_SESSION_ID']) {
    const env = { [marker]: 'test-session', ANTHROPIC_BASE_URL: 'https://api.z.ai/api/anthropic' };
    assert.equal(common.sessionClient(env), 'codex');
    assert.equal(common.sessionFamily(env), 'openai');
    assert.equal(common.sessionClient({ [marker]: '' }), 'claude');
  }
  assert.equal(common.sessionClient({ CODEX_HOME: '/installed/codex' }), 'claude');
  assert.equal(common.sessionFamily({ CODEX_HOME: '/installed/codex' }), 'claude');
});

test('Explicit client selection and Codex family conflicts fail closed', () => {
  assert.equal(common.sessionClient({ HARNESS_CLIENT: ' CoDeX ' }), 'codex');
  assert.equal(common.sessionFamily({ HARNESS_CLIENT: 'codex' }), 'openai');
  assert.equal(common.sessionFamily({ HARNESS_CLIENT: 'codex', HARNESS_SESSION_FAMILY: 'OpenAI' }), 'openai');
  assert.equal(common.sessionFamily({ HARNESS_CLIENT: 'codex', HARNESS_SESSION_FAMILY: 'glm' }), null);
  assert.equal(common.sessionFamily({ CODEX_THREAD_ID: 'id', HARNESS_SESSION_FAMILY: 'claude' }), null);
  assert.equal(common.sessionClient({ HARNESS_CLIENT: 'unknown' }), null);
  assert.equal(common.sessionFamily({ HARNESS_CLIENT: 'unknown', HARNESS_SESSION_FAMILY: 'openai' }), null);
  assert.equal(common.sessionFamily({ HARNESS_CLIENT: 'claude', CODEX_THREAD_ID: 'stale',
    ANTHROPIC_BASE_URL: 'https://api.z.ai/api/anthropic' }), 'glm');
});

test('Claude family detection and explicit overrides retain legacy behavior', () => {
  const cases = [
    ['', 'claude'], ['https://api.anthropic.com', 'claude'],
    ['https://api.z.ai/api/anthropic', 'glm'], ['https://api.minimax.io/anthropic', 'minimax'],
    ['https://api.moonshot.cn/anthropic', 'kimi'], ['https://api.deepseek.com', 'deepseek'],
    ['https://dashscope.aliyuncs.com', 'qwen'], ['https://api.xiaomimimo.com', 'mimo'],
    ['https://api.anthropic.com.evil.example', null], ['https://unknown.example/anthropic.com', null],
    ['invalid URL', null],
  ];
  for (const [url, expected] of cases) assert.equal(common.sessionFamily({ ANTHROPIC_BASE_URL: url }), expected, url);
  assert.equal(common.sessionFamily({ ANTHROPIC_BASE_URL: 'https://unknown.example', HARNESS_SESSION_FAMILY: 'Kimi' }), 'kimi');
});

test('Codex and Claude defaults can be switched without overwriting each other', () => {
  const original = config();
  assert.equal(switches.implementerDefault(original, 'codex'), 'session');
  assert.equal(switches.implementerDefault(original, 'claude'), 'sonnet');
  const codex = switches.planSwitch(original, { role: 'implementer', id: 'gpt-6.1-sol', client: 'codex', sessionFamily: 'openai' }).config;
  assert.equal(codex.implementer.default, 'sonnet');
  assert.equal(codex.implementer.defaultsByClient.codex, 'gpt-6.1-sol');
  const claude = switches.planSwitch(codex, { role: 'implementer', id: 'opus', client: 'claude', sessionFamily: 'claude' }).config;
  assert.equal(claude.implementer.default, 'opus');
  assert.equal(claude.implementer.defaultsByClient.codex, 'gpt-6.1-sol');
  assert.deepEqual(original, config());
  assert.equal(switches.implementerDefault({ implementer: { default: 'opus' } }, 'codex'), 'session');
});

test('Codex refuses Claude aliases, other model families and blocked OpenAI choices', () => {
  for (const id of ['sonnet', 'opus', 'haiku', 'fable', 'glm-5.3', 'unknown-model', 'openai/gpt-6.1-sol']) {
    assert.throws(() => switches.planSwitch(config(), { role: 'implementer', id, client: 'codex', sessionFamily: 'openai' }), /Refused|--model/);
  }
  for (const id of ['session', 'gpt-6.1-sol']) {
    const c = config(); c.blocked = ['openai'];
    assert.throws(() => switches.planSwitch(c, { role: 'implementer', id, client: 'codex', sessionFamily: 'openai' }), /blocked/);
  }
  assert.throws(() => switches.planSwitch(config(), { role: 'implementer', id: 'session', client: 'codex', sessionFamily: 'glm' }), /Refused/);
});

test('Legacy Claude aliases, provider IDs and blocked checks still work', () => {
  for (const id of ['sonnet', 'opus', 'haiku', 'fable', 'session', 'glm-5.3-flash']) {
    assert.equal(switches.planSwitch(config(), { role: 'implementer', id, sessionFamily: 'glm' }).config.implementer.default, id);
  }
  const c = config(); c.blocked = ['glm'];
  assert.throws(() => switches.planSwitch(c, { role: 'implementer', id: 'sonnet', sessionFamily: 'glm' }), /blocked/);
});

test('CLI show/dry-run/write use the correct client and preserve Claude defaults', () => fixture(dir => {
  const file = path.join(dir, 'harness.json');
  const before = fs.readFileSync(file, 'utf8');
  const show = cli('switch-model.mjs', ['--show'], dir, { HARNESS_CLIENT: 'codex' });
  assert.equal(show.status, 0, show.stderr);
  assert.match(show.stdout, /client codex.*family openai/);
  assert.match(show.stdout, /implementer: the main session/);
  const dry = cli('switch-model.mjs', ['--role', 'implementer', '--model', 'gpt-6.1-sol', '--dry-run'], dir, { CODEX_SESSION_ID: 'test' });
  assert.equal(dry.status, 0, dry.stderr);
  assert.equal(fs.readFileSync(file, 'utf8'), before);
  const write = cli('switch-model.mjs', ['--role', 'implementer', '--model', 'gpt-6.1-sol'], dir, { HARNESS_CLIENT: 'codex' });
  assert.equal(write.status, 0, write.stderr);
  const c = JSON.parse(fs.readFileSync(file, 'utf8'));
  assert.equal(c.implementer.default, 'sonnet');
  assert.equal(c.implementer.defaultsByClient.codex, 'gpt-6.1-sol');
  const legacy = cli('switch-model.mjs', ['--show'], dir, { HARNESS_CLIENT: 'claude' });
  assert.equal(legacy.status, 0, legacy.stderr);
  assert.match(legacy.stdout, /subagent on sonnet/);
  const refused = cli('switch-model.mjs', ['--role', 'implementer', '--model', 'sonnet'], dir, { HARNESS_CLIENT: 'codex' });
  assert.equal(refused.status, 1, refused.stderr);
  assert.deepEqual(JSON.parse(fs.readFileSync(file, 'utf8')), c);
}));

test('Reviewer CLI rejects the Codex/OpenAI family before resolving OpenCode', () => fixture(dir => {
  const gh = path.join(dir, 'fake-gh.mjs');
  fs.writeFileSync(gh, 'if(process.argv.includes("--version")) console.log("gh test");');
  const brief = path.join(dir, 'brief.md');
  fs.writeFileSync(brief, 'T24 review (test)\nNo live model call is permitted.\n');
  for (const env of [{ HARNESS_CLIENT: 'codex' }, { CODEX_THREAD_ID: 'test' }, { CODEX_SESSION_ID: 'test' }]) {
    const run = cli('review.mjs', ['--pr', '1', '--brief', brief, '--reviewer', 'luna'], dir,
      { ...env, HARNESS_GH_EXE: gh, HARNESS_OPENCODE_EXE: '/missing/opencode-forbidden' });
    assert.equal(run.status, 1, run.stderr);
    assert.match(run.stderr, /implementer's model family/);
    assert.doesNotMatch(run.stderr, /OpenCode unavailable/);
  }
}));


test('Codex permits a distinct reviewer family; Claude still refuses its own', () => fixture(dir => {
  const c = config();
  c.models.glm = { id: 'zai-coding-plan/glm-5.3-flash', family: 'glm' };
  c.models.claude = { id: 'anthropic/claude-sonnet-4-5', family: 'claude' };
  fs.writeFileSync(path.join(dir, 'harness.json'), JSON.stringify(c));
  const gh = path.join(dir, 'fake-gh.mjs');
  fs.writeFileSync(gh, 'if(process.argv.includes("--version")) console.log("gh test");');
  const brief = path.join(dir, 'brief.md');
  fs.writeFileSync(brief, 'T24 review (test)\nNo live model call is permitted.\n');
  const env = { HARNESS_GH_EXE: gh, HARNESS_OPENCODE_EXE: '/missing/opencode-forbidden' };
  const codex = cli('review.mjs', ['--pr', '1', '--brief', brief, '--reviewer', 'glm'], dir,
    { ...env, HARNESS_CLIENT: 'codex' });
  assert.equal(codex.status, 3, codex.stderr);
  assert.match(codex.stderr, /OpenCode unavailable/);
  const claude = cli('review.mjs', ['--pr', '1', '--brief', brief, '--reviewer', 'claude'], dir,
    { ...env, HARNESS_CLIENT: 'claude', CODEX_SESSION_ID: 'inherited-marker' });
  assert.equal(claude.status, 1, claude.stderr);
  assert.match(claude.stderr, /implementer's model family/);
}));
