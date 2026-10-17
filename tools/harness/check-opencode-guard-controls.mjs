#!/usr/bin/env node
// [designed: T72 rework1] Sequential real-native deletion controls; no model service calls.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

const outIndex = process.argv.indexOf('--out');
assert(outIndex > 0 && process.argv[outIndex + 1], '--out DIRECTORY is required');
const parent = path.resolve(process.argv[outIndex + 1]);
fs.mkdirSync(parent, { recursive: true });
const root = fs.mkdtempSync(path.join(parent, 'native-controls-'));
const cases = [
  {
    name: 'operand-loss', file: 'tools/harness/opencode-guard/scanner.mjs',
    before: 'directories.add(isDirectory ? absolute : path.dirname(absolute));', after: ';',
    script: 'tools/harness/probe-opencode-guard.mjs',
    assertion: 'external-proc-metadata must reject',
  },
  {
    name: 'preload-loss', file: 'tools/harness/lib/opencode-policy.mjs',
    before: "resource: 'plugin:*', effect: 'deny'", after: "resource: 'unrelated:*', effect: 'deny'",
    script: 'tools/harness/probe-opencode-plugins.mjs',
    assertion: 'untrusted source must not import before readiness',
  },
];
const results = [];
// Each control temporarily changes one source file; do not run concurrent source checks.
for (const item of cases) {
  const saved = fs.readFileSync(item.file, 'utf8');
  assert(saved.includes(item.before), `${item.name}: mutation target must exist`);
  const directory = path.join(root, item.name);
  fs.mkdirSync(directory);
  let result;
  try {
    fs.writeFileSync(item.file, saved.replace(item.before, item.after));
    result = spawnSync(process.execPath, [item.script, '--out', directory], {
      encoding: 'utf8', timeout: 90000, maxBuffer: 5000000,
    });
    fs.writeFileSync(path.join(directory, 'stdout.log'), result.stdout || '');
    fs.writeFileSync(path.join(directory, 'stderr.log'), result.stderr || '');
  } finally {
    fs.writeFileSync(item.file, saved);
    assert.equal(fs.readFileSync(item.file, 'utf8'), saved);
  }
  const output = (result.stdout || '') + (result.stderr || '');
  assert.equal(result.status, 1, `${item.name}: native deletion must fail`);
  assert(output.includes(item.assertion), `${item.name}: intended native assertion`);
  assert(!/MODULE_NOT_FOUND|ERR_MODULE_NOT_FOUND|timed out/.test(output), `${item.name}: behavioral failure required`);
  results.push({ name: item.name, status: result.status, assertion: item.assertion, restored: true, externalModelCalls: 0 });
}
fs.writeFileSync(path.join(root, 'results.json'), JSON.stringify(results, null, 2) + '\n');
console.log(JSON.stringify({ root, results }));
