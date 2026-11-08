# Original manual and new-window fidelity audit

[designed: owner2026-11-07, #611; T191] This matrix separates source observations, exercised behavior,
explicit owner differences and unverified journeys. Its inspected application baseline is
`ecdd2ee1676ee977c61faa9b6daa7573a3b78edd`. A screen being implemented is not evidence that every
original action works. The complete fresh-game/manual acceptance journey remains required by #611.
GitHub issues/PRs carry current task status; this document records the evidence and gaps at that baseline.

[confirmed] The original private `GOAL.HLP` was read in full: 32,569 bytes, 703 lines,
SHA-256 `2f3be8648a52045b6f7af1f41cba020d6a662229e5db499e203c5d0957308f60`.
Only section references and paraphrases appear here. The private original help, game files and owner saves
are not copied into this public tree. The [image provenance](../../original-game/image-provenance.tsv)
and [original reference](../../original-game/README.md) identify the retained original captures.

## Manual sections

[confirmed: original help, section/line references below] Requirements are paraphrased, not new game rules.
[derived] The third column maps those requirements to existing code and explicitly names missing evidence.

| Original section / starting line | Original requirement or context | Baseline mapping and evidence/gap |
| --- | --- | --- |
| Title / 2 | Version and publisher identify this manual. | Source identity above; no gameplay acceptance inferred. |
| Features / 17 | Countries, managers, national squads/pools, detailed cards, competitions, watched matches, history and files. | S03–S21 below. Multiple managers #551, other watched matches #570, card/live-data gaps #611 and season coverage T170 remain distinct. |
| Version changes / 81 | Assistant selection, ageing, more statistics, replays and saved summaries. | Ins assistant is still a placeholder (#594/T183); native ageing/continuation is Track B/T170; T181 supplies recording UI. Definitions are not full-season proof. |
| Introduction / 130 | Four-year international cycle, evolving players and consequences of results. | `campaign_rounds`, `campaign_competitive`, T170 boundary. Opening-stage UI receipts cannot certify an entire cycle or indefinite play. |
| Country selection / 176 | Browse countries and assess team strength and competition. | S04/S07; ranking and tactics source exists, but country/team performance/characteristic placeholders are confirmed gaps. No new country-name expansion. |
| Playing / 208 | Keyboard navigation, hub actions, mid-match tactics and substitutions. | S06–S22. #613 provides specific return/status acceptance; #610/#614 adds a separate live-team-tactics correction. Substitution budgets differ by explicit owner decision; see differences below. |
| Competitions / 262 | Qualifying/finals/brackets, hosts, rankings, extra time, shoot-outs and tie rules. | S12/S14/S16/S20, accepted engine and T170. Baseline S12 explicitly lacks later-stage displays; extra-time squad edits are separately missing. Native whole-stage acceptance remains required. |
| Squad selection / 315 | Review a national pool, select twenty, assistant recommendation, monitor form and fatigue. | S08; #594/T183 assistant gap; #611 live energy/performance gap. Pool restrictions and player-state rules need the full journey, not only the selection screen. |
| Skills / 357 | Twelve skill categories, with position-dependent use. | `game/skills.py`, `game/player_card.py`, S08/S09; existing80-card original-screen oracle checks displayed skill bars. No aggregate ability number is introduced. |
| Positioning / 404 | Fourteen roles, left/right/central balance, in-match repositioning. | `game/roles.py`, S08 R/C, S19 R/C, S09 personal settings. T180/T188 actual match receipts cover selected tactical changes, not every formation. |
| Tactics / 469 | Eight team flags, personal overrides and per-match marking assignments. | S09/S10/S15/S19. Baseline team tactics during play are read-only: #610/#614. Personal tactics/marks already have actual engine tests; all-eight live-team flags need independent acceptance. |
| Match / 557 | Speed/marks, bench, replay control, commentary, quick result, captain/takers, live ratings. | S15–S20. Insert toggles replay on S15; the follow-up original-key probe below confirms the pitch consumes Insert without toggling. Performance rendering and live values are confirmed separate gaps. |
| Sound / 626 | Optional original PC-speaker effects and quiet mode. | S17 reports sound unavailable. Existing owner sound scope applies; no sound research/model spending is initiated by this audit. |
| Print / 640 | Screen printing. | F5 replaced by system screenshots in accepted S06 design (#526); retain as a deliberate difference, not a working printer feature. |
| Displays / 648 | Team identification through alternative pitch marks. | S17 five mark styles and kit/source tests. Native/fractional-DPI acceptance must still cover readable cards and controls. |
| Customisation / 658 | Session player/manager names; separate DOS utility for permanent database changes. | S08/desk F2. Owner33 authored surname profiles,80 names each, are a separate accepted scope. The external ALTER utility is not provided by these screens. |
| Publisher information / 677 | Historical contact information. | Help content only; no application action or modern contact validity claimed. |
| Footer / 701 | Repeats manual identity; ends the file. | Hash-bound source context, no acceptance claim. |

## Every screen and action

[confirmed] Original references are T156-R1 step numbers/captures unless an original routine is named.
[derived] Code names and test names identify where the baseline implements/exercises each action.
“Source” does not mean a natural journey was rerun for this audit. Existing tests are an evidence location,
not blanket permission to mark the complete manual covered.

| Screen / original reference | Actions and current source | Exercised evidence and remaining acceptance |
| --- | --- | --- |
| S01 Import / rebuild addition | Locate/verify/copy private files; `s01_import.py`. | T153 import/setup and `test_ui_start_t163`; fresh package/help completeness must be checked. Original bytes stay private. |
| S02 Start / title, load prompt | Continue/load/new, retry corrupt/missing saves; `s02_start.py`, `saves.py`. | T168 persistence tests and original startup/save reference. Complete fresh save/restart/load journey still needed for #611. |
| S03 Manager count / steps1–3 | Count/year input; `s03_new_game.py`. | Source supports the bounded route, not original1–6 manager parity (#551). |
| S04 Country/name / steps3–11 | Country/group/ranking browse, inspect players, choose/type/cancel; `s04_country.py`. | T163 tests/captures. Team-card placeholder data remains incomplete even when a country can be selected. |
| S05 Bulletin / steps11–12,200,317 | Read/advance news; `s05_bulletin.py`. | Source labels demonstration pages. Native bulletin and later-stage content need T170 evidence; stand-ins are not original news acceptance. |
| S06 Desk / steps13,201,244,318 | Six hub options, squad/tactics/help, recordings/save/quit, rename; `s06_desk.py`. | T164/T168/T177 tests; latest T190 actual walk returns here with exactly one publication. Multi-manager handoff and full-year continuation remain separate. |
| S07 Team info / M244-G4C-05 | Country/ranking, players, tactics, fixtures; `s07_team_info.py`, `game/country_card.py`. | Source and T177 tests. Country card lacks decoded team skills/performance/characteristics and some rankings/status data despite existing engine/core helpers (#611). |
| S08 Squad/pool / steps14–29,202,320 | Browse/swap pool/squad, R/C positions, personal tactics, F2 names, Ins assistant; `s08_squad.py`, `squad_card.py`. | T165 calls/Qt tests; original E00780-card oracle. Assistant is a placeholder (#594/T183), performance is raw/undecoded, facts compressed, colours need comparison (#611). |
| S09 Personal tactics / step30;1771:4B61/49B8 | Cycle personal defaults/values, mark an opponent, return; `s09_player_tactics.py`, `BenchAnswer`. | T165/T180/T188 tests; T190 natural injury/half-time journey uses the actual screens. Live energy/performance comes from stale career records, not a complete match snapshot. |
| S10 Team tactics / steps33–35;1771:1981 | Eight flags and formation; `s10_team_tactics.py`. | Pre-match T165 controls. In-match read-only baseline is #610/#614; characteristic placeholders remain #611. |
| S11 Fixtures / step224 | Browse country fixtures, choose watched matches, change own friendlies; `s11_fixtures.py`. | Own upcoming matches shown. Other-match watch selection (#570) and friendly cancellation/rearrangement (#571) explicitly unavailable. |
| S12 Tournament / steps227–231,316 | Groups/continents/displays, top scorers/championship; `s12_tournament.py`. | T178 source/tests; later displays/groups and Championship action explicitly not reached until T170. A printed tab is not completed tournament parity. |
| S13 History / M244-G1A-03 | Browse team seasons/records/results; `s13_history.py`. | T178 tests; source stores route-produced results, so all original historical categories and multiple seasons need reconciliation with T170. |
| S14 Round / steps41,262–263 | Results arriving, pause/speed/continue, watched selections; `s14_round.py`. | T167/T176/T178 round journeys; other-country watch control remains #570. |
| S15 Match menu / steps42,68–73,193–198 | Both countries, row/country arrows, team/players, stats/tournament, replay toggle, Play/Exit/watch question; `s15_match_menu.py`. | T184 arrows, T190 actual return/reference. Active-menu Esc follows original0791:ED8A continuation; before/full-time menus select/explain Play/Exit. #614 reconciles T190 return tests and adds live team-tactics acceptance. |
| S16 Captain/taker/order / steps43–47,56–58;F030 | Choose/computer recommendation, timed takers, undo shoot-out selection; `s16_choose.py`. | T167/T181, captain replacement T187, accepted engine. Full extra-time/shoot-out user journey remains distinct from the friendly T190 proof. |
| S17 Pitch / steps45–192,247–255,267 | Speed/marks, commentary pause, quick result, stop request, replay display; `s17_pitch.py`. | T166/T185/T190 actual matches and bridge equality. Ins replay toggle belongs to the match menu; the bounded original9372 probe below confirms pitch behavior. Sound remains outside current owner scope. |
| S18 Stops / steps67–68,149–150,175–178 | Notice acknowledgement, replay/save questions, injury opportunity; `s18_stop.py`, `match_day.py`. | T181 replay packets/actual tests and T190 natural injury stop. Keyboard auto-repeat is covered in T190; every mouse/pending branch must also be reconciled with #614. |
| S19 Bench / steps124–137;1771:42BC | Twenty/eleven, R/C/T, legal immediate swaps, accepted/refused feedback; `s19_bench.py`. | T188 actual injury/captain, T190 natural swaps/refused re-entry and full memory equality; #609 green cue. Extra-time bench is read-only; live performance/energy snapshot is absent. Both are required #611 gaps, separate from tactics. |
| S20 Board / steps119,192,198–199,270,310–313 | Stats, quick-result banner, back/continue, saved summaries; `s20_board.py`. | T180/T181 and T190 actual halves/full result. Quick-result stat discard and every recorded category remain part of the complete audit journey. |
| S21 Files/quit / steps233–246 | Name/save/load, quit confirmation, recording lists; `s21_save.py`, `replays.py`, `saves.py`. | T168/T181 persistence tests. Free names are accepted owner design; new recordings do not imply original DOS recording import compatibility. |
| S22 Help / manual playing section | F1 read/scroll/back; `s22_help.py`. | T177 help tests, private imported file. Original help-viewer capture is still an evidence gap; illustrative mockups are not that capture. |

## Confirmed gaps and required follow-ups

[derived: baseline source above; designed: owner #611] These are independent corrections, not one large PR:

- Live team tactics and original stop/back semantics: #610/#614, including pending mouse actions and retained personal drafts.
- Performance display: `game/player_card.py` returns the raw word; `squad_card.PlayerCard` prints an undecoded explanation.
  Original1771:3827, accepted port `performance_text_state` and `core.views.player_card` already establish star buckets.
  T192 corrects display decoding while preserving raw data compatibility.
- Live data: `BenchAnswer.record` overlays position/personal tactics onto career records. No complete live performance/energy record
  reaches that card. A decoder cannot repair freshness. Trace and extend the accepted engine snapshot contract upstream first.
- Player-card facts/colours: original [squad](../../original-game/images/t156-014-squad.png) and
  [half-time bench](../../original-game/images/t156-124-halftime-bench.png) have aligned label/value cells,
  semantic label/value colours, blank initial performance and later stars. Use rendered comparisons, all20 rows and fractional scales.
- Team cards: existing `engine/team_card` and Core decoded panels must be reconciled with the legacy Python card placeholders;
  do not invent aggregate values or discard the source's live/match conditions.
- Extra-time substitutions: the original mapped extra-time squad menus offer edits; baseline `takes_substitutions` and the accepted
  `edit_only` guard exclude them. Team-tactics-only extra-time support does not supply substitution support.
- Existing broader parity gaps: assistant #594/T183; multiple managers #551; watch other matches #570; friendly scheduling #571;
  later competitions/news/history/native season continuation T170. Do not close these through an opening-friendly review.
- Match Insert replay control: the follow-up original9372 probe confirms no replay toggle on the pitch. Keep the S15 menu binding;
  the broad manual match section does not establish a separate in-play toggle. See the source-bound receipt below.

## Evidence and explicit differences

[confirmed] New original images inspected for this audit are the T156 initial squad and half-time bench above.
The former has a blank performance cell; the latter visibly has six stars for the injured selected player.
The original routine compares signed16-bit rating words, removes the10000 substitute marker for positive encoded values,
and chooses1..9 stars; the sentinel0x7FFF draws no text. The final subtraction is16-bit: do not infer all extreme-word behavior
solely from the Core helper's Python arithmetic.

[derived] The most recent independently executed complete match in this Track A session is T190:
[receipt](../../../measurements/T190/receipt.json), [actual result](../../../measurements/T190/actual-after.log),
[focused controls](../../../measurements/T190/focused-after.log). It includes an ordinary pause, natural injury,
immediate substitutions/refusal, personal tactics and half-time menu returns, with exact result/RNG/events/full memory/career equality
against the bridge. Its acknowledgement hold is an explicitly declared presentation fixture for a repeatable pause boundary.
It does not certify a full season, save/restart journey, live team tactics, current live card data or complete UI fidelity.

[designed: accepted owner decisions #526/#597/#599/#73] Preserve the integrated pitch/commentary, readable scalable font,
free file names, five competitive/unlimited friendly substitution policy, and stopped-only immediate substitutions without a queue.
Keep the33 authored surname profiles/80names each; unlisted countries retain original names. System screenshots replace F5 printing
in the accepted screen design. No extra-country research, old-career migration or sound-model spending follows from this audit.

[designed: owner #611] Acceptance still requires a fresh isolated natural journey through squad/pool, both tactics screens,
ordinary and half-time stops, swaps, complete result, save/quit/reload, commentary/replay and the identified required gaps.
Record exact application/build head, original evidence, input sequence, outcomes, screenshots and remaining limitations.
Never operate the owner's live game or call prepared packets natural play. Full suites run on the reconciled integrated milestone.

[confirmed: original0791:9372/ED8A; E031C37; archaeology b0c0fae2] The [Insert probe](../../../measurements/T191/insert-audit/README.md) executes four bounded original pitch-key controls, including positive speed controls, with a declared keyboard-ready service input. Insert leaves the replay setting unchanged on the pitch for both initial settings; ED8A contains the menu toggle. This corrects one suspected gap above without claiming a natural complete match or changing replay behavior.
