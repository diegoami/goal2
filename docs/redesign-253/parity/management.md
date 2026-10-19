# Information parity: management

[confirmed: accepted manual ebdd6879d469a574f6d4b446f59b33a6be3ffd81 and cited records] Original fields below are observed labels/states unless explicitly text-supported, printed-only or unknown. [designed: #253] Destinations/access/owners are proposals, not shipped features. Context statements apply to every field in their following table. See [matrix rules](../information-parity.md).

## Start and session · ST

[confirmed: E031 C11–C16b; M244-G1A-01 steps0–2; E015-r0008 state10] **observed+hint**. Original comparisons: [title-player-count](../../original-game/images/title-player-count.png), [m244-load-name](../../original-game/images/m244-load-name.png), [file-not-found-prompt](../../original-game/images/file-not-found-prompt.png).

[designed] **When/why:** At launch: distinguish starting a career from continuing one; avoid replacing the active game. **Discoverability:** Launch direct; country detail direct; load picker1 action. **Delivery:** B02/B06/B07. **Limits:** One manager supported in rebuild; offered3–6 unexercised in original. Retry text is printed; exact original error recovery unverified. No GL compatibility promised.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| ST01 | New game versus load existing game | [designed] S01/S02 | [designed] B02/B07 |
| ST02 | Local manager count: offered1–6; two exercised | [designed] S01/S02 | [designed] B07 |
| ST03 | Selected manager number, country and manager name | [designed] S01/S02 | [designed] B02/B06/B07 |
| ST04 | Manager name entry; original maximum14 characters | [designed] S01/S02 | [designed] B02/B06 |
| ST05 | Load list for several saves / prefilled single-save name | [designed] S01/S02 | [designed] B02/B07 |
| ST06 | Missing-file explanation and try-again choice | [designed] S01/S02 | [designed] B02/B07 |

## Country context · CO

[confirmed: E015-r0007 states3/10; M244-G4C-05 step3; E031 C13–C14b] **observed**. Original comparisons: [country-select](../../original-game/images/country-select.png), [country-select-name-entry](../../original-game/images/country-select-name-entry.png), [m244-team-info-2030](../../original-game/images/m244-team-info-2030.png).

[designed] **When/why:** Before choosing a country or scouting an opponent: judge challenge, experience and the side being managed. **Discoverability:** Identity/rank/difficulty direct; complete profile1 labelled action. **Delivery:** #249. **Limits:** Profile source and persistence audit required. Ranking top is retained under its original label until semantics established. Status/skill/difficulty formulas and strip glyph encoding are not inferred; generic decorative shirt is not an authentic kit.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| CO01 | Country identity / country list / selected row | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO02 | Country status text (e.g. major, very good) | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO03 | Country manager identity | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO04 | Manager skill text and adjacent bar | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO05 | World ranking now | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO06 | World ranking top | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO07 | Continental ranking now | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO08 | Continental ranking top | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO09 | World versus continental list order | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO10 | Difficulty category: SIMPLE / EASY TASK / TOO EASY / QUITE EASY | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO11 | Formation name | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO12 | Strip symbols / displayed team identity | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO13 | Average international caps | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |
| CO14 | Average age | [designed] S02/S06; ranking summary S03/S08 | [designed] #249 |

## Country context · CS

[confirmed: E015-r0007 state3; M244-G4C-05 step3] **observed**. Original comparisons: [country-select](../../original-game/images/country-select.png), [m244-team-info-2030](../../original-game/images/m244-team-info-2030.png), [team-tactics](../../original-game/images/team-tactics.png).

[designed] **When/why:** Compare squad strengths and displayed performance before choosing team, tactics or opponent approach. **Discoverability:** All8 labelled rows together; no hidden tooltip-only numbers. **Delivery:** #249. **Limits:** Original bars visible, scale and performance derivation unknown. Preserve separate groups; do not substitute aggregate Ability or invent percentages.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| CS01 | Team skills: keeper | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS02 | Team skills: defence | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS03 | Team skills: midfield | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS04 | Team skills: attack | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS05 | Team performance: keeper | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS06 | Team performance: defence | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS07 | Team performance: midfield | [designed] S02/S06 profile; comparison S08 | [designed] #249 |
| CS08 | Team performance: attack | [designed] S02/S06 profile; comparison S08 | [designed] #249 |

## Country context · CC

[confirmed: M244-G1A-02 step11; E015-r0007 state3] **observed**. Original comparisons: [country-select](../../original-game/images/country-select.png), [m244-team-tactics](../../original-game/images/m244-team-tactics.png).

[designed] **When/why:** Inspect team condition and tendencies before confirming a tactical plan. **Discoverability:** Four labelled rows direct in team profile; summary at Team. **Delivery:** #249. **Limits:** Original verbal labels/bars do not establish numeric units. Rebuild calculated morale is a distinct documented projection.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| CC01 | Team hardness | [designed] S06 team profile; S04 team-tactics context | [designed] #249 |
| CC02 | Team fitness | [designed] S06 team profile; S04 team-tactics context | [designed] #249 |
| CC03 | Team energy | [designed] S06 team profile; S04 team-tactics context | [designed] #249 |
| CC04 | Team morale | [designed] S06 team profile; S04 team-tactics context | [designed] #249 |

## Country desk · HU

[confirmed: E015-r0007 state16; M244-G1A-02 step2; M244-G1E-06 step19; E031 C16–C21/C54–C55] **observed+text**. Original comparisons: [manager-menu](../../original-game/images/manager-menu.png), [m244-holland-menu](../../original-game/images/m244-holland-menu.png), [m244-finals-stage-hub](../../original-game/images/m244-finals-stage-hub.png).

[designed] **When/why:** After every round: understand who/when/why to prepare and the next available action. **Discoverability:** Direct next-fixture/context/availability; roster preview direct; full roster1 action. **Delivery:** B03/#249/B07. **Limits:** No empty Play dead end. Actual next supported fixture drives action. Manager rating/host and handoff require source/capability audit; no invented dismissal or reassignment.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| HU01 | Active managed country, manager name and manager rating | [designed] S03 | [designed] B03/#249/B07 |
| HU02 | Campaign year and competition/stage title | [designed] S03 | [designed] B03/#249/B07 |
| HU03 | Competition host/location in title | [designed] S03 | [designed] B03/#249/B07 |
| HU04 | Next opponent identity | [designed] S03 | [designed] B03/#249/B07 |
| HU05 | Next opponent world and continental ranks | [designed] S03 | [designed] B03/#249/B07 |
| HU06 | Next fixture type and home/away | [designed] S03 | [designed] B03/#249/B07 |
| HU07 | Twenty-player squad strip; XI and bench split; position codes | [designed] S03 | [designed] B03/#249/B07 |
| HU08 | Managers list / active manager / next player action | [designed] S03 | [designed] B07 |
| HU09 | No next opponent; advance remaining round and stage | [designed] S03 | [designed] B03/#249/B07 |

## Player card · PI

[confirmed: M244-G1A-02 steps3–6; E031 C34–C34b; E015-r0007 state76] **observed+text**. Original comparisons: [m244-squad](../../original-game/images/m244-squad.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-pool](../../original-game/images/m244-pool.png), [squad-substitution-take-off](../../original-game/images/squad-substitution-take-off.png).

[designed] **When/why:** When picking XI, comparing a reserve, captain or substitute: identity, eligibility and role must be beside the choice. **Discoverability:** Selected card direct; comparison pins two cards; small window labelled card pane. **Delivery:** #242. **Limits:** T84 field contract owns decoding/display. Exact original performance and card-box rendering unresolved: explicit unavailable text, never fabricated stars/percentages. Opponent card stays read-only.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| PI01 | Player name | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI02 | Age | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI03 | International caps | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI04 | International goals | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI05 | Height | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI06 | Bias / dominant foot | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI07 | Current national position | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI08 | Club position | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI09 | Performance box | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI10 | Card/discipline boxes | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |
| PI11 | Readiness: ready, selected, on bench, injured, suspended | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 |

## Player skills · SK

[confirmed: M244-G1A-02 steps3–6; M244-G4C-05 step4; F008 source contract in T84] **observed**. Original comparisons: [m244-squad](../../original-game/images/m244-squad.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-pool](../../original-game/images/m244-pool.png), [m244-team-info-players-2030](../../original-game/images/m244-team-info-players-2030.png).

[designed] **When/why:** Compare relevant skills for XI/role, reserve exchange, captain, taker or substitution without leaving the decision. **Discoverability:** All12 labels in card; compact table plus Show all attributes retained; numeric domains only per T84. **Delivery:** #242. **Limits:** Bars permit comparison. Exact numeric decoding comes from T84/F008, not image color. Never collapse12 skills into Ability; no invented1–100 scale.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| SK01 | Keeping | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK02 | Kicking | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK03 | Tackling | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK04 | Heading | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK05 | Marking | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK06 | Passing | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK07 | Crossing | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK08 | Feinting | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK09 | Control | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK10 | Dribbling | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK11 | Shooting | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| SK12 | Penalties | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |

## Player characteristics · PC

[confirmed: M244-G1A-02 steps3–6] **observed**. Original comparisons: [m244-squad](../../original-game/images/m244-squad.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-pool-next](../../original-game/images/m244-pool-next.png).

[designed] **When/why:** Before committing a selection: compare temperament, condition and captain suitability in the same view. **Discoverability:** All5 together; Energy/readiness remain in roster rows. **Delivery:** #242. **Limits:** Keep fitness versus energy and morale versus rebuild Confidence distinct. Use T84 verified domains; unknown original descriptive buckets are unavailable, not guessed.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| PC01 | Hardness | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| PC02 | Fitness | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| PC03 | Energy | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| PC04 | Morale | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |
| PC05 | Leadership | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 |

## Personal tactics · PT

[confirmed: M244-G1A-02 step8; M244-G1A-04 steps5–12; E031 C31–C33d; E015-r0007 states165–166] **observed**. Original comparisons: [m244-individual-tactics](../../original-game/images/m244-individual-tactics.png), [m244-position-tactic-toggle](../../original-game/images/m244-position-tactic-toggle.png), [mark-protect-zone](../../original-game/images/mark-protect-zone.png), [mark-named-opponent](../../original-game/images/mark-named-opponent.png), [m244-position-next](../../original-game/images/m244-position-next.png), [m244-position-club](../../original-game/images/m244-position-club.png).

[designed] **When/why:** Choose how this player behaves and whom to mark before the match or at an allowed intervention. **Discoverability:** Selected player and all instructions direct; opponent-picker1 action beside both cards. **Delivery:** #248. **Limits:** T84 owns read-only projection; #248 owns supported edits. P meaning stays unknown; separate from possession. No invented formation algorithm or live mark context. Named mark resets only when supported source contract establishes it.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| PT01 | Position instruction (stay back / push forward etc.) | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT02 | Possession instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT03 | Passing instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT04 | Tackling instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT05 | Mark: Protect zone / named opponent | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT06 | Named opponent role beneath mark | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT07 | Trailing P display flag | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |
| PT08 | Current role change and restore club role | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 |

## Team tactics · TT

[confirmed: M244-G1A-02 step11; E015-r0007 state119; E031 C07/C36] **observed**. Original comparisons: [m244-team-tactics](../../original-game/images/m244-team-tactics.png), [team-tactics](../../original-game/images/team-tactics.png).

[designed] **When/why:** Before kickoff or supported tactical pause: compare team-wide approach with individual overrides and opponent. **Discoverability:** Eight labelled current values in one panel; edit with explicit choices; no ambiguous unchecked/checked prose. **Delivery:** #248. **Limits:** Rebuild eight-bit mapping includes designed labels for elements5/8: retain accepted contracts until evidenced mapping is reconciled. Do not infer engine effect from a displayed phrase.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| TT01 | Defence system | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT02 | Protection | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT03 | Offside | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT04 | Positioning | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT05 | Possession | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT06 | Passing | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT07 | Tackling | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |
| TT08 | Marking | [designed] S04 Team instructions; read-only opponent S06/S08 | [designed] #248 |

## Selection decisions · SD

[confirmed: E031 C06/C28–C32c/C38; M244-G1A-02 steps3–6; reviewed F030] **observed+hint+text**. Original comparisons: [m244-squad](../../original-game/images/m244-squad.png), [m244-pool](../../original-game/images/m244-pool.png), [captain-select](../../original-game/images/captain-select.png), [squad-substitution-put-on](../../original-game/images/squad-substitution-put-on.png).

[designed] **When/why:** Make deliberate team changes with all candidate information and clear confirmation boundaries. **Discoverability:** Roster/card direct; exchange review1 action; assistant preview1 action; captain direct. **Delivery:** #241/#242/#248/B03. **Limits:** Retain merged #241 scrolling and full IDs; #252 is diagnostics only. Assistant and rename are capability-audit dependencies. Proposed preview/Confirm replaces original immediate assistant mutation; no silent auto-select.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| SD01 | Selected twenty versus wider national pool | [designed] S04/S05/S08 | [designed] #241 |
| SD02 | Browse previous/next player and list boundaries | [designed] S04/S05/S08 | [designed] #241 |
| SD03 | Starting eleven versus nine-player bench | [designed] S04/S05/S08 | [designed] B03 |
| SD04 | Two-stage squad-slot/player exchange | [designed] S04/S05/S08 | [designed] B03 |
| SD05 | Assistant recommended twenty | [designed] S04/S05/S08 | [designed] B06 |
| SD06 | Player rename; original maximum12 characters | [designed] S04/S05/S08 | [designed] B06 |
| SD07 | Choose captain from XI | [designed] S04/S05/S08 | [designed] B03 |
| SD08 | Computer captain selection hint/default | [designed] S04/S05/S08 | [designed] #250 |
| SD09 | Formation updates after picks/swaps/roles | [designed] S04/S05/S08 | [designed] #248 |

