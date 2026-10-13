# Handover — 2026-10-13, third session (GLM): #46 merged; queue for the MiniMax session

This session ran on GLM-5.3 Flash (Z.AI, via clother), the day's third. The two earlier
handovers cover T15–T18 and T19–T20; this one covers #46 and hands you the queue.
**The owner's instruction for you (2026-10-13): do the easy and medium items; do NOT do the
hard ones** — those wait for a stronger session (Claude, or Z.ai after its reset).

## What shipped this session

- **#46 closed.** `measurements/T19/divergence.py`'s exit-path print guarded (`first record
  none` when `first_divergence` is `None`); PR #47 squash-merged as `f11256b`. Implemented by
  GLM-5.3 Flash (the `implementer` subagent on `sonnet`, ~82.7k tokens, zero rework); reviewed
  by GPT-5.6 Luna — clean approve, 1 round, no findings, both Done-when lines re-run by the
  reviewer. §9 measure comment on the PR.
- **Triage decisions recorded on #46** (the worked example for fix-class triage): bug
  reproduced before dispatch; rule-5 amendment — the fix PR commits the regenerated all-zero
  `report.md`, and "must not change its numbers" is honoured as *don't touch the measurement
  logic*.
- **The owner's #43 decision** (2026-10-13, this session): the three written-here files are
  NOT vendored ("we created them") — so they **move out of `goal2/engine/`** (option (a) of
  the issue's three; a PROVENANCE row is impossible for a file with no upstream commit).
- No product code touched this session; the test suite is unchanged (T20's count was 186/186).

## Your queue, with difficulty

| # | Item | Difficulty | Notes |
|---|---|---|---|
| 1 | Session start (rule 14) | **easy** | Triage list (should be only #43), in-flight check, worktree sweep: 5 `agent-*` worktrees (T17–T20, #46) + `goal2-work/` T01–T15, all with commits ≤ 7 days old — expect none eligible; list what you checked. |
| 2 | **#43** — move the three files | **MEDIUM — allowed** | Move `new_game.py`, `skills.py`, `state.py` out of `goal2/engine/` into a rebuild-side package (propose `goal2/game/`; confirm the destination with the owner in your ONE implementer question). Grep-driven import updates everywhere (`measurements/T19/divergence.py`, `goal2/tests/test_new_game.py`, `test_p1_fidelity.py`, any other importer). Done-when includes: `tools/check_provenance.py` green on the PR head, full suite green, the fidelity pins untouched in meaning. One task/branch/PR (triage it to a task file first), one review round, `status:in-progress` labels as usual. |
| 3 | **P4 (BM-1..7)** | **HARD — do NOT do** | The next build milestone; gated on #43 (P4 branches off `new_game.py`, which the move relocates). Do not implement, do not open its branch, do not plan beyond reading. When #43 is merged: stop and report. |

"Hard" also covers: anything touching the vendored engine's semantics, the fidelity tests'
meaning, or `measurements/**` logic — out of your scope without the owner asking.

## Models (the "Choosing models" rules run as written)

- Your family is **minimax** → never a minimax reviewer. Review #43 with **GPT-5.6 Luna**
  (`luna`, openai, ~97% headroom) via `review.mjs`; fallback MiMo Pro (OpenCode Go ~23%
  headroom, pace 44 — tight). zai resets ~1.5–2 h after this handover; `glm` becomes legal
  then (never glm-flash on a provenance-adjacent review without the full "Blocking means"
  brief — see its L47 note in `harness.json`).
- Implementer: `harness.json` default `sonnet` = **MiniMax-M3** on your backend (heavy);
  `haiku` = MiniMax-M2.7 (light). #43 is a moderate mechanical task: M3 per the effort rule is
  right. Ask the owner your ONE question first, and one before the review.

## Traps

- `measurements/T19/report.md` on `main` is now the all-zero reconciled output and
  `divergence.py` exits 0. Do not "fix" the consistency-NO flags — they are correct post-T20
  (the ablation chain deliberately reverts to the *pre-T20* encoding, so it no longer matches
  the fixed model).
- Fixtures (rule 19, git-ignored) live in `.cache/` at the repo root; a reviewer worktree has
  none — stage them into `/tmp` and have the brief say so (`/tmp/goal2-fixtures-t46/` may
  still exist; otherwise re-stage from `.cache/`). The #46 brief
  (`/tmp/goal2-t46-review-brief.md`) is the pattern, if still present.
- Fix-class Done-when lines: run each yourself at triage — it must fail on `main` and pass on
  a mock fix (rule 9a write-back, never `git checkout`); record on the issue.
- The provenance check is red until #43 lands — that is the issue itself, not a regression;
  every other pre-merge check must pass (the `ci.yml` list: links, review self-test, lock
  hashes, agent permissions, no-original-files; GitGuardian is the only GitHub-side check).

## Workspace

`main` @ `f11256b`, clean. Labels: #46 `status:merged` + closed; #43 `triage:needed` (triage
it first). Nothing in flight. This session's scratch (`/tmp/goal2r-t46.log`,
`/tmp/goal2-t46-review-brief.md`) is disposable.
