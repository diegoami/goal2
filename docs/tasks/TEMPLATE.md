# T<nn> <Title>

- **Kind**: feature | slice | fix | correction (of T<nn>, bug #<n>) | infrastructure
- **Issue**: #<n> · **Branch**: `task/T<nn>-<slug>` · **Merge after**: T<nn>, …
- **Implementer**: the `implementer` subagent on the model chosen at the question, or the main session directly (CLAUDE.md "Choosing models"); say which, and why, only when it matters (L57).
- **Reviewer**: `reviewer.default` (`luna`, GPT-5.6 Luna), or a `harness.json` key with the reason: `sol-6.1` for hard reviews (an engine seam, a fidelity test, a vendored model); never the implementer's family.
- **Evidence**: the goal2-archaeology findings (F-numbers + commits) and the goal2 state this task
  rests on, with the evidence tags its claims will carry (CLAUDE.md rule 17).
- **Owns**: directories or files, e.g. `src/Calendar/**`, `tests/Calendar/**`. A task that measures
  owns a tracked path for its outputs, e.g. `measurements/T<nn>/**`: they are
  pushed after each batch and every 30 minutes, never deleted or overwritten; originals stay out,
  their hashes recorded (L40).
- **Scope**: what to build, in a few sentences. What is out of scope, if it is easy to confuse. A task
  likely to outlast one implementer run (about an hour), or whose Done-when is all or nothing (an exact
  match, a whole model), is split into milestone tasks first, each merging on its own with a Done-when
  that measures a number (L58).
- **Done when**:
  1. One check a command can run, with the expected result. Before dispatch, each line fails on
     `main` and passes on a mock fix (L45).
  2. …
  3. The build and the test suite are green.
- **Hazards**: the mistake an implementer is most likely to make here, and how to avoid it.
- **Notes for the main session**:
  - The only Python interpreter on this machine is `python3` (the `python` alias is unavailable).
    Use `python3 -m unittest …` in Done-when commands, not `python -m unittest …`. (L108 captures
    the rule that surfaced in T16 R3 and T17 R3 — both rounds returned `python -m unittest …` as
    "command cannot be run as written" until DW1 was amended on main.)
  - If the task touches any file whose SHA-256 is listed in `harness.lock` (e.g.
    `.claude/agents/implementer.md`, `docs/lessons.md`, …), the implementer must update the
    `harness.lock` entries on the PR branch before claiming the pre-merge
    `grep -E '^[0-9a-f]{64}  ' harness.lock | sha256sum -c --quiet` passes (rule-5 of the
    ci.yml checks). Compute `sha256sum <file>`, replace the old hash line in `harness.lock`,
    commit + push. L108 captures the pattern that surfaced in T17 R2.
