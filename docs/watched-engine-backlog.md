# Original watched-engine backlog: stage 1

[designed: owner, 2026-10-16] The [decision in #97](https://github.com/diegoami/goal2/issues/97#issuecomment-6209860384) and [handover #130](https://github.com/diegoami/goal2/issues/130) select the original watched-match routine under Unicorn for the next playable milestone: choose a team and lineup in our browser, watch an original friendly, inspect its results, save and play another. Original engine resources are supplied at runtime or fetched by verified hash; none are committed. Unicorn is approved as an optional dependency.

## Sequence and difficulty

[designed] Execute in order, one task/PR at a time. The first two issues belong upstream; their local task files are handover contracts, not permission to implement archaeology code here. GitHub labels carry current status. Creating this backlog does not select models or begin implementation/reviews.

| Order | Task | Difficulty | Repository | Depends on |
| --- | --- | --- | --- | --- |
| 1 | [T60](tasks/T60.md) · [#248](https://github.com/diegoami/goal2-archaeology/issues/248) — Prove original watched-match fixture entry | Medium; feasibility uncertainty | archaeology | Decision/estimate gate |
| 2 | [T61](tasks/T61.md) · [#249](https://github.com/diegoami/goal2-archaeology/issues/249) — Package reusable original watched-match calls | Medium | archaeology | T60 + upstream review gate |
| 3 | [T62](tasks/T62.md) · [#132](https://github.com/diegoami/goal2/issues/132) — Vendor the optional watched runtime and verified assets | Easy–Medium | goal2 | T61 |
| 4 | [T63](tasks/T63.md) · [#133](https://github.com/diegoami/goal2/issues/133) — Adapt game state into an original watched fixture | Medium | goal2 | T62 |
| 5 | [T64](tasks/T64.md) · [#134](https://github.com/diegoami/goal2/issues/134) — Commit watched results atomically and preserve saves | Medium | goal2 | T63 |
| 6 | [T65](tasks/T65.md) · [#135](https://github.com/diegoami/goal2/issues/135) — Run watched matches in a worker with progress | Medium | goal2 | T64 |
| 7 | [T66](tasks/T66.md) · [#136](https://github.com/diegoami/goal2/issues/136) — Watch an original friendly in the browser | Medium | goal2 | T65 |

[designed] Medium means ordinary integration with bounded state/parity checks. T60 has feasibility uncertainty rather than inherently difficult coding. T62 is primarily packaging and installation. Each task protects one outcome; before dispatch, validate its failing baseline and runnable acceptance commands and split any slice that exceeds a bounded implementer run. Proposed test names in the task files are acceptance contracts, not existing checks or completed evidence.

## Gates and evidence

[designed: #130] Before T60 implementation, review and merge the existing [close-enough estimate PR #122](https://github.com/diegoami/goal2/pull/122), [original-engine estimate PR #123](https://github.com/diegoami/goal2/pull/123), and [decision PR #126](https://github.com/diegoami/goal2/pull/126) through the normal process. The owner chooses the eligible OpenCode reviewer; the planning request does not select one. Choose the implementer/model before dispatching each new task.

[derived: estimate #123] T60 starts with one hour to establish whether `run_match` at `0791:F1F6` accepts an arbitrary supplied fixture without hidden menu preconditions. Preserve a quantitative negative result if it does not. Entering one level higher through `000E:6E15` may add the estimated 3–6 hours; stop and re-scope that repair before proceeding. T61 requires a positive entry verdict. A failed probe is not a successful engine integration.

[designed] T61/T62 consume only a reviewed, merged upstream runtime and strict E032 comparator, including the relevant work from [archaeology PR #243](https://github.com/diegoami/goal2-archaeology/pull/243). Pin exact source commits and asset hashes at dispatch; do not treat an estimate branch as accepted production evidence. T60 may inspect the explicitly pinned research branch for its experiment. Reuse `runtime/emul/watched_match.py` and `watched.py` rather than reimplementing match mathematics.

## Estimate and milestone

[derived: PR #123] The source estimate is **13.5 implementer hours, range 8.5–22**, across U1 upstream (5h), G1 vendoring (2.5h), G2 adapter (3h) and G3 browser (3h). This backlog splits those four packages into seven reviewable milestones: T60–T61 = U1, T62 = G1, T63–T64 = G2, T65–T66 = G3. These are not seven additional packages. More PRs add review/process time that the source's four-PR estimate did not quantify. Hidden-precondition repair and review/rework can extend elapsed time. The measured 9.7–14.6 CPU seconds per watched match is not a response-time guarantee.

[designed] Stage 1 is complete when ten strict original records reproduce through the adapter, original post-match effects publish exactly once, and a real browser friendly shows original commentary, boards, ratings and man of the match with save/resume and deterministic continuation. Quick play remains usable without the optional runtime. A-WATCH-1 changes only after this path is proven. No pitch animation, halftime editing or competitive/full-cycle support is implied.

[designed: owner #97] This sequence takes priority over starting the next [campaign-backlog](full-cycle-backlog.md) implementation task. Preserve the campaign work and issues. After the first playable original watched friendly, the owner decides between continuing Python campaign adapters and adopting more of the original core. No stage-3 whole-core or stage-4 distribution tasks are created here; later watched UI work also remains outside this stage.
