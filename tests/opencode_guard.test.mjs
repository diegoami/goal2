// [designed: T72 rework1] Static operand boundaries, native hook contracts and source activation; no model access.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
const { operandDirectories, externalEffect, matches } = await import(process.env.T72_GUARD_SCANNER || '../tools/harness/opencode-guard/scanner.mjs');
const { setup, verifyInventory } = await import(process.env.T72_GUARD_PLUGIN || '../tools/harness/opencode-guard/guard.mjs');
const { stageGuard, verifyPlugins, selectGuardPlugins, couldMatchPlugin, inspectConfig, pinGuardBinary, verifyGuardDependencies } = await import(process.env.T72_GUARD_HELPER || '../tools/harness/lib/opencode-guard.mjs');
const { reviewerPolicy, trustedReviewEnv } = await import(process.env.T72_GUARD_POLICY || '../tools/harness/lib/opencode-policy.mjs');
const policy = reviewerPolicy(new URL('../.opencode/agents/reviewer.md', import.meta.url));
const root = path.resolve(fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-guard-')));
const outside = path.resolve(root, '../outside operand');

test('legacy FILES grammar finds quoted nested relative and multi-file operands while preserving ls behavior', async () => {
  for (const command of ['cat', 'rm', 'cp', 'mv', 'mkdir', 'touch', 'chmod', 'chown', 'cd']) {
    const directories = await operandDirectories(`${command} '${outside}/file'`, root, [root]);
    assert(directories.includes(outside), command + ' external operand');
  }
  assert.deepEqual(await operandDirectories(`ls '${outside}'`, root, [root]), []);
  assert.deepEqual(await operandDirectories(`echo $(cat '${outside}/file')`, root, [root]), [outside]);
  assert.deepEqual(await operandDirectories(`cat '../outside operand/file'`, root, [root]), [outside]);
  assert.deepEqual(await operandDirectories(`cat ./inside && cat '${outside}/file'`, root, [root]), [outside]);
  assert.deepEqual(await operandDirectories(`cat '${root}/inside'`, root, [root]), []);
  assert.deepEqual(await operandDirectories(`Get-Content -LiteralPath '${outside}/file'`, root, [root], '/usr/bin/pwsh'), [outside]);
  await assert.rejects(() => operandDirectories("cat 'broken", root, [root]), /unsupported shell grammar/);
});
test('same ordered external policy preserves exact tmp and research roots, rejects neighbors', () => {
  for (const directory of [
    '/tmp', '/tmp/opencode', '/tmp/another', path.join(os.homedir(), 'projects/goal2-archaeology'),
    path.join(os.homedir(), 'projects/goal2-archaeology/sub'),
  ]) assert.equal(externalEffect(directory, policy.profile.permissions), 'allow', directory);
  for (const directory of ['/etc', path.join(os.homedir(), 'projects/goal2-archaeology-other')]) {
    assert.equal(externalEffect(directory, policy.profile.permissions), 'ask', directory);
  }
  assert(matches('plugin:/controlled/source', 'plug*'));
  assert(matches('plugin:/controlled/source', '*:*'));
  assert(matches('cat', 'cat *'), 'native trailing command-prefix grant matches bare command');
});
function context() {
  const options = { id: 'guard.test', source: '/guard/server.js', nativeIDs: ['builtin'], permissions: policy.profile.permissions };
  const hooks = {};
  const ctx = {
    options, location: { directory: root },
    plugin: { list: async () => ({ data: [
      { id: 'builtin', source: { type: 'builtin' }, state: { status: 'active' } },
      { id: options.id, source: { type: 'local', path: options.source }, state: { status: 'active' } },
    ] }) },
  };
  for (const domain of ['tool', 'permission', 'shell']) ctx[domain] = {
    hook: async (name, callback) => {
      hooks[domain + '.' + name] = callback;
      return { dispose: async () => { delete hooks[domain + '.' + name]; } };
    },
  };
  return { ctx, hooks };
}
test('native hooks tighten saved allow, preserve deny/ask and reject missing mismatched scan', async () => {
  const { ctx, hooks } = context();
  const cleanup = await setup(ctx);
  const call = { tool: 'shell', sessionID: 's', id: 'c', agent: 'reviewer', input: { command: 'cat /etc/hostname' } };
  await hooks['tool.execute.before'](call);
  await hooks['shell.create.before']({ command: call.input.command, cwd: root, shell: '/bin/bash' });
  for (const effect of ['allow', 'ask', 'deny']) {
    const event = { action: 'shell', sessionID: 's', agent: 'reviewer', source: { id: 'c' }, resources: [call.input.command], effect };
    await hooks['permission.evaluate'](event);
    assert.equal(event.effect, effect === 'deny' ? 'deny' : 'ask');
  }
  const allowed = { ...call, id: 'allowed', input: { command: 'cat inside' } };
  await hooks['tool.execute.before'](allowed);
  await hooks['shell.create.before']({ command: allowed.input.command, cwd: root, shell: '/bin/sh' });
  const template = { action: 'shell', sessionID: 's', agent: 'reviewer', source: { id: 'allowed' }, resources: ['cat inside'], effect: 'allow' };
  const event = { ...template };
  await hooks['permission.evaluate'](event);
  assert.equal(event.effect, 'allow');
  for (const change of [{ agent: 'other' }, { source: { id: 'missing' } }, { resources: ['cat /etc/file'] }]) {
    const changed = { ...template, ...change };
    await hooks['permission.evaluate'](changed);
    assert.equal(changed.effect, 'ask');
  }
  await hooks['tool.execute.after'](allowed);
  const missing = { ...template };
  await hooks['permission.evaluate'](missing);
  assert.equal(missing.effect, 'ask');
  await cleanup();
});
test('actual shell and cwd select grammar; absent or unsupported native invocation cannot manufacture allow', async () => {
  for (const shell of ['/usr/bin/pwsh', '/custom/unknown-shell', null]) {
    const { ctx, hooks } = context();
    const cleanup = await setup(ctx);
    const command = shell === '/usr/bin/pwsh' ? 'Get-Content -LiteralPath /etc/hostname' : 'cat inside';
    await hooks['tool.execute.before']({ tool: 'shell', sessionID: 's', id: 'c', agent: 'reviewer', input: { command } });
    if (shell) await hooks['shell.create.before']({ command, cwd: root, shell });
    const event = { action: 'shell', sessionID: 's', agent: 'reviewer', source: { id: 'c' }, resources: [command], effect: 'allow' };
    await hooks['permission.evaluate'](event);
    assert.equal(event.effect, 'ask');
    await cleanup();
  }
});
test('trusted activation overlay pins dependencies and rejects foreign failed duplicate or missing plugins', () => {
  const guard = stageGuard(root, policy);
  const env = trustedReviewEnv({}, policy, 'reviewer', guard);
  const content = JSON.parse(env.OPENCODE_CONFIG_CONTENT);
  assert.equal(content.plugins[0], '-*', 'arbitrary global hooks must be disabled on every reload');
  assert(!content.plugins.includes('*'));
  assert(!content.plugins.includes('opencode.*'));
  assert.equal(content.plugins.at(-1).package, guard.directory, 'trusted guard must be activated');
  assert.deepEqual(content.experimental.policies, [
    { action: 'integration.use', resource: 'plugin:*', effect: 'deny' },
    { action: 'integration.use', resource: 'plugin:' + guard.directory, effect: 'allow' },
  ], 'untrusted sources must be denied before import');
  assert.equal(env.OPENCODE_FILEWATCHER_DISABLE, '1');
  assert.equal(env.OPENCODE_DISABLE_FILEWATCHER, '1');
  const rows = guard.nativeIDs.map(id => ({ id, source: { type: 'builtin' }, state: { status: 'active' } }));
  rows.push({ id: guard.id, source: { type: 'local', path: guard.source }, state: { status: 'active' } });
  verifyPlugins(rows, guard);
  verifyInventory(rows, guard);
  for (const invalid of [
    rows.slice(0, -1), [...rows, { id: 'foreign', source: { type: 'package' }, state: { status: 'active' } }],
    rows.map((row, number) => number ? row : { ...row, state: { status: 'failed' } }),
    rows.map((row, number) => number ? row : { ...row, source: { type: 'package' } }),
  ]) assert.throws(() => verifyPlugins(invalid, guard), /plugin|guard|builtin/);
  const baseline = rows.filter(row => row.source.type === 'builtin' && row.id !== 'opencode.warming');
  verifyPlugins(baseline, guard, { baseline: true });
  selectGuardPlugins(guard, baseline.map(row => row.id));
  assert(!guard.plugins.includes('opencode.warming'), 'native disables must not be re-enabled');
});
test('safe native config survey rejects every potentially overlapping allow glob and unverified shells', () => {
  const guard = stageGuard(root, policy);
  const trusted = { type: 'document', info: JSON.parse(trustedReviewEnv({}, policy, 'reviewer', guard).OPENCODE_CONFIG_CONTENT) };
  for (const resource of ['*', 'plugin:*', 'plugin*', 'plug*', '*:*', 'p?ugin:*', 'PLUGIN*']) {
    assert(couldMatchPlugin(resource));
    assert.throws(() => inspectConfig([{ type: 'document', info: { experimental: { policies: [{ action: 'integration.use', resource, effect: 'allow' }] } } }, trusted], guard), /higher-authority plugin allow policy/);
  }
  for (const resource of ['mcp:*', 'skill:*', 'provider:*']) assert.equal(couldMatchPlugin(resource), false);
  assert.throws(() => inspectConfig([{ type: 'document', info: { shell: '/custom/unknown-shell' } }, trusted], guard), /configured shell/);
  assert.equal(inspectConfig([{ type: 'document', info: { shell: '/usr/bin/pwsh', plugins: ['-opencode.warming'] } }, trusted], guard).shell, '/usr/bin/pwsh');
});
test('real wrappers and unpinned binaries fail closed; missing dependency setup never fetches', () => {
  assert.throws(() => pinGuardBinary({ exe: process.execPath, prefix: [] }), /audited OpenCode/);
  assert.throws(() => pinGuardBinary({ exe: process.execPath, prefix: [fileURLToPath(import.meta.url)] }), /wrapped native binaries/);
  assert.throws(() => verifyGuardDependencies(root), /npm ci --prefix tools\/harness\/opencode-guard --ignore-scripts/);
});
test('guard mutation controls fail operand approval activation and source-target assertions', () => {
  for (const [name, file, before, after, pattern, assertion] of [
    ['operand loss', 'opencode-guard/scanner.mjs', 'directories.add(isDirectory ? absolute : path.dirname(absolute));', ';', 'legacy FILES grammar', 'cat external operand'],
    ['approval loss', 'opencode-guard/guard.mjs', "if (!matches || scanned.outcome !== 'allow') {", 'if (false) {', 'native hooks tighten', 'Expected values to be strictly equal'],
    ['activation loss', 'lib/opencode-guard.mjs', 'package: guard.directory,', "package: '/untrusted-source',", 'trusted activation overlay', 'trusted guard must be activated'],
    ['preload loss', 'lib/opencode-policy.mjs', "resource: 'plugin:*', effect: 'deny'", "resource: 'unrelated:*', effect: 'deny'", 'trusted activation overlay', 'untrusted sources must be denied before import'],
  ]) {
    const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-guard-mutant-'));
    fs.cpSync(new URL('../tools/harness/lib/', import.meta.url), path.join(scratch, 'lib'), { recursive: true });
    fs.cpSync(new URL('../tools/harness/opencode-guard/', import.meta.url), path.join(scratch, 'opencode-guard'), { recursive: true });
    const target = path.join(scratch, file);
    const original = fs.readFileSync(target, 'utf8');
    assert(original.includes(before));
    fs.writeFileSync(target, original.replace(before, after));
    const environment = { ...process.env };
    delete environment.NODE_TEST_CONTEXT;
    const result = spawnSync(process.execPath, ['--test', '--test-name-pattern=' + pattern, fileURLToPath(import.meta.url)], {
      encoding: 'utf8', timeout: 20000, env: { ...environment,
        T72_GUARD_SCANNER: pathToFileURL(path.join(scratch, 'opencode-guard/scanner.mjs')).href,
        T72_GUARD_PLUGIN: pathToFileURL(path.join(scratch, 'opencode-guard/guard.mjs')).href,
        T72_GUARD_HELPER: pathToFileURL(path.join(scratch, 'lib/opencode-guard.mjs')).href,
        T72_GUARD_POLICY: pathToFileURL(path.join(scratch, 'lib/opencode-policy.mjs')).href,
      },
    });
    assert.equal(result.status, 1, name);
    assert((result.stdout + result.stderr).includes(assertion), name + ' intended assertion');
    assert(!/ERR_MODULE_NOT_FOUND|MODULE_NOT_FOUND|timed out/.test(result.stdout + result.stderr), name + ' must fail behavior');
  }
});
