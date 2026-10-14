#!/usr/bin/env node
// Hands one pull request to OpenCode for a review, and posts the result as one PR comment.
//
//   node tools/harness/review.mjs --pr 42 --brief brief.md [--reviewer NAME] [--exclude NAME,...]
//     [--issue 12 --apply-label] [--done-when K] [--dry-run] [--env KEY=VALUE]...
//     [--total-timeout-sec N] [--idle-timeout-sec N]   override harness.json's limits for this run
//   node tools/harness/review.mjs --self-test   (the reader's samples and the named-model checks; no model is called)
//
// One reviewer, one run (the owner, 2026-10-11: no chains, no second opinion, no quota check, no
// resume). --reviewer is a harness.json key or any OpenCode id provider/model[@variant]
// (lib/named.mjs); without it, harness.json's reviewer.default runs. The reviewer is never the
// implementer's model family: --exclude names the implementer (a harness.json key, an id or a
// family), else a model:<name> label on the PR or --issue, else the session's own family (the main
// session or an agent it spawned implements by default; lib/common.mjs sessionFamily reads it from
// ANTHROPIC_BASE_URL, or HARNESS_SESSION_FAMILY). Runs use the scripts' own OpenCode data
// directory. harness.json's blocked list is refused (switch-model.mjs --block/--unblock).
//
// The brief's first line is the review header the model prints, e.g. "T07 review (Luna)". The
// model never writes to GitHub (the agent file denies it); this script is the only writer.
//
// A review is never thrown away (lib/chain.mjs readReview). A readable review is posted normalised
// and acted on. One that may be cut off, has no readable verdict, opens and closes with different
// verdicts, or has a finding after its closing verdict is posted whole, exactly as it arrived, under
// a note, with no label: OpenCode's models do not always follow the brief, and the main session
// reads such a review instead of paying for another. Closing keywords lose their '#'.
//
// The review accounts for each Done-when line of the task file pasted in the brief (or --done-when
// K): one "DW<k>:" line each, after the verdict (L32). An approve with a line missing, or one not
// run, is posted under a note and not labelled approved (exit 4).
//
// A brief naming a commit other than the PR's head as the one to review is refused, exit 2, before
// anything runs (#23). Only the lines before the pasted task file's title (`# T<nn>`) are read (#32).
//
// Exit 0: posted, and labelled with --apply-label. Exit 1: refused or a defect. Exit 2: usage, or a
// refused model (DeepSeek, an unknown name). Exit 3: OpenCode unavailable, its model not listed, or
// no review came back; nothing posted. Read the run's final message (CLAUDE.md rule 12 of "Choosing
// models"), fix the cause, and run again; whether another model reviews instead is the user's
// call. A run our own idle or total limit killed is run again with a longer limit. Exit 4: posted
// under a note, no label; the main session reads it on the PR and decides, and never pays for a
// second review because of it. --dry-run prints what would be posted and the exit code it would
// use, and exits 0; it still runs, and bills, the model.

import fs from 'node:fs';
import path from 'node:path';
import { randomBytes } from 'node:crypto';
import { runOpenCodeWatched, resolveOpenCode, OpenCodeInfraError, keyProblem } from './lib/opencode.mjs';
import { credentialJail, OFF_WARNING } from './lib/jail.mjs';
import { namedModel, familiesOfName, familiesOfModel, canonicalFamily, selfTest as namedSelfTest } from './lib/named.mjs';
import { readReview, doneWhenCount, briefTargets } from './lib/chain.mjs';
import { planSwitch, defaultVariant } from './lib/switch.mjs';
import { planPost, publish } from './lib/post.mjs';
import { selfTest, SAMPLES } from './lib/review-selftest.mjs';
import {
  sh, requireTools, repoPaths, loadConfig, parseArgs, envWith, ocArgs, prepareOpenCode, watchLine, sessionFamily,
} from './lib/common.mjs';

const say = (s) => console.log(s);
const die = (code, s) => { console.error(s); process.exit(code); };

