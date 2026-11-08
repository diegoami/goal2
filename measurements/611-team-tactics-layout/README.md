# Original TEAM editor layout comparison

Required bounded follow-up: [issue646](https://github.com/diegoami/goal2/issues/646), under611.

[confirmed: original1771:1981→157D; retained T156 step33] The original
[tactics editor](../../docs/original-game/images/t156-033-team-tactics.png)
draws the complete TEAM panel each iteration. Compare the rebuilt
[1440×900](tactics-1440x900.png), [1800×1125](tactics-1800x1125.png) and
[2110×1213](tactics-2110x1213.png) captures, bound to source in [receipt.json](receipt.json).
The reference is Holland2028; the rebuilt save is Denmark. This comparison establishes
structure and presence, not equal values or pixel-perfect rendering of the same state.

| Region | Original step33 | Rebuilt accepted source8796ef50 | Required correction |
| --- | --- | --- | --- |
| Left TEAM header | Country/status, manager/skill, aligned world/continental Now/Top, formation, strips | Country, formation, next opponent only | Restore accepted original-backed header beside editor |
| Left lower panel | Four line skill rows and conditional four performance rows | Omitted | Restore skill bars; preserve original performance visibility/context |
| Middle upper panel | Three team tactics, then separately headed five player defaults | Combined eight-row table, repeated other-option column | Restore visible three/five grouping and original label/value hierarchy; retain all eight controls |
| Middle lower panel | XI caps/age and four characteristics | Four descriptors in a separate tall column; XI numbers omitted | Keep original-backed descriptors and restore XI numbers/relationship |
| Right roster | Twenty full names coloured by position, clear XI/bench break | Twenty rows; accepted638 now colours names | Preserve corrected full-name colours and readable selection/injury handling |
| Navigation/feedback | Bottom change-tactic and Esc-exit cues | Bottom keyboard/click controls and current-change feedback | Retain accepted keys, confirmation/pending and legal return behavior |

[derived] Existing S04/S07 CountryCard, RankColumns, StripGlyphs, LineBars and
CharacteristicPanel already implement accepted data/rendering pieces. Reuse/factor those
pieces rather than embedding a second static tactic table, inventing aggregates, or
calling a full card decoder on every cursor move. Live values must use accepted current
record/order/tactics data; career data is not fresh match data. PR645 only corrects live
traits, and PR640 owns request/acknowledgement/return and refresh performance.

[designed: owner611, clarified2026-11-08] Restore this information architecture while
preserving readable scalable24px text, all20 rows, eight keyboard/mouse changes and
pending confirmation. Capture actual pre-match and live-stop results at the three sizes,
including native Windows, and compare original-backed values without mutation. A static
screenshot or pre-match receipt cannot accept live freshness, match outcome equality,
full TEAM parity, season continuation or the complete611 journey.

Reproduction: run capture.py from its committed measurements directory with the private
T191 audit target and a separate output directory, under the prepared offscreen environment.
The script resumes that isolated save, enters tactics by real desk keys and makes no edits.
No original bytes/private save/new engine output are included in this evidence.
