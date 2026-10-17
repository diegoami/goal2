// [designed: T72 rework1] Stage trusted native enforcement; preserve global provider configuration, never cwd plugins.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes } from 'node:crypto';
import { hash, OpenCodeInfraError, startPrivateServer, delay } from './opencode-transport.mjs';

const source = fileURLToPath(new URL('../opencode-guard/', import.meta.url));
export const pinnedBinarySHA256 = '20d305d0140bfe04df7264a4ecb014402b74b6ac0a0f6456ee07ef3325fb4a85';
const testStubSHA256 = 'afc431481490e60e574691cd5f54b4fb940081452e9ebc441889169be940ddf6';
export function pinGuardBinary(command) {
  // [designed: T72; tests] Production wrappers are unsupported. Only the exact nonbilling simulator may run inside Node tests.
  if (command.prefix.length) {
    const simulated = process.env.NODE_TEST_CONTEXT && command.exe === process.execPath && command.prefix.length === 1
      && hash(fs.readFileSync(command.prefix[0])) === testStubSHA256;
    if (!simulated) throw new OpenCodeInfraError('guard', 'wrapped native binaries are not audited; use the current native binary directly');
    return 'explicit hashed Node-test simulator; no native enforcement claim';
  }
  if (hash(fs.readFileSync(command.binary ?? command.exe)) !== pinnedBinarySHA256) {
    throw new OpenCodeInfraError('guard', 'native guard requires the audited OpenCode2.0.28 binary');
  }
  return 'audited native OpenCode2.0.28 binary';
}
export function selectGuardPlugins(guard, nativeIDs, evidenceFile) {
  if (nativeIDs.some(id => !guard.availableNativeIDs.includes(id))) throw new OpenCodeInfraError('guard', 'unknown builtin');
  guard.nativeIDs = [...nativeIDs];
  guard.evidenceFile = evidenceFile;
  guard.plugins = ['-*', ...nativeIDs, {
    package: guard.directory,
    options: {
      id: guard.id, source: guard.source, nativeIDs: guard.nativeIDs,
      permissions: guard.permissions, evidenceFile,
    },
  }];
  return guard;
}
export function verifyGuardDependencies(directory = source) {
  const dependencies = JSON.parse(fs.readFileSync(path.join(source, 'dependency-hashes.json')));
  try {
    for (const [file, expected] of Object.entries(dependencies)) {
      if (hash(fs.readFileSync(path.join(directory, file))) !== expected) throw Error('hash mismatch: ' + file);
    }
  } catch {
    throw new OpenCodeInfraError('guard', 'missing or changed guard dependencies; run npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund before offline validation');
  }
  return dependencies;
}
export function stageGuard(root, policy) {
  const dependencies = verifyGuardDependencies();
  const directory = fs.mkdtempSync(path.join(root, 'native-guard-'));
  fs.cpSync(source, directory, { recursive: true });
  const id = 'goal2.review.guard.' + randomBytes(12).toString('hex');
  fs.writeFileSync(path.join(directory, 'server.js'), `import { setup } from './guard.mjs';\nexport default {id:${JSON.stringify(id)},setup};\n`);
  const availableNativeIDs = JSON.parse(fs.readFileSync(path.join(directory, 'native-plugins.json')));
  const files = Object.fromEntries([
    'guard.mjs', 'scanner.mjs', 'package.json', 'package-lock.json',
    'dependency-hashes.json', 'native-plugins.json', 'server.js', 'LICENSE.opencode', 'README.md',
  ].map(file => [file, hash(fs.readFileSync(path.join(directory, file)))]));
  return selectGuardPlugins({
    id, directory, source: path.join(directory, 'server.js'), availableNativeIDs,
    sourceSHA256: files['guard.mjs'], files, dependencies, permissions: policy.profile.permissions,
  }, availableNativeIDs);
}
export function verifyPlugins(items, guard, { baseline = false } = {}) {
  const expected = new Set(baseline ? guard.availableNativeIDs : guard.nativeIDs);
  let found = baseline;
  if (!Array.isArray(items)) throw new OpenCodeInfraError('guard', 'unverified plugin inventory');
  for (const item of items) {
    if (item.state?.status !== 'active') throw new OpenCodeInfraError('guard', 'failed plugin');
    if (!baseline && item.id === guard.id && item.source?.type === 'local' && path.resolve(item.source.path) === guard.source && !found) {
      found = true;
      continue;
    }
    if (item.source?.type !== 'builtin' || !expected.delete(item.id)) {
      throw new OpenCodeInfraError('guard', 'untrusted external plugin requires explicit audit');
    }
  }
  // [designed: T72; tests] Native disables survive baseline discovery; guarded runs must match that exact subset.
  if (!found || (!baseline && expected.size) || (baseline && !items.some(i => i.id === 'opencode.config.policy'))) {
    throw new OpenCodeInfraError('guard', 'missing trusted native guard or builtin');
  }
}
export async function readyPlugins(server, guard, { baseline = false, timeoutMs = 30000 } = {}) {
  const start = Date.now();
  let last;
  do {
    try {
      const value = await server.request('/api/plugin', { timeoutMs: Math.max(1, timeoutMs - (Date.now() - start)) });
      verifyPlugins(value.data, guard, { baseline });
      if (baseline && !value.data.some(i => i.id === 'opencode.config.provider')) throw Error('native startup pending');
      return value.data;
    } catch (error) { last = error; }
    await delay(50);
  } while (Date.now() - start < timeoutMs);
  throw last;
}
export const catalogueProjection = items => items.map(({ id, modelID, providerID, family, enabled, variants }) => ({
  id, modelID, providerID, family, enabled, variants: variants.map(v => v.id),
})).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));

