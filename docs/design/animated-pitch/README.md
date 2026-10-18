# Original-engine animated pitch sequence

[designed: owner,2026-10-18] The next feature after T80 is a simple animated
pitch before the management GUI redesign. Qt keeps management; Pygame renders
numbered team markers and a ball from original-engine observations. Owner model
settings remain Luna High for Easy, Sol Low for Medium and Sol Medium for Hard,
with independent MiniMax M3 thinking reviews and follow-ups until accepted.

[designed] Separate acceptance layers keep coordinate evidence, process delivery
and graphical pacing independently reviewable:

| Contract | Useful outcome | Importance | Difficulty / implementer | Merge after |
| --- | --- | --- | --- | --- |
| [T81](../../tasks/T81.md) | Validated coordinate/identity contract and observation parity probe | High: unlocks trustworthy movement | Hard / Sol Medium | T66, T80 |
| [T82](../../tasks/T82.md) | Bounded headless pitch-frame stream and presentation completion gate | High: enables responsive animation without early publication | Hard / Sol Medium | T81, T80 |
| [T83](../../tasks/T83.md) | Paced real Pygame pitch, numbered markers and ball | High: requested visible feature | Hard / Sol Medium | T82, minute-label fix |

[confirmed: original kit424d5998076da1e4efc399c2715689ddb44d3e1a]
`Match.pitch()` returns22 player records plus ball coordinates, and `ticks=True`
yields tick stops. Its coordinate meaning is documented as likely. Current
application accessors expose unsigned `x` and signed `y`; this does not by itself
establish a usable projection or require a vendor change.

[confirmed: static sources at the same kit pin] Named upstream
`static/goal-exe/named/seg_0791_07.c` draw-player/draw-ball routines and listing
`static/goal-exe/code/seg_0791_05.asm` predicates sign-extend both coordinate bytes.
[derived: draw buffer offset signed(x)*160+signed(y)*2+0x90E]
Original `x` is transverse/screen-row and `y` longitudinal/screen-column.
[confirmed: static predicates2DCA/2E00] These accept absolute coordinates8/37
and9/39 respectively; they are not universal lifecycle bounds. T81 must validate
normalization, visible projection and half-transition interpretation behaviorally.

[confirmed: static named seg_0791_08.c bind_pitch_player; seg_0791_02.c slot mapping,
same pin] Pitch records bind player words from squads and local slots1–11.
[derived] Local slot labels are supported; persistent shirt numbers, substitution
identity changes and halftime projection still need T81 evidence. Do not rotate
coordinates solely because a halftime commentary event was received.

[confirmed: F013, same pin] Original display and movement consume RNG on the
watched path. [designed] Keep guest routines executing and observe their result;
separate presentation frames from canonical match events/results. Preserve exact
Memory/both RNG seeds, publication after validated completion and view consumption,
cancellation before publication, and existing saves. No alternative physics or
positions inferred from commentary.

[designed] Each future task gets main-session failing/positive preflight against
then-current accepted main before dispatch. Unresolved geometry is an evidence
gate, never permission to guess. Original binary/Memory/raw screen bytes stay
ignored; tracked evidence contains derived numbers, hashes and rebuild-only images.
T79 later styles the accepted pitch/frame contract and does not duplicate it.
Execution status belongs to GitHub labels, never this document.

## Issue contracts

[designed: main task administration,2026-10-18] [T81 / #211](https://github.com/diegoami/goal2/issues/211), [T82 / #212](https://github.com/diegoami/goal2/issues/212), [T83 / #213](https://github.com/diegoami/goal2/issues/213).
