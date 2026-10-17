// [designed: T72] Nonbilling actual-shaped protocol simulator, deliberately no provider access.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
const args = process.argv.slice(2); const mode = process.env.STUB_MODE || 'complete';
const get = (key) => args[args.indexOf(key) + 1];
const trace = (what) => { if (process.env.STUB_TRACE) fs.appendFileSync(process.env.STUB_TRACE, JSON.stringify(what) + '\n'); };
trace({ args, cwd: process.cwd(), dataHome: process.env.XDG_DATA_HOME });
if (args[0] === '--version') { console.log(process.env.STUB_VERSION || 'opencode v2.0.28'); process.exit(0); }
if (process.env.STUB_VERSION?.startsWith('1.')) {
  const file = path.join(process.env.STUB_V1_DIR, 'v1.json');
  let records = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file)) : [];
  if (args[0] === 'run') {
    if (!args.includes('--dir') || args.includes('--standalone') || args.includes('--server')) process.exit(2);
    const raw = JSON.parse(fs.readFileSync(new URL('../fixtures/opencode/v1-synthetic-export.json', import.meta.url)));
    raw.info.id = get('--session') || `ses_v1_${Date.now()}`; raw.info.directory = process.cwd(); raw.info.title = get('--title'); raw.info.time = { created: Date.now(), updated: Date.now() };
    raw.info.agent = get('--agent'); const msg = raw.messages[0]; msg.info.sessionID = raw.info.id; msg.info.agent = raw.info.agent;
    msg.info.providerID = get('--model').split('/')[0]; msg.info.modelID = get('--model').split('/')[1]; msg.info.variant = get('--variant');
    msg.parts = msg.parts.filter((p) => mode === 'rejected' || p.callID !== 'call_rejected');
    const actual = JSON.parse(fs.readFileSync(new URL('../fixtures/opencode/v1-actual-metadata-step-projection.json', import.meta.url)));
    msg.parts.push(...actual.parts);
    for (const part of msg.parts) { part.sessionID = raw.info.id; part.messageID = msg.info.id; }
    if (mode === 'wrong-model') msg.info.modelID = 'foreign';
    if (mode === 'partial') msg.info.finish = 'tool-calls';
    records = records.filter((r) => r.info.id !== raw.info.id); records.push(raw); fs.writeFileSync(file, JSON.stringify(records)); console.log('volatile v1');
  } else if (args[0] === 'session') console.log(JSON.stringify(records.map((r) => ({ id: r.info.id, title: r.info.title, directory: r.info.directory, created: r.info.time.created, updated: r.info.time.updated }))));
  else if (args[0] === 'export') console.log(JSON.stringify(records.find((r) => r.info.id === args[1])));
  else if (args[0] === 'models') console.log('minimax/MiniMax-M3');
  else process.exit(2);
  process.exit(0);
}
if (args[0] === 'models') {
  if (!args.includes('--standalone')) process.exit(2);
  console.log('minimax/MiniMax-M3'); process.exit(0);
}
if (args[0] === 'session' && args[1] === 'export') {
  if (!args.includes('--standalone')) process.exit(2);
  const records = JSON.parse(fs.readFileSync(path.join(process.env.XDG_DATA_HOME, 'stub.json')));
  console.log(JSON.stringify(records.find((s) => s.info.id === args.at(-1)))); process.exit(0);
}
if (args[0] === 'serve') {
  if (!args.includes('--stdio') || get('--hostname') !== '127.0.0.1' || get('--port') !== '0') throw Error('unowned launch');
  if (mode === 'startup') { process.stdin.resume(); process.stdin.on('end', () => process.exit(0)); }
  else {
    const db = path.join(process.env.XDG_DATA_HOME, 'stub.json');
    let sessions = fs.existsSync(db) ? JSON.parse(fs.readFileSync(db)) : [];
    const save = () => fs.writeFileSync(db, JSON.stringify(sessions));
    const tokens = { input: 10, output: 4, reasoning: 2, cache: { read: 3, write: 1 } };
    const envelope = (data) => ({ location: { directory: process.cwd() }, data });
    const server = http.createServer(async (req, res) => {
      let body = ''; for await (const b of req) body += b;
      if (body) body = JSON.parse(body);
      const url = new URL(req.url, 'http://localhost'); const sid = url.pathname.split('/')[3];
      let answer;
      const item = () => sessions.find((s) => s.info.id === sid);
      if (url.pathname === '/openapi.json') answer = { openapi: '3.1.0', info: { title: 'T72 synthetic stub', version: '2.0.28' }, paths: {} };
      else if (url.pathname === '/api/model') answer = envelope([{ id: 'MiniMax-M3', modelID: 'MiniMax-M3', providerID: 'minimax', family: mode === 'family' ? 'gpt-sol' : process.env.STUB_FAMILY || 'minimax', enabled: true, variants: mode === 'effort' ? [{ id: 'none' }] : [{ id: 'none' }, { id: 'thinking' }] }]);
      else if (url.pathname === '/api/agent') {
        const config = JSON.parse(process.env.OPENCODE_CONFIG_CONTENT || '{}');
        const agent = { id: 'reviewer', name: 'Reviewer', ...config.agents?.reviewer };
        if (mode === 'agent') agent.id = 'build';
        if (mode === 'policy') agent.permissions.push({ action: 'edit', resource: '*', effect: 'allow' });
        answer = envelope([agent]);
      } else if (url.pathname === '/api/session' && req.method === 'GET') answer = envelope(sessions.map((s) => s.info));
      else if (url.pathname === '/api/session') {
        const time = Date.now(); const info = { id: `ses_stub_${time}_${randomUUID().replaceAll('-', '')}`, ...body, time: { created: time, updated: time }, cost: 0, tokens: { input: 0, output: 0, reasoning: 0, cache: { read: 0, write: 0 } } };
        sessions.push({ info, messages: [] }); save(); answer = envelope(info);
      } else if (url.pathname.endsWith('/export')) {
        const record = sessions.find((s) => s.info.id === url.pathname.split('/')[4]);
        answer = envelope(structuredClone(record));
        if (mode === 'wrong-session') answer.data.info.id = 'ses_foreign';
        if (mode === 'wrong-directory') answer.data.info.location.directory = '/foreign';
        if (mode === 'wrong-model') answer.data.info.model.id = 'foreign';
        if (mode === 'wrong-agent') answer.data.info.agent = 'build';
        if (mode === 'wrong-effort') answer.data.info.model.variant = 'none';
        if (mode === 'malformed') answer.data.messages[0].content[0].text = null;
        if (mode === 'truncated') { res.end('{"data":'); return; }
      } else if (url.pathname.endsWith('/interrupt')) { trace({ interrupt: sid }); answer = { interrupted: mode === 'active' }; }
      else if (url.pathname.endsWith('/test-run')) {
        const record = item();
        if (!record || body.agent !== record.info.agent || body.model !== `${record.info.model.providerID}/${record.info.model.id}#${record.info.model.variant}` || body.directory !== record.info.location.directory) throw Error('client selection differs');
        trace({ generation: sid });
        if (mode === 'active') {
          const worker = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'inherit' }); worker.unref(); trace({ workerPID: worker.pid });
        }
        const template = JSON.parse(fs.readFileSync(new URL('../fixtures/opencode/v2-synthetic-export.json', import.meta.url)));
        const msg = template.messages[0]; msg.id += record.messages.length; msg.model = record.info.model; msg.agent = record.info.agent;
        msg.time = { created: Date.now(), completed: Date.now() };
        msg.content = mode === 'rejected' ? msg.content : msg.content.filter((p) => p.id !== 'call_rejected');
        msg.content.filter((p) => p.type === 'text')[0].text = 'Complete recovered final\n';
        if (process.env.STUB_FINAL) msg.content = [{ type: 'text', text: process.env.STUB_FINAL }, ...msg.content.filter((p) => p.type !== 'text')];
        record.messages.push(msg); record.info.cost = .002; record.info.tokens = tokens; record.info.time.updated = Date.now();
        if (mode === 'partial' || mode === 'active') msg.finish = 'tool-calls';
        if (mode === 'pending') record.messages.push({ id: 'pending', type: 'user', time: { created: Date.now() }, text: 'pending request' });
        save(); answer = envelope(true);
      } else answer = envelope(item()?.info);
      res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(answer));
    });
    server.listen(0, '127.0.0.1', () => console.log(JSON.stringify({ url: `http://127.0.0.1:${server.address().port}` })));
    process.stdin.resume(); process.stdin.on('end', () => server.close(() => process.exit(0)));
  }
} else if (args[0] === 'run') {
  if (!args.includes('--server') || args.includes('--variant') || args.includes('--dir') || args.includes('--standalone')) { console.error('old run command'); process.exit(2); }
  if (mode === 'idle' || mode === 'total') { setInterval(() => {}, 100); }
  else {
    await fetch(get('--server') + `/api/session/${get('--session')}/test-run`, { method: 'POST', body: JSON.stringify({ model: get('--model'), agent: get('--agent'), directory: process.cwd() }) });
    console.log('volatile output deliberately missing final');
    if (mode === 'progress') await new Promise((r) => setTimeout(r, 150));
    if (mode === 'active') setInterval(() => {}, 1000); else process.exit(mode === 'nonzero' ? 7 : 0);
  }
} else { console.error('unsupported old command'); process.exit(2); }
