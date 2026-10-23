# Handover: existing G13/G16 states (2026-10-23)

From goal2-archaeology, answering [archaeology #390](https://github.com/diegoami/goal2-archaeology/issues/390),
delivery [PR #392](https://github.com/diegoami/goal2-archaeology/pull/392), task T84.
The branch `docs/register-existing-states-2026-10-23` changes only this file and
`docs/assumptions.md` (CORE-PROMPT-1, CORE-SHOOTOUT-1, CORE-LIFECYCLE-1, CORE-STATE-1).
It adds evidence and its limits, with no core implementation or remaster design change.

## Evidence and retrieval

[confirmed: existing artifacts, not a new rule] The delivery has 21 unchanged files: all 17 E031
campaign `.GL` saves, the E031 shootout announcement `.sav`, and three published E014 input states.
The complete filename/size/SHA-256/source-commit index is archaeology `notes/390/inventory.json`;
the explanation and missing-state list are `docs/requests/390-existing-states.md`.
These are in archaeology PR #392; consume its merged revision before merging this branch.
The original observations/findings themselves are already merged at archaeology
`255de405b9c6a730960dcae23ed423ae433ad9f5` (F015/F016/F017/F023/F029/F030 remain proposed).

[confirmed: content verified after upload and download] Private
[Drive delivery folder](https://drive.google.com/drive/folders/19VahGbhN6YPiREXZ0uPAZbf7sCErSCLY):
`goal2drive:goal2-archaeology/390-existing-states-20261023/`.
Do not put any `.GL`, `.sav`, guest bytes or original-game asset in this Git tree. Fetch only the
needed files into `.cache/`. The archaeology verifier checks all 21 copies by SHA-256, the
shootout's screen digest and its saved caller frames; it also rejects a same-size corrupted file.

## The useful immediate input

[confirmed: E031 g1 checkpoint 3874; source log commit c601ecc7219b165de09d955e45a6eece5f4ab2c0]
`3ea57029282b849f-g1-03874-shootout-start.sav` has SHA-256
`3ea57029282b849fd3114a995178f35e48c420c768f0702b9d3b7d48600dc1fc`.
It shows Belgium 2–Holland 2, LAST 16, `penalty shoot out  PRESS ANY KEY`.
Season 1, stage 8, next fixture 2392, count 2393. This is an in-match checkpoint, not a `.GL`.

[derived: read-only stack inspection in #392, using the original's 08DD/Intr frame convention]
The CPU is in BIOS `F000:CFA6`, SS `3875`, SP `3CF2`; recover the original read frame instead of
using the BIOS's EBP `FEFE`. Read BP `3D1A` returns to `214B:098A`; its caller BP `3D20`
returns through `214B:054E`; message-box BP `3E7A` returns near to `0791:A137`, following
`A132 call far 214B:04F8`. The parent shootout frame BP is `3EA6`. These frames distinguish
this message box from other `098A` uses. The original announcement accepts any key.
This handover does not claim a goal2 `Core.start` replay or order-selection test was run.

[confirmed: proposed listing readings F015/F030; E031 C48b/c are screen observations]
The following managed order is `0791:9B93`, key helper called at `9D62`, returning `9D67`;
the helper's read is `214B:157C`. It asks for all available players among the first eleven,
not five. Up/Down navigate, Enter appends, Esc undoes the last pick. Enter pushes back Down.
There is no managed-order timeout/default in this loop. The parent A10A frame, passed at
`[9B93 bp+4]`, holds side byte `-1F` and byte-string order at `-1A + 12*side`.
The highlighted squad slot is `[9B93 bp-6]`. No separately retained E031 order-screen state
was located; resume the supplied announcement input if the core needs to capture one.

## What remains missing, and what the evidence does establish

[confirmed: E031 logs C43–C49/C56–C57] E031 logged a corner taker at g1 1552, goal-kick taker at
2630, extra time at 3830, its half time at 3851, order at 3876/3884, and sudden death at
4611–4617. Its checkpoint log retains none of those exact screens as a separately published
state. A screen read does not establish an available savestate. No new playthrough was made.

[confirmed: F030, proposed static reading] Taker `CC7B` role `[bp+4]`, side `[bp+6]`, highlight
`[bp-5]`, current pick `[bp-7]`; stored role word `DS:9976 + 10*side + 2*role`. Its poll in
CC2E is CC4F, followed by CED9's final poll and CEE8's optional key read. No key for 1000 polls
keeps the current pick; 10 seconds is nominal calibrated time. C computes the pick, Enter
uses the highlighted available player, Esc keeps the current pick; other keys restart the wait.
Space at a taker opens the board and performs another blocking read. Stop the core at the
decision poll before allowing its timeout if a client must answer it.

[confirmed: existing listing, archaeology pin above] Extra-time `9B0C` and `9B5B` call the shared
`ED8A` menu at returns 9B42/9B70 when `DS:80FD` is set. The menu's helper call returns EE9F;
its selection word is `[ED8A bp-7]`, country `[bp-5]`, side `[bp-2]`. It blocks for input and
uses EA09 to validate an exit; it is not the taker timeout. No retained extra-time-menu
checkpoint was located. E022 E062/E19F and EA09 EC60 vacancy remain unvisited-state gaps;
here E022 is a routine, not the video/contest experiment identifier.

[confirmed: F016/F017 and committed E014 captures; producer and storage commits distinguished]
Existing checks still give 300/300 computer squad-word comparisons and 38/38 recreations from
uniquely recovered RNG entry words over five annual pairs. These are three **computer squads**,
not the managed squad plus 80 pool. E014's delivered states are its original E006 input,
`e014-s1-y0` and `e014-cal3-y1`; several other annual captures have hashes/extracted records but
no located full state. The full missing-state hashes are in archaeology's delivery document.
No managed 100-player boundary or managed replacement RNG proof is added by this handover.

[confirmed: E031 C56/C56b/C57/C57b] E031 observed Nicholls retire and Bolton replace him
(g1 2390/2394), Kelso quit (2560) and another retirement (3421). `G2C.GL`/`G3A.GL` bracket the
first event but do not isolate the replacement instructions. F017's managed path and result →
ranking → country rating → replacement quality chain remain static; no measured change in
rank causing a change in replacement quality is supplied. The desktop's T111 annual and
replacement evidence is separate and must retain its own provenance.

## What the goal2 session does

1. Confirm archaeology #392 is merged, then check the four new rows against current core code
   and G13/G16 tasks. The World Cup, round-pause and normal annual paths already supplied by
   the desktop on #390 are not requested again.
2. Open a docs-only PR from this branch and run the usual gate. The requester explicitly
   authorized merging docs-only handovers without a separate reviewer; no reviewer question
   is needed for this handover. goal2 owns its PR and merge.
3. Use the supplied announcement checkpoint for the next shootout slice. Keep missing
   taker/extra-time/vacancy states as explicit evidence gaps; request targeted collection only
   when static evidence and available continuations cannot supply what is required.

## Owner's wishes and archaeology's next work

[owner: #390] Reuse existing evidence, avoid an expensive new playthrough, do not edit game
memory to reach a state, and keep original bytes private. No remaster design decision is made
here. Archaeology has delivered the located inventory; any requested fresh collection is a
separate scoped request with the above missing cases named explicitly.
