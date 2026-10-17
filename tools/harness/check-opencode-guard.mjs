#!/usr/bin/env node
// [designed: T72 rework1] Offline dependency-byte verification only; never install/fetch implicitly.
import { verifyGuardDependencies } from './lib/opencode-guard.mjs';
try {
  const dependencies = verifyGuardDependencies();
  console.log(`PASS trusted guard dependencies: ${Object.keys(dependencies).length} exact file hashes`);
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
