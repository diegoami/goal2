# Information parity: match

[confirmed: accepted manual ebdd6879d469a574f6d4b446f59b33a6be3ffd81 and cited source inventory] Original fields are observed labels/states unless explicitly hint/text-supported or unknown. [designed: #253] Destinations and delivery/reuse are proposals, not shipped capabilities. `UNOWNED:Gxx` means no implementation owner exists: the linked owner decision must create a scoped contract before full parity. An existing issue in Reuse is audit/display when available within its written scope, never authority to implement excluded behavior. See [matrix rules](../information-parity.md) and [unowned decisions](../decisions.md#unowned-capability-decisions).

## Match preparation · MP

[confirmed: E031 C35–C39/C68b; E015-r0007 states28/30/63; reviewed F030] **observed+text**. Original comparisons: [captain-select](../../original-game/images/captain-select.png), [match-menu](../../original-game/images/match-menu.png), [match-watch-prompt](../../original-game/images/match-watch-prompt.png).

[designed] **When/why:** Before kickoff: review both teams, know how match delivery differs and explicitly start. **Discoverability:** Preparation direct via Play a match; Quick and Watch visible beside prerequisites/speed **Delivery / unowned decision:** #243/B04/#250/UNOWNED:G01/UNOWNED:G04. **Limits:** T85 owns supported entry/speed only, not a new watched mode. #250 audits support/first intervention. Competitive/other-country Watch is unowned O08/G01; replay preferences require O11/G04. Friendly Quick and original Watch remain different routes.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| MP01 | Quick versus watched route and side being managed | [designed] S08 | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| MP02 | Conditional watch question: Y/N; no timeout | [designed] S08 | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| MP03 | Two starting lineups with position codes | [designed] S08 | [designed] #243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| MP04 | Two formation names | [designed] S08 | [designed] #243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| MP05 | Venue/location, match type and stage | [designed] S08 | [designed] #243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| MP06 | Team tactics / players / tournament / statistics actions | [designed] S08 | [designed] #243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| MP07 | Captain selection before managed watched play | [designed] S08 | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| MP08 | Other-country watch without managed captain | [designed] S08 | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| MP09 | Automatic action replay current setting versus next toggle action | [designed] S08 | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |

## Live match · LI

[confirmed: E031 C39–C40/C08; E015-r0007 states31/42/67; M244-G4C-07 steps32–55] **observed+hint**. Original comparisons: [injury-event](../../original-game/images/injury-event.png), [match-commentary](../../original-game/images/match-commentary.png), [match-live](../../original-game/images/match-live.png).

[designed] **When/why:** During a watched match: follow tension and events, control presentation and discover supported interventions. **Discoverability:** Score/clock/pitch/latest event/speed always visible; commentary inline; Bench named button **Delivery / unowned decision:** #198/#243/B04/#250. **Limits:** Original exact pitch glyphs/F9 meaning unknown. Original Space opens commentary, Esc-play is printed only; direct bench is unexercised. Proposed controls operate only supported worker capability; no hidden no-op bench.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| LI01 | Match clock and phase | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI02 | Ordered countries and score | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI03 | Match type / round context | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI04 | Latest event/chance/action text | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI05 | Pitch positions of players and ball | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI06 | Team identity and selected pitch-label/display mode | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI07 | Speed indicator and Left/Right printed legend | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI08 | Request quick continuation (R), including conditional stops | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI09 | Chronological commentary scroll beside pitch | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI10 | Bench control offered as Esc/Enter | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| LI11 | F9 glyph/sound suffix | [designed] S09 | [designed] #198/#243/B04/#250 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |

## Conditional match decisions · IN

[confirmed: E031 C40–C50/C71; M244-G4C-07 steps39–56; M244-G4C-08 steps0–19; E015-r0007 states76/82/150/176] **observed+text**. Original comparisons: [e031-shootout-start](../../original-game/images/e031-shootout-start.png), [m244-extra-time-halftime](../../original-game/images/m244-extra-time-halftime.png), [m244-extra-time-menu](../../original-game/images/m244-extra-time-menu.png), [m244-knockout-halftime](../../original-game/images/m244-knockout-halftime.png), [m244-shootout-first-goal](../../original-game/images/m244-shootout-first-goal.png), [m244-shootout-five-chosen](../../original-game/images/m244-shootout-five-chosen.png), [m244-shootout-order](../../original-game/images/m244-shootout-order.png), [m244-shootout-prompt](../../original-game/images/m244-shootout-prompt.png), [squad-substitution-illegal](../../original-game/images/squad-substitution-illegal.png), [squad-substitution-put-on](../../original-game/images/squad-substitution-put-on.png), [squad-substitution-tactic](../../original-game/images/squad-substitution-tactic.png), [squad-substitution-take-off](../../original-game/images/squad-substitution-take-off.png).

[designed] **When/why:** At actual engine decision boundary: make an informed intervention, see refusal and resume deliberately. **Discoverability:** Panel opens automatically for supported required choice; Bench button for supported optional pause **Delivery / unowned decision:** #250/B04/UNOWNED:G01. **Limits:** Current quick-friendly halftime is supported separately; #250 audits and delivers only its supported first choice. O08/G01 blocks watched competitive extra-time/order and additional unsupported choices. Original5/2 counts do not replace accepted remaster policy; no-subs-left remains unknown.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| IN01 | Opponent substitution notice | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN02 | Managed player injured and substitution opportunity | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN03 | Starter to take off | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN04 | Bench replacement to put on | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN05 | Substitutions remaining | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN06 | Candidates and complete condition/skills card | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN07 | Two candidates chosen before committing exchange | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN08 | Illegal-substitution warning / acknowledgement | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN09 | Individual instructions from bench | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN10 | Half-time score/board and explicit resume | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN11 | Quick continuation can stop at half-time | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| IN12 | Extra-time entry after level knockout | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN13 | Extra-time midpoint and resume | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN14 | Shoot-out transition question / acknowledgement | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN15 | Eleven taker order slots / selected player card | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN16 | Undo most recent order choice | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN17 | Individual kick commentary and scored/missed/saved/post outcomes | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |
| IN18 | Shoot-out score separate from match score; sixth-kick continuation | [designed] S10 with persistent S09 score/phase | [designed] UNOWNED:G01 | [designed] #249 audit/display when available; #243 supported entry/speed only; #250 support audit and first supported intervention only; existing competitive Quick result remains separate. |

## Conditional match decisions · PR

[confirmed: E031 C42–C43b/C51; F030 prompt table at archaeology53d7ef5; manual coverage gaps] **text+hint**. Original comparisons: [captain-select](../../original-game/images/captain-select.png), [match-menu](../../original-game/images/match-menu.png), [match-summary-save-prompt](../../original-game/images/match-summary-save-prompt.png).

[designed] **When/why:** At goal/set piece/result: answer a contextual choice with time/default made explicit if runtime enforces one. **Discoverability:** Prompt replaces decision panel, focus stays within it; timer/default text only when supported **Delivery / unowned decision:** #250/UNOWNED:G04. **Limits:** #250 audits supported prompts/first choice; O11/G04 new replay/goal/summary export delivery remains unowned, with #251 audit/display when available only. Nominal6/10s are not guaranteed wall time. No new timers, default Yes or recording invented.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| PR01 | Goal action-replay question and Yes/No | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| PR02 | Save-goal question after replay Yes | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| PR03 | Replay automatic ON/OFF pre-match option | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| PR04 | Captain / corner / penalty / free-kick / goal-kick current taker and computer choice | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250 | [designed] Support audit and first supported decision only; no promise of every future prompt or competitive Watch. G01 covers additional mode-dependent capability. |
| PR05 | Replay/save-goal/summary timed default No; nominal6s | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| PR06 | Captain/taker timed current-pick default; nominal10s | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250 | [designed] Support audit and first supported decision only; no promise of every future prompt or competitive Watch. G01 covers additional mode-dependent capability. |
| PR07 | Save-summary only watched without R quick conversion | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| PR08 | Replay filename and cancel/save choice | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |

## Results and statistics · RS

[confirmed: E015-r0007 states50–52/207; E031 C24–C24b/C51–C55] **observed**. Original comparisons: [match-menu-fulltime](../../original-game/images/match-menu-fulltime.png), [match-summary-save-prompt](../../original-game/images/match-summary-save-prompt.png), [match-summary](../../original-game/images/match-summary.png), [round-results](../../original-game/images/round-results.png).

[designed] **When/why:** After the match: explain outcome, retain useful comparison and return to the campaign. **Discoverability:** All comparative stats and scorers direct; round results adjacent tab1 action; archive same schema **Delivery / unowned decision:** #251/B04. **Limits:** Unavailable quick/historical fields say Not recorded, never zero. Preserve source A/B order, normal/extra-time/penalty scores separately. Rebuild raw ratings/provenance are useful extras, not original-parity substitutions.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| RS01 | Full-time score | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS02 | Half-time score | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS03 | Scorer identity | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS04 | Scorer minute | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS05 | Corners | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS06 | Free kicks | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS07 | Penalties | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS08 | Shots | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS09 | Shots on target | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS10 | Saves | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS11 | Fouls | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS12 | Bookings / yellow cards | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS13 | Red cards | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS14 | Possession comparison | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS15 | Territory comparison | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS16 | MAN OF THE MATCH identity | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS17 | Full-time exit action replacing play | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS18 | Round results beyond managed fixture | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| RS19 | Saved summary statistics revisited from hub | [designed] S11/S12; latest result summary S03 | [designed] UNOWNED:G04 | [designed] #251 audit/display when available for already retained summaries; full new capture/export/retention has no delivery owner under G04. |

## Save, replay and help · SV

[confirmed: E031 C04–C05b/C22–C26b; E015-r0007 states207/215/223–224; reviewed F030] **observed+hint+text**. Original comparisons: [file-not-found-prompt](../../original-game/images/file-not-found-prompt.png), [match-summary](../../original-game/images/match-summary.png), [quit-confirm](../../original-game/images/quit-confirm.png), [save-game-name-entry](../../original-game/images/save-game-name-entry.png), [save-game-prompt](../../original-game/images/save-game-prompt.png).

[designed] **When/why:** At checkpoints: preserve/resume campaign deliberately; later discover past outcomes without guessing function keys. **Discoverability:** Save Ctrl+S direct; Game menu1 action; Archive navigation direct; Help F1 **Delivery / unowned decision:** B02/B03/B06/#251/UNOWNED:G04. **Limits:** Current rebuild JSON save semantics remain; B06 identity support separate. #251 audit/display when available for retained summaries; O11/G04 for new summary-export/goal replay. F5 print offer is unverified output, not a new print contract.

| ID | Original information | Proposed destination | Delivery owner / unowned decision | Reuse within existing scope |
| --- | --- | --- | --- | --- |
| SV01 | Save active game; suggested name/last used name | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV02 | Explicit save versus quit decisions | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV03 | Save-name cancel (Esc) and commit (Enter) | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV04 | Load error with visible retry/cancel offer | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV05 | Save-summary question and filename | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| SV06 | Saved-goal replay discoverable separately from summary | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] UNOWNED:G04 | [designed] #250 prompt/support audit only; #251 audit/display when available and read-only retained summaries; neither authorizes a replay viewer/recording or new export capability. |
| SV07 | Summary load opens match/stats route | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] UNOWNED:G04 | [designed] #251 audit/display when available for already retained summaries; full new capture/export/retention has no delivery owner under G04. |
| SV08 | Manager rename via F2 | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B06 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV09 | Help offered by F1 | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B03 | [designed] Within the named contract only; absent data or behavior is not granted by a destination. |
| SV10 | Print screen offered by F5 | [designed] S13 contextual Help: original F5 offer documented; no print action promised | [designed] B03 | [designed] Original printed offer and observed continuation only; actual print output unverified, no new printing capability assigned to B02. |

