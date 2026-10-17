# Trusted OpenCode review operand guard

[confirmed: pinned OpenCode v1.18.32/v2.0.28 source and measurements/T72/rework1]
The legacy shell scanned static FILES operands for external-directory approval.
Native 2.0.28 retains cwd/directory-changing checks but omits other file operands.
This package restores that narrow compatibility boundary using pinned Bash and
PowerShell grammars. Adapted upstream helper/matcher code is MIT licensed;
`LICENSE.opencode` retains the exact pinned upstream notice.

[designed: T72 rework1] Fresh checkout setup:

```bash
npm ci --prefix tools/harness/opencode-guard --ignore-scripts --no-audit --no-fund
node tools/harness/check-opencode-guard.mjs
```

[confirmed: clean-install evidence] No install scripts are needed for these WASM
paths. A clean installation matched all 156 dependency file hashes. The offline
checker and premerge command never install/fetch. `stageGuard` copies trusted
source/dependencies into its owned run directory and records exact hashes, including
the shipped license. Source is resolved from the launching checkout, never PR cwd.

[designed: T72 rework1] Before billing, native config discovery is surveyed with
external setup activations disabled. Safe declaration/policy/shell checks run again
on the actual baseline and guarded execution servers; credential/provider setting
values are not selected or persisted by this survey. Unknown executable plugins or
potentially overlapping higher-authority integration allow globs require explicit
audit. A source-target native `integration.use` policy denies external plugin
modules before import except this staged trusted directory. Native builtin disables
survive baseline discovery and the guarded registry must match that exact subset.
The two native filewatcher-disable flags freeze each loaded configuration snapshot;
new runs reread/revalidate globals. Normal provider configuration/native login DB
remain in place and safe catalogue projections must agree. No provider substitution.

[confirmed: native pinned hook source] Hooks have no protected priority. The native
pre-load policy prevents untrusted allow/mutation hooks or ID/source spoofs from
being registered; inventory alone is insufficient. Native managed policy may only
tighten the guard outcome. This is not a sandbox against arbitrary already-trusted
host/global code or plugin import side effects under an unsupported widening host
policy. Such declarations stop before model generation. Current native adversarial
fixtures proved no import/setup occurred for foreign hooks, same-ID/source spoofing,
builtin-ID spoofing or cwd hooks; changed config stayed frozen for its active lease,
while a fresh native launch read the changes and still blocked those sources.

[designed: T72 rework1] `tool.execute.before` retains call/session/agent identity;
`shell.create.before` scans the final actual native shell/cwd. Unsupported/malformed
or mismatched scans require approval. `permission.evaluate` never broadens outcomes:
configured native denies remain authoritative, and an otherwise allowed shell
request becomes ask when a static external operand lacks a trusted grant. Native
noninteractive mode rejects asks with feedback. The public plugin API cannot create
a new external_directory request, so evidence truthfully records the resulting
shell rejection. The harness rejects that outcome even if the model later finishes.

[confirmed: native probes] Inside/tmp/research reads retain actual expected content;
external quoted/nested/relative/proc-metadata reads reject, native mutation denies
remain effective, and active real shell cancellation preserves a foreign native
server/session. These probes use a deterministic loopback provider, never a paid
model; fake zero tokens are simulated. The raw native `executed` flag is not used
as proof of host execution. Actual content/typed errors and pinned native source
establish the outcomes. Neither this static v1-compatible scan nor shell permission
patterns confine interpreter indirection or provide an OS filesystem jail.

[designed: T72 rework1] Runtime native support pins the audited 2.0.28 binary bytes.
Other native builds/wrappers fail closed until revalidation. Only the exact hashed
nonbilling simulator under Node's test context may exercise protocol tests; its
receipt explicitly identifies simulation, never native enforcement.

[designed: T72 rework1] Reproduce the two behavioral native deletion controls
from an isolated author/review worktree, with no concurrent source checks:

```bash
node tools/harness/check-opencode-guard-controls.mjs --out .cache/T72-native-controls
```

The command restores each changed source in `finally`, retains full logs, and
requires the intended native operand/import assertion to fail. It makes no paid calls.

[confirmed: pinned ModelsDev source and final-readiness receipts] Cold startup can
serve a bundled catalogue while a background remote refresh is in flight. The
harness keeps its owned baseline lease alive until guarded startup and compares
both complete live catalogues contemporaneously, including custom/nonselected
providers. Exact parity must remain stable within the caller's startup/total
budget; mismatch fails before generation. Both leases stop on every outcome.
This verifies the current discovery snapshots; normal later native catalogue
refreshes remain enabled.
