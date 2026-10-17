// [designed: T72 rework1] Tighten shell outcomes at the legacy static-operand boundary; no OS jail claim.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { operandDirectories, externalEffect } from './scanner.mjs';

export function verifyInventory(items, { id, source, nativeIDs }) {
  if (!Array.isArray(items) || items.length !== nativeIDs.length + 1) throw Error('unverified native plugin inventory');
  const expected = new Set(nativeIDs);
  let guard = false;
  for (const item of items) {
    if (item.state?.status !== 'active') throw Error('failed native plugin');
    if (item.id === id && item.source?.type === 'local' && path.resolve(item.source.path) === source && !guard) {
      guard = true;
      continue;
    }
    if (item.source?.type !== 'builtin' || !expected.delete(item.id)) throw Error('untrusted external plugin: ' + item.id);
  }
  if (!guard || expected.size) throw Error('missing trusted native guard');
}
export async function setup(ctx) {
  const options = ctx.options;
  if (!options || !Array.isArray(options.permissions) || !Array.isArray(options.nativeIDs)) throw Error('missing trusted guard policy');
  const roots = [ctx.location.directory, ctx.location.project?.directory]
    .filter(root => typeof root === 'string' && path.parse(root).root !== root);
  await operandDirectories('true', ctx.location.directory, roots);
  const state = new Map();
  const key = event => event.sessionID + ':' + (event.id ?? event.source?.id);
  const inventory = async () => {
    const value = await ctx.plugin.list();
    verifyInventory(value.data ?? value, options);
  };
  const before = await ctx.tool.hook('execute.before', async event => {
    if (event.tool !== 'shell') return;
    await inventory();
    const input = event.input;
    state.set(key(event), {
      outcome: 'ask', scanned: false, agent: event.agent,
      command: input?.command,
      cwd: path.resolve(ctx.location.directory, input?.workdir ?? '.'),
    });
  });
  const shell = await ctx.shell.hook('create.before', async invocation => {
    // [confirmed: native Shell.create source; tests/probe] Use the FINAL actual shell/cwd, not an OS default guess.
    const cwd = path.resolve(ctx.location.directory, invocation.cwd);
    const matching = [...state.entries()].filter(([, value]) => value.command === invocation.command && value.cwd === cwd);
    let outcome = 'ask';
    const name = path.basename(invocation.shell).toLowerCase();
    const supported = /^(?:bash|sh|dash|zsh|pwsh|powershell)(?:\.exe)?$/.test(name);
    if (supported) {
      try {
        const dirs = await operandDirectories(invocation.command, cwd, roots, invocation.shell);
        outcome = dirs.map(dir => externalEffect(dir, options.permissions)).find(effect => effect !== 'allow') ?? 'allow';
      } catch { /* A malformed or unsupported scan requires approval, never implicit allow. */ }
    }
    for (const [, value] of matching) Object.assign(value, { outcome, scanned: true });
    if (options.evidenceFile) fs.appendFileSync(options.evidenceFile, JSON.stringify({
      shell: invocation.shell, cwd, grammar: /^(?:pwsh|powershell)/.test(name) ? 'powershell' : supported ? 'bash' : 'unsupported',
      commandSHA256: createHash('sha256').update(invocation.command).digest('hex'), outcome,
    }) + '\n');
  });
  const evaluate = await ctx.permission.hook('evaluate', async event => {
    if (event.action !== 'shell') return;
    await inventory();
    const scanned = state.get(key(event));
    const matches = scanned?.scanned && scanned.agent === event.agent && Array.isArray(event.resources)
      && event.resources.every(resource => typeof resource === 'string' && scanned.command?.includes(resource));
    // [designed: T72; native proof/mutants] Saved grants cannot suppress this additional operand approval.
    if (!matches || scanned.outcome !== 'allow') {
      if (event.effect !== 'deny') event.effect = scanned?.outcome === 'deny' ? 'deny' : 'ask';
      event.message = 'Legacy external_directory shell operand approval required; native noninteractive run must reject.';
    }
  });
  const after = await ctx.tool.hook('execute.after', event => {
    if (event.tool === 'shell') state.delete(key(event));
  });
  return async () => {
    await after.dispose();
    await evaluate.dispose();
    await shell.dispose();
    await before.dispose();
    state.clear();
  };
}
