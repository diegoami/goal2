# T203: exact owner bench/request/opportunity flow

[designed: owner clarification #662, T203, 2026-11-08] Esc/Enter during play opens
own players directly, without setting the independent request. Enter on any player
or the explicit request/cancel button toggles that latch through an acknowledged
edit. Bench Esc returns to the visible match menu; Play or Esc there resumes.
The menu still provides team tactics. No request or confirmed swap auto-resumes.

A real eligible guest stoppage offers the timed opportunity; both accepting keys
open the legal bench. Pairs apply immediately through the guest. Only an actual
made-swap acknowledgement clears its presentation cue on bench/pitch/team/menu,
not submission or refusal. Guest legality and allowance remain authoritative, so
clearing a cue imposes no one-swap limit. Half-time substitutions stay immediate.
No engine, game rule, private option/RAM, wire/schema, campaign or season edit.
Model: inherited Codex GPT-6 family; exact variant unavailable.

## Changed files and reasons

- match_day.py: own bench over the existing menu at a normal pause; acknowledged
  cue state and current views refresh together. No fabricated ball stoppage.
- s19_bench.py: explicit readable button shares player Enter; independent
  opportunity presentation state, confirming lock and current stopped metadata.
- s15_match_menu.py: existing row widgets refresh the acknowledged XI and cue;
  cheap XI/role/injury invalidation avoids decoding unchanged players.
- s17_pitch.py and s10_team_tactics.py: consistent request/opportunity status,
  retaining the actual request latch and the established TEAM calculations.
- test_substitution_flow_t203.py: exact entry/toggles/accept keys, pending/refused/
  made acknowledgement, current lineups, permission retention, button render/
  header bounds at three sizes, zero redundant card decoding and full owner journey.
- test_substitution_actual_636.py: optional exact-owner variant reuses EVERY old
  full equality/publication guard; True/False/True, team view and half-time checks
  are additive. No outcome, seed, fixture, wait or timer assertion was relaxed.
- test_live_team_tactics_610.py and test_ui_pitch_t166.py: navigation selectors
  follow direct bench entry; the existing menu/Play/close assertions remain.
- test_live_card_overlay_619.py, test_match_menu_arrows_t184.py and
  test_roster_colours_637.py: minimal stub fields matching real UI objects only.
  Every old data, colour and navigation assertion remains intact.
- docs/ui.md: the exact owner flow; task contract is unchanged.

## Red and measured corrections

The unchanged-runtime actual owner-key red (22.220s) records literal Esc→MenuScreen,
then Enter→PitchScreen, request FALSE, with NO preparatory Space. Packet reds prove
missing explicit button, stale MAKE_NOW after acknowledgement, and stale menu XI.
The original-name-bearing lineup assertion log remains PRIVATE; its public receipt
records only error/count/hash. No fixture original records enter Git.

The first functional owner run passed308.681s but is NOT final acceptance: root
inspected captures and found white-on-white button text and stale lowercase bench
context. Those private captures and hashes remain unchanged. Measured contrast
was1.15; final actual rendered glyph/background controls require21 normal,7.46
 disabled and9.04 focused contrast at1440x900,1800x1125 and2110x1213. Real Qt focus,
visible pixels, full cue/button bounds and no overlap are checked. Earlier palette-
only focus calibration is not rendered-focus evidence; button-render-v3 and the
final focused log provide the rendered checks.

Two unchanged menu refreshes previously decoded22 cards in1.0873s; final control
requires0 decodes (measured0.000238s), while changed XI/roles/injuries still invalidate
rows. Request/tactics acknowledgements always refresh status without decoding all11.

## Final measured proofs

Application/ActualOwnerFlow source is frozen at7b85d680e12e5261aa6c3dbca1fe82926f64a0b0:

- Linux actual owner journey:1PASS/0skips/550.483s, both flags, exact initial keys,
  True/False/True with no pairs, resume/badge, REAL timed opportunity, acceptance,
  immediate swap, all-view case-insensitive cue/current-XI checks, refusal,
  team tactics and immediate half-time substitution.
- Windows native Qt/PyPy worker:1PASS/0skips/812.815s (813.490s bootstrap wall), same
  full owner scenario. No activation window, direct-target test keys, no owner
  game process/data changes. Main inspected the private native captures.
- Final focused controls:52tests,49executed PASS/3 existing declared slow cases
  excluded,244.828s. No skipped case counts as actual proof.

Both actual journeys retain complete result/events/full-memory/both-RNG/career
and exactly-once-publication assertions against the SAME-CHOICE HEADLESS BRIDGE
using the same accepted sealed engine. These are UI/worker translation equality
proofs, NOT fresh original-binary/Unicorn or whole-season comparisons. Original
engine fidelity is inherited from accepted upstream; engine files are unchanged.

The old main gate completed219/223 modules,239 declared slow exclusions, with only
four fixture/navigation errors. Raw failure is preserved; it is not relabelled PASS.
Approved corrections add missing window/pitch-refresh/bench/lineup-map stub fields
and wait for BenchScreen at the SAME120s limit, removing obsolete Space. Focused
619+184+637 then20tests PASS/1existing slow exclusion in1.139s; the actual166
BenchAndClose class2PASS/0skips in8.940s. No application or ActualOwnerFlow dependency
changed. Main owns the NEW final gate/checks/merge/install.

`final-v2/acceptance-v2.json` binds measured7b85, current app/resources/tables/test
bytes, fixtures, all public receipts and private-capture hashes. Native raw/archive
files remain in the recorded keeper, never overwritten. Only the four approved
non-journey test fixtures/selectors and proof metadata differ after7b85. The
previous package is historical: tests are ZIP inputs, so main builds a fresh final
package. No old ZIP is claimed as the final artifact.

Repeat the actual case with source .cache/cloud.env and GOAL2_SLOW=1 through a
registered heavy job: python -B -m unittest
 goal2.tests.test_substitution_flow_t203.ActualOwnerFlow -v.
Private inputs/dependencies use existing explicit requirements; retained actual
runs have zero skips. Full suites/review were not started by the implementer.
