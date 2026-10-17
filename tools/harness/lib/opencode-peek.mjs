// [designed: T72] Read a known receipt's DB/export; never attach to a shared execution service.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { capture, privateHome, OpenCodeInfraError } from './opencode-transport.mjs';
import { command, normalizeSession } from './opencode-protocol.mjs';
export function findReceipt(target, env = process.env) {
  let sid = target;
  if (fs.existsSync(target) && fs.statSync(target).isFile()) {
    const text = fs.readFileSync(target, 'utf8');
    try { const record = JSON.parse(text); if (record.major === 2 && record.files && record.sessionID) return { manifest: path.resolve(target), record }; } catch {}
    sid = [...text.matchAll(/session (ses_[A-Za-z0-9_]+) started/g)].at(-1)?.[1];
  }
  if (!/^ses_[A-Za-z0-9_]+$/.test(sid || '')) throw new OpenCodeInfraError('peek', 'target has no valid session ID');
  const base = path.resolve(env.HARNESS_OPENCODE_HOME || path.join(env.HOME || os.homedir(), '.local/share/harness-opencode'));
  const runs = path.join(base, 'v2/runs'); const matches = [];
  if (fs.existsSync(runs)) for (const run of fs.readdirSync(runs)) {
    const index = path.join(runs, run, 'receipts');
    if (!fs.existsSync(index)) continue;
    for (const name of fs.readdirSync(index)) if (name.endsWith('.json')) {
      const entry = JSON.parse(fs.readFileSync(path.join(index, name), 'utf8'));
      if (entry.sessionID === sid) {
        const record = JSON.parse(fs.readFileSync(entry.manifest, 'utf8'));
        if (record.sessionID !== sid) throw new OpenCodeInfraError('peek', 'receipt index identity mismatch');
        matches.push({ manifest: entry.manifest, record });
      }
    }
  }
  if (!matches.length) return { sessionID: sid };
  const roots = new Set(matches.map((m) => m.record.dataRoot));
  if (roots.size !== 1) throw new OpenCodeInfraError('peek', 'ambiguous session ownership across private roots');
  return matches.sort((a, b) => b.record.started - a.record.started)[0];
}
export async function peekRecord(cmd, receipt, { env = process.env, timeoutMs = 15000 } = {}) {
  const m = receipt.record;
  if (!m || m.major !== 2) throw new OpenCodeInfraError('ownership', 'v2 peek requires a retained owned receipt; use explicit --major 1 for legacy receipts');
  let raw;
  if (m.phase !== 'running' && fs.existsSync(m.files['export.json'])) raw = JSON.parse(fs.readFileSync(m.files['export.json'], 'utf8'));
  else {
    const home = privateHome(env, { resumeRoot: m.dataRoot });
    const built = command(2, 'export', { directory: m.directory, sessionID: m.sessionID });
    const result = await capture(cmd, built.args, { cwd: built.cwd, env: { ...home.env, OPENCODE_DISABLE_PROJECT_CONFIG: '1' }, timeoutMs });
    if (result.code !== 0) throw new OpenCodeInfraError('peek', `private session export failed: ${result.error ?? result.code}`);
    raw = JSON.parse(result.stdout);
  }
  normalizeSession(2, { info: raw.info, messages: [] }, { sessionID: m.sessionID, directory: m.directory, agent: m.agent, model: { providerID: m.model.id.split('/')[0], id: m.model.id.slice(m.model.id.indexOf('/') + 1), ...(m.model.variant ? { variant: m.model.variant } : {}) } });
  if (!Array.isArray(raw.messages)) throw new OpenCodeInfraError('peek', 'missing session messages');
  return raw;
}
export function renderPeek(raw, major, n = 20) {
  const steps = raw.messages.flatMap((m) => major === 2 ? m.content ?? [] : m.parts ?? []).flatMap((p) => {
    if (p.type === 'tool') {
      const input = p.state?.input;
      // [confirmed: measurements/T72/peek-tool-state-schemas.json] V2 streaming uses string input; other states require objects.
      if (major === 2 && !(p.state?.status === 'streaming' ? typeof input === 'string' : ['running', 'completed', 'error'].includes(p.state?.status) && input && typeof input === 'object' && !Array.isArray(input))) throw new OpenCodeInfraError('peek', 'malformed native tool state/input');
      const text = JSON.stringify(input);
      if (text === undefined) throw new OpenCodeInfraError('peek', 'missing tool input');
      return [`  tool ${p.name ?? p.tool} [${p.state?.status}]: ${text.slice(0, 140)}`];
    }
    if (p.type === 'text' && p.text) return [`  says: ${String(p.text).replaceAll('\n', ' ').slice(0, 200)}`];
    return [];
  });
  return [`${raw.info.title} · ${raw.info.model?.providerID ?? ''}/${raw.info.model?.id ?? ''} · ${raw.info.location?.directory ?? raw.info.directory}`, ...steps.slice(-n)].join('\n');
}
