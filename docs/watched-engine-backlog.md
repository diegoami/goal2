# Original watched-engine backlog: stage 1

[designed: owner #97/#130, 2026-10-16] Stage 1 is the original watched friendly
under Unicorn in goal2's PySide6 desktop app: select a team/lineup, watch, inspect results,
save and play another. Unicorn is optional and owner-approved. Original resources
are supplied locally or fetched by full verified hash under ignored caches;
none enter git. The [estimate](estimates/99-original-engine-plugged-in.md) and
[decision](plan.md) define the scope.

## Upstream handoff and acceptance gate

[designed: owner authorization, T67] Reconcile the existing tasks with archaeology
[#250](https://github.com/diegoami/goal2-archaeology/issues/250) and
[PR #251](https://github.com/diegoami/goal2-archaeology/pull/251) before integration.
Do not repeat the T60/T61 investigation/packaging already proposed there. Their
existing issue identities remain evidence-acceptance obligations, with gaps
explicitly blocking acceptance. Production consumption requires PR #251 to be
independently approved and merged, exact accepted source/resource pins, and a
reviewed T62 coverage report. Candidate source is never a production pin. Status
lives in GitHub labels; this document defines conditional gates, not their status.

[derived: proposed kit README and E033 at archaeology candidate
`c5b5402bf74a1592a8bbb799942839f41ad79361`]
The proposed deliverable is `runtime/original_match/`, stdlib plus Unicorn,
with a README, example and `check --family`. Its API accepts `Image`, `Fixture`
and `Match`, yields events and original decision points, and returns `result()`
and `memory_component()`. Consult the
[pinned README](https://github.com/diegoami/goal2-archaeology/blob/c5b5402bf74a1592a8bbb799942839f41ad79361/runtime/original_match/README.md)
and [entry](https://github.com/diegoami/goal2-archaeology/issues/248#issuecomment-6215687812)
/[packaging handovers](https://github.com/diegoami/goal2-archaeology/issues/249#issuecomment-6215688224).
These describe proposed coverage, not goal2 acceptance or arbitrary-fixture fidelity.

| Existing obligation | Proposed upstream coverage | Goal2 acceptance / remaining work |
| --- | --- | --- |
| T60 fixture entry | E033 `entry_probe.py`, E011/E021 reference and E032 family; direct `run_match` entry with the caller frame | Account for every entry/boundary input, hashes and repeated-run parity. The tried friendly/pair does not prove arbitrary campaigns. Record gaps; do not dispatch a duplicate probe. |
| T61 reusable caller | `runtime/original_match/`, example, focused tests, mutation checks and independent check | Accept calling/decision/post-match contracts and all ten strict records from the merged source. No second `runtime/emul/watched_match.py` caller. |
| T62 optional install | Vendoring instructions, optional Unicorn import and verified existing image loader | Vendor exact accepted package, per-file provenance/full asset hashes, missing-dependency/build/hash failure checks and quick-only regression. No reduced binary or new asset is presumed necessary. |
| T63 adapter | `Image.from_savestate`, `Fixture(first, second, index, kind)`, `Match(..., managed, captain)`, events/answers, full returned memory | Map actual goal2 fixture/year/team/management state; compare all ten direct records plus sensitive changed-input/side-B cases without publishing. |
| T64 result/save | `result()` and full `memory_component()` after original player update; kit `Match.save/load` | Atomic goal2 publication, T41 queue/history, compatible completed-session saves and deterministic continuation. A kit checkpoint is not automatically a new desktop save feature. |
| T65/T66 process worker/desktop | Incremental original events and `decision`/answer interface | Responsive worker, explicit default answers, once-only completion and desktop results/save/repeat. Interactive editing and animation remain later scope. |

[designed: T67, acceptance of the
[review at the candidate pin](https://github.com/diegoami/goal2-archaeology/pull/251#issuecomment-6215910890)]
T62 must verify approved regression evidence for all three reported defects,
not merely observe another passing reference score:

- **R1 build guard:** meaningful engine-code changes outside short routine prefixes
  are rejected; legitimate adapted player/country state remains accepted.
- **R2 full-time save:** saving at a public `full_time` event can resume through the
  original player-update tail with the same complete outcome as uninterrupted play.
- **R3 commentary timestamps:** original commentary minutes match guest writes;
  an equal line count alone cannot establish correct timestamps.

## Implementation sequence and difficulty

[designed] Keep the existing task/issue IDs; one goal2 implementation task/PR at a
time. T60/T61 acceptance can be recorded within T62, without separate duplicate
upstream implementation PRs. A demonstrated evidence gap is a bounded upstream
question, not permission for an open-ended investigation. Before any new task,
choose its implementer; choose its independent reviewer for its validated PR.

| Order | Task | Difficulty | Repository / prerequisite |
| --- | --- | --- | --- |
| Gate | [T60](tasks/T60.md) / [#248](https://github.com/diegoami/goal2-archaeology/issues/248) — Accept entry evidence | Medium; evidence reconciliation | archaeology handoff; accepted with T62 |
| Gate | [T61](tasks/T61.md) / [#249](https://github.com/diegoami/goal2-archaeology/issues/249) — Accept reusable kit | Medium; evidence reconciliation | archaeology PR #251 approval/merge; accepted with T62 |
| 1 | [T62](tasks/T62.md) / [#132](https://github.com/diegoami/goal2/issues/132) — Vendor optional kit and verify handoff | Easy–Medium | accepted PR #251 + T60/T61 coverage |
| 2 | [T63](tasks/T63.md) / [#133](https://github.com/diegoami/goal2/issues/133) — Adapt state/fixture/result | Medium | T62 |
| 3 | [T64](tasks/T64.md) / [#134](https://github.com/diegoami/goal2/issues/134) — Atomic publication and compatible saves | Medium | T63 |
| 4 | [T65](tasks/T65.md) / [#135](https://github.com/diegoami/goal2/issues/135) — Worker and progress | Medium | T64 |
| 5 | [T66](tasks/T66.md) / [#136](https://github.com/diegoami/goal2/issues/136) — Pygame original-friendly view from Qt | Medium | T65, T70 |

## State and scope rules

[derived: proposed E033 kit at the candidate pin] Setup reseeds with
`index * (year + 1)`. The proposed `Fixture` has no year argument: T63 must pin
which image field supplies the engine year and reconcile it with goal2's campaign
ordinal/source-year metadata. Production defaults preserve the original reseed;
reference-family overrides remain explicit test inputs. Inherited live RNG words
must not silently replace this rule. Record final RNG for deterministic continuation.

[derived: proposed README/E033] Setup changes the computer's country/squad/player
records, and the post-match tail applies energy/form/confidence effects. T63/T64
must preserve full `memory_component()` and countries as well as player bytes.
A `full_time` event alone is not the completed publication boundary: finish the
tail and obtain a valid result. Do not apply Python match effects again.

[designed: T67] T65 consumes original decisions using the stage-1 automatic
play-on policy (`m.answer()`), verifying it on accepted normal/injury paths.
Unsupported/refused decisions get a bounded clear failure with active state
unchanged; do not spin or invent substitutions. T66 consumes live events through
ordinary desktop controls but does not add halftime/in-play editing, mid-match
desktop saves, pitch animation, competitive fixtures or whole-core support.
The T41 source-ordered campaign queue, history and unsupported qualifier barrier
remain part of desktop acceptance; ordinary quick friendlies remain usable.

[designed: owner correction of T67, 2026-10-16] Campaign work continues in
parallel. [T42](tasks/T42.md) follows T41 without waiting for T64 or a later route
choice. It integrates energy on the quick campaign path; T63/T64 must carry the
original watched result's effects without running that Python path again.
Continue the existing campaign dependencies while preserving the engine-kit
acceptance gates for watched integration.

## Estimate and milestone

[derived: original estimate PR #123] The historical baseline is 13.5 implementer
hours (8.5–22): U1 upstream 5h, G1 vendoring 2.5h, G2 adapter 3h, G3 browser 3h.
T60/T61 originally split U1; the kit proposes to supply that work. Do not budget
it a second time. Remaining effort must be re-estimated after accepted-kit
preflight; this planning update supplies no new measured time estimate. Historical
9.7–14.6 CPU seconds per watched match is not a hardware-independent deadline.

[designed] Stage 1 still requires all ten strict original records through the
adapter, once-only original post-match publication, and a real desktop friendly
with original commentary/boards/ratings/man of the match, save/resume and another
fixture. Keep the stand-in until that path is proven; update A-WATCH-1 only then.
[designed: owner, 2026-10-22] Stage 3, the whole game as goal2's core, is the first version: #308 dispatches it. Stage 4 packaging implementation is not dispatched by this backlog.

[designed: owner #148; T68] The desktop pivot preserves T60–T64 evidence and
state contracts. T65 uses a local process and IPC, with no HTTP session layer;
T66 joins it to T70's Qt management and a separate Pygame match window
(owner choice, 2026-10-17), with Qt retaining active state and saves. The engine kit comes first on this track, while
portable campaign work continues. The historical browser estimate is not a new
Qt estimate. Distribution is wanted but small, last and unscheduled (#130/#148):
deliver the image from the private release at package build time, never git.
No server, hosting or mobile requirement is introduced by stage 1.

[designed: T68; derived: archaeology PR #251 review of candidate
`8664eed22c9f2522f2a0a1e6af96beaf0211aa57`,
[review evidence](https://github.com/diegoami/goal2-archaeology/pull/251#issuecomment-6219224724)]
T62 also requires approved regression evidence that quick-result scratch score
writes do not become public goals, and that disallowed-goal cancellations retain
their actual order relative to commentary. Per-kind timestamp checks alone do
not establish cross-kind event order. Pin the accepted regression commands during
T62 preflight; these candidate findings do not authorize local kit fixes.

[derived: T62 accepted-source preflight, archaeology PR251 merge
`3656a2d26e0f57a410d648edeaa6cd9eb7d1f607`] The exact handoff inputs,
verification procedure and mapped evidence are in
[watched-kit-acceptance.md](watched-kit-acceptance.md). Historical candidate pins
above explain the planning/review gates; they are never production pins.
Application integration still follows T63-T66 and their independent acceptance.
