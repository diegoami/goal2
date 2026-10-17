// [designed: T72] Production transport/permission/workflow regressions; no model calls.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { reviewerPolicy, trustedReviewEnv, verifyReviewer } from '../tools/harness/lib/opencode-policy.mjs';
const agentFile = new URL('../.opencode/agents/reviewer.md', import.meta.url);
test('trusted reviewer freezes exact deny rules and legacy external boundary without replacing globals', () => {
  const policy = reviewerPolicy(agentFile);
  assert(policy.profile.permissions.some((r) => r.action === 'external_directory' && r.resource === '*' && r.effect === 'ask'));
  const env = trustedReviewEnv({ OPENCODE_CONFIG_DIR: '/untrusted', OPENCODE_CONFIG: '/untrusted', OPENCODE_CONFIG_CONTENT: 'untrusted', KEEP: 'yes' }, policy);
  assert.equal(env.OPENCODE_CONFIG_DIR, undefined); assert.equal(env.OPENCODE_CONFIG, undefined); assert.equal(env.OPENCODE_DISABLE_PROJECT_CONFIG, '1'); assert.equal(env.KEEP, 'yes');
  const profile = { id: 'reviewer', ...policy.profile };
  verifyReviewer(profile, policy, 'reviewer');
  verifyReviewer({ ...profile, permissions: [...profile.permissions, profile.permissions.at(-1)] }, policy, 'reviewer');
  assert.throws(() => verifyReviewer({ ...profile, permissions: [...profile.permissions, { action: 'edit', resource: '*', effect: 'allow' }] }, policy, 'reviewer'), /effective reviewer/);
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'goal2-policy-'));
  const file = path.join(scratch, 'reviewer.md'); const original = fs.readFileSync(agentFile, 'utf8');
  for (const [before, after] of [['    "*": ask\n', ''], ['  edit: deny', '  edit: allow'], ['"git push *": deny', '"git push *": allow'], ['"/tmp/*": allow', '"/home/*": allow']]) {
    fs.writeFileSync(file, original.replace(before, after)); assert.throws(() => reviewerPolicy(file), /reviewer must preserve|exact research/);
  }
});
