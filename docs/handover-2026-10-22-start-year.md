# Handover 2026-10-22: the start year as an input to the core

From goal2-archaeology, answering goal2's request diegoami/goal2-archaeology#369, a follow-up to #367 / F032 / NG-7–NG-8.

## What this branch holds
- `docs/assumptions.md`: rows NG-9 and NG-10, new, sourced from finding F033.
- This file.

## Evidence
- Finding **F033** (proposed), goal2-archaeology PR #371.
- DOSBox-X runs **E039-r0001** (DOS date 10/04/1990) and **E039-r0002** (10/04/1992). Both are new games to the first manager menu at `cycles=30000`.
- **E039-r0005**: a savestate caught during start-up, before the date read.
- `experiments/E039-start-year/out/derive-r0005.json`: the state carried to the date call under Unicorn.
- `out/trace-1990.json` and `out/trace-1992.json`: from that state, each date served, to the first manager menu.
  - Each read matches the DOSBox-X record of the same date: site, callers, screen, DS:A9FD, the seeds, and the game record's +0x38..+0x41.
  - At the manager menu the screen bytes and the player and country arrays are byte-equal.

## The date (F033)
- **One read only.** The DOS date is read once, at start-up. Unit start-up `214B:206A` ends by calling `214B:1C63`, which calls `GetDate` `235C:006C`, which executes `mov ah, 2Ah; int 21h` at `235C:0071`. It is a real `int`, not `Intr`.
- **What is kept.** The year is stored at `DS:A9FD`; month, day and weekday are dropped.
- **No key read comes first.** The first key read is the title's, so the state is stopped at the date call.
- **The start year and stage.** `DS:A9FD` is used only at a new game, by `1771:9B85` (after the title's `n`):
  - start year `+0x3A` = DOS year + 1, then + 1 if odd;
  - `+0x40` = (start year mod 4 = 2);
  - stage `+0x3C` = `DS:118E[+0x40]` (`02 05`).
  So a player who wants even start year S answers DOS year S − 1 or S − 2.
- **Measured:**
  - DOS 1990 → 1992, stage 2;
  - DOS 1992 → 1994, stage 5;
  - DOS 2026 → 2028 (E038), the "2028" on the screens.
- **Accepted years.** The game checks nothing; DOS returns only 1980–2099. Other years were not tried.
- **Nothing else depends on the date** on this path. The seed is the DOS time at the first bulletin (NG-8). E039 measured `DS:7B62` = `EE42` at the manager menu for both 1990 and 1992 at 10:00, so the start year did not change the main seed word up to there. NG-6's "the start year seeds the RNG" is not tested by F033.
- **DOS's own date copy.** DOS keeps a copy of the date in guest memory (in DOSBox-X: weekday at linear 07C76, year at 07C7A). GOAL never reads it; the delivered state holds 1990 there.

## The state (owner's Drive, folder root)
- **`e039-r0005-date-call.sav`**, sha256 `0d9c683023c7327f17bfc29900f2eff4e703641d21d3f353693f09654688494b`.
  - CS:IP = load+235C:0071 (2B7F:0071 at load 0823), the `int 21h` not executed yet.
  - Registers: AX 2A10, BX 3D6F, CX 0, DX 296E, SI 0, DI 3DF0, BP = SP 3DDA, SS 3875, DS 2DA4, ES 3D6F, FLAGS 7206.
  - Stack at SS:SP: the saved BP, the far return 214B:1C82, then GetDate's four far pointers.
  - `DS:A9FD` = 0; `DS:A9FF` = 4279 (the delay calibration, already done); BIOS tick 0040:006C = 655438.
- **How it was made.** E039-r0005's start-up savestate (`e039-r0005-pre-date.sav`, CPU load+2382:0074) was run under Unicorn to the call. The written file is that savestate with its `Memory` component and the `CPU` component's registers replaced. It is a state for the core, not one DOSBox-X was shown to load.
- **Copies.** `goal2-archaeology/E039/` on the Drive holds every state of the runs under the records' names.

## The interrupts from the date call to the title's read (NG-7's form)
| # | interrupt | site | the core answers |
| --- | --- | --- | --- |
| 1 | INT 21h AH=2Ah, the state's first instruction | `int` at `235C:0071` (GetDate; callers 214B:1C82, 214B:210B, 0000:000F) | CX = year, DH = month, DL = day, AL = weekday (0 = Sunday); continue at 235C:0073 |

Nothing else is an interrupt on this path.
- **Polls.** 333 calls of "key pressed?" 214B:0723 from the title's animation, at returns 1771:0723 (×216) and 1771:0782 (×117). Answer them "no key", as the existing core does.
- **Speaker.** OUT 43h, OUT 42h ×666, IN/OUT 61h ×2.
- **BIOS tick.** `0791:F3F2` stores the tick count's low word at DS:8336 (the second random stream). The core has no timer, so it gets the state's value, `004E`, as both DOSBox-X runs did.
- **After the title's read.** NG-7's path follows, unchanged by the date.

## What the goal2 session does
1. Check NG-9 and NG-10 against `goal2/core/runner.py`, `docs/core.md` and the stage-3 tasks. Note NG-6's wording.
2. Add the core's second entry kind, "resume at a DOS call":
   - load the state with its registers;
   - serve its `int 21h` AH=2Ah with the player's date;
   - run to the title's read (1771:085F), where the existing table applies.
3. Open a docs-only PR from this branch and ask the owner for the reviewer.

## Owner's wishes
The owner decided (2026-10-22) that the player chooses the start year by the date the core answers, never by writing memory or patching code. That decision is the reason for this answer.

## What goal2-archaeology does next
Nothing is pending. Other start years can be measured by a new request if the core needs them.