const a = parseArgs(process.argv.slice(2), { flags: ['apply-label', 'dry-run', 'self-test'], repeatable: ['env'] });
// The run's title names its files (the brief, the logs): a model id's '/' would make a directory
// there (#145, Sol's R5 on PR 149). The id and variant passed to OpenCode stay as named.
const fileSafe = (s) => String(s).replace(/[^\w.@-]+/g, '-');

// The family guard's cases (Sol's R1-R5 on PR 149), for --self-test.
function guardSelfTest() {
  const failures = [];
  const ok = (what, cond) => { if (!cond) failures.push(what); };
  const fam = (u) => sessionFamily({ ANTHROPIC_BASE_URL: u });
  ok('no endpoint is claude', fam('') === 'claude');
  ok('Z.AI is glm', fam('https://api.z.ai/api/anthropic') === 'glm');
  ok('MiniMax is minimax', fam('https://api.minimax.io/anthropic') === 'minimax');
  ok('anthropic.com in a path is unknown (R4)', fam('https://unknown.example/anthropic.com') === null);
  ok('a host containing anthropic.com is unknown (R4)', fam('https://api.anthropic.com.proxy.example') === null);
  ok('the override wins', sessionFamily({ ANTHROPIC_BASE_URL: 'https://x.example', HARNESS_SESSION_FAMILY: 'Kimi' }) === 'kimi');
  const cfg = { blocked: ['deepseek'], models: {}, reviewer: {}, implementer: {} };
  const refused = (opts) => { try { planSwitch(cfg, opts); return false; } catch (e) { return /^Refused/.test(e.message); } };
  ok('a blocked implementer is refused (R3)', refused({ role: 'implementer', id: 'DeepSeek-v4-pro' }));
  ok('an alias implementer passes', !refused({ role: 'implementer', id: 'sonnet' }));
  ok('a Claude reviewer in a Claude session is refused (R2)', refused({ id: 'anthropic/claude-sonnet-4-5', variant: 'high', sessionFamily: 'claude' }));
  ok('a forced family does not pass the session family (R2)',
    refused({ id: 'openai/gpt-5.6-luna', variant: 'high', family: 'other', force: true, sessionFamily: 'openai' }));
  ok('a blocked session refuses an alias implementer (round-1 R1)',
    refused({ role: 'implementer', id: 'sonnet', sessionFamily: 'deepseek' }) && refused({ role: 'implementer', id: 'session', sessionFamily: 'deepseek' }));
  ok('an unknown session refuses an alias implementer (round-1 R1)', refused({ role: 'implementer', id: 'sonnet', sessionFamily: null }));
  ok('codex and chatgpt ids are openai (round-1 R2)',
    familiesOfModel({ id: 'openai/codex-mini-latest' }).includes('openai') && familiesOfModel({ id: 'openai/chatgpt-4o-latest' }).includes('openai'));
  ok('a forced implementer entry keeps its id\'s family (round-1 R3)',
    familiesOfName('forced-openai', { 'forced-openai': { id: 'openai/gpt-5.6-luna', family: 'other' } }).includes('openai'));
  ok('the switcher refuses codex and chatgpt in an openai session (round-1 R2)',
    ['openai/codex-mini-latest', 'openai/chatgpt-4o-latest'].every((id) => refused({ id, variant: 'high', sessionFamily: 'openai' })));
  ok('a key named after a family keeps that family (round-2 R1)',
    familiesOfName('claude', { claude: { id: 'openai/gpt-5.6-luna', family: 'openai' } }).includes('claude'));
  ok('a blocked session refuses a model-id implementer too (round-2 R2)',
    refused({ role: 'implementer', id: 'glm-5.3', sessionFamily: 'deepseek' }) && refused({ role: 'implementer', id: 'gpt-5.6-luna', sessionFamily: 'deepseek' }));
  ok('a model-id implementer on a Claude session passes', !refused({ role: 'implementer', id: 'glm-5.3', sessionFamily: 'claude' }));
  let variantOk = true;
  try { defaultVariant('openai/gpt-5.6-luna', null); defaultVariant('openai/gpt-6.1-sol', ['low', 'medium', 'high']); } catch { variantOk = false; }
  ok('a reviewer switch without --variant works (round-2 R3)', variantOk);
  ok('a model id makes no directory in a title (R5)', !fileSafe('pr149-openai/gpt-6.1-sol@medium').includes('/'));
  return failures;
}

