// [designed: T73] Deterministic native-shape protocol simulator; never calls a provider.
import fs from 'node:fs';
import readline from 'node:readline';
import { spawn } from 'node:child_process';
const a = process.argv.slice(2); const get = key => a[a.indexOf(key) + 1];
const mode = process.env.T73_STUB_MODE ?? 'ok'; const emit = o => process.stdout.write(JSON.stringify(o) + '\n');
const fixture = JSON.parse(fs.readFileSync(new URL('../fixtures/claude/native-shape.json', import.meta.url)));
const session = get('--session-id');
if (process.env.T73_STUB_TRACE) fs.appendFileSync(process.env.T73_STUB_TRACE, JSON.stringify({ phase: a.includes('--input-format') ? 'projection' : 'generation', session, stdinTTY: !!process.stdin.isTTY }) + '\n');
if (a.includes('--input-format')) {
  const settings = JSON.parse(get('--settings'));
  for await (const line of readline.createInterface({ input: process.stdin })) {
    const q = JSON.parse(line); const sub = q.request.subtype; let response;
    if (sub === 'initialize') response = { account: { apiProvider: mode === 'provider' ? 'gateway' : 'firstParty', authTokenSource: 'SYNTHETIC-SECRET-MUST-NOT-BE-RETAINED' } };
    if (sub === 'get_settings') { response = { effective: structuredClone(settings), sources: [{ source: 'flagSettings', settings }], applied: { model: settings.model, effort: 'medium', advisor: null } }; if (mode === 'routing') response.effective.env = { ANTHROPIC_BASE_URL: 'https://proxy.invalid', ANTHROPIC_AUTH_TOKEN: 'SYNTHETIC-SECRET-MUST-NOT-BE-RETAINED' }; }
    if (sub === 'list_permission_rules') { response = { state: { rules: [...settings.permissions.allow.map(rule => ({ behavior: 'allow', source: 'flagSettings', rule })), ...settings.permissions.deny.map(rule => ({ behavior: 'deny', source: 'flagSettings', rule }))] } }; if (mode === 'permissions') response.state.rules.push({ behavior: 'allow', source: 'policySettings', rule: 'Bash(*)' }); }
    if (sub === 'get_hooks_listing') response = { groups: [] };
    emit({ type: 'control_response', response: { subtype: 'success', request_id: q.request_id, response } });
  }
  process.exit(0);
}
const scope = JSON.parse(fs.readFileSync(process.env.T73_STUB_SCOPE));
const settings = JSON.parse(get('--settings'));
const init = { ...fixture.init, session_id: session, cwd: process.cwd() };
if (mode === 'startup') { setInterval(() => {}, 1000); }
else {
 if (mode !== 'missing-init') { if (mode === 'wrong-model') init.model = 'MiniMax-M3'; if (mode === 'wrong-cwd') init.cwd = '/other'; if (mode === 'toolset') init.tools.push('Write'); if (mode === 'malformed-init') init.tools = 'Bash'; emit(init); if (mode === 'duplicate-init') emit(init); }
 if (mode === 'idle' || mode === 'total' || mode === 'cancel-descendant') {
  if (mode === 'cancel-descendant') { const c = spawn(process.execPath, ['-e', 'setInterval(()=>{},1000)'], { stdio: 'inherit' }); fs.writeFileSync(process.env.T73_STUB_TRACE + '.child', String(c.pid)); }
  if (mode === 'total') setInterval(() => emit({ type: 'system', subtype: 'progress', session_id: session }), 15);
  else setInterval(() => {}, 1000);
 } else {
  const commands = scope.commands ?? settings.permissions.allow.filter(s => s.startsWith('Bash(')).map(s => s.slice(5, -1));
  const planned = scope.deniedCanaries ?? [];
  let i = 0; const denials = [];
  for (const command of [...commands, ...planned, ...(mode === 'denied' ? ['node --test tests/ungranted.test.mjs'] : [])]) {
   if (mode === 'missing-check' && command === commands.at(-1)) continue;
   const id = `toolu_fixture_${++i}`; const deny = (mode === 'denied' && command === 'node --test tests/ungranted.test.mjs') || planned.includes(command);
   emit({ type: 'assistant', session_id: session, parent_tool_use_id: null, message: { model: fixture.assistant.message.model, role: 'assistant', type: 'message', stop_reason: null, content: [{ type: 'tool_use', id, name: 'Bash', input: { command } }] } });
   emit({ type: 'user', session_id: session, parent_tool_use_id: null, message: { role: 'user', content: [{ type: 'tool_result', tool_use_id: id, content: command === 'git rev-parse HEAD' ? mode === 'wrong-head' ? 'f'.repeat(40) : scope.head : deny ? 'Permission denied' : 'checks passed; negative control assertion failed as intended', is_error: deny }] }, tool_use_result: { stdout: 'fixture', stderr: '', interrupted: false } });
   if (deny) denials.push({ tool_use_id: id, tool_name: 'Bash', tool_input: { command } });
  }
  if (['read-optional-error', 'read-malformed-error', 'read-failed'].includes(mode)) {
    emit({ type: 'assistant', session_id: session, parent_tool_use_id: null, message: { model: fixture.assistant.message.model, content: [{ type: 'tool_use', id: 'toolu_read', name: 'Read', input: { file_path: 'source.txt' } }] } });
    emit({ type: 'user', session_id: session, message: { content: [{ type: 'tool_result', tool_use_id: 'toolu_read', ...(mode === 'read-malformed-error' ? { is_error: 'false' } : mode === 'read-failed' ? { is_error: true } : {}), content: '1 after' }] }, tool_use_result: { type: 'text', file: { filePath: 'source.txt', content: 'after', numLines: 1, startLine: 1, totalLines: 1 } } });
  }
  let text = `${scope.header}\napprove\nIDENTITY PR ${mode === 'wrong-pr' ? scope.pr + 1 : scope.pr} HEAD ${scope.head} BASE ${scope.base}\nDW1: ran ${commands.at(-1)} -> pass\n${mode === 'scope' ? '' : scope.inventory.map(x => `COVER ${x.id}: audited implementation and negative cases`).join('\n')}\n${mode === 'control' ? '' : `CONTROL: ran ${scope.negativeControl} -> intended assertion failed`}\nFinal pass done\napprove\n`;
  if (mode === 'dw') text = text.replace(/^DW1:.*\n/m, '');
  const assistant = structuredClone(fixture.assistant); assistant.session_id = session; assistant.message.content[0].text = text; emit(assistant);
  const final = { ...fixture.result, session_id: session, result: text, permission_denials: denials };
  if (mode === 'bad-usage') final.usage.output_tokens = '4';
  if (mode === 'wrong-session') final.session_id = '00000000-0000-4000-8000-000000000002';
  if (mode === 'provider-final') final.modelUsage[final.modelUsage ? Object.keys(final.modelUsage)[0] : 'none'].provider = 'bedrock';
  if (mode === 'final-mismatch') final.result += 'different';
  if (mode === 'malformed') process.stdout.write('{invalid}\n');
  else if (mode === 'truncated') process.stdout.write(JSON.stringify(final).slice(0,-3));
  else if (mode !== 'missing-final') emit(final);
  process.exitCode = mode === 'nonzero' ? 7 : 0;
 }
}
