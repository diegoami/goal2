# Read-only native permission semantics investigation

[confirmed: primary source, OpenCode tags v2.0.28/v1.18.32, 2026-10-17] Only public source was fetched/read. No CLI/model call, local credentials, native DB inspection, tracked edit, config change, permission answer or active-review interaction occurred. Source URLs and exact SHA256 are in sources.json. git status --short was empty.

## V2 native shell

[confirmed: pinned v2.0.28 source] packages/core/src/tool/plugin/shell.ts:123–143 resolves the invocation cwd, scans the command, resolves parsed.directories, calls FileAccess.authorizeExternal on cwd plus those directories, then checks shell resources. This is NOT filetools-only enforcement.

[confirmed: pinned v2.0.28 source] packages/core/src/shell/parse.ts:13 CWD is cd/chdir/popd/pushd/push-location/set-location. Both legacy scanner (184–202) and portable scanner (235–264) populate directories only for CWD commands; ordinary commands become shell permission resources. In particular ls and cat path operands do not become external_directory requests. directoryArgument/expandKnownDirectory (306–375) resolve only supported static directory expressions; unknown $/backtick/parenthesis expressions are omitted. This is lexical/static command analysis, not runtime filesystem confinement.

[confirmed: pinned v2.0.28 source] packages/core/src/file-access.ts:93–120 treats paths inside location.directory or non-root project.directory as internal; external paths obtain a directory/* resource. authorizeExternal at125–142 calls Permission.assert. Thus an external explicit cwd or statically parsed cd may ask, while `cat ~/.local/share/harness-opencode/...` from internal cwd gets only shell permission. The trusted shell '*' allow covers such cat/ls commands unless a narrower shell deny matches.

## Noninteractive responses

[confirmed: retained pinned source] .cache/T72-preparation/cli-run.ts:27 sets auto=input.auto||input.yolo||input.dangerouslySkipPermissions; run.ts:148 defaults false. packages/cli/src/run/noninteractive.ts:158–187 replies decision auto ? once : reject. With no auto and native-v2 mode it includes explanatory feedback, and the model can continue after the rejected tool; compatibility-v1 instead marks rejected/interruption. permission.asked events are handled at221–223, and admission-time pending requests at740–752. There is no default affirmative answer on this path.

[confirmed: pinned v2.0.28 source] packages/core/src/permission.ts:86–96 uses last matching rule, default ask. Configured explicit deny is checked before saved allow rules; saved project grants can turn otherwise ask into allow; plugin permission.evaluate hook can alter the resulting effect (164–190). assert blocks deny, allows allow, and waits on ask (230–258). This describes native capabilities only; no saved-rule/installed-plugin claim is made because local DB/config contents were not inspected.

## Historical V1 comparison

[confirmed: actual legacy pinned source, not the tag's new-core compatibility implementation] v1.18.32 packages/opencode/src/tool/shell.ts:28–50 defines FILES including CWD, cat/rm/cp/mv/mkdir/touch/chmod/chown and selected PowerShell names, excluding ls. collect at389–411 resolves these command operands with argPath (369–375), adds external directories, and ask at263–280 requests external_directory before shell permissions. Execution at613–627 also adds external cwd.

[inferred: comparison of the two exact native source paths] The observed successful external ls is consistent with an existing unconfined shell grant in v1 as well. Successful external cat represents a narrower regression in the v1 best-effort operand scan: v1's supported static cat operands would request external_directory; v2's native shell does not request it. It is incorrect to describe all external shell operand protection as preserved solely because the effective profile contains external_directory '*' ask. Both majors still execute allowed shell commands with host authority; neither implements an OS filesystem jail or comprehensive interpreter/script/indirection confinement.

[unverified: active review] Main reported successful ls/cat of the review's own safe receipt metadata; this investigation did not inspect its full transcript or DB. Source establishes a sufficient explanation without assuming automatic permission approval. Main retains decisions and reads the full selected M3 final before any run action. No source changes proposed/applied in this read-only investigation.
