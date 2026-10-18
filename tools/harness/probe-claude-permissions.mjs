#!/usr/bin/env node
// [designed: T73] Synthetic LOOPBACK native enforcement fixture, never a model/provider-access trial.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { capture } from './lib/opencode-transport.mjs';
import { CLAUDE, claudeReviewArgs, sha } from './lib/claude-policy.mjs';
import { claudeCommand } from './lib/claude-workflow.mjs';
const ix = process.argv.indexOf('--out'); assert(ix > 0 && process.argv[ix + 1], '--out required');
const out = path.resolve(process.argv[ix + 1]); fs.mkdirSync(out, { recursive: true });
const root = fs.mkdtempSync(path.join(out, 'native-')); const cwd = path.join(root, 'work'); const config = path.join(root, 'empty-native-config');
for (const dir of [cwd, config, path.join(root, 'tmp')]) fs.mkdirSync(dir);
const archaeology = fs.realpathSync(path.resolve(process.argv[process.argv.indexOf('--archaeology') + 1]));
assert(process.argv.includes('--archaeology') && path.basename(archaeology) === 'goal2-archaeology');
const readFile = path.join(archaeology, '.gitignore'); assert(fs.statSync(readFile).isFile());
fs.writeFileSync(path.join(cwd, 'allowed.test.mjs'), "import test from 'node:test';import assert from 'node:assert/strict';test('native compound fixture',()=>assert.equal(2+2,4));\n", { flag: 'wx' });
fs.writeFileSync(path.join(cwd, 'isolated.py'), "import sys\nfrom pathlib import Path\nassert sys.flags.isolated == 1\nassert Path('allowed.test.mjs').is_file()\nprint('T73_ISOLATED_PYTHON_OK')\n", { flag: 'wx' });
const commands = ['node --test allowed.test.mjs && git diff --check', 'python3 -I isolated.py'];
const canary = 'git push T73-NO-REMOTE';
const tmpSentinel = path.join(fs.mkdtempSync('/tmp/goal2-t73-native-'), 'sentinel.txt'); fs.writeFileSync(tmpSentinel, 'T73_SYNTHETIC_TMP_READ\n', { flag: 'wx' });
const calls = [
 { id: 'toolu_t73_compound', name: 'Bash', input: { command: commands[0], description: 'Synthetic compound permission fixture' } },
 { id: 'toolu_t73_python', name: 'Bash', input: { command: commands[1], description: 'Synthetic isolated Python permission fixture' } },
 { id: 'toolu_t73_research', name: 'Read', input: { file_path: readFile } },
 { id: 'toolu_t73_tmp', name: 'Read', input: { file_path: tmpSentinel } },
 { id: 'toolu_t73_forbidden', name: 'Bash', input: { command: canary, description: 'Planned forbidden canary; must be denied' } },
];
const permission = { model: CLAUDE.model, effortLevel: CLAUDE.effort, permissions: { defaultMode: 'dontAsk', additionalDirectories: ['/tmp', archaeology], allow: ['Read', 'Grep', 'Glob', ...commands.flatMap(c => c.split(' && ')).map(c => `Bash(${c})`)], deny: ['Edit', 'Write', 'Agent', 'Bash(git push *)'] } };
const policy = { settings: permission, directories: ['/tmp', archaeology] };
const requestReceipts = []; let turns = 0; let fakeError;
const fake = http.createServer(async (request, response) => {
 try {
  assert.equal(request.socket.remoteAddress, '127.0.0.1'); assert(request.url.startsWith('/v1/messages'));
  let raw = ''; for await (const chunk of request) { raw += chunk; assert(raw.length < 4 * 1024 * 1024); }
  const body = JSON.parse(raw); assert.equal(body.model, CLAUDE.model); assert.equal(body.stream, true); assert(++turns <= 3, 'bounded synthetic turns');
  // Never retain headers/auth, full system prompt or arbitrary source content.
  requestReceipts.push({ turn: turns, path: request.url, model: body.model, messageCount: body.messages.length, toolResultIds: body.messages.flatMap(m => Array.isArray(m.content) ? m.content.filter(c => c.type === 'tool_result').map(c => c.tool_use_id) : []) });
  response.writeHead(200, { 'content-type': 'text/event-stream' });
  const event = (name, data) => response.write(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`);
  event('message_start', { type: 'message_start', message: { id: 'msg_t73_' + turns, type: 'message', role: 'assistant', model: CLAUDE.model, content: [], stop_reason: null, stop_sequence: null, usage: { input_tokens: 1, output_tokens: 0 } } });
  if (turns === 1) calls.forEach((c, index) => {
    event('content_block_start', { type: 'content_block_start', index, content_block: { type: 'tool_use', id: c.id, name: c.name, input: {} } });
    event('content_block_delta', { type: 'content_block_delta', index, delta: { type: 'input_json_delta', partial_json: JSON.stringify(c.input) } });
    event('content_block_stop', { type: 'content_block_stop', index });
  });
  else { event('content_block_start', { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } }); event('content_block_delta', { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'Synthetic native enforcement fixture complete.' } }); event('content_block_stop', { type: 'content_block_stop', index: 0 }); }
  event('message_delta', { type: 'message_delta', delta: { stop_reason: turns === 1 ? 'tool_use' : 'end_turn', stop_sequence: null }, usage: { output_tokens: 1 } });
  event('message_stop', { type: 'message_stop' }); response.end();
 } catch (error) { fakeError = error; response.writeHead(500); response.end('{"error":{"type":"fixture_error","message":"synthetic fixture refused"}}'); }
});
await new Promise(r => fake.listen(0, '127.0.0.1', r));
const endpoint = `http://127.0.0.1:${fake.address().port}`;
const env = { HOME: process.env.HOME, PATH: process.env.PATH, LANG: 'C.UTF-8', TMPDIR: path.join(root, 'tmp'), CLAUDE_CONFIG_DIR: config, ANTHROPIC_API_KEY: 'T73-SYNTHETIC-NOT-A-CREDENTIAL', ANTHROPIC_BASE_URL: endpoint, CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: '1', DISABLE_AUTOUPDATER: '1', DISABLE_TELEMETRY: '1', DISABLE_ERROR_REPORTING: '1', NO_COLOR: '1' };
const command = claudeCommand(); let run; const receipt = { kind: 'synthetic native enforcement; no external inference/provider-access proof', cwd, fixtureGitOwned: true, version: CLAUDE.version, binarySHA256: CLAUDE.binarySHA256, endpoint, configHomeFresh: true, realCredentialsForwarded: false, environmentNames: Object.keys(env), commands, plannedCanary: canary, permissionSHA256: sha(JSON.stringify(permission)) };
try {
 // [designed: T73] Fixture git repo has no remote; canary cannot publish even if enforcement regresses.
 const setup = await capture({ exe: 'git', prefix: [] }, ['init', '-q'], { env, cwd, timeoutMs: 3000 }); assert.equal(setup.code, 0);
 const remotes = await capture({ exe: 'git', prefix: [] }, ['remote', '-v'], { env, cwd, timeoutMs: 3000 }); assert.equal(remotes.code, 0); assert.equal(remotes.stdout, ''); receipt.fixtureGitRemotes = [];
 const args = claudeReviewArgs(policy, randomUUID(), 'Synthetic local protocol fixture: execute the scripted tool calls, then finish. No external inference.');
 receipt.argv = args;
 run = await capture(command, args, { env, cwd, timeoutMs: 45000 });
 receipt.ownedExit = run.code; receipt.timedOut = run.timedOut; receipt.stdoutSHA256 = sha(run.stdout); receipt.stderrSHA256 = sha(run.stderr); receipt.stderrBytes = Buffer.byteLength(run.stderr);
 assert.equal(run.code, 0, 'owned native fixture exit'); assert(!fakeError, 'loopback protocol accepted');
 const frames = run.stdout.trimEnd().split('\n').map(line => JSON.parse(line));
 const final = frames.find(f => f.type === 'result'); assert(final, 'complete synthetic native result');
 const outcomes = frames.filter(f => f.type === 'user').flatMap(f => f.message.content.filter(c => c.type === 'tool_result'));
 receipt.outcomes = outcomes.map(c => ({ id: c.tool_use_id, is_error: c.is_error ?? false, contentSHA256: sha(JSON.stringify(c.content)), isolatedPythonSentinel: String(c.content).includes('T73_ISOLATED_PYTHON_OK'), compoundTestPassed: String(c.content).includes('pass 1') }));
 for (const id of ['toolu_t73_compound', 'toolu_t73_python', 'toolu_t73_research', 'toolu_t73_tmp']) assert(outcomes.some(c => c.tool_use_id === id && c.is_error !== true && typeof c.content === 'string' && c.content.length > 0), `${id} actually succeeded`);
 assert(receipt.outcomes.find(c => c.id === 'toolu_t73_python').isolatedPythonSentinel, 'Python isolated interpreter executed');
 assert(receipt.outcomes.find(c => c.id === 'toolu_t73_compound').compoundTestPassed, 'compound test actually ran');
 assert(outcomes.some(c => c.tool_use_id === 'toolu_t73_forbidden' && c.is_error === true), 'forbidden canary denied');
 assert.equal(final.permission_denials.length, 1); assert.equal(final.permission_denials[0].tool_use_id, 'toolu_t73_forbidden');
 receipt.denials = final.permission_denials; receipt.syntheticUsage = final.usage; receipt.nativePolicyEnforcementPassed = true;
} catch (error) { receipt.nativePolicyEnforcementPassed = false; receipt.failure = error.code === 'ERR_ASSERTION' ? String(error.message).split('\n')[0] : error.name; process.exitCode = 1; }
finally {
 fake.closeAllConnections(); await new Promise(r => fake.close(r)); receipt.requests = requestReceipts; receipt.scriptSHA256 = sha(fs.readFileSync(new URL(import.meta.url))); receipt.argumentBuilderSHA256 = sha(fs.readFileSync(new URL('./lib/claude-policy.mjs', import.meta.url))); receipt.argumentBuilder = 'claudeReviewArgs shared with production; no masking option after directories';
 fs.writeFileSync(path.join(root, 'receipt.json'), JSON.stringify(receipt, null, 2) + '\n', { flag: 'wx' });
 console.log(JSON.stringify({ root, passed: receipt.nativePolicyEnforcementPassed, requests: turns, failure: receipt.failure }));
}
