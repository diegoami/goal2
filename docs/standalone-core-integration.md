# Standalone match engine: Core integration design

[designed: owner, 2026-10-25; goal2 #393] Integrate the current desktop Core first.
Adoption by the older watched worker is optional and needs a separate contract. This design
allocates consumer tasks; implementation requires the accepted upstream delivery. The original
whole-game Core remains the first-release architecture (#308). A match engine does not replace
the campaign, menus, calendar or news. There is no automatic default switch.

## Audited boundaries

[derived: goal2 3f9f8cd7a8fec38c0c9e9276bf8d299b396bbfca; G15 merge
a76a47dfbcc4870a89f8e8a6f3b3846fc275c037] `CoreModel.round_step` calls the original-key
Driver/Core under `live_frames`; `CoreJobs` supplies its worker thread. It bypasses
`watched_worker`/`WatchedJobs`. Replacing the vendored Match cannot replace this path.
See `goal2/desktop/core_model.py`, `goal2/core/{driver,runner}.py`.

[derived: same pins; vendored provenance in PROVENANCE.md] The kit names run_match
`0791:F1F6`, return `000E:6F1D`, and player update `0791:B7FA`, return `000E:6FFD`.
`Match._advance` runs both calls; `_call` constructs ENTRY_BP/SP. Those constants do not
establish an arbitrary live Core frame. The candidate natural far call at `000E:6F18` must be
qualified against the source and actual entry. Archaeology
[#427](https://github.com/diegoami/goal2-archaeology/issues/427) requests a supported input,
write-set, return ABI and original-caller continuation contract, or an explicit unsupported answer.
No capture hook or external return is implemented by this design.

[derived: same pins; `goal2/game/{watched_match,watched_pitch,watched_publication,watched_schema}.py`]
The older worker serializes a template/Image, reads `opts`, `_squad` and guest pitch data, then
installs completed returned records privately. Its publication transaction checks owner identity,
waits for frame acknowledgements and swaps state once. It separately advances Python campaign
ledgers/silent fixtures. Preserve the transaction principle; do not copy those campaign updates
into a whole-game Core whose original caller advances the calendar itself.

## Proposed ownership

[designed: #393] The accepted upstream API and #427 must confirm every row before coding.
Unspecified fields or continuations block acceptance; this matrix is not a guessed ABI.

| State or action | Proposed single owner | Consumer rule |
| --- | --- | --- |
| Pre-match original management and natural entry frame | Original Core | Capture before setup, freeze memory/CPU/keys and session identity |
| Canonical request and policy identity | T125 adapter | Explicit IDs/order, fixture/year, choices, budgets and named RNG; no image/code buffer |
| Match setup/reseeding, events, decisions, match and delivered player-update tail | Sealed engine | Execute once, under the exact delivered public contract |
| Returned player/country/squad/tactic/result/RNG and non-record effects | T126 candidate / T127 bridge | Validate every field and full authorized write set privately; no second quick/original tail |
| Live result installation | T130 session transaction | One acknowledged, validated commit to the unchanged frozen owner |
| Fixture/calendar progression, news and management continuation | Original caller | Resume only at the verified post-engine boundary; no legacy Python campaign advancement |
| Views and manager answers | T128 worker / T131 desktop | Public immutable snapshots and ordered protocol; never a guest-memory fallback |
| In-flight save ownership | T129 envelope | Frozen Core plus backend-bound engine state, decision/event/watermark and commit phase |

[derived: same pins; `goal2/game/state.py`, `watched_match.py`, `goal2/core/runner.py`]
GameState has 3061 player records of 20 bytes and 129 country records of 191 bytes, plus
selection/campaign metadata and raw Memory/VGA. Existing result identities use image_sha256.
The records request needs a distinct canonical-input identity. Match outcome RNG names are
DS7B62/8336; Core save headers separately expose DS7B62/7B64 and retain all memory. Never map
these pairs by position. Original fixture index and engine year participate in setup reseeding.

## Delivery and saves

[designed: owner clarification, 2026-10-25] Extracted information may be public. The exact
table/display/commentary extracts, generation recipe and provenance must be identified in the
delivery. This permission does not publish original executables, opaque original memory images,
original savestates or personal saves. Package and table hashes must be reproducible. The prior
T80 assumption about the obsolete #253 package is not goal2's architecture.

[designed: #393] Accept T78/T79/T80 only through the reviewed merged pin, complete file/helper/
dependency/table manifest, exact public records and view API, strict fidelity and event-boundary
resume evidence, timings, discrepancy dispositions and scope limits. m4-port-ui-frontier is a
Unicorn-backed baseline, not that delivery. Vendor byte-for-byte; defects return upstream.
The sealed backend child must run with Unicorn import and original executable/data/savestate
access denied; the surrounding existing Core retains its dependencies.

[derived: audited pins] G2C1 Core saves, OMK1 kit checkpoints and completed session saves have
different identities. [designed: #393] Keep historical saves on their recorded backend. The new
active envelope binds package/table/API/schema, canonical input, engine native state or answer
replay, pending decision/event position, frame watermark and commit phase to the frozen Core.
Reject incompatibility before mutation. Cross-backend migration is not scheduled. Completion
before/after acknowledgement and resumed completion must never commit twice.

## Numbered consumer sequence

[designed: #393] All numbers are goal2 numbers, separate from archaeology's T78–T80. GitHub
labels remain authoritative; task files carry contracts, not completion status. Proposed test
modules in these contracts do not exist and have not run. Each implementation records their
fail-before/pass-after, mutation sensitivity, exact-head gates and applicable native acceptance.
Refine/split any slice exceeding an hour or three independently mergeable layers once the
accepted API is concrete; do not weaken its Done-when.

| Contract | Dependency | Acceptance focus |
| --- | --- | --- |
| [T124](tasks/T124.md), #397 | Accepted upstream delivery | Complete provenance, public extracts, isolated no-original/no-Unicorn execution |
| [T125](tasks/T125.md), #398 | T124 + #427 input contract | Complete canonical input round trips; zero mutation on refusal |
| [T126](tasks/T126.md), #399 | T125 + #427 output contract | Private candidate, complete effects/write-set validation |
| [T127](tasks/T127.md), #400 | T126 + #427 ABI | Natural entry and complete original/external return-state proof |
| [T128](tasks/T128.md), #401 | T124/T125 | Isolated Core worker, public events/views/answers, cancellation/reaping |
| [T129](tasks/T129.md), #402 | T127/T128 | Every-event/decision save/resume and provenance refusal |
| [T130](tasks/T130.md), #403 | T126–T129 | One commit, original caller continuation, no duplicated setup/tail/calendar/RNG |
| [T131](tasks/T131.md), #404 | T130 | Real desktop controls/guards/bounds and Qt/SDL acknowledgement |
| [T132](tasks/T132.md), #405 | T131 | Strict application differential and resumed equivalence |
| [T133](tasks/T133.md), #406 | T132 | Native Linux/Windows lifecycle, measured rollout proposal |

[designed: #393] Differential cases include friendly/competitive, either managed side and
supported unmanaged fixtures, finals regression, owner-policy substitutions/refusals/no-re-entry,
extra time, shootout order and straight/resumed execution. Compare ordered canonical events,
results, all returned records, named RNG and resumed caller state. Document representation-only
projections without weakening upstream strict fields. Preserve synthetic versus natural evidence
and archaeology #416's unvisited-boundary limits. T79 statistical measurement cannot substitute
for per-match equality or authorize ignoring differences.

## Coordination and owner decisions

[designed: consumer requests, 2026-10-25] Public API/effects/views/save requests are posted on
[T78](https://github.com/diegoami/goal2-archaeology/issues/289#issuecomment-6394281159),
strict discrepancy acceptance on
[T79](https://github.com/diegoami/goal2-archaeology/issues/290#issuecomment-6394281282), and
packaging/records/provenance/handover requirements on
[T80](https://github.com/diegoami/goal2-archaeology/issues/291#issuecomment-6394281425).
The separate [#427](https://github.com/diegoami/goal2-archaeology/issues/427) defines the missing
Core bridge request. An unsupported bridge leaves Core integration blocked; it does not authorize
substituting the older worker or a new campaign implementation.

[designed: owner, 2026-10-25] Core first and public extracted information are settled. Default
selection/performance thresholds remain a later owner decision after evidence. No automatic
cross-backend save migration is proposed. The integrated independent milestone review and owner
Windows playtest precede a separately contracted default-selection change. The first-release
queue (#308) continues independently of this long-term planning work.
