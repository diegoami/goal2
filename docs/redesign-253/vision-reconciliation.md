# Reconciliation with the accepted vision (#266) and the approved queue

[designed: owner ‘Ok do as proposed’, 2026-10-20] This is the operative record of how the #253 candidate plan (PR #258) was reconciled to the accepted destination and the owner-approved queue. Sources: [accepted vision #266 / merged PR #267](https://github.com/diegoami/goal2/issues/266#issuecomment-6287825622), the [approved issue audit and dependency order](https://github.com/diegoami/goal2/issues/253#issuecomment-6287891360), the [applied queue](https://github.com/diegoami/goal2/issues/253#issuecomment-6288245660), the [triage record](https://github.com/diegoami/goal2/issues/253#issuecomment-6288421712) and the [rework steer on PR #258](https://github.com/diegoami/goal2/pull/258#issuecomment-6288226799). This reconciliation records a plan. It does not file, edit, close or relabel an issue, authorize any implementation or merge the candidate unchanged.

## What was replaced and what was kept

| Candidate element (PR #258 head `bd878531`) | Status after reconciliation |
| --- | --- |
| Recommendation “A — Country desk”, with a paper/ink/emerald identity and a darker match header | [designed] **Replaced** by the accepted original-first direction. Kept only as reviewed historical evidence in [decisions.md](decisions.md#historical-candidate-directions-superseded) and [layouts.md](layouts.md). |
| Owner questions asking to choose among A/B/C or to approve the paper/emerald look (old O01) | [designed] **Resolved** by the owner’s acceptance on #266. Not asked again. |
| Ten candidate layouts `layouts/01…10` presented as the proposed screens | [designed] **Superseded**: every one maps to an accepted screen below, is marked historical and is not a recommendation. Files and receipts are unchanged. |
| 234-source inventory (SHA256 `d69ee5bff1afde58e0de4d0235b8bc63cb7d73d8be6761b687fa78523cf34282`), 237 allocations, 23 contexts, 17 categories | [confirmed: unchanged bytes, checked by `validate.py --check parity`] **Kept.** The destination column still names surfaces S01–S15; the tables below map those surfaces to the accepted screens. |
| Capability boundaries G01–G05, LI08, B06/B07 and the current-build audit at `3335da83` | [designed] **Kept.** Scope gaps stay explicit under this issue ([ownership table](#scope-gaps-and-their-owners)). |
| Backlog B01–B07 and the milestone order M0–M4 | [designed] **Reconciled** to the approved lanes ([queue](#approved-queue)). The local contracts under [backlog/](backlog/) now mirror the live amended bodies of #259–#265. |
| Technology recommendation | [designed] **Kept as a recommendation, not a selection**: Python backend; Widgets plus the accepted SDL boundary unless measured proof fails a concrete requirement. See [technology.md](technology.md). |

## The accepted direction

[designed: owner direction on #266, accepted] The owner-selected target is an **installable desktop game that looks like the original**: black screens; strong, varied functional colors; large characters; information directly in view; complete graphical (segmented) attribute bars with the raw original value beside each; maximum-size pitch during play; full commentary hidden by default with the latest two lines visible; and independently retractable top and side bars with a reliable restore path. “In doubt, it should look like the original.” The authoritative description is [docs/vision-266/README.md](../vision-266/README.md); the nineteen illustrations are in [the storyboard](../vision-266/storyboard.md), its [evidence](../vision-266/evidence.md) and [validation](../vision-266/validation.md). Pinned at merge commit `9683a47647f21bd2a3274ea5dc56bb8c14e6c5a9`. All nineteen are finished-target illustrations with fictional data; none is a current capture or an executable prototype.

| Accepted requirement | Where the accepted screens show it | Where this plan carries it |
| --- | --- | --- |
| Black, large, strongly colored original-style screens; attribute bars | [03](../vision-266/screens/03-team.png), [04](../vision-266/screens/04-pool.png), [07](../vision-266/screens/07-half-time.png) | [#242](https://github.com/diegoami/goal2/issues/242) cards/bars, [#261](https://github.com/diegoami/goal2/issues/261) shell, Team and pool |
| Maximum-size pitch; default-hidden commentary with the latest two lines | [06](../vision-266/screens/06-watched.png) default, [15](../vision-266/screens/15-watched-drawers.png) opened | [#198](https://github.com/diegoami/goal2/issues/198), [#262](https://github.com/diegoami/goal2/issues/262) |
| Independently retractable top and side bars, restore without losing selection, draft, scroll or focus | [14](../vision-266/screens/14-team-focus.png), [02](../vision-266/screens/02-country-desk.png) handles | [#261](https://github.com/diegoami/goal2/issues/261), [#262](https://github.com/diegoami/goal2/issues/262), [#263](https://github.com/diegoami/goal2/issues/263) acceptance |
| Small-window panes instead of shrunken text | [11](../vision-266/screens/11-small-window.png), [17](../vision-266/screens/17-small-roster.png) | [#259](https://github.com/diegoami/goal2/issues/259) geometry proof, [#261](https://github.com/diegoami/goal2/issues/261) |
| Plain refusals and recoverable errors | [12](../vision-266/screens/12-unavailable-errors.png) | [#260](https://github.com/diegoami/goal2/issues/260), [#262](https://github.com/diegoami/goal2/issues/262) |
| Longer career and later squad | [10](../vision-266/screens/10-career.png), [18](../vision-266/screens/18-later-squad.png), [19](../vision-266/screens/19-campaign.png) | career stream (lane 4) and G03/G05 |

[designed] The surface names S01–S15 and journeys J01–J09 of the candidate are retained as **logical** structure (they key the parity destinations); their presentation is the accepted top/side-bar desktop. The accepted navigation reads Country · Team · Fixtures · Match · History · Save · F1 Help: Fixtures is the candidate’s Competition (S07), History its Archive (S12), Save its Game menu (S13), and Match covers Preparation, Live, Decision and Result (S08–S11). Where an accepted screen and a candidate label differ, the accepted screen governs.

## Surface-to-screen mapping

[designed] Coverage is stated honestly: **drawn** means an accepted screen illustrates the surface; **partial** means part of it is drawn; **undrawn** means the accepted nineteen show it only as a route or not at all. A partial or undrawn surface is not a request to invent a screen here. The owning task adds the missing screen to its own contract before dispatch. “Allocations” counts the parity destinations that name the surface (an allocation may name several), so it shows how much of the 237-allocation matrix lands there.

| Surface | Coverage | Accepted screens | Not yet drawn, and its bounded owner | Allocations |
| --- | --- | --- | --- | --- |
| S01 Launch | drawn | 01 | — | 6 |
| S02 New career | partial | 01 | Country preview, manager identity and review-before-start are not drawn. #260 adds the screen in its contract; G05 profile data and #265 editable identity stay separate. | 36 |
| S03 Country desk | drawn | 02, 09 | — | 70 |
| S04 Team | drawn | 03, 11, 14, 16, 17, 18 | — | 57 |
| S05 Pool comparison | drawn | 04 | — | 37 |
| S06 Country profile and scout | undrawn | route only from 02, 05 | #261 composes the route and adds the screen to its contract; complete profile data is unowned G05. | 62 |
| S07 Competition | partial | 19, 09 | Group selector, bracket and scorers are routes only. #249 supplies available data; #261 composes the routes. | 24 |
| S08 Preparation | drawn | 05 | — | 106 |
| S09 Live | drawn | 06, 15 | — | 29 |
| S10 Decision | drawn | 07, 13 | — | 62 |
| S11 Result | drawn | 08 | — | 27 |
| S12 Archive | partial | 10, 18, 19 | Retained-match browser (#251) and replay tab (unowned G04); full records unowned G05. | 69 |
| S13 Game save/load | partial | 01, 09, 12 | Save as, overwrite and Quit dialogs: #260. | 18 |
| S14 Bulletin | partial | 19 | Generation, retention and news detail: unowned G03; #249 only browses information already held. | 8 |
| S15 Local-manager handoff | undrawn | — | #264 scopes the contract; delivery unowned. | 0 |

## Parity destinations by original context

[designed] The 237 allocations keep their S01–S15 destinations. This table shows, for each of the 23 original contexts, which surfaces its allocations name and which accepted screens draw them; the last column lists the surfaces the accepted set draws only partly or not at all, whose bounded owners are in the surface table above. The rows are recomputed from the destination matrix and the surface registry by `validate.py --check vision`. A drawn surface still needs its fields reachable there: the [parity matrices](information-parity.md) remain the field-level contract.

| Context | Surfaces named | Accepted screens | Not fully drawn |
| --- | --- | --- | --- |
| ST | S01, S02 | 01 | partial S02 |
| CO | S02, S03, S06, S08 | 01, 02, 05, 09 | partial S02; undrawn S06 |
| CS | S02, S06, S08 | 01, 05 | partial S02; undrawn S06 |
| CC | S04, S06 | 03, 11, 14, 16, 17, 18 | undrawn S06 |
| HU | S03 | 02, 09 | none |
| PI | S04, S05, S06, S08, S10 | 03, 04, 05, 07, 11, 13, 14, 16, 17, 18 | undrawn S06 |
| SK | S04, S05, S06, S08, S10 | 03, 04, 05, 07, 11, 13, 14, 16, 17, 18 | undrawn S06 |
| PC | S04, S05, S06, S08, S10 | 03, 04, 05, 07, 11, 13, 14, 16, 17, 18 | undrawn S06 |
| PT | S04, S08, S10 | 03, 05, 07, 11, 13, 14, 16, 17, 18 | none |
| TT | S02, S04, S06, S08 | 01, 03, 05, 11, 14, 16, 17, 18 | partial S02; undrawn S06 |
| SD | S04, S05, S08 | 03, 04, 05, 11, 14, 16, 17, 18 | none |
| FX | S03, S07, S08 | 02, 05, 09, 19 | partial S07 |
| TB | S03, S07 | 02, 09, 19 | partial S07 |
| BR | S07 | 09, 19 | partial S07 |
| HI | S12 | 10, 18, 19 | partial S12 |
| HR | S12 | 10, 18, 19 | partial S12 |
| NW | S03, S12, S14 | 02, 09, 10, 18, 19 | partial S12, S14 |
| MP | S08 | 05 | none |
| LI | S09 | 06, 15 | none |
| IN | S09, S10 | 06, 07, 13, 15 | none |
| PR | S08, S10, S11, S13 | 01, 05, 07, 08, 09, 12, 13 | partial S13 |
| RS | S03, S11, S12 | 02, 08, 09, 10, 18, 19 | partial S12 |
| SV | S12, S13 | 01, 09, 10, 12, 18, 19 | partial S12, S13 |

## Journey-to-screen mapping

| Journey | Accepted screens | Note |
| --- | --- | --- |
| J01 First launch, new career or load | 01, 12 | Manager naming and country-profile review remain S02 gaps. |
| J02 Country desk and next action | 02, 09 | |
| J03 Squad, pool, instructions, confirmation | 03, 04, 11, 14, 16, 17 | Attribute table and 38/37-column views remain accepted contracts (#242). |
| J04 Prepare for a competition, scout an opponent | 02, 05, 19 | Opponent scout pane is S06 undrawn. |
| J05 Choose Quick or Watch | 05, 12 | Competitive Watch refusal is drawn in 12. |
| J06 Watched play and supported intervention | 06, 15, 07 | Finish quickly stays unavailable: LI08/G01. |
| J07 Half-time, extra time, shoot-out | 07, 13 | Conditional states, not routine screens. |
| J08 Result, wider round, next campaign | 08, 09, 10, 18, 19 | |
| J09 Save, resume, quit, local handoff | 01, 09, 12 | Handoff is S15 undrawn. |

## Superseded candidate layouts

[designed] The ten sheets under [layouts/](layouts/) were the candidate’s recommended screens. They stay as reviewed, hash-pinned historical evidence (their [bounds receipt](evidence/layout-bounds-05.json) is unchanged) and carry no recommendation. Nothing in them overrides an accepted screen.

| Candidate sheet | Accepted successor |
| --- | --- |
| 01 country setup | 01 start/resume (partial: country preview and manager review not drawn) |
| 02 country desk | 02 country desk |
| 03 team workspace | 03 team, 14 team focus, 16 team tactics |
| 04 pool compare | 04 pool |
| 05 competition | 19 campaign, 09 continue (partial) |
| 06 match preparation | 05 preparation |
| 07 live match | 06 watched, 15 drawers |
| 08 result and campaign | 08 result, 09 continue |
| 09 small window | 11 small window, 17 small roster |
| 10 match decisions | 07 half-time, 13 conditional |

[designed] Accepted screens 10, 12, 14, 16, 18 and 19 have no candidate predecessor. The candidate’s illustration contexts (scenarios A–D, Q, SETUP) are retired with the sheets; the accepted storyboard’s single Holland/Alex story replaces them. Its fictional Holland/Alex identity is illustrative and must not become a fixed production identity ([#260](https://github.com/diegoami/goal2/issues/260)).

## Approved queue

[designed: owner-approved, 2026-10-20] Lanes 1–5 below are the approved order. Per-issue priorities, areas, milestones and difficulty are on the issues; the [triage record](https://github.com/diegoami/goal2/issues/253#issuecomment-6288421712) is the source. Priority orders the queue and does not mean implementation has started; each task still needs its bounded preflight and the repository’s implementer and reviewer choice.

| Lane | Work | Issues | Rule |
| --- | --- | --- | --- |
| 1 Now | Reconcile this plan; prepare bounded cloud slices | [#253](https://github.com/diegoami/goal2/issues/253) (this package), [#270](https://github.com/diegoami/goal2/issues/270) P0 cloud issue; [#208](https://github.com/diegoami/goal2/issues/208)/[#268](https://github.com/diegoami/goal2/issues/268) keep their own narrow tooling scope | #270 is referenced, not implemented or pre-split here. |
| 2 Existing foundations | Native validation, complete cards/bars, Play/Watch/speed; proofs | [#198](https://github.com/diegoami/goal2/issues/198) (PR #240; #254/#255 resolved), [#242](https://github.com/diegoami/goal2/issues/242), [#243](https://github.com/diegoami/goal2/issues/243), [#259](https://github.com/diegoami/goal2/issues/259) | Existing author/reviewer choices persist. #259 is split into consuming proofs. |
| 3 First supported session | Launch/Resume, shell and Team/pool, preparation/pitch/result/Continue | [#260](https://github.com/diegoami/goal2/issues/260), [#261](https://github.com/diegoami/goal2/issues/261) (split shell and Team/pool), [#262](https://github.com/diegoami/goal2/issues/262); [#249](https://github.com/diegoami/goal2/issues/249) available-information slice; [#263](https://github.com/diegoami/goal2/issues/263) first-slice oracles alongside; [#251](https://github.com/diegoami/goal2/issues/251) retained-history browsing | The first release is smaller than full parity. |
| 4 Independent career stream | Real national career | [#110](https://github.com/diegoami/goal2/issues/110), [#112](https://github.com/diegoami/goal2/issues/112), [#113](https://github.com/diegoami/goal2/issues/113), [#114](https://github.com/diegoami/goal2/issues/114), [#115](https://github.com/diegoami/goal2/issues/115), [#116](https://github.com/diegoami/goal2/issues/116), [#117](https://github.com/diegoami/goal2/issues/117), [#118](https://github.com/diegoami/goal2/issues/118), [#119](https://github.com/diegoami/goal2/issues/119); [#155](https://github.com/diegoami/goal2/issues/155) | UI cosmetics are not part of this stream’s order. |
| 5 Full parity | Supported decisions, retained records, assistant/identity, local managers | [#248](https://github.com/diegoami/goal2/issues/248), [#250](https://github.com/diegoami/goal2/issues/250), [#251](https://github.com/diegoami/goal2/issues/251) (records and separately scoped replay), [#265](https://github.com/diegoami/goal2/issues/265), [#264](https://github.com/diegoami/goal2/issues/264), plus the scope gaps below | P3 polish and legacy maintenance are outside the delivery critical path and have no delivery milestone. |

### Approved dependencies

[designed: owner-approved queue, 2026-10-20] Dependency order is stated **only** in the two tables below (and mirrored in `package.json`); the lane rows above list issues without order. `validate.py --check vision` parses these rows and requires them to equal its independent list of the approved pairs: a reversed, missing or extra row fails, and so does a reverse arrow between issues or an order word that contradicts them elsewhere in this file. “#262” is the base match journey. The tables do not order #249, #263, lane 1 or lane 5, because the approved queue states no order for them. UI cosmetics are not part of the career stream’s order.

| Before | After | Source |
| --- | --- | --- |
| #198 | #242 | lane 2 |
| #198 | #243 | lane 2 |
| #260 | #261 | lane 3 |
| #261 | #262 | lane 3 |
| #262 | #251 | lane 3 |
| #110 | #112 | lane 4 |
| #112 | #113 | lane 4 |
| #113 | #114 | lane 4 |
| #114 | #115 | lane 4 |
| #115 | #116 | lane 4 |
| #116 | #117 | lane 4 |
| #117 | #118 | lane 4 |
| #118 | #119 | lane 4 |
| #155 | #117 | lane 4 |

| Not a prerequisite | Of | Source |
| --- | --- | --- |
| #259 | #198 | lane 2 |
| #259 | #242 | lane 2 |
| #259 | #243 | lane 2 |

## Scope gaps and their owners

[designed: owner amendment] These are planning obligations of #253, not capabilities silently assigned to page-composition issues. Each row names a bounded owner or states plainly that it is unowned and needs a bounded contract before any full-parity claim. No fabricated action and no blanket parity exception is approved. The [gap register](capability-gaps.json) keeps the field membership; [decisions.md](decisions.md#unowned-capability-decisions) keeps the owner choices.

| Obligation | Bounded owner today | Before a full-parity claim |
| --- | --- | --- |
| G01 broader, competitive and other-country Watch, watch flags, in-flight Quick switching | None. #250 only audits supported interventions and may deliver the first one; #243 owns entry and frozen speed; #249 only displays held data. | Unowned: needs a bounded contract. |
| G02 friendly rearrangement | None. #249 may display a schedule; it grants no scheduling mutation. | Unowned: needs evidence of the actual schedule and state behavior, then a bounded contract. |
| G03 generated and retained bulletins | None. #249 browses only information already held. | Unowned: needs a bounded contract. |
| G04 durable match-summary and goal capture, export, replay | None. #251 browses already retained summaries read-only. | Unowned: needs a bounded contract. |
| G05 complete country profiles, history, records | None for the full projection. #249 shows existing fixture, group and opponent data; #115 owns ranking transitions only; #242 owns player projections. | Unowned: needs a bounded contract. |
| O13 country aggregate and result-row encodings; meaning of a nonblank performance value | None. Accepted screens 08 and 16 label these “Meaning unverified”; the player-skill projection of #242 does not establish them. | Unowned: needs a bounded original-evidence contract. No percentage or rating is invented meanwhile. |
| O14 actual assistant, identity and local-manager delivery | [#265](https://github.com/diegoami/goal2/issues/265) and [#264](https://github.com/diegoami/goal2/issues/264) own **contracts only**. | Delivery is unowned until a bounded implementation contract exists. A contract, placeholder or unavailable label is not parity. |

## Open owner choices

[designed] The direction is **not** asked again. These remain open and are stated in product terms on [decisions.md](decisions.md#decisions-for-the-owner): O02 whether the desktop toolkit stays PySide6 Widgets plus the SDL pitch unless measured proof fails a concrete requirement; O03 (resolved by the owner, 2026-10-20: two coordinated windows for the first release); O04 (resolved by the owner, 2026-10-20: the bounded first supported session, lane 3; no original category is excluded from the complete product); O05 whether local managers come after the first release; O06 which accepted departures from the original stand; O07 which platforms and window sizes the product must support. The window and toolkit choices need the measured proof of [#259](https://github.com/diegoami/goal2/issues/259); the design choice implies no migration.

## Evidence boundaries

[confirmed: validate.py --check vision] The accepted screens are checked by byte-identity against the pinned merge commit, not by this plan. Static images are not runtime evidence, and a retracted bar or a drawn bar does not prove a toolkit can render it. Original observations, printed hints, unresolved meanings, current-build facts and designed choices stay distinct, as in the vision and the parity inventory.
