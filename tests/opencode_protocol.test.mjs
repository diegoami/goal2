// [designed: T72a] Protocol fixture and assertion-based mutation controls; never calls a model.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import * as p from '../tools/harness/lib/opencode-protocol.mjs';
const fixture = (name) => JSON.parse(fs.readFileSync(new URL(`fixtures/opencode/${name}`, import.meta.url)));
const evidence = (name) => JSON.parse(fs.readFileSync(new URL(`../measurements/T72a/probe-20261017/${name}`, import.meta.url)));
const actual = evidence('session-export-api.json').data;
const expected = { sessionID: actual.info.id, directory: actual.info.location.directory, agent: 'reviewer', model: actual.info.model };
const copy = (x) => structuredClone(x);
const options = { ...expected, title: 'fixture', prompt: 'Read the brief', provider: 'minimax' };

test('commands explicitly preserve v1 and select v2 syntax', () => {
  assert.deepEqual(p.command(1, 'models', options).args, ['models', 'minimax', '--verbose']);
  assert.deepEqual(p.command(2, 'models', options).args, ['api', '--standalone', 'model.list']);
  assert.deepEqual(p.command(1, 'export', options).args, ['export', expected.sessionID]);
  assert.deepEqual(p.command(2, 'export', options).args, ['session', 'export', '--standalone', expected.sessionID]);
  assert.deepEqual(p.command(1, 'agents', options).args, ['agent', 'list']);
  assert.deepEqual(p.command(2, 'agents', options).args, ['api', '--standalone', 'agent.list']);
  assert.deepEqual(p.command(1, 'list', options).args, ['session', 'list', '--format', 'json']);
  assert.deepEqual(p.command(2, 'list', options).args, ['session', 'list', '--standalone', '--format', 'json']);
  const resumed = p.command(2, 'run', options);
  assert.deepEqual(resumed, { cwd: expected.directory, args: ['run', '--standalone', '--agent', 'reviewer', '--model', 'minimax/MiniMax-M3#thinking', '--session', expected.sessionID, 'Read the brief'] });
  assert.deepEqual(p.command(1, 'run', { ...options, sessionID: null }).args, ['run', '--dir', expected.directory, '--agent', 'reviewer', '--model', 'minimax/MiniMax-M3', '--variant', 'thinking', '--title', 'fixture', 'Read the brief']);
  assert.deepEqual(p.command(2, 'run', { ...options, sessionID: null, model: { ...options.model, variant: undefined } }).args, ['run', '--standalone', '--agent', 'reviewer', '--model', 'minimax/MiniMax-M3', '--title', 'fixture', 'Read the brief']);
  assert.deepEqual(p.command(2, 'interrupt', { ...options, server: 'http://127.0.0.1:4321' }).args, ['api', '--server', 'http://127.0.0.1:4321', 'session.interrupt', '--param', `sessionID=${expected.sessionID}`, '--data', '{}']);
  assert.throws(() => p.command(2, 'interrupt', options), /owned loopback/);
  assert.throws(() => p.command(1, 'interrupt', options), /no supported interrupt/);
  assert.throws(() => p.command(2, 'run', { ...options, directory: 'relative' }), /absolute/);
  assert.throws(() => p.command(2, 'run', { ...options, model: { ...options.model, id: 'bad#variant' } }), /ambiguous/);
});
test('unknown majors never downgrade', () => {
  for (const major of [0, 3, '2', undefined, NaN]) {
    for (const fn of [() => p.command(major, 'run', options), () => p.normalizeSession(major, actual, expected), () => p.normalizeModels(major, {}, {}), () => p.normalizeAgents(major, {}, {}), () => p.normalizePermissions(major, [], ''), () => p.normalizeSessionList(major, [], expected.directory), () => p.normalizeEvents(major, '', expected)]) assert.throws(fn, /unsupported major/);
  }
});
test('observed empty export/list/event identities and zero usage survive', () => {
  const normalized = p.normalizeSession(2, actual, expected);
  assert.equal(normalized.sessionID, expected.sessionID); assert.equal(normalized.completed, false);
  assert.equal(normalized.assistantText, ''); assert.equal(normalized.rejected, false); assert.equal(normalized.cost, 0);
  assert.deepEqual(normalized.tokens, actual.info.tokens); assert.deepEqual(normalized.model, expected.model);
  assert.deepEqual(p.normalizeSessionList(2, evidence('session-list-api.json'), expected.directory), p.normalizeSessionList(2, JSON.parse(evidence('session-list-cli.json').stdout), expected.directory));
  const sse = fs.readFileSync(new URL('../measurements/T72a/probe-20261017/events.sse', import.meta.url), 'utf8');
  const events = p.normalizeEvents(2, sse, expected); assert.equal(events[1].data.sessionID, expected.sessionID);
  assert.throws(() => p.normalizeEvents(2, sse.slice(0, -1), expected), /truncated/);
  assert.throws(() => p.normalizeEvents(2, sse, { ...expected, sessionID: 'ses_other' }), /event session/);
  assert.throws(() => p.normalizeEvents(2, sse, { ...expected, directory: '/other' }), /event directory/);
  assert.throws(() => p.normalizeSessionList(2, evidence('session-list-api.json'), '/other'), /directory mismatch/);
});
test('live model variants and family plus explicit v1 parsed metadata', () => {
  const want = { ...expected.model, directory: expected.directory };
  assert.deepEqual(p.normalizeModels(2, evidence('models.json'), want), { providerID: 'minimax', id: 'MiniMax-M3', modelID: 'MiniMax-M3', family: 'minimax', enabled: true, variants: ['none', 'thinking'] });
  assert.equal(p.normalizeModels(1, { models: [{ id: 'MiniMax-M3', providerID: 'minimax', family: 'minimax', variants: { none: {}, thinking: {} } }] }, want).variants.length, 2);
  for (const change of [{ id: 'missing' }, { providerID: 'other' }, { variant: 'high' }, { directory: '/other' }]) assert.throws(() => p.normalizeModels(2, evidence('models.json'), { ...want, ...change }));
  const bad = evidence('models.json'); bad.data[0].variants = {}; assert.throws(() => p.normalizeModels(2, bad, want), /variants/);
  const duplicate = evidence('models.json'); duplicate.data.push(duplicate.data[0]); assert.throws(() => p.normalizeModels(2, duplicate, want), /ambiguous/);
});
test('effective agent permissions preserve order and expose legacy boundary gap', () => {
  const profile = p.normalizeAgents(2, evidence('agents.json'), expected);
  assert.equal(profile.id, 'reviewer'); assert.equal(profile.mode, 'all'); assert.match(profile.system, /You review one pull request/);
  assert(profile.permissions.some((r) => r.action === 'shell' && r.resource === 'git push *' && r.effect === 'deny'));
  assert(profile.permissions.some((r) => r.action === 'subagent' && r.effect === 'deny'));
  assert(profile.permissions.some((r) => r.action === 'external_directory' && r.resource === '/tmp/*' && r.effect === 'allow'));
  assert.equal(profile.permissions.some((r) => r.action === 'external_directory' && r.resource === '*' && r.effect === 'ask'), false);
  assert.deepEqual(profile.permissions, evidence('agents.json').data.find((a) => a.id === 'reviewer').permissions);
  assert.throws(() => p.normalizeAgents(2, { location: { directory: expected.directory }, data: [] }, expected), /missing/);
  assert.throws(() => p.normalizeAgents(2, evidence('agents.json'), { ...expected, agent: 'build-unknown' }), /missing/);
  assert.throws(() => p.normalizeAgents(2, evidence('agents.json'), { ...expected, directory: '/other' }), /directory mismatch/);
  const v1 = { agents: [{ name: 'reviewer', mode: 'all', prompt: 'Review', permission: { edit: 'deny', bash: { '*': 'allow', 'git push *': 'deny' } } }] };
  assert.deepEqual(p.normalizeAgents(1, v1, expected).permissions, [{ action: 'edit', resource: '*', effect: 'deny' }, { action: 'bash', resource: '*', effect: 'allow' }, { action: 'bash', resource: 'git push *', effect: 'deny' }]);
});
test('full text usage and rejected tool outcomes survive both protocols', () => {
  for (const major of [1, 2]) {
    const normalized = p.normalizeSession(major, fixture(`v${major}-synthetic-export.json`), expected);
    assert.equal(normalized.assistantText, 'Header\napprove\nFinal pass done\napprove\n', 'complete assistant text');
    assert.equal(normalized.rejected, true, 'rejected outcome must survive approval-looking text');
    assert.equal(normalized.completed, true); assert.equal(normalized.cost, 0.002);
    assert.deepEqual(normalized.tokens, { input: 10, output: 4, reasoning: 2, cache: { read: 3, write: 1 } });
    assert.equal(normalized.messages[0].parts[2].name, 'shell'); assert.equal(normalized.messages[0].parts[2].status, 'error');
    assert.match(normalized.messages[0].parts[2].error.message, /rejected permission/);
    assert.equal(normalized.messages[0].parts[3].status, 'completed');
    assert.equal(normalized.messages[0].parts[1].text, 'private reasoning sample');
  }
});
test('wrong session directory agent model and effort fail closed', () => {
  for (const major of [1, 2]) {
    const record = fixture(`v${major}-synthetic-export.json`);
    for (const change of [{ sessionID: 'ses_other' }, { directory: '/other' }, { agent: 'build' }, { model: { ...expected.model, id: 'other' } }, { model: { ...expected.model, providerID: 'other' } }, { model: { ...expected.model, variant: 'none' } }]) {
      assert.throws(() => p.normalizeSession(major, record, { ...expected, ...change }), /mismatch/, `identity ${JSON.stringify(change)}`);
    }
    const bad = copy(record); if (major === 2) bad.messages[0].agent = 'build'; else bad.messages[0].info.agent = 'build';
    assert.throws(() => p.normalizeSession(major, bad, expected), /message agent/);
  }
});
test('malformed truncated incomplete records never become success', () => {
  for (const major of [1, 2]) {
    const base = fixture(`v${major}-synthetic-export.json`);
    for (const mutate of [
      (r) => delete r.messages, (r) => delete r.info.agent,
      (r) => delete (major === 2 ? r.messages[0] : r.messages[0].info).time.completed,
      (r) => (major === 2 ? r.messages[0] : r.messages[0].info).finish = 'length',
      (r) => (major === 2 ? r.messages[0].content : r.messages[0].parts)[2].state.status = 'running',
      (r) => delete (major === 2 ? r.messages[0].content : r.messages[0].parts)[2].state.error,
      (r) => (major === 2 ? r.messages[0] : r.messages[0].info).tokens.output = -1,
    ]) { const bad = copy(base); mutate(bad); assert.throws(() => p.normalizeSession(major, bad, expected)); }
    assert.throws(() => p.normalizeSession(major, null, expected), /object/);
  }
  assert.throws(() => p.normalizeSession(1, fixture('v1-synthetic-export.json').info, expected), /session info/);
  assert.throws(() => p.normalizeSession(2, JSON.parse('{"info":{}}'), expected));
});
test('structured rejection tags and failed outcomes remain explicit', () => {
  for (const type of ['Permission.DeclinedError', 'Permission.BlockedError', 'Permission.CorrectedError']) {
    const record = fixture('v2-synthetic-export.json');
    record.messages[0].content[2].state.error = { type, message: 'No' };
    assert.equal(p.normalizeSession(2, record, expected).rejected, true);
  }
  for (const outcome of ['failed', 'interrupted']) {
    const record = fixture('v2-synthetic-export.json'); record.info.outcome = outcome;
    const normalized = p.normalizeSession(2, record, expected);
    assert.equal(normalized.outcome, outcome); assert.equal(normalized.completed, false);
  }
  const duplicate = fixture('v2-synthetic-export.json'); duplicate.messages.push(copy(duplicate.messages[0]));
  assert.throws(() => p.normalizeSession(2, duplicate, expected), /duplicate/);
});
test('actual v1 step metadata survives and unfinished or errored assistants never complete', () => {
  const projection = fixture('v1-actual-metadata-step-projection.json');
  const record = { info: { id: projection.info.sessionID, agent: 'reviewer', directory: expected.directory, time: { created: projection.info.time.created, updated: projection.info.time.completed } }, messages: [{ info: projection.info, parts: projection.parts }] };
  const want = { ...expected, sessionID: projection.info.sessionID };
  const normalized = p.normalizeSession(1, record, want);
  assert.deepEqual(normalized.messages[0].parts, projection.parts);
  assert.deepEqual(normalized.messages[0].tokens, projection.info.tokens);
  assert.deepEqual(normalized.tokens, projection.info.tokens);
  assert.equal(normalized.completed, false, 'tool-calls is not final completion');
  const wrong = copy(record); wrong.messages[0].parts[0].sessionID = 'ses_other';
  assert.throws(() => p.normalizeSession(1, wrong, want), /part session/);
  for (const major of [1, 2]) {
    for (const finish of ['tool-calls', 'stop']) {
      const value = fixture(`v${major}-synthetic-export.json`);
      const meta = major === 2 ? value.messages[0] : value.messages[0].info;
      meta.finish = finish;
      if (finish === 'stop') meta.error = major === 2 ? { type: 'APIError', message: 'failed' } : { name: 'APIError', data: { message: 'failed' } };
      const result = p.normalizeSession(major, value, expected);
      assert.equal(result.completed, false, 'unfinished or assistant error must not complete');
      assert.match(result.assistantText, /approve/);
      assert.deepEqual(result.messages[0].error, meta.error ?? null);
    }
  }
});
test('permission requests preserve source resource and session ownership', () => {
  const record = fixture('synthetic-permissions.json');
  const normalized = p.normalizePermissions(2, record, expected.sessionID);
  assert.deepEqual(normalized[0], { ...record.data[0] });
  assert.throws(() => p.normalizePermissions(2, record, 'ses_other'), /session mismatch/);
  const v1 = [{ id: 'per_fixture', sessionID: expected.sessionID, permission: 'external_directory', patterns: ['/outside/*'] }];
  assert.equal(p.normalizePermissions(1, v1, expected.sessionID)[0].action, 'external_directory');
  assert.deepEqual(p.normalizePermissions(2, evidence('permissions.json'), expected.sessionID), []);
});
test('real old v2 command failures are behavioral failures', () => {
  const old = evidence('old-commands.json');
  for (const r of [old.oldVariants, old.oldExport]) { assert.notEqual(r.code, 0); assert.match(r.stderr, /Unexpected|Unknown|command|argument/i); assert.doesNotMatch(r.stderr, /MODULE_NOT_FOUND|timed out/); }
  assert.equal(evidence('session-export-cli.json').code, 0);
});

