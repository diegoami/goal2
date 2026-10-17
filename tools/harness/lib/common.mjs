// git, gh, the config and argument parsing, for review.mjs, post-review.mjs and switch-model.mjs.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { privateHome } from './opencode-transport.mjs';
import { openCodeHome, listedModels, loginHint, openCodeVersion, versionProblem } from './opencode.mjs';

// The command that runs a tool. HARNESS_GH_EXE names the gh to run (the tests' fake, #2); a .mjs or
// .js one runs through Node, since Windows cannot execute a script.
export function toolCommand(cmd, env = process.env) {
  const over = cmd === 'gh' ? env.HARNESS_GH_EXE : null;
  if (!over) return [cmd, []];
  return /\.m?js$/.test(over) ? [process.execPath, [over]] : [over, []];
}

export function sh(cmd, args, { cwd, allowFail = false, env } = {}) {
  const [exe, pre] = toolCommand(cmd, env ?? process.env);
  const r = spawnSync(exe, [...pre, ...args], { cwd, env, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
  if (r.error) throw new Error(`${cmd} could not run: ${r.error.message}`);
  if (r.status !== 0 && !allowFail) throw new Error(`${cmd} ${args.join(' ')} failed (${r.status}):\n${r.stderr}`);
  return r.status === 0 ? r.stdout.trim() : '';
}

export function requireTools(...tools) {
  for (const t of tools) {
    const [exe, pre] = toolCommand(t);
    const r = spawnSync(exe, [...pre, '--version'], { stdio: 'ignore' });
    if (r.error) throw new Error(`${t} is not on PATH.`);
  }
}

// The main checkout, even when run from a worktree, and the directory agents' worktrees live in.
export function repoPaths(config) {
  const top = sh('git', ['rev-parse', '--show-toplevel']);
  const commonDir = sh('git', ['-C', top, 'rev-parse', '--path-format=absolute', '--git-common-dir']);
  const mainRoot = path.dirname(commonDir);
  const rel = (config.worktreeRoot ?? '../{repo}-work').replaceAll('{repo}', path.basename(mainRoot));
  return { top, commonDir, mainRoot, workRoot: path.resolve(mainRoot, rel) };
}

export function loadConfig(top) {
  const file = path.join(top, 'harness.json');
  if (!fs.existsSync(file)) throw new Error(`harness.json not found at ${file}`);
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

// A model's note in harness.json (what to look for, its login, its effort), printed when it runs.
export function watchLine(name, model) {
  const note = model.note ?? model.watch;
  return note ? `note: ${name} (${model.id}): ${note}` : null;
}

// --name value, --flag, and repeatable --env KEY=VALUE / --copy path.
export function parseArgs(argv, { flags = [], repeatable = [] } = {}) {
  const out = {};
  for (const r of repeatable) out[r] = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) throw new Error(`Unexpected argument: ${a}`);
    const key = a.slice(2);
    if (flags.includes(key)) { out[key] = true; continue; }
    const val = argv[++i];
    if (val === undefined) throw new Error(`${a} needs a value`);
    if (repeatable.includes(key)) out[key].push(val); else out[key] = val;
  }
  return out;
}

export function envWith(pairs) {
  const env = { ...process.env };
  for (const p of pairs) {
    const i = p.indexOf('=');
    if (i < 1) throw new Error(`--env takes KEY=VALUE; got ${p}`);
    env[p.slice(0, i)] = p.slice(i + 1);
  }
  return env;
}

// OpenCode silently falls back to its default, full-permission agent when --agent names one it
// cannot find, and a branch cut before the agent file existed does not carry it (IC2 #480). Copy
// the agent into the worktree, and keep the copy out of git so the model cannot commit it.
export function ensureAgent({ top, commonDir, worktree, agent }) {
  const rel = `.opencode/agents/${agent}.md`;
  const src = path.join(top, rel);
  if (!fs.existsSync(src)) throw new Error(`Agent file not found: ${src}`);
  if (sh('git', ['-C', worktree, 'ls-files', '--', rel], { allowFail: true })) return;
  fs.mkdirSync(path.join(worktree, '.opencode', 'agents'), { recursive: true });
  fs.copyFileSync(src, path.join(worktree, rel));
  const exclude = path.join(commonDir, 'info', 'exclude');
  const text = fs.existsSync(exclude) ? fs.readFileSync(exclude, 'utf8') : '';
  if (!text.split(/\r?\n/).includes(rel)) {
    fs.mkdirSync(path.dirname(exclude), { recursive: true });
    fs.appendFileSync(exclude, `${text && !text.endsWith('\n') ? '\n' : ''}${rel}\n`);
  }
}

// Before anything is billed: the scripts' own data directory, the OpenCode version (any major but
// the supported one is refused, #26), and which models of `chain` OpenCode lists there. A model it
// does not list (an unknown id, or a provider not logged in in that directory) is dropped, with the
// command that fixes it. Quota is not checked (the owner, 2026-10-11: the model named runs).
// Returns { env, usable, problems }.
export async function prepareOpenCode({ opencode, chain, models, env, cwd, log }) {
  const version = await openCodeVersion(opencode, { env, cwd });
  // [designed: T72] Version before legacy data access; v2 never opens/migrates the v1 receipts DB.
  const home = version?.startsWith('2.') ? privateHome(env) : null;
  const oc = home ? { ...home, dataHome: home.env.XDG_DATA_HOME } : version?.startsWith('1.') ? openCodeHome(env, { log }) : { env, dataHome: '(not opened)' };
  log(`opencode: ${version ?? 'unknown version'} (${opencode.exe})`);
  const bad = versionProblem(version, opencode.exe);
  if (bad) return { env: oc.env, usable: [], problems: [bad], version };
  const { listed, errors } = await listedModels(opencode, chain.map((m) => models[m].id.split('/')[0]), { env: oc.env, cwd });
  const problems = [];
  const usable = chain.filter((m) => {
    if (listed.has(models[m].id)) return true;
    problems.push(`${m}: ${loginHint(models[m].id, listed, oc.dataHome, errors)}`);
    return false;
  });
  return { env: oc.env, usable, problems, version };
}

// [designed: T24] Identify the implementation client independently of provider settings.
// Explicit selection supports detached jobs; Codex session markers support native tools.
// CODEX_HOME alone is an installation/config location, not evidence of the active client.
export function sessionClient(env = process.env) {
  if (env.HARNESS_CLIENT) {
    const client = env.HARNESS_CLIENT.trim().toLowerCase();
    return ['codex', 'claude'].includes(client) ? client : null;
  }
  return env.CODEX_THREAD_ID || env.CODEX_SESSION_ID ? 'codex' : 'claude';
}

// [designed: T24] Codex implements with OpenAI; conflicting overrides fail closed.
// Claude retains the endpoint/override rules below.
// The family of the main session, and so of every Claude Code agent it spawns (an agent runs through
// the same endpoint). For Claude, the session is set by the Anthropic environment variables: with
// ANTHROPIC_BASE_URL unset or at anthropic.com it is Claude; when Claude's tokens are out the owner
// points it at another provider that speaks the same API: Z.AI's GLM, MiniMax, or Moonshot's Kimi
// (the owner, 2026-10-12), and the family rule must then keep that family out of the reviewer's
// seat. The names match the families the reviewer models get (glm, minimax, kimi). HARNESS_SESSION_FAMILY
// overrides the guess; an endpoint this list does not know returns null, and the caller refuses
// to review until it is set. Only the URL's host is read, on domain boundaries: a path, a query or
// a host that merely contains a name (api.anthropic.com.proxy.example) is unknown (Sol's R4 on PR 149).
// The owner's endpoints: https://api.z.ai/api/anthropic, https://api.minimax.io/anthropic.
const ENDPOINT_FAMILIES = [[['anthropic.com'], 'claude'], [['z.ai', 'bigmodel.cn'], 'glm'],
  [['minimax.io', 'minimaxi.com'], 'minimax'], [['moonshot.ai', 'moonshot.cn', 'kimi.com'], 'kimi'],
  [['deepseek.com'], 'deepseek'], [['aliyuncs.com'], 'qwen'], [['xiaomimimo.com'], 'mimo']];
export function sessionFamily(env = process.env) {
  const client = sessionClient(env);
  if (!client) return null;
  if (client === 'codex') {
    const override = env.HARNESS_SESSION_FAMILY?.trim().toLowerCase();
    return !override || override === 'openai' ? 'openai' : null;
  }
  if (env.HARNESS_SESSION_FAMILY) return env.HARNESS_SESSION_FAMILY.trim().toLowerCase();
  if (!env.ANTHROPIC_BASE_URL) return 'claude';
  let host;
  try { host = new URL(env.ANTHROPIC_BASE_URL).hostname.toLowerCase(); } catch { return null; }
  return ENDPOINT_FAMILIES.find(([ds]) => ds.some((d) => host === d || host.endsWith(`.${d}`)))?.[1] ?? null;
}

export const ocArgs = (worktree, agent, model) =>
  ['run', '--dir', worktree, '--agent', agent, '--model', model.id, ...(model.variant ? ['--variant', model.variant] : [])];