if (a['self-test']) {
  const failures = [...selfTest(), ...namedSelfTest(), ...guardSelfTest()];
  for (const f of failures) console.error(`FAIL ${f}`);
  say(`self-test: ${SAMPLES.length - failures.length} of ${SAMPLES.length} samples read as expected, and the named-model checks ${failures.length ? 'failed' : 'passed'}`);
  process.exit(failures.length ? 1 : 0);
}
if (!a.pr || !a.brief) die(2, '--pr and --brief are required.');
if (a['apply-label'] && !a.issue) die(2, '--apply-label needs --issue.');
const limit = (k) => {
  if (a[k] === undefined) return null;
  const n = Number(a[k]);
  if (!Number.isInteger(n) || n <= 0) die(2, `--${k} takes a positive number of seconds; got ${a[k]}`);
  return n;
};
const totalSec = limit('total-timeout-sec');
const idleSec = limit('idle-timeout-sec');
const brief = fs.readFileSync(a.brief, 'utf8').split(/\r?\n/);
const briefHeader = brief[0].trim();
const doneWhen = a['done-when'] !== undefined ? Number(a['done-when']) : doneWhenCount(brief.join('\n'));
if (!Number.isInteger(doneWhen) || doneWhen < 0) die(2, `--done-when takes a count; got ${a['done-when']}`);
if (!/review \(/.test(briefHeader)) die(2, `The brief's first line must be the review header, e.g. "T07 review (Luna)"; got: ${briefHeader}`);

requireTools('git', 'gh');

const top0 = sh('git', ['rev-parse', '--show-toplevel']);
const config = loadConfig(top0);
const { top, workRoot } = repoPaths(config);
const rev = config.reviewer;

// The implementer's family never reviews: the session's family always (every Claude Code agent runs
// through its endpoint), and with it --exclude and the model: labels (Sol's R1 on PR 149: they
// replaced it).
const labelsOf = (kind, n) => sh('gh', [kind, 'view', String(n), '--json', 'labels', '--jq', '.labels[].name'], { cwd: top, allowFail: true }).split('\n');
// All three are united (Sol's round-1 R4: --exclude dropped the labels).
const named = [...(a.exclude ? a.exclude.split(',').map((s) => s.trim()).filter(Boolean) : []),
  ...[...labelsOf('pr', a.pr), ...(a.issue ? labelsOf('issue', a.issue) : [])]
    .filter((l) => l.startsWith('model:')).map((l) => l.slice(6))];
const own = sessionFamily();
if (!own) die(2, `The session's family cannot be told from the client/provider settings: check HARNESS_CLIENT and HARNESS_SESSION_FAMILY.`);
const implementedBy = [...new Set([...named, own])];
// The reviewer: the one named, else harness.json's reviewer.default; a harness.json key, or any
// OpenCode id the user names, provider/model[@variant] (lib/named.mjs).
const reviewer = a.reviewer ?? rev.default;
if (!reviewer) die(2, 'No reviewer: pass --reviewer, or set reviewer.default in harness.json.');
let model;
try { model = namedModel(reviewer, config.models, config.blocked ?? []); } catch (e) { die(2, e.message); }
if (!model) die(2, `Unknown reviewer ${reviewer}: give a harness.json key or an OpenCode id, provider/model[@variant].`);
config.models[reviewer] = model;
// the session's own family stays in, whatever a harness.json key of that name holds (Sol's round-2 R1)
const families = [...new Set([canonicalFamily(own), ...implementedBy.flatMap((n) => familiesOfName(n, config.models))])];
say(`implemented by: ${implementedBy.join(', ')} (${own}: the session's family, from client/provider settings)`);
if (familiesOfModel(model).some((f) => families.includes(f))) die(1, `Refused: ${reviewer} is the implementer's model family (${families.join(', ')}). Nothing posted.`);
const fallback = 'Nothing posted. Read the run\'s final message (CLAUDE.md, "Choosing models" rule 12) and fix the cause; another reviewer is the user\'s call.';
// OpenCode is looked for only now, so that its absence is reported with the same fallback (Sol's R1 on PR 41).
let opencode;
try { opencode = resolveOpenCode(); } catch (e) {
  if (e instanceof OpenCodeInfraError) die(3, `OpenCode unavailable: ${e.message} ${fallback}`);
  throw e;
}
// OpenCode, and every command it runs, in the credential jail (lib/jail.mjs, #68), only where
// harness.json turns it on (jail.enabled); where it is on but cannot run, the log says so first.
const jail = config.jail?.enabled === true ? credentialJail() : { off: 'harness.json does not enable it', quiet: true };
if (jail.off && !jail.quiet) say(OFF_WARNING(jail.off));
else if (!jail.off) opencode = { exe: jail.exe, prefix: [...jail.args, '--', opencode.exe, ...opencode.prefix] };
const pre = await prepareOpenCode({ opencode, chain: [reviewer], models: config.models, env: envWith(a.env), cwd: top, log: say });
for (const p of pre.problems) say(p);
if (!pre.usable.length) die(3, `OpenCode unavailable: ${pre.problems.join('; ')}. ${fallback}`);

// The reviewer's agent and OpenCode config come from this checkout, the main session's, never from
// the PR under review: OpenCode reads a project's .opencode/ by default, so a PR's own reviewer.md
// (or anything else it puts there) would decide what its reviewer may do. Checked on OpenCode
// 1.18.34: without these two variables a PR's reviewer.md with `git push *: allow` was the one
// loaded (#10, L34; ic2-conquest's reviewer does the same).
const agentFile = path.join(top, '.opencode', 'agents', `${rev.agent}.md`);
if (!fs.existsSync(agentFile)) die(2, `The reviewer agent is missing from this checkout: ${agentFile}. Nothing run.`);
const reviewEnv = { ...pre.env, OPENCODE_CONFIG_DIR: path.join(top, '.opencode'), OPENCODE_DISABLE_PROJECT_CONFIG: '1' };
const headSha = sh('gh', ['pr', 'view', String(a.pr), '--json', 'headRefOid', '--jq', '.headRefOid'], { cwd: top });
// A brief that names another commit as the one to review would make the reviewer's tree proof stop
// it after a billed run (#23): refuse it before any worktree or model run.
const stale = [...new Set(briefTargets(brief.join('\n')))].filter((c) => c !== headSha.toLowerCase());
if (stale.length) {
  die(2, `The brief names ${stale.join(', ')} as the commit to review, but PR ${a.pr}'s head is ${headSha}. `
    + 'Nothing was run or posted. The brief was written before the latest push, or the head was read before '
    + 'GitHub updated: take it from the local branch (git rev-parse <branch>), or rerun once GitHub shows it.');
}
sh('git', ['-C', top, 'fetch', '-q', 'origin', `pull/${a.pr}/head`]);
// A path of this invocation's own; only this tree is ever removed.
const worktree = path.join(workRoot, `${a.pr}-review-${randomBytes(4).toString('hex')}`);
let created = false;
const removeTree = () => {
  if (!created) return;
  sh('git', ['-C', top, 'worktree', 'remove', '--force', worktree], { allowFail: true });
  fs.rmSync(worktree, { recursive: true, force: true });
  sh('git', ['-C', top, 'worktree', 'prune'], { allowFail: true });
  created = false;
};
const newTree = () => {
  removeTree();
  fs.mkdirSync(workRoot, { recursive: true });
  sh('git', ['-C', top, 'worktree', 'add', '--detach', worktree, headSha]);
  created = true;
  say(`worktree: ${worktree} at ${headSha}`);
};

// The review, in a fresh worktree at the PR's head. Resolves { ok: true, value } or
// { ok: false, reason, detail }. The header names the default reviewer when none was given.
const attempt = async (m) => {
      const header = a.reviewer ? briefHeader : briefHeader.replace(/\([^()]*\)\s*$/, `(${m})`);
      const prompt = `${header}\n${brief.slice(1).join('\n')}

---
OUTPUT RULES (from tools/harness/review.mjs; they override anything above that conflicts):
- Do not post to GitHub, edit, commit, push, label or merge anything. The script posts your review.
- Your final message is the review and nothing else. Line 1 is exactly: ${header}
  Line 2 is the verdict, alone on its line: approve, approve after named fixes, rework, or user
  decision. Then any where-I-worked lines (worktree, HEAD, diff, the commands you ran), then the
  findings (R1, R2, ... with file and line, blocking or not), then the verdict again as the very
  last line. Nothing comes after it.
- A finding you proved that lets a forbidden action or a wrong result past what the task protects
  is blocking, and blocks an approve: never "follow-up hardening" or "outside the threat model"
  unless the task's text says so (L47).
- Report every blocking finding in this one review, not one per round: read the whole diff, then
  make a final pass and write "Final pass done" as the line before the closing verdict. Name any
  part you did not cover, and do not approve then (L49).${doneWhen ? `
- The task has ${doneWhen} Done-when line${doneWhen > 1 ? 's' : ''}. Right after the verdict line, account for each, one
  line per Done-when line, DW1 to DW${doneWhen}: "DW<k>: ran <command> → <result>", or
  "DW<k>: not run — <reason>". An approve with one missing, or one not run, is not applied.` : ''} A review that does not end with its verdict, or that has a
  finding after it, is posted flagged and acted on by no one until the main session reads it.
- Your worktree is ${worktree} at ${headSha}, and it is already your working directory. Run git
  there without -C, and never type that path: a mistyped path ends the run. This rule is about
  your own worktree only (L61): a Done-when line may send git at a pinned repository outside it
  (git -C <path> show <pin>:<file>); run that exactly as written — OpenCode does not path-check
  git -C — and read a granted outside path only with the L59 recipe.
`;
      newTree();
      const watch = watchLine(m, model);
      if (watch) say(watch);
      let run;
      try {
        run = await runOpenCodeWatched({
          args: ocArgs(worktree, rev.agent, model), prompt, workDir: worktree, title: `pr${a.pr}-${fileSafe(m)}`,
          startupTimeoutMs: rev.startupTimeoutSec * 1000, idleTimeoutMs: (idleSec ?? rev.idleTimeoutSec) * 1000,
          totalTimeoutMs: (totalSec ?? rev.totalTimeoutSec) * 1000, opencode, env: reviewEnv, log: say,
        });
      } catch (e) {
        if (!(e instanceof OpenCodeInfraError)) throw e;
        return { ok: false, reason: e.reason, detail: e.message };
      }
      // OpenCode's own error stream on a failed run, never the model's output (Luna's R1, round 2).
      if (run.exitCode !== 0) return { ok: false, reason: keyProblem(run.stderr, model.id, reviewEnv.XDG_DATA_HOME) ?? `exit ${run.exitCode}`, detail: run.output };
      if (run.agentFallback) return { ok: false, reason: 'fell back to the default agent', detail: run.output };
      if (run.permissionRejected) {
        return { ok: false, reason: `permission rejected: ${run.permissionRejected}${run.permissionHint ? `; ${run.permissionHint}` : ''}`, detail: run.output };
      }
      const read = readReview(run.stdout, header);
      if (read.kind === 'none') return { ok: false, reason: read.reason, detail: run.output };
      return { ok: true, value: { ...read, header, model } };
};

say(`attempt: ${reviewer}`);
let result;
try { result = await attempt(reviewer); } finally { removeTree(); }
if (!result.ok) {
  if (result.detail) say(result.detail.split(/\r?\n/).slice(-20).join('\n'));
  die(3, `No review from ${reviewer}: ${result.reason}. ${fallback}`);
}
const plan = planPost({
  read: result.value, header: result.value.header, doneWhen, source: 'tools/harness/review.mjs',
  signature: `${reviewer}, via tools/harness/review.mjs (${result.value.model.id})`,
});
publish({ plan, pr: a.pr, issue: a.issue, applyLabel: a['apply-label'], dryRun: a['dry-run'], top, say, die });