test('mutation controls fail specific identity and rejection assertions', () => {
  const file = new URL('../tools/harness/lib/opencode-protocol.mjs', import.meta.url);
  const original = fs.readFileSync(file, 'utf8');
  const mutations = [
    { name: 'identity-loss', before: "equal(a.providerID, e.providerID, 'provider'); equal(a.id, e.id, 'model'); equal(a.variant, e.variant, 'effort');", after: '', pattern: 'wrong session directory agent model and effort', assertion: /Missing expected exception/ },
    { name: 'rejection-loss', before: 'rejected: assistants.some((m) => m.parts.some((p) => p.type === \'tool\' && p.rejected))', after: 'rejected: false', pattern: 'full text usage and rejected tool outcomes', assertion: /rejected outcome must survive/ },
    { name: 'unfinished-completion', before: "assistants.at(-1).finish === 'stop'", after: 'true', pattern: 'actual v1 step metadata', assertion: /tool-calls is not final completion/ },
    { name: 'assistant-error-loss', before: '!assistants.some((m) => m.error)', after: 'true', pattern: 'actual v1 step metadata', assertion: /unfinished or assistant error must not complete/ },
    { name: 'step-metadata-loss', before: 'return structuredClone(part);', after: 'return { type: part.type };', pattern: 'actual v1 step metadata', assertion: /deep-equal|deeply|strictly deep/ },
    { name: 'text-loss', before: ".filter((p) => p.type === 'text').map((p) => p.text)", after: ".filter((p) => p.type === 'text').slice(-1).map((p) => p.text)", pattern: 'full text usage and rejected tool outcomes', assertion: /complete assistant text/ },
  ];
  const results = [];
  try {
    for (const m of mutations) {
      assert(original.includes(m.before), `mutation ${m.name} must apply`);
      fs.writeFileSync(file, original.replace(m.before, m.after));
      const childEnv = { ...process.env }; delete childEnv.NODE_TEST_CONTEXT;
      const r = spawnSync(process.execPath, ['--test', '--test-name-pattern', m.pattern, 'tests/opencode_protocol.test.mjs'], { encoding: 'utf8', timeout: 20000, env: childEnv });
      assert(!r.error, 'mutation must execute, never count timeout'); assert.equal(r.status, 1);
      assert.match(r.stdout + r.stderr, m.assertion); assert.doesNotMatch(r.stdout + r.stderr, /MODULE_NOT_FOUND|SyntaxError/);
      results.push({ name: m.name, status: r.status, stdout: r.stdout, stderr: r.stderr });
    }
  } finally { fs.writeFileSync(file, original); }
  assert.equal(createHash('sha256').update(fs.readFileSync(file)).digest('hex'), createHash('sha256').update(original).digest('hex'));
  if (process.env.T72A_MUTATION_OUT) fs.writeFileSync(process.env.T72A_MUTATION_OUT, JSON.stringify(results, null, 2) + '\n', { flag: 'wx' });
});
