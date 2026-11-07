# Validation at PRs and milestones

[designed: owner, 2026-11-07] Full suites protect an integrated milestone. PRs use focused tests
and fast regression checks. This supersedes older automatic per-PR slow/full requirements.

## PR

Run the task's named tests at the exact source, with `GOAL2_SLOW=1` for the relevant actual match
or original-reference cases. Preserve all cases and assertions in those selected tests. Then:

```bash
python3 tools/check_premerge.py --expected-head <full-sha>
```

The default checks every module's fast tests and the cheap layout/reserve slow checks. Hosted
Linux/Windows workflows use the equivalent `--batch-fast`, including native scaling. Slow suites
are not started automatically by PRs, main pushes or a seven-day timer. An investigation may
explicitly select the existing reachable slow scope with `--affected`.

## Integrated milestone

With prepared originals/dependencies and `GOAL2_CASES` unset, dispatch `linux-slow.yml` and
`windows-slow.yml` on the integrated candidate. Each runs:

```bash
python3 tools/check_premerge.py --expected-head <candidate-sha> --slow
```

That is one complete run per platform, with every slow test and case. Retain portable build/smoke
and native acceptance, original comparisons, exact source pins and all outcome/RNG/publication oracles.
After fixes rerun affected checks; repeat the full suites when changed behavior, dependencies,
fixtures or a broad regression invalidates the earlier coverage. Record the reason for another full run.

## Evidence reuse

A new SHA alone does not invalidate tests. Record the tested SHA, candidate SHA, platform/runtime,
commands/scope, fixture and dependency identity, and the exercised code/test identity (Git objects,
hashes or a reviewed diff). Metadata/ancestry-only merges reuse those results after the new head's
clean-checkout, asset and link/JSON checks. CI-plumbing changes run the tooling regressions without
invalidating unrelated game fidelity results. If the identity or scope is uncertain, rerun the affected
checks. Never reuse a pass for changed exercised inputs or relabel failures/skips. A known failure
still requires the owner's explicit scoped exception.

Existing active task contracts now follow this policy; behavioral Done-when assertions, reference
inputs, seeds, limits and cases remain unchanged. Already-running suites may finish and their
results remain useful; the policy prevents scheduling redundant future rounds.

## Original player journeys

[designed: owner,2026-11-07,#611] Passing a scoped task or a packet mock is not evidence that the original player journey is complete. Before a build handoff, compare required actions with the original manual/captures/source and walk them in an isolated real game; record explicit approved differences and concrete gaps. Do not use a pending implementation as installed-build evidence.

Stopped-match controls require the actual client validation, engine worker, returned decision and final result/publication path. A mock can isolate UI behavior, but cannot prove those contracts. Clearing a pending flag can mean submission failed: require a sent command and actual accepted values before claiming confirmation. Retain before/after failures and full memory/event/RNG/publication oracles. This adds no per-PR full-suite rerun; the scheduling policy above remains unchanged.
