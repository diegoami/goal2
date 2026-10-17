#!/usr/bin/env node
// [designed: T72 rework1] Deterministic LOOPBACK provider drives real native tools; never contacts a model provider.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import assert from 'node:assert/strict';
import { randomBytes } from 'node:crypto';
import { resolveOpenCode, runOpenCodeWatched } from './lib/opencode.mjs';
import { hash, privateHome, startPrivateServer, settledCatalogue } from './lib/opencode-transport.mjs';
import { reviewerPolicy, trustedReviewEnv, verifyReviewer } from './lib/opencode-policy.mjs';

const index = process.argv.indexOf('--out');
assert(index > 0 && process.argv[index + 1], '--out required');
const out = path.resolve(process.argv[index + 1]);
fs.mkdirSync(out, { recursive: true });
const root = fs.mkdtempSync(path.join(out, 'native-'));
const work = path.join(root, 'work');
const tmp = path.join(root, 'tmp');
const config = path.join(root, 'config', 'opencode');
for (const directory of [work, tmp, config]) fs.mkdirSync(directory, { recursive: true });
const save = (name, value) => fs.writeFileSync(path.join(root, name), JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
fs.writeFileSync(path.join(work, 'inside.txt'), 'INSIDE_SENTINEL\n');
// [designed: T72] Retain this uniquely owned tiny sentinel; never delete user temp files.
const tmpFile = '/tmp/T72-guard-' + randomBytes(8).toString('hex') + '.txt';
fs.writeFileSync(tmpFile, 'TMP_SENTINEL\n', { flag: 'wx' });
const researchFile = path.join(process.env.HOME, 'projects/goal2-archaeology/.gitignore');
const active = process.argv.includes('--active-cancel');
const external = ['external-proc-metadata', 'external-cat', 'external-quoted', 'external-nested', 'external-relative'];
const calls = active ? [{
  id: 'active-cancel', timeout: 0,
  command: process.execPath + ' -e ' + JSON.stringify("require('node:fs').writeFileSync('active.pid',String(process.pid));setInterval(()=>{},1000)"),
}] : [
  { id: external[0], command: 'cat /proc/self/comm' },
  { id: external[1], command: 'cat /etc/hostname' },
  { id: external[2], command: 'cat "/etc/hostname"' },
  { id: external[3], command: 'echo $(cat /etc/hostname)' },
  { id: external[4], command: 'cat ' + JSON.stringify(path.relative(work, '/etc/hostname')) },
  { id: 'inside-cat', command: 'cat inside.txt' },
  { id: 'tmp-cat', command: 'cat ' + JSON.stringify(tmpFile) },
  { id: 'research-cat', command: 'cat ' + JSON.stringify(researchFile) },
  { id: 'git-deny', command: 'git push T72-NO-REMOTE' },
];
const requests = [];
const responses = [];
let planned = false;
// [confirmed: pinned openai-compatible-chat/OpenAIChat source hashes] Native protocol uses this SSE route/schema.
const fake = http.createServer(async (request, response) => {
  try {
    assert.equal(request.socket.remoteAddress, '127.0.0.1');
    assert.equal(request.url, '/v1/chat/completions');
    let raw = '';
    for await (const chunk of request) raw += chunk;
    const body = JSON.parse(raw);
    assert.equal(body.model, 'guard');
    requests.push(body);
    const toolCall = Array.isArray(body.tools) && body.tools.length > 0 && !planned;
    if (toolCall) planned = true;
    const delta = toolCall ? {
      tool_calls: calls.map((call, number) => ({
        index: number, id: call.id, type: 'function',
        function: { name: 'shell', arguments: JSON.stringify({ command: call.command, timeout: call.timeout ?? 2000 }) },
      })),
    } : { content: 'Deterministic loopback probe complete.' };
    const chunks = [
      { id: 'fake', choices: [{ index: 0, delta, finish_reason: null }] },
      { id: 'fake', choices: [{ index: 0, delta: {}, finish_reason: toolCall ? 'tool_calls' : 'stop' }],
        usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 } },
    ];
    responses.push(chunks);
    response.writeHead(200, { 'content-type': 'text/event-stream' });
    for (const chunk of chunks) response.write('data: ' + JSON.stringify(chunk) + '\n\n');
    response.end('data: [DONE]\n\n');
  } catch (error) {
    response.writeHead(500);
    response.end(JSON.stringify({ error: { message: error.message } }));
  }
});
await new Promise(resolve => fake.listen(0, '127.0.0.1', resolve));
const provider = {
  shell: '/bin/sh', providers: { 't72-loopback': {
    name: 'T72 nonbilling deterministic fake', package: '@opencode/ai/providers/openai-compatible',
    settings: { baseURL: `http://127.0.0.1:${fake.address().port}/v1`, apiKey: 'T72-FAKE-NOT-A-CREDENTIAL' },
    models: { guard: {
      name: 'Deterministic fake', family: 'minimax', capabilities: { tools: true, input: ['text'], output: ['text'] },
      cost: { input: 0, output: 0 }, limit: { context: 100000, output: 4096 },
    } },
  } },
};
fs.writeFileSync(path.join(config, 'opencode.json'), JSON.stringify(provider, null, 2));
const env = { ...process.env, TMPDIR: tmp, XDG_CONFIG_HOME: path.dirname(config), HARNESS_OPENCODE_HOME: path.join(root, 'runtime') };
const command = resolveOpenCode();
let unrelated;
let sentinel;
let before;
let receipt;
let outcome;
try {
  if (active) {
    const policy = reviewerPolicy(new URL('../../.opencode/agents/reviewer.md', import.meta.url));
    const home = privateHome(env);
    unrelated = await startPrivateServer(command, { env: trustedReviewEnv(home.env, policy), cwd: work });
    await settledCatalogue(unrelated, {
      model: { id: 't72-loopback/guard', family: 'minimax', variant: 'medium' }, agent: 'reviewer',
      verifyAgent: profile => verifyReviewer(profile, policy, 'reviewer'),
    });
    sentinel = (await unrelated.request('/api/session', { body: {
      title: 'T72-unrelated-empty', agent: 'reviewer', model: { id: 'guard', providerID: 't72-loopback', variant: 'medium' },
      location: { directory: work },
    } })).data;
    before = await unrelated.request('/api/session/' + sentinel.id);
  }
  try {
    await runOpenCodeWatched({
      opencode: command, args: ['run'], model: { id: 't72-loopback/guard', family: 'minimax', variant: 'medium' },
      agent: 'reviewer', agentFile: new URL('../../.opencode/agents/reviewer.md', import.meta.url),
      prompt: 'Only deterministic loopback fake provider may respond; planned shell tool permission probe.',
      workDir: work, title: 'T72-native-guard', startupTimeoutMs: 30000, totalTimeoutMs: 60000,
      idleTimeoutMs: active ? 1500 : 15000, pollMs: 100, logDir: path.join(root, 'receipts'), env,
      log: line => console.log(line),
    });
    throw Error('external operand probe unexpectedly succeeded');
  } catch (error) {
    if (error.manifest) receipt = JSON.parse(fs.readFileSync(error.manifest));
    outcome = { reason: error.reason, message: error.message };
  }
  save('outcome.json', outcome);
  save('requests.json', requests);
  save('responses.json', responses);
  assert(receipt, 'retained native receipt required');
  assert(fs.existsSync(receipt.files['export.json']), outcome.message);
  const exported = JSON.parse(fs.readFileSync(receipt.files['export.json']));
  const tools = exported.messages.filter(message => message.type === 'assistant').flatMap(message => message.content).filter(part => part.type === 'tool');
  save('tool-outcomes.json', tools);
  console.log(JSON.stringify({ root, outcome, tools: tools.map(tool => ({ id: tool.id, status: tool.state.status, error: tool.state.error })) }));
  if (active) {
    assert.equal(outcome.reason, 'idle');
    const pid = Number(fs.readFileSync(path.join(work, 'active.pid'), 'utf8'));
    const stat = '/proc/' + pid + '/stat';
    assert(!fs.existsSync(stat) || fs.readFileSync(stat, 'utf8').split(' ')[2] === 'Z', 'active native tool worker must terminate');
    assert.equal(receipt.interrupt?.interrupted, true, 'native execution must actually interrupt');
    const after = await unrelated.request('/api/session/' + sentinel.id);
    assert.deepEqual(after, before, 'foreign same-DB session must survive');
    save('active-cancellation.json', { workerPID: pid, terminated: true, interrupt: receipt.interrupt, unrelatedBefore: before, unrelatedAfter: after });
  } else {
    assert.equal(outcome.reason, 'permission-rejected');
    for (const id of [...external, 'git-deny']) assert.equal(tools.find(tool => tool.id === id)?.state.status, 'error', id + ' must reject');
    for (const id of ['inside-cat', 'tmp-cat', 'research-cat']) assert.equal(tools.find(tool => tool.id === id)?.state.status, 'completed', id + ' must run');
    for (const id of external) assert.equal(tools.find(tool => tool.id === id).state.error.type, 'permission.rejected');
    const text = id => tools.find(tool => tool.id === id).state.content.filter(part => part.type === 'text').map(part => part.text).join('');
    assert.equal(text('inside-cat'), 'INSIDE_SENTINEL\n');
    assert.equal(text('tmp-cat'), 'TMP_SENTINEL\n');
    assert.equal(text('research-cat'), fs.readFileSync(researchFile, 'utf8'));
    for (const tool of tools.filter(tool => external.includes(tool.id))) assert(!tool.state.content?.length, 'rejected external tool cannot contain external sentinel data');
  }
  const shellEvidence = fs.readFileSync(receipt.files['shell-guard.jsonl'], 'utf8').trim().split('\n').map(JSON.parse);
  assert(shellEvidence.length > 0 && shellEvidence.every(event => event.shell === '/bin/sh' && event.grammar === 'bash'), 'scanner must observe the configured actual native shell');
  assert.equal(receipt.usage.cost, 0);
  assert.equal(receipt.usage.tokens.input, 0);
  assert.equal(receipt.usage.tokens.output, 0);
  save('result.json', {
    classification: 'Actual native2 dispatch with deterministic loopback provider; zero provider billing; fake-reported zero tokens are simulated',
    externalNetworkModelCalls: 0, requests: requests.length, receipt: receipt.files['run.json'],
    binarySHA256: receipt.binarySHA256, probeSHA256: hash(fs.readFileSync(new URL(import.meta.url))), calls: calls.map(call => call.id), passed: true,
  });
} finally {
  if (unrelated) save('unrelated-shutdown.json', await unrelated.stop());
  await new Promise(resolve => fake.close(resolve));
}
console.log('Native guard nonbilling proof passed: ' + root);
