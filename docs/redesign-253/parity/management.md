# Information parity: management

[confirmed: accepted manual ebdd6879d469a574f6d4b446f59b33a6be3ffd81 and cited source inventory] Original fields are observed labels/states unless explicitly hint/text-supported or unknown. [designed: #253] Destinations and delivery/reuse are proposals, not shipped capabilities. `UNOWNED:Gxx` means no implementation owner exists: the linked owner decision must create a scoped contract before full parity. An existing issue in Reuse is audit/display when available within its written scope, never authority to implement excluded behavior. See [matrix rules](../information-parity.md) and [unowned decisions](../decisions.md#unowned-capability-decisions).

## Start and session · ST

[confirmed: E031 C11–C16b; M244-G1A-01 steps0–2; E015-r0008 state10] **observed+hint**. Original comparisons: [file-not-found-prompt](../../original-game/images/file-not-found-prompt.png), [m244-load-name](../../original-game/images/m244-load-name.png), [title-player-count](../../original-game/images/title-player-count.png).

[designed] **When/why:** At launch: distinguish starting a career from continuing one; avoid replacing the active game. **Discoverability:** Launch direct; country detail direct; load picker1 action **Delivery / unowned decision:** B02/B06/B07. **Limits:** One manager supported in rebuild; offered3–6 unexercised in original. Retry text is printed; exact original error recovery unverified. No GL compatibility promised.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| ST01 | New game versus load existing game | [designed] S01/S02 | [designed] B02/B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| ST02 | Local manager count: offered1–6; two exercised | [designed] S01/S02 | [designed] B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| ST03 | Selected manager number, country and manager name | [designed] S01/S02 | [designed] B02/B06/B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| ST04 | Manager name entry; original maximum14 characters | [designed] S01/S02 | [designed] B02/B06 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| ST05 | Load list for several saves / prefilled single-save name | [designed] S01/S02 | [designed] B02/B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| ST06 | Missing-file explanation and try-again choice | [designed] S01/S02 | [designed] B02/B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Country context · CO

[confirmed: E015-r0007 states3/10; M244-G4C-05 step3; E031 C13–C14b] **observed**. Original comparisons: [country-select-name-entry](../../original-game/images/country-select-name-entry.png), [country-select](../../original-game/images/country-select.png), [m244-team-info-2030](../../original-game/images/m244-team-info-2030.png).

[designed] **When/why:** Before choosing a country or scouting an opponent: judge challenge, experience and the side being managed. **Discoverability:** Identity/rank/difficulty direct; complete profile1 labelled action **Delivery / unowned decision:** UNOWNED:G05. **Limits:** Complete profile delivery is unowned under O12. B02/B03 reuse basic identity and verified current values; #249 audit/display when available only. Original status/skill/difficulty/bar/strip meanings remain unverified; no fabricated scale or authentic kit.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| CO01 | Country identity / country list / selected row | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO02 | Country status text (e.g. major, very good) | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO03 | Country manager identity | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO04 | Manager skill text and adjacent bar | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO05 | World ranking now | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO06 | World ranking top | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO07 | Continental ranking now | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO08 | Continental ranking top | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO09 | World versus continental list order | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO10 | Difficulty category: SIMPLE / EASY TASK / TOO EASY / QUITE EASY | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO11 | Formation name | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO12 | Strip symbols / displayed team identity | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO13 | Average international caps | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CO14 | Average age | [designed] S02/S06; ranking summary S03/S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |

## Country context · CS

[confirmed: E015-r0007 state3; M244-G4C-05 step3] **observed**. Original comparisons: [country-select](../../original-game/images/country-select.png), [m244-team-info-2030](../../original-game/images/m244-team-info-2030.png), [team-tactics](../../original-game/images/team-tactics.png).

[designed] **When/why:** Compare squad strengths and displayed performance before choosing team, tactics or opponent approach. **Discoverability:** All8 labelled rows together; no hidden tooltip-only numbers **Delivery / unowned decision:** UNOWNED:G05. **Limits:** O12 requires a separately scoped source/projection contract. #249 audit/display when available only. Preserve four skill and four performance groups; original bar scale/derivation unknown.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| CS01 | Team skills: keeper | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS02 | Team skills: defence | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS03 | Team skills: midfield | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS04 | Team skills: attack | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS05 | Team performance: keeper | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS06 | Team performance: defence | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS07 | Team performance: midfield | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CS08 | Team performance: attack | [designed] S02/S06 profile; comparison S08 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |

## Country context · CC

[confirmed: M244-G1A-02 step11; E015-r0007 state3] **observed**. Original comparisons: [country-select](../../original-game/images/country-select.png), [m244-team-tactics](../../original-game/images/m244-team-tactics.png).

[designed] **When/why:** Inspect team condition and tendencies before confirming a tactical plan. **Discoverability:** Four labelled rows direct in team profile; summary at Team **Delivery / unowned decision:** UNOWNED:G05. **Limits:** O12 complete country projection remains unowned; #249 audit/display when available. Verbal labels/bars do not establish numeric units; rebuild calculated morale stays distinct.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| CC01 | Team hardness | [designed] S06 team profile; S04 team-tactics context | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CC02 | Team fitness | [designed] S06 team profile; S04 team-tactics context | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CC03 | Team energy | [designed] S06 team profile; S04 team-tactics context | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| CC04 | Team morale | [designed] S06 team profile; S04 team-tactics context | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |

## Country desk · HU

[confirmed: E015-r0007 state16; M244-G1A-02 step2; M244-G1E-06 step19; E031 C16–C21/C54–C55] **observed+text**. Original comparisons: [m244-finals-stage-hub](../../original-game/images/m244-finals-stage-hub.png), [m244-holland-menu](../../original-game/images/m244-holland-menu.png), [manager-menu](../../original-game/images/manager-menu.png).

[designed] **When/why:** After every round: understand who/when/why to prepare and the next available action. **Discoverability:** Direct next-fixture/context/availability; roster preview direct; full roster1 action **Delivery / unowned decision:** B03/B07/UNOWNED:G05. **Limits:** B03 composes verified active state; B07 concerns local ownership. Full manager/rank/host profile fields need O12/G05. #249 audit/display when available; new news generation is O10/G03, never inferred from T51a.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| HU01 | Active managed country, manager name and manager rating | [designed] S03 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| HU02 | Campaign year and competition/stage title | [designed] S03 | [designed] B03 | [designed] Existing campaign identity/next-fixture state; #249 audit/display when available. New campaign mechanics and B07 local ownership remain separate. |
| HU03 | Competition host/location in title | [designed] S03 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| HU04 | Next opponent identity | [designed] S03 | [designed] B03 | [designed] Existing campaign identity/next-fixture state; #249 audit/display when available. New campaign mechanics and B07 local ownership remain separate. |
| HU05 | Next opponent world and continental ranks | [designed] S03 | [designed] UNOWNED:G05 | [designed] #249 audit/display when available within its fixture/group/opponent scope; rankings/records remain conditional on established source/persistence. T55 mechanics and T84 player projections retain their contracts; B02/B03 may compose verified current identity/team values. |
| HU06 | Next fixture type and home/away | [designed] S03 | [designed] B03 | [designed] Existing campaign identity/next-fixture state; #249 audit/display when available. New campaign mechanics and B07 local ownership remain separate. |
| HU07 | Twenty-player squad strip; XI and bench split; position codes | [designed] S03 | [designed] B03 | [designed] Existing campaign identity/next-fixture state; #249 audit/display when available. New campaign mechanics and B07 local ownership remain separate. |
| HU08 | Managers list / active manager / next player action | [designed] S03 | [designed] B07 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| HU09 | No next opponent; advance remaining round and stage | [designed] S03 | [designed] B03 | [designed] Existing campaign identity/next-fixture state; #249 audit/display when available. New campaign mechanics and B07 local ownership remain separate. |

## Player card · PI

[confirmed: M244-G1A-02 steps3–6; E031 C34–C34b; E015-r0007 state76] **observed+text**. Original comparisons: [m244-pool](../../original-game/images/m244-pool.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-squad](../../original-game/images/m244-squad.png), [squad-substitution-take-off](../../original-game/images/squad-substitution-take-off.png).

[designed] **When/why:** When picking XI, comparing a reserve, captain or substitute: identity, eligibility and role must be beside the choice. **Discoverability:** Selected card direct; comparison pins two cards; small window labelled card pane **Delivery / unowned decision:** #242. **Limits:** T84 field contract owns decoding/display. Exact original performance and card-box rendering unresolved: explicit unavailable text, never fabricated stars/percentages. Opponent card stays read-only.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| PI01 | Player name | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI02 | Age | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI03 | International caps | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI04 | International goals | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI05 | Height | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI06 | Bias / dominant foot | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI07 | Current national position | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI08 | Club position | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI09 | Performance box | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI10 | Card/discipline boxes | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PI11 | Readiness: ready, selected, on bench, injured, suspended | [designed] S04/S05/S06/S08/S10 selected card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Player skills · SK

[confirmed: M244-G1A-02 steps3–6; M244-G4C-05 step4; F008 source contract in T84] **observed**. Original comparisons: [m244-pool](../../original-game/images/m244-pool.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-squad](../../original-game/images/m244-squad.png), [m244-team-info-players-2030](../../original-game/images/m244-team-info-players-2030.png).

[designed] **When/why:** Compare relevant skills for XI/role, reserve exchange, captain, taker or substitution without leaving the decision. **Discoverability:** All12 labels in card; compact table plus Show all attributes retained; numeric domains only per T84 **Delivery / unowned decision:** #242. **Limits:** Bars permit comparison. Exact numeric decoding comes from T84/F008, not image color. Never collapse12 skills into Ability; no invented1–100 scale.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| SK01 | Keeping | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK02 | Kicking | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK03 | Tackling | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK04 | Heading | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK05 | Marking | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK06 | Passing | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK07 | Crossing | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK08 | Feinting | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK09 | Control | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK10 | Dribbling | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK11 | Shooting | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SK12 | Penalties | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Player characteristics · PC

[confirmed: M244-G1A-02 steps3–6] **observed**. Original comparisons: [m244-pool-next](../../original-game/images/m244-pool-next.png), [m244-squad-next](../../original-game/images/m244-squad-next.png), [m244-squad](../../original-game/images/m244-squad.png).

[designed] **When/why:** Before committing a selection: compare temperament, condition and captain suitability in the same view. **Discoverability:** All5 together; Energy/readiness remain in roster rows **Delivery / unowned decision:** #242. **Limits:** Keep fitness versus energy and morale versus rebuild Confidence distinct. Use T84 verified domains; unknown original descriptive buckets are unavailable, not guessed.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| PC01 | Hardness | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PC02 | Fitness | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PC03 | Energy | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PC04 | Morale | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PC05 | Leadership | [designed] S04/S05/S06/S08/S10 complete player card | [designed] #242 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Personal tactics · PT

[confirmed: M244-G1A-02 step8; M244-G1A-04 steps5–12; E031 C31–C33d; E015-r0007 states165–166] **observed**. Original comparisons: [m244-individual-tactics](../../original-game/images/m244-individual-tactics.png), [m244-position-club](../../original-game/images/m244-position-club.png), [m244-position-next](../../original-game/images/m244-position-next.png), [m244-position-tactic-toggle](../../original-game/images/m244-position-tactic-toggle.png), [mark-named-opponent](../../original-game/images/mark-named-opponent.png), [mark-protect-zone](../../original-game/images/mark-protect-zone.png).

[designed] **When/why:** Choose how this player behaves and whom to mark before the match or at an allowed intervention. **Discoverability:** Selected player and all instructions direct; opponent-picker1 action beside both cards **Delivery / unowned decision:** #248. **Limits:** T84 owns read-only projection; #248 owns supported edits. P meaning stays unknown; separate from possession. No invented formation algorithm or live mark context. Named mark resets only when supported source contract establishes it.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| PT01 | Position instruction (stay back / push forward etc.) | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT02 | Possession instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT03 | Passing instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT04 | Tackling instruction | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT05 | Mark: Protect zone / named opponent | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT06 | Named opponent role beneath mark | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT07 | Trailing P display flag | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| PT08 | Current role change and restore club role | [designed] S04 instructions panel; S08/S10 contextual opponent mark | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Team tactics / player defaults · TT

[confirmed: M244-G1A-02 step11; E015-r0007 state119; E031 C07/C36; E015-r0007 states3/10; M244-G4C-05 step3] **observed**. Original comparisons: [country-select-name-entry](../../original-game/images/country-select-name-entry.png), [country-select](../../original-game/images/country-select.png), [m244-team-info-2030](../../original-game/images/m244-team-info-2030.png), [m244-team-tactics](../../original-game/images/m244-team-tactics.png), [team-tactics](../../original-game/images/team-tactics.png).

[designed] **When/why:** Before kickoff or supported tactical pause: compare team-wide approach with individual overrides and opponent. **Discoverability:** S02 tendency summary plus Complete profile1 action to S06 all8 read-only defaults; S04 all8 direct; supported edits explicit **Delivery / unowned decision:** B03/UNOWNED:G05. **Limits:** Current team bits/controls stay with existing management and B03 composition; #248 is personal edits only. O12/G05 covers full setup/opponent defaults. Elements5/8 retain accepted designed wording; no inferred effect.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| TT01 | Defence system | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT02 | Protection | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT03 | Offside | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT04 | Positioning | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT05 | Possession | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT06 | Passing | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT07 | Tackling | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |
| TT08 | Marking | [designed] S02/S06 read-only country tactics/defaults; S04 Team instructions; S08 preparation | [designed] B03/UNOWNED:G05 | [designed] Existing team-management bits and T84 read-only display; #248 owns personal edits only. Complete country/default projection remains G05. |

## Selection decisions · SD

[confirmed: E031 C06/C28–C32c/C38; M244-G1A-02 steps3–6; reviewed F030] **observed+hint+text**. Original comparisons: [captain-select](../../original-game/images/captain-select.png), [m244-pool](../../original-game/images/m244-pool.png), [m244-squad](../../original-game/images/m244-squad.png), [squad-substitution-put-on](../../original-game/images/squad-substitution-put-on.png).

[designed] **When/why:** Make deliberate team changes with all candidate information and clear confirmation boundaries. **Discoverability:** At wide desktop all20 names/XI-bench split beside full card; at900x640 named scroll/jump to Bench, selected identities pinned **Delivery / unowned decision:** #241/#242/#248/B03/B06/#250. **Limits:** Retain merged #241 scrolling and full IDs; #252 is diagnostics only. Assistant and rename are capability-audit dependencies. Proposed preview/Confirm replaces original immediate assistant mutation; no silent auto-select.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| SD01 | Selected twenty versus wider national pool | [designed] S04/S05/S08 | [designed] #241 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD02 | Browse previous/next player and list boundaries | [designed] S04/S05/S08 | [designed] #241 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD03 | Starting eleven versus nine-player bench | [designed] S04/S05/S08 | [designed] B03 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD04 | Two-stage squad-slot/player exchange | [designed] S04/S05/S08 | [designed] B03 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD05 | Assistant recommended twenty | [designed] S04/S05/S08 | [designed] B06 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD06 | Player rename; original maximum12 characters | [designed] S04/S05/S08 | [designed] B06 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD07 | Choose captain from XI | [designed] S04/S05/S08 | [designed] B03 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD08 | Computer captain selection hint/default | [designed] S04/S05/S08 | [designed] #250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SD09 | Formation updates after picks/swaps/roles | [designed] S04/S05/S08 | [designed] #248 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

