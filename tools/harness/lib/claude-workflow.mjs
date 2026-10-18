// [designed: T73] Separate bounded model-free control lease; actual review has DEVNULL stdin.
import fs from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { StringDecoder } from 'node:string_decoder';
import { spawnOwned, killOwned } from './opencode-transport.mjs';
import { CLAUDE, ClaudeError, claudeArgs, claudeEnv, demand, sha, reviewPolicy, selectClaude, verifyRules, verifySettings } from './claude-policy.mjs';
import { parseClaude, verifyInit } from './claude-protocol.mjs';
import { localGit, pinnedScope } from './claude-scope.mjs';
// [designed: T73] Only an exact nonbilling simulator in a native Node test may replace the audited executable.
const STUB_SHA256 = 'b4318112fa2e8400d4f8521d281fc733039657a12ac08dd07940f5a6dec02749';
export function claudeCommand(command) {
  const file = command?.prefix?.[0];
  if (command?.simulator === true) {
    demand(process.env.NODE_TEST_CONTEXT && command.exe === process.execPath && command.prefix.length === 1 && sha(fs.readFileSync(file)) === STUB_SHA256, 'simulator identity');
    return command;
  }
  const exe = fs.realpathSync(command?.exe ?? path.join(process.env.HOME, '.local/bin/claude'));
  demand(!command?.prefix?.length && sha(fs.readFileSync(exe)) === CLAUDE.binarySHA256, 'binary identity');
  return { exe, prefix: [] };
}
function ownedRun(command, args, { cwd, env, input, files, frame, startupTimeoutMs, idleTimeoutMs, totalTimeoutMs, signal, log = () => {} }) {
  return new Promise((resolve, reject) => {
    const decoder = new StringDecoder('utf8');
    let child; let pending = ''; let started = false; let failure; let done = false; let last = Date.now(); let bytes = 0;
    const start = Date.now(); const sums = { stdout: [], stderr: [] }; const fds = {};
    if (files) for (const name of ['stdout', 'stderr']) fds[name] = fs.openSync(files[name], 'wx');
    const close = () => { for (const fd of Object.values(fds)) fs.closeSync(fd); };
    const finish = (code) => { if (done) return; done = true; clearInterval(timer); signal?.removeEventListener('abort', abort); killOwned(child); close();
      const r = { exitCode: code, pid: child?.pid, durationMs: Date.now() - start, streams: Object.fromEntries(Object.entries(sums).map(([k, chunks]) => [k, Buffer.concat(chunks).toString('utf8')])) };
      if (failure) { const error = new ClaudeError(failure); Object.assign(error, { run: r }); reject(error); } else resolve(r);
    };
    const stop = reason => { if (failure) return; failure = reason; child?.stdin?.destroy(); killOwned(child); setTimeout(() => { child?.stdout?.destroy(); child?.stderr?.destroy(); finish(128); }, 300).unref(); };
    const abort = () => stop('cancelled');
    const timer = setInterval(() => { const now = Date.now(); if (!started && now - start > startupTimeoutMs) stop('startup deadline'); else if (now - start > totalTimeoutMs) stop('total deadline'); else if (idleTimeoutMs > 0 && now - last > idleTimeoutMs) stop('idle deadline'); }, 10);
    try {
      child = spawnOwned(command, args, { cwd, env, stdio: [input ? 'pipe' : 'ignore', 'pipe', 'pipe'] });
      child.stdin?.on('error', () => {});
      signal?.addEventListener('abort', abort, { once: true }); if (signal?.aborted) abort();
      for (const name of ['stdout', 'stderr']) child[name].on('data', chunk => {
        last = Date.now(); bytes += chunk.length;
        if (bytes > 128 * 1024 * 1024) { stop('output limit'); return; }
        sums[name].push(chunk); if (files) fs.writeSync(fds[name], chunk);
        if (name !== 'stdout') return;
        pending += decoder.write(chunk);
        while (pending.includes('\n')) {
          const i = pending.indexOf('\n'); const line = pending.slice(0, i); pending = pending.slice(i + 1);
          if (failure) continue;
          try { const event = JSON.parse(line); const ready = frame(event, child); if (ready && !started) { started = true; log(`session ready (${input ? 'model-free control lease' : 'closed review input'})`); } }
          catch (e) { stop(e instanceof ClaudeError ? e.reason : 'malformed native stream'); }
        }
      });
      child.on('error', () => stop('owned spawn')); child.on('close', (code) => finish(code));
      if (input) { for (const request of input) child.stdin.write(JSON.stringify(request) + '\n'); }
    } catch { stop('owned spawn'); }
  });
}
export async function projectClaude({ command, policy, cwd, env, sessionID, startupTimeoutMs = 180000, idleTimeoutMs = 600000, totalTimeoutMs = 3600000, signal, log }) {
  const requests = ['initialize', 'get_settings', 'list_permission_rules', 'get_hooks_listing']; const replies = new Map(); let projection;
  let run;
  try { run = await ownedRun(command, claudeArgs(policy, sessionID, { projection: true }), { cwd, env, startupTimeoutMs, idleTimeoutMs, totalTimeoutMs, signal, log,
    input: requests.map(subtype => ({ type: 'control_request', request_id: `projection-${subtype}`, request: { subtype } })),
    frame(event, child) {
      demand(event.type === 'control_response' || event.type === 'system', 'model-free projection generated a message');
      if (event.type !== 'control_response') return false;
      const r = event.response; const id = r?.request_id?.replace(/^projection-/, '');
      demand(requests.includes(id) && !replies.has(id) && r.subtype === 'success', 'projection response'); replies.set(id, r.response);
      if (replies.size !== requests.length) return false;
      const account = replies.get('initialize')?.account;
      demand(account?.apiProvider === 'firstParty', 'native account provider');
      projection = { sessionID, account: { apiProvider: account.apiProvider }, settings: verifySettings(replies.get('get_settings'), policy), rules: verifyRules(replies.get('list_permission_rules'), policy), hooksSHA256: sha(JSON.stringify(replies.get('get_hooks_listing'))) };
      child.stdin.end(); return true;
    } }); } catch (error) { throw new ClaudeError(error instanceof ClaudeError ? error.reason : 'model-free projection'); }
  // [designed: T73] Raw settings/account/env/hook values stay in memory, even on error.
  demand(run.exitCode === 0 && projection, 'incomplete model-free projection');
  return { ...projection, exitCode: run.exitCode, pid: run.pid, durationMs: run.durationMs, stdin: 'owned pipe lease closed after read-only responses', stdoutSHA256: sha(run.streams.stdout), stderrSHA256: sha(run.streams.stderr) };
}
export async function runClaudeReview({ command: chosen, model, policyFile, workDir, reviewedHead, reviewBase, reviewPR, prompt, header, doneWhen, negativeControl, deniedCanaries = [], sessionID = randomUUID(), projectionSessionID = randomUUID(), logDir, env: inherited = process.env, startupTimeoutMs = 180000, idleTimeoutMs = 600000, totalTimeoutMs = 3600000, signal, log = () => {} }) {
  selectClaude(model); const command = claudeCommand(chosen); const cwd = fs.realpathSync(workDir); const policy = reviewPolicy(policyFile, cwd);
  demand(policy.commands.includes(negativeControl) && policy.commands.includes('git rev-parse HEAD'), 'required control/tree commands');
  demand(deniedCanaries.every(c => typeof c === 'string' && /^git (?:push|merge|stash|reset|restore|checkout|worktree)\b/.test(c) && !policy.commands.includes(c)), 'denied canary selection');
  demand(sessionID !== projectionSessionID, 'distinct owned sessions');
  const parent = logDir ?? path.join(cwd, '.cache'); fs.mkdirSync(parent, { recursive: true });
  const directory = fs.mkdtempSync(path.join(parent, 'claude-review-'));
  const files = Object.fromEntries(['stdout', 'stderr', 'final', 'brief', 'projection'].map(k => [k, path.join(directory, k + ({ stdout: '.jsonl', stderr: '.txt', projection: '.json', final: '.txt', brief: '.md' }[k]))]));
  const manifestFile = path.join(directory, 'run.json'); const started = Date.now();
  const manifest = { backend: 'claude', sessionID, projectionSessionID, reviewedHead, reviewBase, reviewPR, directory: cwd, policySHA256: policy.sourceSHA256, binarySHA256: command.simulator ? STUB_SHA256 : CLAUDE.binarySHA256, sources: Object.fromEntries(['claude-policy.mjs', 'claude-protocol.mjs', 'claude-scope.mjs', 'claude-workflow.mjs', '../review.mjs'].map(n => [n, sha(fs.readFileSync(new URL(n, import.meta.url)))])), files, phase: 'preflight', started, redactions: [], limits: 'Native startup policy hooks are respected; projection is point-in-time and does not freeze native policy refresh. No OS jail.' };
  const save = () => { manifest.hashes = Object.fromEntries(Object.entries(files).filter(([, f]) => fs.existsSync(f)).map(([k, f]) => [k, sha(fs.readFileSync(f))])); fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + '\n'); };
  save();
  try {
    const scope = pinnedScope({ cwd, base: reviewBase, head: reviewedHead, pr: reviewPR, directory });
    manifest.scope = scope; files.scope = path.join(directory, 'scope.json');
    for (const c of scope.chunks) files[c.name] = path.join(directory, c.name);
    const scopeLines = scope.inventory.map(i => `${i.id}: ${JSON.stringify(i)}`).join('\n');
    const brief = `${prompt}\n\nTRUSTED LOCAL REVIEW EVIDENCE\n${scopeLines}\nRead every complete diff chunk and scope.json in ${directory}.\nPrint exactly: IDENTITY PR ${reviewPR} HEAD ${reviewedHead} BASE ${reviewBase}\nFor every inventory ID print COVER <ID>: audited <concrete scope and result>.\nRun all required commands exactly (and identify each DW with ran command -> result):\n${policy.commands.join('\n')}\nRun substantive negative control: ${negativeControl}\nPrint CONTROL: ran ${negativeControl} -> <observed result>.\n${deniedCanaries.length ? `Planned forbidden canaries must be denied; do not retry or perform their actions: ${JSON.stringify(deniedCanaries)}. All other denials block acceptance.` : 'Any permission denial blocks acceptance.'}\nYour complete final must begin ${header}, use standard verdict/DW findings format and end with its verdict. Never post or merge.\n`;
    fs.writeFileSync(files.brief, brief, { flag: 'wx' });
    const evidence = Object.fromEntries(Object.entries(files).filter(([, f]) => fs.existsSync(f)).map(([k, f]) => [k, sha(fs.readFileSync(f))]));
    manifest.evidenceSHA256 = evidence;
    const env = claudeEnv(inherited, cwd);
    // [designed: T73] Simulator knobs cannot reach the native command/environment.
    if (command.simulator) for (const k of ['T73_STUB_MODE', 'T73_STUB_SCOPE', 'T73_STUB_TRACE']) if (inherited[k]) env[k] = inherited[k];
    const projection = await projectClaude({ command, policy, cwd, env, sessionID: projectionSessionID, startupTimeoutMs, idleTimeoutMs, totalTimeoutMs, signal, log });
    fs.writeFileSync(files.projection, JSON.stringify(projection, null, 2) + '\n', { flag: 'wx' });
    demand(sha(fs.readFileSync(policy.file)) === policy.sourceSHA256 && localGit(cwd, ['rev-parse', 'HEAD']).trim() === reviewedHead && !localGit(cwd, ['status', '--porcelain', '--untracked-files=no']).trim(), 'policy/head drift');
    claudeCommand(command); manifest.phase = 'running'; save(); log(`Claude review session ${sessionID}; retained ${manifestFile}`);
    const expected = { sessionID, cwd, head: reviewedHead, base: reviewBase, pr: reviewPR, inventory: scope.inventory, commands: policy.commands, negativeControl, deniedCanaries, doneWhen };
    const run = await ownedRun(command, [...claudeArgs(policy, sessionID), `Read and follow the entire trusted review brief at ${files.brief}.`], { cwd, env, files, startupTimeoutMs, idleTimeoutMs, totalTimeoutMs: Math.max(1, totalTimeoutMs - (Date.now() - started)), signal, log,
      frame(event) { if (event.type === 'system' && event.subtype === 'init') { verifyInit(event, expected); return true; } return false; } });
    manifest.owned = { pid: run.pid, exitCode: run.exitCode, durationMs: run.durationMs, stdin: 'DEVNULL' };
    const recovered = run.streams.stdout.trimEnd().split('\n').flatMap(line => { try { const r = JSON.parse(line); return r.type === 'result' && typeof r.result === 'string' ? [r.result] : []; } catch { return []; } });
    if (recovered.length) fs.writeFileSync(files.final, recovered.at(-1), { flag: 'wx' });
    demand(run.exitCode === 0, 'nonzero review exit');
    // [designed: T73] Complete native result and final assistant must agree; partial output is retained, never resumed for formatting.
    const parsed = parseClaude(fs.readFileSync(files.stdout, 'utf8'), expected);
    demand(fs.readFileSync(files.final, 'utf8') === parsed.reviewText, 'retained complete final');
    demand(sha(fs.readFileSync(policy.file)) === policy.sourceSHA256 && localGit(cwd, ['rev-parse', 'HEAD']).trim() === reviewedHead && !localGit(cwd, ['status', '--porcelain', '--untracked-files=no']).trim(), 'post-review policy/head drift');
    demand(Object.entries(evidence).every(([k, hash]) => sha(fs.readFileSync(files[k])) === hash), 'review evidence drift');
    manifest.phase = 'complete'; manifest.usage = parsed.usage; manifest.modelUsage = parsed.modelUsage; manifest.cost = parsed.cost; manifest.denials = parsed.denials; save();
    return { ...parsed, exitCode: run.exitCode, manifest: manifestFile, sessionID };
  } catch (error) {
    manifest.phase = 'failed'; manifest.failure = error instanceof ClaudeError ? error.reason : 'infrastructure';
    // Never persist exception text/raw projection replies: native config may carry credentials.
    if (error.run && manifest.phase !== 'preflight' && fs.existsSync(files.stdout)) manifest.owned = { pid: error.run.pid, exitCode: error.run.exitCode, durationMs: error.run.durationMs, stdin: 'DEVNULL' };
    if (fs.existsSync(files.stdout) && !fs.existsSync(files.final)) {
      const recovered = fs.readFileSync(files.stdout, 'utf8').split('\n').flatMap(line => { try { const f = JSON.parse(line); return f.type === 'result' && typeof f.result === 'string' ? [f.result] : []; } catch { return []; } });
      if (recovered.length) fs.writeFileSync(files.final, recovered.at(-1), { flag: 'wx' });
    }
    save(); const safe = new ClaudeError(manifest.failure); safe.manifest = manifestFile; throw safe;
  }
}
