// [designed: T72a] Pure protocol contract; production activation belongs to T72.
// [confirmed: measurements/T72a] V2 envelopes/fields differ from the supported v1 CLI.
import path from 'node:path';
const fail = (what) => { throw new Error(`OpenCode protocol: ${what}`); };
const object = (v, name) => v && typeof v === 'object' && !Array.isArray(v) ? v : fail(`${name} must be an object`);
const array = (v, name) => Array.isArray(v) ? v : fail(`${name} must be an array`);
const string = (v, name) => typeof v === 'string' && v.length ? v : fail(`${name} must be a nonempty string`);
const number = (v, name) => typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : fail(`${name} must be nonnegative finite`);
export function majorProtocol(major) { if (major !== 1 && major !== 2) fail(`unsupported major ${major}`); return major; }
function directory(v) { string(v, 'directory'); if (!path.isAbsolute(v)) fail('directory must be absolute'); return path.normalize(v); }
function equal(a, b, label) { if (a !== b) fail(`${label} mismatch`); }
function ref(v) {
  object(v, 'model');
  return { providerID: string(v.providerID, 'providerID'), id: string(v.id, 'model id'), ...(v.variant === undefined ? {} : { variant: string(v.variant, 'variant') }) };
}
function identity(actual, expected) {
  const a = ref(actual); const e = ref(expected);
  equal(a.providerID, e.providerID, 'provider'); equal(a.id, e.id, 'model'); equal(a.variant, e.variant, 'effort'); return a;
}
export function command(major, operation, options = {}) {
  majorProtocol(major);
  const cwd = directory(options.directory);
  let args;
  switch (operation) {
    case 'models': args = major === 1 ? ['models', string(options.provider, 'provider'), '--verbose'] : ['api', '--standalone', 'model.list']; break;
    case 'agents': args = major === 1 ? ['agent', 'list'] : ['api', '--standalone', 'agent.list']; break;
    case 'list': args = ['session', 'list', ...(major === 2 ? ['--standalone'] : []), '--format', 'json']; break;
    case 'export': args = [...(major === 1 ? ['export'] : ['session', 'export', '--standalone']), string(options.sessionID, 'sessionID')]; break;
    case 'run': {
      const model = ref(options.model);
      const id = `${model.providerID}/${model.id}`;
      if (/[#\s]/.test(id) || model.variant && /[#\s]/.test(model.variant)) fail('ambiguous model reference');
      args = ['run', ...(major === 2 ? ['--standalone'] : ['--dir', cwd]), '--agent', string(options.agent, 'agent'), '--model', major === 2 && model.variant ? `${id}#${model.variant}` : id,
        ...(major === 1 && model.variant ? ['--variant', model.variant] : []),
        ...(options.sessionID ? ['--session', string(options.sessionID, 'sessionID')] : ['--title', string(options.title, 'title')]), string(options.prompt, 'prompt')];
      break;
    }
    case 'interrupt':
      if (major !== 2) fail('v1 has no supported interrupt command in this contract');
      // [designed: T72a] Cancellation must attach to the known execution owner, never a fresh standalone process.
      if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(options.server || '')) fail('interrupt requires owned loopback server');
      args = ['api', '--server', options.server, 'session.interrupt', '--param', `sessionID=${string(options.sessionID, 'sessionID')}`, '--data', '{}']; break;
    default: fail(`unknown operation ${operation}`);
  }
  return { cwd, args };
}
export function usage(v) {
  object(v, 'tokens'); object(v.cache, 'cache tokens');
  return { ...(v.total === undefined ? {} : { total: number(v.total, 'total tokens') }), input: number(v.input, 'input tokens'), output: number(v.output, 'output tokens'), reasoning: number(v.reasoning, 'reasoning tokens'), cache: { read: number(v.cache.read, 'cache read'), write: number(v.cache.write, 'cache write') } };
}
export function normalizeModels(major, record, expected) {
  majorProtocol(major); object(record, 'model catalogue');
  if (major === 2) equal(directory(record.location?.directory), directory(expected.directory), 'directory');
  const rows = major === 2 ? array(record.data, 'model catalogue data') : array(record.models, 'v1 parsed models');
  const matches = rows.filter((m) => m.providerID === expected.providerID && m.id === expected.id);
  if (matches.length !== 1) fail('selected model missing or ambiguous');
  const m = object(matches[0], 'model');
  if (m.enabled === false || major === 2 && m.enabled !== true) fail('selected model disabled');
  const variants = major === 2 ? array(m.variants, 'variants').map((v) => string(v.id, 'variant id')) : Object.keys(object(m.variants, 'v1 variants'));
  if (new Set(variants).size !== variants.length) fail('duplicate variant');
  if (expected.variant != null && !variants.includes(expected.variant)) fail('effort unavailable');
  return { providerID: m.providerID, id: m.id, modelID: string(m.modelID ?? m.id, 'modelID'), family: string(m.family, 'model family'), variants, enabled: m.enabled !== false };
}
export function normalizeAgents(major, record, expected) {
  majorProtocol(major); object(record, 'agents');
  if (major === 2) equal(directory(record.location?.directory), directory(expected.directory), 'directory');
  const rows = array(major === 2 ? record.data : record.agents, 'agents');
  const matches = rows.filter((a) => (major === 2 ? a.id : a.name) === expected.agent);
  if (matches.length !== 1) fail('selected agent missing or ambiguous');
  const a = matches[0]; if (a.hidden === true || a.disabled === true) fail('selected agent unavailable');
  if (!['all', 'primary'].includes(a.mode)) fail('agent is not primary capable');
  let permissions;
  if (major === 2) permissions = array(a.permissions, 'permissions').map(rule);
  else {
    permissions = [];
    for (const [action, setting] of Object.entries(object(a.permission, 'v1 permission'))) {
      if (typeof setting === 'string') permissions.push(rule({ action, resource: '*', effect: setting }));
      else for (const [resource, effect] of Object.entries(object(setting, 'v1 permission map'))) permissions.push(rule({ action, resource, effect }));
    }
  }
  return { id: expected.agent, name: string(a.name, 'agent name'), mode: a.mode, hidden: a.hidden ?? false, permissions, model: a.model === undefined ? null : ref(a.model), system: a.system ?? a.prompt ?? null };
}
function rule(r) {
  object(r, 'permission rule');
  if (!['allow', 'ask', 'deny'].includes(r.effect)) fail('invalid permission effect');
  return { action: string(r.action, 'action'), resource: string(r.resource, 'resource'), effect: r.effect };
}
// [designed: T72a] Expose ordered rules verbatim; matching/tool enforcement belongs to OpenCode.
export function normalizePermissions(major, record, sessionID) {
  majorProtocol(major);
  return array(major === 2 ? record.data : record, 'permission requests').map((p) => {
    object(p, 'permission request'); equal(p.sessionID, sessionID, 'permission session');
    return { id: string(p.id, 'permission id'), sessionID, action: string(major === 2 ? p.action : p.permission, 'permission action'), resources: array(major === 2 ? p.resources : p.patterns, 'permission resources').map((r) => string(r, 'permission resource')), source: p.source ?? null, metadata: p.metadata ?? null };
  });
}
function structuredError(v, major) {
  if (major === 1) return { type: 'LegacyToolError', message: string(v, 'tool error') };
  object(v, 'tool error'); return { ...v, type: string(v.type, 'error type'), message: string(v.message, 'error message') };
}
function tool(v, major) {
  const state = object(v.state, 'tool state');
  if (!['error', 'completed'].includes(state.status)) fail('incomplete tool outcome');
  const error = state.status === 'error' ? structuredError(state.error, major) : null;
  const rejected = Boolean(error && (['Permission.DeclinedError', 'Permission.BlockedError', 'Permission.CorrectedError'].includes(error.type) || /permission.*(?:reject|denied)|(?:reject|denied).*permission/i.test(error.type + ' ' + error.message)));
  if (state.status === 'completed') {
    if (major === 1 && typeof state.output !== 'string') fail('missing tool output');
    if (major === 2 && !array(state.content, 'tool content').length) fail('missing tool output');
  }
  return { id: string(major === 2 ? v.id : v.callID, 'tool id'), name: string(major === 2 ? v.name : v.tool, 'tool name'), status: state.status, input: object(state.input, 'tool input'), error, rejected, output: major === 2 ? state.content ?? [] : state.output ?? null, metadata: state.metadata ?? null };
}
export function normalizeSession(major, record, expected) {
  majorProtocol(major); object(record, 'export');
  const info = object(record.info, 'session info'); const messages = array(record.messages, 'messages');
  const sessionID = string(info.id, 'session id'); equal(sessionID, string(expected.sessionID, 'expected session id'), 'session');
  const dir = directory(major === 2 ? info.location?.directory : info.directory); equal(dir, directory(expected.directory), 'directory');
  equal(info.agent, string(expected.agent, 'expected agent'), 'agent');
  object(info.time, 'session time'); number(info.time.created, 'created'); number(info.time.updated, 'updated');
  if (info.outcome !== undefined && !['succeeded', 'failed', 'interrupted'].includes(info.outcome)) fail('unknown session outcome');
  const normalized = []; let assistantCount = 0; const ids = new Set();
  for (const message of messages) {
    object(message, 'message'); const meta = major === 2 ? message : object(message.info, 'message info');
    const type = major === 2 ? meta.type : meta.role;
    if (!['assistant', 'user', 'system', 'synthetic', 'skill', 'shell', 'compaction', 'agent-switched', 'model-switched', 'location-switched', 'idle'].includes(type)) fail('unknown message type');
    const id = string(meta.id, 'message id');
    if (ids.has(id)) fail('duplicate message id'); ids.add(id);
    if (major === 1) equal(meta.sessionID, sessionID, 'message session');
    if (type !== 'assistant') { normalized.push({ id, type, raw: structuredClone(message) }); continue; }
    assistantCount++;
    equal(meta.agent, expected.agent, 'message agent');
    const model = identity(major === 2 ? meta.model : { providerID: meta.providerID, id: meta.modelID, variant: meta.variant }, expected.model);
    object(meta.time, 'message time'); number(meta.time.created, 'message created'); number(meta.time.completed, 'message completion');
    if (!['stop', 'tool-calls'].includes(meta.finish)) fail('incomplete or failed assistant finish');
    const content = array(major === 2 ? message.content : message.parts, 'assistant content');
    const parts = content.map((part) => {
      object(part, 'content');
      if (major === 1) {
        if (part.sessionID !== undefined) equal(part.sessionID, sessionID, 'part session');
        if (part.messageID !== undefined) equal(part.messageID, id, 'part message');
        if (['step-start', 'step-finish', 'snapshot', 'patch', 'file', 'agent', 'retry', 'compaction', 'subtask'].includes(part.type)) {
          if (part.type === 'step-finish') { string(part.reason, 'step finish reason'); number(part.cost, 'step cost'); usage(part.tokens); }
          return structuredClone(part);
        }
      }
      if (part.type === 'tool') return { type: 'tool', ...tool(part, major) };
      if (part.type !== 'text' && part.type !== 'reasoning') fail('unknown assistant content');
      if (typeof part.text !== 'string') fail('malformed assistant text');
      return { type: part.type, text: part.text };
    });
    normalized.push({ id, type, agent: meta.agent, model, parts, cost: number(meta.cost, 'message cost'), tokens: usage(meta.tokens), finish: meta.finish, error: meta.error === undefined ? null : structuredClone(object(meta.error, 'assistant error')) });
  }
  const model = major === 2 ? identity(info.model, expected.model) : assistantCount ? ref(expected.model) : fail('v1 model identity unproven without assistant metadata');
  const assistants = normalized.filter((m) => m.type === 'assistant');
  return { major, sessionID, directory: dir, agent: info.agent, model, created: info.time.created, updated: info.time.updated,
    cost: major === 2 ? number(info.cost, 'session cost') : assistants.reduce((n, m) => n + m.cost, 0),
    tokens: major === 2 ? usage(info.tokens) : { ...(assistants.every((m) => m.tokens.total !== undefined) ? { total: assistants.reduce((sum, m) => sum + m.tokens.total, 0) } : {}), ...assistants.reduce((a, m) => ({ input: a.input + m.tokens.input, output: a.output + m.tokens.output, reasoning: a.reasoning + m.tokens.reasoning, cache: { read: a.cache.read + m.tokens.cache.read, write: a.cache.write + m.tokens.cache.write } }), { input: 0, output: 0, reasoning: 0, cache: { read: 0, write: 0 } }) },
    outcome: info.outcome ?? null, messages: normalized, assistantText: assistants.flatMap((m) => m.parts.filter((p) => p.type === 'text').map((p) => p.text)).join(''),
    rejected: assistants.some((m) => m.parts.some((p) => p.type === 'tool' && p.rejected)), completed: assistants.length > 0 && assistants.at(-1).finish === 'stop' && !assistants.some((m) => m.error) && ['assistant', 'idle'].includes(normalized.at(-1).type) && !['failed', 'interrupted'].includes(info.outcome) };
}
export function normalizeSessionList(major, record, directoryExpected) {
  majorProtocol(major);
  const rows = array(major === 2 && !Array.isArray(record) ? record.data : record, 'session list');
  return rows.map((s) => {
    const dir = directory(s.location?.directory ?? s.directory); equal(dir, directory(directoryExpected), 'directory');
    return { id: string(s.id, 'session id'), title: string(s.title, 'title'), directory: dir, created: number(s.time?.created ?? s.created, 'created'), updated: number(s.time?.updated ?? s.updated, 'updated') };
  });
}
// [confirmed: measurements/T72a/probe-20261017/events.sse] Native v2 events are JSON in SSE data frames.
export function normalizeEvents(major, text, expected) {
  if (majorProtocol(major) !== 2) fail('native SSE is a v2 contract');
  if (typeof text !== 'string' || !text.endsWith('\n\n')) fail('truncated SSE');
  return text.split('\n\n').filter((f) => f && !f.startsWith(':')).map((frame) => {
    const lines = frame.split('\n').filter((l) => l.startsWith('data: '));
    if (lines.length !== 1) fail('malformed SSE data frame');
    const event = JSON.parse(lines[0].slice(6)); object(event, 'event'); string(event.id, 'event id'); string(event.type, 'event type'); object(event.data, 'event data');
    if (event.type !== 'server.connected') {
      equal(event.data.sessionID, expected.sessionID, 'event session'); equal(directory(event.location?.directory), directory(expected.directory), 'event directory');
    }
    return event;
  });
}
