# Information parity: match

[confirmed: accepted manual ebdd6879d469a574f6d4b446f59b33a6be3ffd81 and cited records] Original fields below are observed labels/states unless explicitly text-supported, printed-only or unknown. [designed: #253] Destinations/access/owners are proposals, not shipped features. Context statements apply to every field in their following table. See [matrix rules](../information-parity.md).

## Match preparation · MP

[confirmed: E031 C35–C39/C68b; E015-r0007 states28/30/63; reviewed F030] **observed+text**. Original comparisons: [match-watch-prompt](../../original-game/images/match-watch-prompt.png), [match-menu](../../original-game/images/match-menu.png), [captain-select](../../original-game/images/captain-select.png).

[designed] **When/why:** Before kickoff: review both teams, know how match delivery differs and explicitly start. **Discoverability:** Preparation direct via Play a match; Quick and Watch visible beside prerequisites/speed. **Delivery:** #243/B04/#250. **Limits:** Current friendly quick and original watched routes are not promised to be outcome-identical. T85 owns speed semantics15/60/120 samples/s internally; retain Normal default/session-only/frozen while busy. No competitive Watch promise.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| MP01 | Quick versus watched route and side being managed | [designed] S08 | [designed] #243/B04/#250 |
| MP02 | Conditional watch question: Y/N; no timeout | [designed] S08 | [designed] #243/B04/#250 |
| MP03 | Two starting lineups with position codes | [designed] S08 | [designed] #243/B04/#250 |
| MP04 | Two formation names | [designed] S08 | [designed] #243/B04/#250 |
| MP05 | Venue/location, match type and stage | [designed] S08 | [designed] #243/B04/#250 |
| MP06 | Team tactics / players / tournament / statistics actions | [designed] S08 | [designed] #243/B04/#250 |
| MP07 | Captain selection before managed watched play | [designed] S08 | [designed] #243/B04/#250 |
| MP08 | Other-country watch without managed captain | [designed] S08 | [designed] #243/B04/#250 |
| MP09 | Automatic action replay current setting versus next toggle action | [designed] S08 | [designed] #243/B04/#250 |

## Live match · LI

[confirmed: E031 C39–C40/C08; E015-r0007 states31/42/67; M244-G4C-07 steps32–55] **observed+hint**. Original comparisons: [match-live](../../original-game/images/match-live.png), [match-commentary](../../original-game/images/match-commentary.png), [injury-event](../../original-game/images/injury-event.png).

[designed] **When/why:** During a watched match: follow tension and events, control presentation and discover supported interventions. **Discoverability:** Score/clock/pitch/latest event/speed always visible; commentary inline; Bench named button. **Delivery:** #198/#243/B04/#250. **Limits:** Original exact pitch glyphs/F9 meaning unknown. Original Space opens commentary, Esc-play is printed only; direct bench is unexercised. Proposed controls operate only supported worker capability; no hidden no-op bench.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| LI01 | Match clock and phase | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI02 | Ordered countries and score | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI03 | Match type / round context | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI04 | Latest event/chance/action text | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI05 | Pitch positions of players and ball | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI06 | Team identity and selected pitch-label/display mode | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI07 | Speed indicator and Left/Right printed legend | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI08 | Request quick continuation (R), including conditional stops | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI09 | Chronological commentary scroll beside pitch | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI10 | Bench control offered as Esc/Enter | [designed] S09 | [designed] #198/#243/B04/#250 |
| LI11 | F9 glyph/sound suffix | [designed] S09 | [designed] #198/#243/B04/#250 |

## Conditional match decisions · IN

[confirmed: E031 C40–C50/C71; M244-G4C-07 steps39–56; M244-G4C-08 steps0–19; E015-r0007 states76/82/150/176] **observed+text**. Original comparisons: [squad-substitution-take-off](../../original-game/images/squad-substitution-take-off.png), [squad-substitution-put-on](../../original-game/images/squad-substitution-put-on.png), [squad-substitution-illegal](../../original-game/images/squad-substitution-illegal.png), [squad-substitution-tactic](../../original-game/images/squad-substitution-tactic.png), [m244-knockout-halftime](../../original-game/images/m244-knockout-halftime.png), [m244-extra-time-menu](../../original-game/images/m244-extra-time-menu.png), [m244-extra-time-halftime](../../original-game/images/m244-extra-time-halftime.png), [m244-shootout-prompt](../../original-game/images/m244-shootout-prompt.png), [m244-shootout-order](../../original-game/images/m244-shootout-order.png), [m244-shootout-five-chosen](../../original-game/images/m244-shootout-five-chosen.png), [m244-shootout-first-goal](../../original-game/images/m244-shootout-first-goal.png), [e031-shootout-start](../../original-game/images/e031-shootout-start.png).

[designed] **When/why:** At actual engine decision boundary: make an informed intervention, see refusal and resume deliberately. **Discoverability:** Panel opens automatically for supported required choice; Bench button for supported optional pause. **Delivery:** #250/B04. **Limits:** Original friendly5/competition2 substitutions are observed/manual-backed, not a new remaster rule. Exact rejection predicate, no-subs-left behavior, opponent order and complete final penalty board remain gaps. Existing quick-halftime path is distinct from watched controls.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| IN01 | Opponent substitution notice | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN02 | Managed player injured and substitution opportunity | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN03 | Starter to take off | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN04 | Bench replacement to put on | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN05 | Substitutions remaining | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN06 | Candidates and complete condition/skills card | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN07 | Two candidates chosen before committing exchange | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN08 | Illegal-substitution warning / acknowledgement | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN09 | Individual instructions from bench | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN10 | Half-time score/board and explicit resume | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN11 | Quick continuation can stop at half-time | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN12 | Extra-time entry after level knockout | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN13 | Extra-time midpoint and resume | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN14 | Shoot-out transition question / acknowledgement | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN15 | Eleven taker order slots / selected player card | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN16 | Undo most recent order choice | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN17 | Individual kick commentary and scored/missed/saved/post outcomes | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |
| IN18 | Shoot-out score separate from match score; sixth-kick continuation | [designed] S10 with persistent S09 score/phase | [designed] #250/B04 |

## Conditional match decisions · PR

[confirmed: E031 C42–C43b/C51; F030 prompt table at archaeology53d7ef5; manual coverage gaps] **text+hint**. Original comparisons: [match-menu](../../original-game/images/match-menu.png), [captain-select](../../original-game/images/captain-select.png), [match-summary-save-prompt](../../original-game/images/match-summary-save-prompt.png).

[designed] **When/why:** At goal/set piece/result: answer a contextual choice with time/default made explicit if runtime enforces one. **Discoverability:** Prompt replaces decision panel, focus stays within it; timer/default text only when supported. **Delivery:** #250/#251. **Limits:** Prompt screenshots missing beyond captain/summary.6/10s are nominal calibration counts, not guaranteed wall time. Do not add timers or pause semantics that change original engine. No default auto-Yes or invented persistent replay.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| PR01 | Goal action-replay question and Yes/No | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR02 | Save-goal question after replay Yes | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR03 | Replay automatic ON/OFF pre-match option | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR04 | Captain / corner / penalty / free-kick / goal-kick current taker and computer choice | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR05 | Replay/save-goal/summary timed default No; nominal6s | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR06 | Captain/taker timed current-pick default; nominal10s | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR07 | Save-summary only watched without R quick conversion | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |
| PR08 | Replay filename and cancel/save choice | [designed] S08 replay preference; S10 prompt; S11 summary retention; S13 filename | [designed] #250/#251 |

## Results and statistics · RS

[confirmed: E015-r0007 states50–52/207; E031 C24–C24b/C51–C55] **observed**. Original comparisons: [match-summary-save-prompt](../../original-game/images/match-summary-save-prompt.png), [match-summary](../../original-game/images/match-summary.png), [match-menu-fulltime](../../original-game/images/match-menu-fulltime.png), [round-results](../../original-game/images/round-results.png).

[designed] **When/why:** After the match: explain outcome, retain useful comparison and return to the campaign. **Discoverability:** All comparative stats and scorers direct; round results adjacent tab1 action; archive same schema. **Delivery:** #251/B04. **Limits:** Unavailable quick/historical fields say Not recorded, never zero. Preserve source A/B order, normal/extra-time/penalty scores separately. Rebuild raw ratings/provenance are useful extras, not original-parity substitutions.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| RS01 | Full-time score | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS02 | Half-time score | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS03 | Scorer identity | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS04 | Scorer minute | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS05 | Corners | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS06 | Free kicks | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS07 | Penalties | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS08 | Shots | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS09 | Shots on target | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS10 | Saves | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS11 | Fouls | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS12 | Bookings / yellow cards | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS13 | Red cards | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS14 | Possession comparison | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS15 | Territory comparison | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS16 | MAN OF THE MATCH identity | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS17 | Full-time exit action replacing play | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS18 | Round results beyond managed fixture | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |
| RS19 | Saved summary statistics revisited from hub | [designed] S11/S12; latest result summary S03 | [designed] #251/B04 |

## Save, replay and help · SV

[confirmed: E031 C04–C05b/C22–C26b; E015-r0007 states207/215/223–224; reviewed F030] **observed+hint+text**. Original comparisons: [save-game-name-entry](../../original-game/images/save-game-name-entry.png), [save-game-prompt](../../original-game/images/save-game-prompt.png), [quit-confirm](../../original-game/images/quit-confirm.png), [file-not-found-prompt](../../original-game/images/file-not-found-prompt.png), [match-summary](../../original-game/images/match-summary.png).

[designed] **When/why:** At checkpoints: preserve/resume campaign deliberately; later discover past outcomes without guessing function keys. **Discoverability:** Save Ctrl+S direct; Game menu1 action; Archive navigation direct; Help F1. **Delivery:** B02/#251. **Limits:** Save overwrite/error/cancel alternatives need own evidence. Current rebuild JSON saves remain authoritative and incompatible with original GL. F1 driver crash is infrastructure, not original game fault. F5 continuation observed; printed screen output not independently verified.

| ID | Original information | Proposed destination | Sole scoped delivery / reuse owner |
| --- | --- | --- | --- |
| SV01 | Save active game; suggested name/last used name | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 |
| SV02 | Explicit save versus quit decisions | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 |
| SV03 | Save-name cancel (Esc) and commit (Enter) | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 |
| SV04 | Load error with visible retry/cancel offer | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 |
| SV05 | Save-summary question and filename | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] #251 |
| SV06 | Saved-goal replay discoverable separately from summary | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] #251 |
| SV07 | Summary load opens match/stats route | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] #251 |
| SV08 | Manager rename via F2 | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B06 |
| SV09 | Help offered by F1 | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B03 |
| SV10 | Print screen offered by F5 | [designed] S13 Game menu; S12 Summaries/Replays; contextual Help | [designed] B02 |

