// [designed: T73] Pin complete local evidence, including rename source paths; no GitHub diff-size limit.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { demand, sha } from './claude-policy.mjs';
export function localGit(cwd, args) {
  const r = spawnSync('git', ['--no-pager', ...args], { cwd, encoding: 'utf8', maxBuffer: 128 * 1024 * 1024, env: { ...process.env, GIT_CONFIG_COUNT: '0', GIT_EXTERNAL_DIFF: '', GIT_PAGER: 'cat' } });
  demand(!r.error && r.status === 0, 'local git evidence'); return r.stdout;
}
export function pinnedScope({ cwd, base, head, pr, directory }) {
  demand(/^[0-9a-f]{40}$/.test(head) && /^[0-9a-f]{40}$/.test(base) && Number.isSafeInteger(pr) && pr > 0, 'scope identity');
  demand(localGit(cwd, ['rev-parse', 'HEAD']).trim() === head && !localGit(cwd, ['status', '--porcelain', '--untracked-files=no']).trim(), 'clean exact head');
  demand(localGit(cwd, ['merge-base', base, head]).trim() === base, 'base must be pinned PR merge base');
  for (const ref of [base, head]) demand(localGit(cwd, ['rev-parse', ref + '^{commit}']).trim() === ref, 'pinned commit');
  const names = localGit(cwd, ['diff', '--no-ext-diff', '--no-textconv', '--name-status', '-z', '--find-renames', base, head]).split('\0');
  const inventory = [];
  while (names[0]) { const status = names.shift(); const paths = [names.shift()]; if (/^[RC]/.test(status)) paths.push(names.shift()); demand(paths.every(p => typeof p === 'string' && p.length), 'inventory path'); inventory.push({ id: 'F' + String(inventory.length + 1).padStart(3, '0'), status, paths }); }
  demand(inventory.length > 0, 'empty scope');
  const diff = localGit(cwd, ['diff', '--no-ext-diff', '--no-textconv', '--find-renames', '--no-color', base, head, '--']);
  const chunks = [];
  for (let i = 0; i < diff.length; i += 24000) { const name = `diff-${String(chunks.length + 1).padStart(4, '0')}.txt`; const text = diff.slice(i, i + 24000); fs.writeFileSync(path.join(directory, name), text, { flag: 'wx' }); chunks.push({ name, sha256: sha(text) }); }
  const scope = { pr, base, head, inventory, chunks, diffSHA256: sha(diff) };
  fs.writeFileSync(path.join(directory, 'scope.json'), JSON.stringify(scope, null, 2) + '\n', { flag: 'wx' });
  return scope;
}
// [designed: T73] A staged review tree retains offline dependencies; never adopt the implementation/main checkout.
export function preparedClaudeWorktree({ directory, top, workRoot, commonDir, head }) {
  const real = fs.realpathSync(directory);
  demand(real !== fs.realpathSync(top) && localGit(real, ['branch', '--show-current']).trim() === '' && real.startsWith(fs.realpathSync(workRoot) + path.sep) && localGit(real, ['rev-parse', '--path-format=absolute', '--git-common-dir']).trim() === commonDir && localGit(real, ['rev-parse', 'HEAD']).trim() === head && !localGit(real, ['status', '--porcelain', '--untracked-files=no']).trim(), 'prepared review worktree identity');
  return real;
}
