# Deterministic sharing regressions

[confirmed: sharing-before.log, accepted source 77b28447] The initial deterministic
suite reaches the original writer/read/teardown paths and fails on immediate
Windows denial and cleared ownership/references. No sharing red result is a setup
or import failure. Two propagation guards already pass before the fix; mutation
checks separately exercise their ability to reject broadened error handling.

[confirmed: sharing-after-02.log] All13 deterministic tests pass using controlled
clocks. The Windows writer/read budgets are250ms; owned-folder cleanup budget
is500ms. These tests retain the status fields and reject malformed/stale/digest
and rendered-frame acknowledgements after a deferred read. No original resources
are needed or included.

[confirmed: import-before.log, import-after.log] The bounded #234 regression
loads the actual acceptance script without running its expensive main: the
pre-fix sibling navigation import fails, and an injected loader failure exposes
lost sys.path context. The scoped setup adds the helper directory and restores
the complete original path in finally. This import defect is separate from the
sharing fail-before proof. The full unchanged original main remains the runtime
gate; replacing main in the bounded context test does not accept that gate.

[confirmed: sharing-before-final.log, sharing-after-final.log,
baseline-restoration.json] The final propagation tests first recover from the
matching transient denial, then check unrelated/non-Windows propagation. All13
final tests fail against accepted pre-fix product source77b28447, with no
setup/import failure, and all13 pass on the fix. The original earlier log is
retained unchanged. Saved product bytes were restored exactly after this serial
negative control; broader-error mutations under author-mutations-01 also fail
at behavior assertions.

[confirmed: import-before-final.log, import-after-final.log] Both final context
tests fail at assertions when the #234 setup/finally is removed; both pass with
it. This final bounded red does not depend on an import/setup failure.