export function couldMatchPlugin(pattern) {
  // [derived: native Wildcard.match; tests] A literal prefix incompatible with plugin: proves disjointness; all other globs fail closed.
  pattern = pattern.replaceAll('\\', '/').toLowerCase();
  const wildcard = pattern.search(/[?*]/);
  if (wildcard < 0) return pattern.startsWith('plugin:');
  const prefix = pattern.slice(0, wildcard);
  return prefix.startsWith('plugin:') || 'plugin:'.startsWith(prefix);
}
export function inspectConfig(entries, guard) {
  if (!Array.isArray(entries)) throw new OpenCodeInfraError('guard', 'unverified config discovery');
  let shell;
  const declarations = [];
  for (const entry of entries.slice(0, -1)) {
    if (entry.type === 'document') {
      if (entry.info.shell !== undefined) shell = entry.info.shell;
      for (const rule of entry.info.experimental?.policies ?? []) {
        if (rule.action === 'integration.use' && rule.effect === 'allow' && couldMatchPlugin(rule.resource)) {
          throw new OpenCodeInfraError('guard', 'higher-authority plugin allow policy requires explicit audit');
        }
      }
      for (const raw of entry.info.plugins ?? []) {
        const target = typeof raw === 'string' ? raw : raw.package;
        if (!target.startsWith('-') && !guard.availableNativeIDs.includes(target)) declarations.push(hash(target));
      }
    } else if (entry.type === 'directory') {
      for (const name of ['plugin', 'plugins']) {
        let children;
        try { children = fs.readdirSync(path.join(entry.path, name), { withFileTypes: true }); }
        catch (error) { if (error.code === 'ENOENT') continue; throw error; }
        for (const child of children) if (child.isDirectory() || child.isSymbolicLink() || /\.(?:js|ts)$/.test(child.name)) {
          declarations.push(hash(path.join(entry.path, name, child.name)));
        }
      }
    }
  }
  if (declarations.length) throw new OpenCodeInfraError('guard', 'external executable plugins require explicit audit before review');
  if (shell && !/^(?:bash|sh|dash|zsh|pwsh|powershell)(?:\.exe)?$/i.test(path.basename(shell))) {
    throw new OpenCodeInfraError('guard', 'configured shell has no verified operand grammar');
  }
  return { shell: shell ?? null, externalPluginDeclarations: 0 };
}
export async function baselinePlugins(command, { env, cwd, guard, timeoutMs = 30000 }) {
  // [designed: T72] Survey has no external setup activations; provider fields are discarded without inspection/persistence.
  const content = JSON.parse(env.OPENCODE_CONFIG_CONTENT);
  content.plugins = ['-*'];
  let survey = await startPrivateServer(command, { env: { ...env, OPENCODE_CONFIG_CONTENT: JSON.stringify(content) }, cwd, timeoutMs });
  let config;
  let surveyShutdown;
  try { config = inspectConfig(await survey.request('/api/config', { timeoutMs }), guard); }
  finally { surveyShutdown = await survey.stop(); survey = null; }
  const server = await startPrivateServer(command, { env, cwd, timeoutMs });
  let result;
  try {
    const actualConfig = inspectConfig(await server.request('/api/config', { timeoutMs }), guard);
    const plugins = await readyPlugins(server, guard, { baseline: true, timeoutMs });
    const models = catalogueProjection((await server.request('/api/model', { timeoutMs })).data);
    result = { plugins, models, config, actualConfig, surveyShutdown };
    return result;
  } finally {
    const shutdown = await server.stop();
    if (result) result.shutdown = shutdown;
  }
}
