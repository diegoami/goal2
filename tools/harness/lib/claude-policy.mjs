// [designed: T73; confirmed: measurements/T73/preflight.md] Mandatory native policy remains authoritative.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
export const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export const CLAUDE = Object.freeze({ version: '2.1.292', model: 'claude-sonnet-5-5', effort: 'medium', binarySHA256: 'a967e7b1d8b4e47ee421d5433027880347952b0c0857abf880e2c942a4ec93b3' });
export const TOOLS = ['Bash', 'Glob', 'Grep', 'Read'];
export class ClaudeError extends Error {
  constructor(reason) { super(`Claude review refused: ${reason}`); this.reason = reason; }
}
export function demand(ok, reason) { if (!ok) throw new ClaudeError(reason); }
export function selectClaude(model) {
  demand(model?.backend === 'claude' && model.id === CLAUDE.model && model.variant === CLAUDE.effort && model.family === 'claude', 'selection');
  return { ...CLAUDE };
}
// [designed: T73] Reconstruct, rather than clear an endpoint while forwarding its provider token.
export function claudeEnv(input, cwd) {
  const out = {};
  for (const name of ['HOME', 'PATH', 'LANG', 'LC_ALL', 'USER', 'LOGNAME', 'CLAUDE_CODE_OAUTH_TOKEN']) if (input[name]) out[name] = input[name];
  out.NO_COLOR = '1'; out.TMPDIR = path.join(fs.realpathSync(cwd), '.cache/tmp');
  fs.mkdirSync(out.TMPDIR, { recursive: true });
  return out;
}
const DENY = ['Edit', 'Write', 'Agent', 'Bash(git push *)', 'Bash(git merge *)', 'Bash(git stash *)', 'Bash(git reset *)', 'Bash(git restore *)', 'Bash(git checkout *)', 'Bash(git worktree *)', 'Bash(gh *)', 'Bash(sudo *)'];
export function reviewPolicy(file, workDir) {
  const real = fs.realpathSync(file); const cwd = fs.realpathSync(workDir);
  demand(real !== cwd && !real.startsWith(cwd + path.sep), 'policy must come from outside reviewed tree');
  const bytes = fs.readFileSync(real); const policy = JSON.parse(bytes);
  demand(Object.keys(policy).sort().join() === 'commands,directories' && Array.isArray(policy.commands) && policy.commands.length > 0 && Array.isArray(policy.directories), 'policy shape');
  // [designed: T73] These are trusted exact native command grants, never arbitrary wildcard grants.
  for (const command of policy.commands) demand(typeof command === 'string' && command.length > 0 && !/[\n\r()*]/.test(command) && /^(?:git |node --test |python3? (?:-I )?)/.test(command), 'command grant');
  const dirs = policy.directories.map(d => fs.realpathSync(d));
  demand(new Set(dirs).size === dirs.length && dirs.every(d => path.isAbsolute(d) && d !== '/' && d !== process.env.HOME), 'directory grant');
  demand(dirs.some(d => d === '/tmp') && dirs.some(d => path.basename(d) === 'goal2-archaeology'), 'research/tmp grants');
  const settings = { model: CLAUDE.model, effortLevel: CLAUDE.effort, permissions: { defaultMode: 'dontAsk', allow: ['Read', 'Grep', 'Glob', ...policy.commands.map(c => `Bash(${c})`)], deny: DENY, additionalDirectories: dirs } };
  return { file: real, sourceSHA256: sha(bytes), commands: policy.commands, directories: dirs, settings };
}
export function claudeArgs(policy, sessionID, { projection = false } = {}) {
  demand(/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/.test(sessionID), 'session UUID');
  return ['--print', '--verbose', '--output-format', 'stream-json', ...(projection ? ['--input-format', 'stream-json', '--no-session-persistence'] : []), '--session-id', sessionID, '--model', CLAUDE.model, '--effort', CLAUDE.effort, '--setting-sources', '', '--safe-mode', '--restricted', '--settings', JSON.stringify(policy.settings), '--permission-mode', 'dontAsk', '--permission-prompts', 'none', '--tools', TOOLS.join(','), '--disallowedTools', 'Edit', 'Write', 'Agent', '--strict-mcp-config', '--mcp-config', '{"mcpServers":{}}', '--disable-slash-commands', '--no-chrome', ...policy.directories.flatMap(d => ['--add-dir', d])];
}
export function verifySettings(reply, policy) {
  demand(reply && !reply.errors?.length && JSON.stringify(reply.effective) === JSON.stringify(policy.settings), 'effective settings');
  demand(Array.isArray(reply.sources) && reply.sources.every(s => ['flagSettings', 'policySettings'].includes(s.source)), 'settings sources');
  demand(reply.applied?.model === CLAUDE.model && reply.applied?.effort === CLAUDE.effort && reply.applied?.advisor == null, 'applied model/effort');
  return { effectiveSHA256: sha(JSON.stringify(reply.effective)), sources: reply.sources.map(s => ({ source: s.source, sha256: sha(JSON.stringify(s.settings)) })), model: reply.applied.model, effort: reply.applied.effort };
}
export function verifyRules(reply, policy) {
  const rules = [];
  const visit = v => { if (Array.isArray(v)) v.forEach(visit); else if (v && typeof v === 'object') { if ('behavior' in v && 'rule' in v) rules.push(v); Object.values(v).forEach(visit); } };
  visit(reply.state);
  demand(rules.length > 0, 'missing live permission rules');
  const expected = new Set(policy.settings.permissions.allow);
  for (const r of rules) {
    demand(['allow', 'deny', 'ask'].includes(r.behavior) && typeof r.rule === 'string', 'live rule shape');
    if (r.behavior === 'allow') demand(r.source === 'flagSettings' && expected.delete(r.rule), 'widened live permission');
    else demand(['flagSettings', 'policySettings', 'cliArg', 'toolsNarrowing', 'hostCredential', 'mcpServerPolicy'].includes(r.source), 'unknown permission source');
  }
  demand(expected.size === 0 && DENY.every(rule => rules.some(r => r.behavior === 'deny' && r.rule === rule)), 'missing required live permission');
  return rules.map(({ behavior, source, rule }) => ({ behavior, source, ruleSHA256: sha(rule) }));
}
