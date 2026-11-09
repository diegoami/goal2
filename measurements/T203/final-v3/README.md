# T203 public receipt representation correction

This is a metadata-only correction to the public evidence index. The native
Windows result was written with CRLF line endings; Git normalized its public
JSON copy to LF at7091d330. The v2 index accidentally retained the RAW Windows
source hash for that public path. The JSON values and the measured result are
identical. The raw receipt and its original hash remain in the private keeper.

V3 binds the existing committed LF bytes and records both representations. The
v2 index and every committed measurement/receipt remain unchanged and historical;
no original native measurement is rewritten. The read-only7091 binding audit found
zero source mismatches (457 bindings) and only this one normalization mismatch
among30 public entries. Native455 historical source bindings match7b85 exactly;
only the four already declared test-fixture/navigation fixes differ at7091.

Application, owner-journey dependencies, tests, resources, tables and package
inputs are identical to7091. Its actual gate/hosted-CI scope may be reused with
explicit7091→metadata-head identity under docs/runners.md; main runs the exact
metadata-head --no-tests guard. No duplicate full suite or new runtime claim is
introduced. Both actual UI proofs remain SAME-CHOICE HEADLESS BRIDGE equality,
not fresh original-binary/Unicorn comparisons.

Model: inherited Codex GPT-6 family; exact variant unavailable.
