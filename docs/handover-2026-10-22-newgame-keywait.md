# Handover 2026-10-22: new-game savestates in the key read, and the interrupts to the first manager menu

From goal2-archaeology, answering goal2's request diegoami/goal2-archaeology#367 (stage 3, G10, goal2's core).

## What this branch holds
- `docs/assumptions.md`: rows NG-7 and NG-8 (new), sourced from finding F032.
- This file.

## Evidence
- Finding **F032** (proposed), goal2-archaeology PR #368: `findings/F032-from-the-titles-key-read-…md`.
- Run record **E038-r0001** (DOSBox-X 2024.03.01, one new game at DOS 10:00 on 10/04/2026, keys `n Enter Enter b o b Enter Enter Enter`).
- Trace `experiments/E038-new-game-keywait/out/trace-r0001.json`: the original's code under Unicorn from the title state. It serves only the interrupts below and ends byte-equal to DOSBox-X's manager menu (screen, `DS:7B62` `EE42`, `DS:7B64`, player and country arrays). Each intermediate screen matches too, 6 of 6.

## The savestates (owner's Drive, folder root; nothing of the original goes into goal2)
| screen | Drive name | sha256 (prefix) | 08DD returns to | callers |
| --- | --- | --- | --- | --- |
| title-load-prompt | `e038-r0001-title-keywait.sav` | `1c106cc3` | `1771:085F` | `0000:0029` |
| title-player-count | `e038-r0001-title-player-count.sav` | `6ad3920d` | `1771:0081` | `1771:08A8` (near), `0000:0029` |
| country-select | `e038-r0001-country-select.sav` | `586dbfcf` | `1771:28F5` | `1771:2D55`, `0000:003F` |
| country-select-name-entry | `e038-r0001-country-select-name-entry.sav` | `879a5520` | not in the read (polled screen) | — |
| bulletin "APPOINT A NEW MANAGER" | `e038-r0001-after-name-1.sav` | `3036081b` | `000E:0629` | `000E:6964` (near), `0000:0078` |
| bulletin "GROUPS ARE ANNOUNCED" | `e038-r0001-after-name-2.sav` | `8df96e01` | `000E:0629` | `000E:6625` (near), `0000:00BE` |
| manager-menu | `e038-r0001-manager-menu.sav` | `4031771a` | `000E:75D1` | `0000:00CB` |

The same files are under `goal2-archaeology/E038/` with the record's names (`e038-<screen>-r0001.sav`). Run against goal2's `Core.start`, every read state passes `read_entry`. The core then stops with `UnknownScreen` only because `goal2/core/screens.py` has no entries for these sites yet. The name-entry state is refused (no 08DD frame), as it should be.

## The interrupts from the title's read to the first manager menu (F032)
Two routes reach interrupts. One is `int` instructions. The other is Turbo Pascal's `Intr` 235C:000B and `MsDos` 235C:0000: `Intr` pushes the flags and a return to 235C:0045, loads the vector from 0:4n and `retf`s into the BIOS, with **no `int` instruction**. A Unicorn interrupt hook therefore misses it. Hook `Intr`'s entry instead: the stack holds the return IP and CS, the register record's offset and segment (AX BX CX DX BP SI DI DS ES Flags), and the vector number. Serve the call, write the record back, and `retf 6`.

| # | when | interrupt | site | effect |
| --- | --- | --- | --- | --- |
| 1 | after `n` at the title ("loading") | INT 21h AH=3Dh AL=02h | `MsDos` from `214B:1ABE` | open `goal.dat` (ASCIIZ at SS:3DB2); AX = handle, CF clear |
| 2–11 | the same | INT 21h AH=3Fh ×10 | `MsDos` from `214B:1B81` | reads 2064, 33671, 3061, 1755, 135, 387, 129, 129, 129, 2580 bytes, the whole 44040-byte file in order; the first five go to heap blocks, the rest to DS:9D80, 9B7C, 9BFD, 9C7E, 9F03; AX = count |
| 12 | the same | INT 21h AH=3Eh | `MsDos` from `214B:1A54` | close |
| 13 | after Enter on the first bulletin | INT 21h AH=2Ch | `int 21h` at `23E4:11D9` (`Randomize`, called from `1771:6730`, called from `1771:76B1`) | CX → DS:7B62 (hour·256+minute, the seed), DX → DS:7B64 (seconds, hundredths) |

There is no INT 10h and no AH=2Ah on this path: the year was read before the title. The program reaches the video BIOS only at start-up, in the exit procedure 214B:136B (F10 quit), in CRT `Write(Output)`, and in the DOS shell, which is dead code in 08DD. The INT 10h goal2 met when leaving the menu is likely the exit procedure. The site the core reports would settle it.

Key and poll behaviour on this path:
- Every read goes through 214B:08DD.
- The name entry (214B:0D90) is a **polled** screen. It polls 214B:0723 at return 214B:0DB9 and blinks the cursor from the BIOS tick count. It calls 08DD (return 214B:112B) only after a poll answers "a key waits". Answer that poll "yes" for each letter and for Enter.
- The bulletins' animation (000E:0572) made no polls in the trace.

## What the goal2 session does
1. Check NG-7 and NG-8 against goal2's code and tasks (core runner, `screens.py`, the new-game work of stage 3).
2. Map the sites above into `goal2/core/screens.py` (kinds: title-load-prompt, title-player-count, country-select, country-select-name-entry as a polled kind, bulletin, manager-menu).
3. Open a docs-only PR from this branch and ask the owner for the reviewer.

## Owner's wishes
None stated for this request.

## What goal2-archaeology does next
Nothing is pending. Other new-game paths (loading a saved game, several managers) were not traced. Ask by a new request if the core needs them.
