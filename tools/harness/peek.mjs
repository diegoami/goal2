#!/usr/bin/env node
// [designed: T72] Current v2 is default; legacy v1 is explicit and reads only the retained v1 root.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { resolveOpenCode, openCodeVersion } from './lib/opencode.mjs';
import { capture } from './lib/opencode-transport.mjs';
import { findReceipt, peekRecord, renderPeek } from './lib/opencode-peek.mjs';
try {
  const [target, ...args] = process.argv.slice(2);
  if (!target) throw new Error('usage: peek.sh ses_ID|run.json|run.log [-n N] [--major 1]');
  const n = args.includes('-n') ? Number(args[args.indexOf('-n') + 1]) : 20;
  if (!Number.isSafeInteger(n) || n < 1) throw new Error('-n must be positive');
  const cmd = resolveOpenCode(); const receipt = findReceipt(target);
  let raw; let major = 2;
  if (args.includes('--major')) {
    if (args[args.indexOf('--major') + 1] !== '1') throw new Error('only explicit --major 1 is supported');
    major = 1;
    if (!(await openCodeVersion(cmd, { env: process.env, cwd: os.tmpdir() }))?.startsWith('1.')) throw new Error('--major 1 requires an explicitly selected v1 binary');
    const base = process.env.HARNESS_OPENCODE_HOME || path.join(os.homedir(), '.local/share/harness-opencode');
    const env = { ...process.env, XDG_DATA_HOME: path.join(base, 'data'), XDG_CACHE_HOME: path.join(base, 'cache'), XDG_STATE_HOME: path.join(base, 'state') };
    const sid = receipt.sessionID ?? receipt.record?.sessionID;
    const result = await capture(cmd, ['export', sid], { cwd: os.tmpdir(), env, timeoutMs: 15000 });
    if (result.code !== 0) throw new Error('explicit v1 export failed');
    raw = JSON.parse(result.stdout); if (raw.info.id !== sid) throw new Error('v1 session mismatch');
  } else raw = await peekRecord(cmd, receipt);
  console.log(renderPeek(raw, major, n));
} catch (e) { console.error(`peek: ${e.message}`); process.exitCode = 1; }
