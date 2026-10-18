// [designed: T73; confirmed: measurements/T73/preflight.md] Complete native stream, never console approval words.
import { CLAUDE, TOOLS, demand } from './claude-policy.mjs';
import { accountDoneWhen } from './chain.mjs';
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
// [confirmed: native2.1.292 source offsets 204884737, 219215522, 219222149;
// measurements/T73/native-progress-rework.json] Accept the observed advisory subset only.
const fields = (o, allowed) => o && typeof o === 'object' && !Array.isArray(o) && Object.keys(o).every(k => allowed.includes(k));
const nonnegative = n => Number.isFinite(n) && n >= 0;
const epoch = n => Number.isSafeInteger(n) && n >= 0;
function verifyAdvisory(f, calls, outcomes) {
  demand(typeof f.uuid === 'string' && /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i.test(f.uuid), 'advisory frame identity');
  if (f.type === 'rate_limit_event') {
    const r = f.rate_limit_info; const status = s => ['allowed', 'allowed_warning', 'rejected'].includes(s);
    demand(fields(f, ['type', 'rate_limit_info', 'uuid', 'session_id']) && fields(r, ['status', 'resetsAt', 'rateLimitType', 'overageStatus', 'overageResetsAt', 'isUsingOverage', 'unifiedWindows', 'utilization']) && status(r.status)
      && (r.resetsAt === undefined || epoch(r.resetsAt)) && (r.overageResetsAt === undefined || epoch(r.overageResetsAt))
      && (r.rateLimitType === undefined || ['five_hour', 'seven_day', 'seven_day_opus', 'seven_day_sonnet', 'seven_day_overage_included', 'overage'].includes(r.rateLimitType))
      && (r.overageStatus === undefined || status(r.overageStatus)) && (r.isUsingOverage === undefined || typeof r.isUsingOverage === 'boolean')
      && (r.utilization === undefined || nonnegative(r.utilization))
      && (r.unifiedWindows === undefined || (fields(r.unifiedWindows, ['five_hour', 'seven_day', 'seven_day_overage_included']) && Object.values(r.unifiedWindows).every(w => fields(w, ['utilization', 'resetsAt']) && nonnegative(w.utilization) && epoch(w.resetsAt)))), 'rate-limit shape');
  } else {
    demand(fields(f, ['type', 'tool_use_id', 'tool_name', 'parent_tool_use_id', 'elapsed_time_seconds', 'heartbeat', 'session_id', 'uuid']) && f.heartbeat === true && nonnegative(f.elapsed_time_seconds), 'heartbeat shape');
    const call = calls.get(f.parent_tool_use_id);
    demand(call && !outcomes.has(call.id) && call.name === f.tool_name && typeof f.tool_use_id === 'string' && f.tool_use_id.startsWith(call.id + '-heartbeat-') && /^\d+$/.test(f.tool_use_id.slice((call.id + '-heartbeat-').length)), 'heartbeat identity');
  }
}
export function verifyInit(frame, expected) {
  demand(frame?.type === 'system' && frame.subtype === 'init', 'missing init');
  demand(frame.session_id === expected.sessionID && frame.cwd === expected.cwd && frame.model === CLAUDE.model && frame.claude_code_version === CLAUDE.version, 'init identity');
  demand(Array.isArray(frame.tools) && same([...frame.tools].sort(), TOOLS) && frame.permissionMode === 'dontAsk' && frame.mcp_servers?.length === 0 && frame.slash_commands?.length === 0 && frame.skills?.length === 0 && frame.plugins?.every(p => p.path === 'builtin'), 'init toolset');
}
export function parseClaude(text, expected) {
  demand(text.endsWith('\n'), 'truncated stream');
  let frames; try { frames = text.trimEnd().split('\n').map(line => JSON.parse(line)); } catch { demand(false, 'malformed stream'); }
  const init = frames.filter(f => f.type === 'system' && f.subtype === 'init');
  demand(init.length === 1, 'missing/duplicate init'); verifyInit(init[0], expected);
  demand(frames.indexOf(init[0]) < frames.findIndex(f => f.type === 'assistant'), 'init order');
  const results = frames.filter(f => f.type === 'result'); demand(results.length === 1 && frames.at(-1) === results[0], 'missing/duplicate final');
  const final = results[0]; const calls = new Map(); const outcomes = new Map(); const assistants = [];
  for (const f of frames) {
    demand(f.session_id === expected.sessionID, 'frame session identity');
    if (f.type === 'assistant') {
      demand(f.message?.model === CLAUDE.model && Array.isArray(f.message.content) && !f.parent_tool_use_id, 'assistant identity');
      assistants.push(f);
      for (const c of f.message.content) if (c.type === 'tool_use') {
        demand(typeof c.id === 'string' && !calls.has(c.id) && TOOLS.includes(c.name), 'tool identity'); calls.set(c.id, c);
      }
    } else if (f.type === 'user') {
      demand(Array.isArray(f.message?.content), 'tool result shape');
      for (const c of f.message.content) {
        demand(c.type === 'tool_result' && calls.has(c.tool_use_id) && !outcomes.has(c.tool_use_id) && (c.is_error === undefined || typeof c.is_error === 'boolean'), 'tool result identity');
        // [confirmed: T73 native loopback receipt] Successful Read results omit optional is_error.
        outcomes.set(c.tool_use_id, { ...c, is_error: c.is_error ?? false, interrupted: f.tool_use_result?.interrupted === true });
      }
    } else if (f.type === 'rate_limit_event' || f.type === 'tool_progress') verifyAdvisory(f, calls, outcomes);
    else demand(f.type === 'system' || f.type === 'result', 'unknown native frame');
  }
  demand(calls.size === outcomes.size, 'unfinished tool calls');
  const denied = final.permission_denials; demand(Array.isArray(denied), 'missing denials');
  const planned = new Set(expected.deniedCanaries ?? []); const observedCanaries = new Set();
  for (const [id, c] of calls) {
    const outcome = outcomes.get(id); const isCanary = c.name === 'Bash' && planned.has(c.input?.command);
    const rejection = denied.find(d => d.tool_use_id === id);
    if (isCanary) {
      demand(rejection?.tool_name === c.name && rejection.tool_input?.command === c.input.command && outcome.is_error, 'canary not denied');
      observedCanaries.add(c.input.command);
    } else demand(!outcome.is_error && !outcome.interrupted && !rejection, 'required tool denied/failed');
  }
  demand(denied.every(d => calls.has(d.tool_use_id) && calls.get(d.tool_use_id).name === 'Bash' && planned.has(calls.get(d.tool_use_id).input?.command)), 'unaccounted permission denial');
  demand(observedCanaries.size === planned.size, 'missing denied canary');
  demand(final.subtype === 'success' && final.is_error === false && final.terminal_reason === 'completed' && final.stop_reason === 'end_turn' && typeof final.result === 'string' && final.result.trim(), 'incomplete final');
  const last = assistants.at(-1)?.message;
  // [confirmed: retained native2.1.292 stream] Assistant stop_reason is null; native result owns completion.
  demand(last && !last.content.some(c => c.type === 'tool_use') && last.content.filter(c => c.type === 'text').map(c => c.text).join('') === final.result, 'complete final recovery');
  const usage = final.modelUsage;
  const count = n => Number.isSafeInteger(n) && n >= 0;
  demand(usage && Object.keys(usage).length === 1 && usage[CLAUDE.model]?.canonicalModel === CLAUDE.model && usage[CLAUDE.model]?.provider === 'firstParty', 'final model/provider identity');
  demand(Number.isFinite(final.total_cost_usd) && final.total_cost_usd >= 0 && Number.isFinite(final.duration_ms) && final.duration_ms >= 0 && final.usage && Object.values(usage).every(u => Number.isFinite(u.costUSD) && u.costUSD >= 0), 'usage accounting');
  demand(['input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'].every(k => count(final.usage[k])) && Object.values(usage).every(u => ['inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens'].every(k => count(u[k]))) && Math.abs(usage[CLAUDE.model].costUSD - final.total_cost_usd) < 1e-8 && count(final.num_turns), 'native token/cost accounting');
  // [designed: T73] Native command outcomes, exact tree proof and explicit final scope are all required.
  const successful = [...calls].filter(([id, c]) => c.name === 'Bash' && !outcomes.get(id).is_error).map(([, c]) => c.input?.command);
  demand(expected.commands.every(c => successful.includes(c)), 'required command coverage');
  demand(expected.negativeControl && successful.includes(expected.negativeControl), 'negative control coverage');
  const headProof = [...calls].find(([id, c]) => c.name === 'Bash' && c.input?.command === 'git rev-parse HEAD' && String(outcomes.get(id).content).trim() === expected.head);
  demand(headProof, 'executed head identity');
  const identity = `IDENTITY PR ${expected.pr} HEAD ${expected.head} BASE ${expected.base}`;
  demand(final.result.split('\n').includes(identity), 'review PR/head/base identity');
  const dw = accountDoneWhen(final.result, expected.doneWhen);
  demand(expected.doneWhen > 0 && Object.values(dw).every(a => a.length === 0), 'Done-when coverage');
  demand(expected.inventory.length > 0 && expected.inventory.every(item => final.result.split('\n').some(line => line.startsWith(`COVER ${item.id}: audited `) && line.slice(`COVER ${item.id}: audited `.length).trim())), 'changed-file scope coverage');
  demand(final.result.split('\n').some(line => line.startsWith('CONTROL: ran ') && line.includes(expected.negativeControl) && /(?:→|->)\s*\S/.test(line)), 'substantive control accounting');
  return { reviewText: final.result, init: init[0], calls: [...calls.values()], denials: denied, usage: final.usage, modelUsage: usage, cost: final.total_cost_usd, durationMs: final.duration_ms };
}
