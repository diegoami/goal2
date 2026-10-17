# Fresh/resumed root identity through a symlinked parent

[confirmed: M3 r2 full review and symlink-before.log] Fresh privateHome returned
the literal mkdtemp path, while resume canonicalized it. A symlinked owned parent
therefore changed the retained dataRoot identity. The production regression fails
at "fresh owned root must have physical identity" against168f345, rather than a
missing module or timeout. Existing strict equality/realpath/ownership checks were
not weakened.

[designed: T72 narrow rework2] Canonicalize only the newly created run root using
fs.realpathSync before writing its ownership marker. Keep persistent v2 data
selection/pointer, resume security checks and all legacy receipts intact. No
permission, parser, provider, transport lifecycle or model-routing change.

[confirmed: symlink-final.log and combined.log] Production fresh+resume through an
owned symlink retain the same canonical dataRoot/session and data pointer. Marker,
physical staged guard entrypoint/directory and owned cache/state remain valid.
Combined protocol/workflow/client checks:52 pass,0fail,0skip. Earlier guard/native
matrices were unchanged and not redundantly rerun.

[confirmed: normal/ and alias/] Normal and alias-parent actual native preflight
both pass selected M3 thinking/effective unchanged reviewer, complete catalogue
parity, empty zero-cost/token session, export/peek, owned clean shutdown and foreign
survival. No model generation. physical-identity.json proves canonical run/guard
source identities; schema and full baseline originals stay ignored and hashed,
with bounded safe baseline summary retained. Native artifact identities remain
exact, not synthetic paid evidence.

[designed: scope] Only lib/opencode-transport.mjs, focused workflow regression,
current lock digests and this bounded evidence batch changed. No setup document
became incorrect. Main owns review/merge and the unrelated launch PATH correction.
