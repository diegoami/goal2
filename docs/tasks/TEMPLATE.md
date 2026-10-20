# T<nn> <Title>

- **Kind**: feature | slice | fix | correction (of T<nn>, bug #<n>) | infrastructure
- **Issue**: #<n> · **Branch**: `task/T<nn>-<slug>` · **Merge after**: T<nn>, …
- **Evidence**: the goal2-archaeology findings (F-numbers + commits) and the goal2 state this task
  rests on, with the evidence tags its claims will carry (CLAUDE.md rule 12).
- **Owns**: directories or files. A task that measures owns a tracked path for its outputs, e.g.
  `measurements/T<nn>/**`.
- **Scope**: what to build, in a few sentences, and the one claim the task protects. What is out of
  scope, if it is easy to confuse.
- **Done when**:
  1. One check a command can run, with the expected result (`python3 -m unittest …`, not
     `python`). It fails on `main` and passes once the task is done.
  2. …
  3. `python3 tools/check_premerge.py --expected-head <sha>` passes.
- **Review**: none, or `tools/review_pr.sh` with the reason (engine, fidelity, saves, timing).
- **Hazards**: the mistake an implementer is most likely to make here, and how to avoid it.
