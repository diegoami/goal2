# Where goal2's UI design lives

This page is the index of every source the UI redesign rests on. Most of the design is recorded on
GitHub issues, so it links them. Read it before changing a screen of `goal2/ui`, together with the
[UI evidence rule](../../CLAUDE.md#ui-evidence). Status (what is done, what is next) is kept on the
issues, not here (CLAUDE.md rule 9). [designed: owner, 2026-11-27]

## What is being built

A native Windows desktop game: the PySide6 window `goal2/ui`, drawn in the original's layout
grammar, over the Python route and the sealed match engine running under PyPy in its own process,
shipped as a portable Windows ZIP. [designed: owner, 2026-11-03, #524, #526, #527; 2026-11-08,
#666; [plan.md](../plan.md#architecture), [technology](technology-2026-11/README.md),
[engine process](../engine-process.md), [packaging](../packaging.md)]

`goal2/desktop`, the older window, is what v0.1 ships. It takes no redesign work, and T169 replaces it
with `goal2/ui` in the portable build. [designed: owner, 2026-11-03, #527; 2026-11-13, #705]

## Which source wins

When two sources disagree, the one higher in this list wins. A departure from the original must name
the benefit to the player or the approved rebuild requirement behind it and is tagged `[designed]`.
If a comparison shows no benefit, keep the original pattern. [designed: owner, 2026-11-25,
[#862 owner direction](https://github.com/diegoami/goal2/issues/862#issuecomment-7162783816)]

1. **The original, as documented.** The default for screen layout, information hierarchy, colour
   roles, key placement and the order of play.
   - [The original's illustrated manual](../original-game/README.md): the uninterrupted
     [playthrough](../original-game/playthrough.md) (run T156-R1), the chapters, the
     [screen inventory](../original-game/screen-inventory.md), the [flow](../original-game/flow.md)
     and the [coverage](../original-game/coverage.md) checklist of what is not yet pictured.
   - **The original's own manual, `GOAL.HLP`**, the help text the game shipped with. It is private
     (CLAUDE.md rule 14): it lives in the owner's folder, is imported by S01 and shown by S22 (F1).
     [manual-fidelity.md](ui-2026-11/manual-fidelity.md) cites it by section and line, and the
     original chapters cite it as "original GOAL.HLP".
   - goal2-archaeology's E031 play guide and its
     [observed-claims register](https://github.com/diegoami/goal2-archaeology/blob/main/experiments/E031-play-the-game/out/claims.md)
     (private repository), cited as `E031 Cnn`.
2. **The owner's decisions, on GitHub.** Each one is tagged where the design applies it.
   - [#526](https://github.com/diegoami/goal2/issues/526#issuecomment-6590816260), 2026-11-03: the
     screens S01–S22, their flow and keys, decisions 1–19. Collected in
     [§6 of the design](ui-2026-11/README.md#6-decisions-owner-2026-11-03).
   - [#527](https://github.com/diegoami/goal2/issues/527), 2026-11-03: PySide6 widgets, the Python route,
     the engine boundary.
   - [#666](https://github.com/diegoami/goal2/issues/666), 2026-11-08: the original's layout grammar
     at 2× (16 × 32 cell, one text size, rule-and-label frames, line-art titles, no dead regions),
     shown at 4:3. Its diagnosis and method are in
     [fidelity-review.md](ui-2026-11/fidelity-review.md), and the drawn proposal in
     [proposal/](ui-2026-11/proposal/README.md).
   - [#862](https://github.com/diegoami/goal2/issues/862), 2026-11-25: the walkthrough-led redesign,
     the current execution order of #666. The issue body orders the slices, the owner's direction
     comment sets the rule above, and each later comment records one slice: its original evidence
     before the work, and its merge, Windows captures and receipts after it.
   - [#777](https://github.com/diegoami/goal2/issues/777): optional 22- and 24-player squads.
   - [#573](https://github.com/diegoami/goal2/issues/573), decision 19: S17's players are
     non-overlapping discs with the role letter inside, and everything else on the pitch mimics the original.
   - [#862](https://github.com/diegoami/goal2/issues/862), 2026-11-27 (answers to the design audit):
     (a) S18's stops sit on the key line, as in the original, with the pitch fully visible; the
     substitution notice keeps its blink and colours, so it stays as prominent as #426 asked.
     (b) #451's targeted pool suggestion is a post-playable `[designed]` addition to S08, after the
     full assistant (#594). (c) No screen-reader route and no participant usability thresholds:
     the original-first rule and the keyboard, mouse and Windows-scaling checks are the bar (#263).
     (d) vision-266's rulings do not bind beyond what the original shows.
3. **The accepted design**, [ui-2026-11/README.md](ui-2026-11/README.md): every screen S01–S22
   with its original evidence, the rules for the whole UI (§3) and the mapping of every original
   screen (§5, checked by [check_mapping.py](ui-2026-11/check_mapping.py)). Supporting records:
   [prematch-actions.md](ui-2026-11/prematch-actions.md),
   [substitution-flow.md](ui-2026-11/substitution-flow.md),
   [manual-fidelity.md](ui-2026-11/manual-fidelity.md). Its mockups predate #666 and show the
   pre-grammar look. Where they differ, #666 and #862 decide how a screen is drawn.
4. **The technology**, [technology-2026-11/README.md](technology-2026-11/README.md), and the
   window's own guide, [docs/ui.md](../ui.md).

## Where the work is tracked

- [#862](https://github.com/diegoami/goal2/issues/862) orders the slices and records each one's
  merge. This is where to look for what is next.
- [#666](https://github.com/diegoami/goal2/issues/666) is the umbrella, and the
  [UI fidelity milestone](https://github.com/diegoami/goal2/milestone/5) holds its signature-element
  issues #673–#680. #862's slices take them up screen by screen.
- The foundation (#667, T215) merged in [#748](https://github.com/diegoami/goal2/pull/748) after
  the milestone review and owner playtest on [#749](https://github.com/diegoami/goal2/issues/749).
- Behaviour that the redesigned screens need but the route does not supply yet lives on its own
  issue, which #862's slice names: #457 (commentary pause), #570 and #571 (S11), #551 (several
  managers), #817 (native stopped-match reads).

## Evidence of the redesigned screens

- **Before and after captures of each #862 slice**, from the installed Windows preview at 150%, are
  indexed in `docs/design/ui-2026-11/review-862/README.md` on the branch
  [`evidence/862-ui-review`](https://github.com/diegoami/goal2/blob/evidence/862-ui-review/docs/design/ui-2026-11/review-862/README.md).
  The branch is not merged into `main`. Receipts for each slice are in `goal2-keep/T862/` on the
  owner's machine.
- **Renders of each screen as first built** are in the `T1*-screens/` and `T215-*` folders of
  [ui-2026-11](ui-2026-11/). Each folder records the build it was taken from.
- **The rebuild's illustrated manual, [docs/current-game](../current-game/README.md), shows the
  older window.** It was captured from `goal2/desktop` (the core route and the pygame match window)
  at 1440 × 900 on 2026-11-09, before T215 and #862. It records what v0.1 ships, not `goal2/ui`.
  For the redesigned window, use the captures above. A manual of `goal2/ui` is still to be made
  ([#862 first review](https://github.com/diegoami/goal2/issues/862): "capture the installed
  `goal2-new.cmd` build").

## Earlier directions: history only

These directions came before the 2026-11-03 design and the 2026-11-08 grammar decisions. They take
no new work. Where they disagree with the sources above, the sources above win. A ruling one of
them recorded counts only where the design above carries it.

| Document | What it was | Replaced by |
| --- | --- | --- |
| [vision-266](../vision-266/README.md) | The finished-game vision accepted on #266 (2026-10-20) for the `goal2/desktop` shell: retractable bars, two commentary lines, illustrations with fictional data | the design of #526 (2026-11-03) and #666 |
| [redesign-253](../redesign-253/README.md) | The parity inventory, surfaces S01–S15 and the approved queue built from vision-266 | #526's screens S01–S22 and #862's order |
| [football-gui](football-gui/README.md) | The "national-team dugout" proposal (2026-10-18): evergreen and paper surfaces | vision-266, then #526 |
| [desktop-ui-roadmap.md](../desktop-ui-roadmap.md) | The `goal2/desktop` roadmap (2026-10-16): Qt management beside a separate pygame match window | #526 decision 2: the pitch in the main window |
| [browser-ui-roadmap.md](../browser-ui-roadmap.md) | The browser interface (T34–T38) | desktop-ui-roadmap, then #526 |
| [animated-pitch](animated-pitch/README.md) | The pygame pitch sequence T81–T83 | S17 in `goal2/ui` (#573) |
| [original-presentation-cues.md](original-presentation-cues.md) | The first visual-fidelity pass on `goal2/desktop` (#412, 2026-10-25) | #666 ([fidelity-review.md](ui-2026-11/fidelity-review.md) builds on it) |
