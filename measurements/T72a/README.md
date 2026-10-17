# OpenCode 2 protocol evidence

[confirmed: probe-20261017/manifest.json] The installed2.0.28 binary was probed
without invoking `run`, `prompt` or `generate`. The manifest hashes the binary,
probe revision and complete safe artifacts retained in the ignored output run.
The tracked subset contains actual JSON/CLI/SSE responses and selected installed
OpenAPI fragments under `tests/fixtures/opencode/schema-v2/`. Model/agent request
settings are excluded; projected model records preserve actual identity/variants.
Generated server authentication passwords are excluded. No auth file was read.
The schema source hash identifies the complete source; fragments are exact
selections, not a replacement claim about the entire catalogue.

[confirmed: probe-20261017/old-commands.json] The old `models minimax --verbose`
and `export <id>` commands failed with real v2 command errors. Correct commands
returned the selected variants and the owned empty session. Missing modules and
timeouts were not used as regression evidence.

[confirmed: probe-20261017/owned-serve-timed/timeline.json] Agent discovery on a
persistent owned server returned empty, then built-ins, then configured agents.
The minimal and isolated-config repetitions have the same progression. Immediate
`api --standalone agent.list` output cannot establish that the reviewer is absent.
The probe waits for the exact agent and selected model variant, with a deadline.

[confirmed: probe-20261017/agents.json] The retained legacy reviewer loads and
normalizes `bash` to `shell` and `task` to `subagent`. Its effective profile lacks
an `external_directory` wildcard `ask` rule. Existing tmp/research allow exceptions
do not preserve the old default boundary. The observed profile is evidence of
this gap, not approval to launch it in production.

[confirmed: probe-20261017/events.sse, lifecycle.json] An empty session produces
native `session.created` SSE, costs zero and has no messages. Interrupting an idle
owned session returns `interrupted:false`; SIGTERM shuts down the owned server
(exit130). An independently owned HTTP stub survives. This demonstrates process
isolation, not cancellation of a live billed execution or survival of every
possible external service. Events are volatile: the installed schema explicitly
says disconnected/slow consumers can miss events.

[designed: T72a] T72 must integrate the pure adapter explicitly by major, retain
full session/assistant/tool/error artifacts, verify exact directory/session/model/
variant/agent identities and effective reviewer permissions before billing,
translate the historical external-directory default and exceptions, and bound
cancellation to the process that owns execution. Shared service lifecycle is
outside this prerequisite; never stop/restart a shared service to cancel a run.
A session accepting an agent string proves only stored selection. Empty-session
usage does not prove model execution, permissions enforcement or review success.

[designed: T72a] Production imports/launch behavior remain unchanged here. V1 is
an explicit compatibility protocol; unknown majors and incomplete records fail
closed. Synthetic message/tool/permission fixtures are labeled separately and
prove normalization only. No migration-complete or paid-execution claim is made.

Primary references: [migration](https://opencode.ai/v2/docs/migrate-v1/),
[agents](https://opencode.ai/v2/docs/agents/),
[API](https://opencode.ai/v2/docs/api).

[confirmed: probe-20261017-shutdown/lifecycle.json] The second probe also asserts the owned endpoint is unreachable after bounded process shutdown; its exact source snapshot is retained beside the manifest.

[confirmed: mutation-controls-20261017.json] Six deliberate losses (identity checks, rejection, complete text, final-stop completion, assistant-error gating, step metadata) each fail a specific assertion with child exit1. Tests clear inherited Node test-runner context so child checks execute; neither timeout nor module/syntax errors count as successful controls.

[confirmed: v1-help-run.json, v1-primary-schema-fragments.json] The retained v1 CLI advertises separate --dir/--variant; primary v1 schema fragments pin full assistant metadata and step/tool records. The actual v1 database projection and synthetic records have distinct provenance. Final probe evidence is retained in probe-20261017-final with the matching source hash.

[confirmed: mutation-controls-final-20261017.json] The final control batch additionally removes earlier assistant messages and fails the complete-transcript assertion. Both protocols preserve all assistant text across a tool-call sequence followed by a final stop; later user input leaves completion false.

[confirmed: mutation-controls-roundtrip-20261017.json] The final eight-control batch also proves that absent effort stays absent through session normalization and command construction; inserting a null variant fails the roundtrip assertion. No effort is invented or silently substituted.

[confirmed: mutation-controls-idle-20261017.json] The nine-control batch adds pending user followed by idle: reintroducing the last-record-only completion gate fails its specific assertion. Idle records require schema-shaped timestamps/outcome; failed or errored trailing idle prevents completion.
