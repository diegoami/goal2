# Protocol fixtures

[confirmed: measurements/T72a/probe-20261017/schema-source.json] schema-v2 fragments are selected from the captured installed OpenAPI schema.

[designed: T72a] v2-synthetic-export.json and synthetic-permissions.json are schema-shaped synthetic outcomes, extending the observed empty export identity. They are not observed model/tool execution and have no billed usage evidence. v1-synthetic-export.json uses the historical v1 info/parts/state.error string layout already consumed by tools/harness/lib/opencode.mjs; its content is synthetic. Shared text includes multiple assistant text segments and a rejection despite an approve-looking string, proving normalization never manufactures permission approval.

[confirmed: v1-actual-metadata-step-projection.json] The main session supplied a read-only v1 database projection of actual assistant and step metadata. It is not a raw export. The test adds a synthetic session envelope only; the original projection values remain unchanged. It proves optional total tokens and step-start/step-finish retention, including tool-calls completion boundaries.
