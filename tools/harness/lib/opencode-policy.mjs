// [designed: T72] Freeze the launching checkout's reviewer; never trust the PR's config.
import fs from 'node:fs';
import { hash, OpenCodeInfraError } from './opencode-transport.mjs';
const ACTION = { bash: 'shell', task: 'subagent', edit: 'edit', external_directory: 'external_directory' };
export function reviewerPolicy(agentFile) {
  const source = fs.readFileSync(agentFile, 'utf8');
  const match = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/.exec(source);
  if (!match) throw new Error('reviewer frontmatter is missing');
  const [, front, system] = match;
  const permissions = []; let action;
  for (const line of front.split('\n')) {
    let m;
    if ((m = /^  ([a-z_]+): (allow|ask|deny)$/.exec(line))) {
      if (!ACTION[m[1]]) throw new Error(`unsupported reviewer permission ${m[1]}`);
      permissions.push({ action: ACTION[m[1]], resource: '*', effect: m[2] }); action = null;
    } else if ((m = /^  ([a-z_]+):$/.exec(line))) {
      action = ACTION[m[1]]; if (!action) throw new Error(`unsupported reviewer permission ${m[1]}`);
    } else if ((m = /^    "([^"\n]+)": (allow|ask|deny)$/.exec(line))) {
      if (!action) throw new Error('reviewer permission resource has no action');
      permissions.push({ action, resource: m[1].replace(/^~(?=\/|$)/, process.env.HOME), effect: m[2] });
    } else if (/^\s+\S/.test(line)) throw new Error(`unsupported reviewer permission syntax`);
  }
  // [confirmed: T72a captured legacy profile] Legacy compatibility also denies browser tools.
  permissions.push({ action: 'browser', resource: '*', effect: 'deny' });
  const requireRule = (action, resource, effect) => {
    if (!permissions.some((r) => r.action === action && r.resource === resource && r.effect === effect)) throw new Error(`reviewer must preserve ${action} ${resource} ${effect}`);
  };
  requireRule('edit', '*', 'deny'); requireRule('subagent', '*', 'deny'); requireRule('external_directory', '*', 'ask');
  for (const command of ['git push *', 'git -C * push *', 'git commit *', 'git -C * commit *', 'gh pr merge *', 'gh pr comment *', 'gh pr review *', 'gh pr edit *', 'gh issue edit *', 'gh issue comment *']) requireRule('shell', command, 'deny');
  const allowed = permissions.filter((r) => r.action === 'external_directory' && r.effect === 'allow').map((r) => r.resource).sort();
  const exact = ['/tmp/opencode/*', '/tmp', '/tmp/*', `${process.env.HOME}/projects/goal2-archaeology`, `${process.env.HOME}/projects/goal2-archaeology/*`].sort();
  if (JSON.stringify(allowed) !== JSON.stringify(exact)) throw new Error('reviewer external grants differ from exact research/tmp contract');
  return { sourceSHA256: hash(source), profile: { mode: 'all', hidden: false, system: system.trim(), permissions } };
}
export function trustedReviewEnv(env, policy, agent = 'reviewer') {
  const next = { ...env };
  for (const key of ['OPENCODE_CONFIG_DIR', 'OPENCODE_CONFIG', 'OPENCODE_CONFIG_CONTENT', 'OPENCODE_CONFIG_PROJECT_DISABLE']) delete next[key];
  return { ...next, OPENCODE_DISABLE_PROJECT_CONFIG: '1', OPENCODE_CONFIG_CONTENT: JSON.stringify({ agents: { [agent]: policy.profile } }) };
}
export function verifyReviewer(profile, policy, agent) {
  const expected = policy.profile;
  // [derived: T72 live profile; test] Consecutive identical rules have identical last-match effect.
  const canonical = (rules) => rules.map(({ action, resource, effect }) => ({ action, resource, effect })).filter((r, i, rows) => i === 0 || JSON.stringify(r) !== JSON.stringify(rows[i - 1]));
  const actualRules = canonical(profile.permissions); const expectedRules = canonical(expected.permissions);
  if (profile.id !== agent || profile.mode !== expected.mode || profile.hidden !== false || profile.system !== expected.system || JSON.stringify(actualRules.slice(-expectedRules.length)) !== JSON.stringify(expectedRules)) {
    throw new OpenCodeInfraError('profile', 'effective reviewer differs from the trusted permission contract');
  }
}
