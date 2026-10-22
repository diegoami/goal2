# The core: the original's game under Unicorn

[designed: owner, 2026-10-22, #308] goal2's headless core is the original game's own code, run under Unicorn
from a savestate of the original; goal2 is the desktop interface and the bot over it. `goal2/core/` is its first
slice (T100, G8): the main loop runs from the main screen of a new game, stops at every key the original reads,
and saves and resumes exactly. It reuses the vendored kit `goal2/engine/original_match` (its `Machine` and
`Image`) as they are. Evidence cites goal2-archaeology at `53d7ef5` unless a commit is named.

```python
from goal2.core import Core
wait = Core.start(open(".cache/e006-r0001-main.sav", "rb").read())   # E006-r0001, Drive (docs/artifacts.md)
wait.site                    # '1771:28F5': the return address of the 214B:08DD call that reads the key
wait.text                    # the 80x25 text page, CP437, trailing blanks trimmed (E006-r0001's record, exactly)
wait.kind, wait.view         # 'team-info', {'country': 7, 'row': 1}: the screen kind and its cursor (T103, below)
wait.state.managed, wait.state.year()   # (7,), 0: read through the kit's Image (players(), countries(), ...)
core = wait.core
wait = core.press(0x1B)      # Esc: the main menu, site '000E:75D1'
core.queue("match-live", "r")   # a key for the next poll of a polled screen (below); refused if it does not list it
blob = core.save()           # the memory, the CPU, the seeds, the key log and the queued keys
core = Core.load(blob)       # at the same wait: core.wait
```

## What a wait is

- [confirmed: the kit's `match.py`; `static/goal-exe/code/seg_214B_02.asm` 08DD-0982] Every key the original
  reads goes through `214B:0723` ("key pressed?") and `214B:08DD` (read a key). 08DD stores the key code at
  `DS:A976`, copies it to `DS:A977` and returns it in AL. The return address of an 08DD call is the read's
  **site**; it says which screen reads. Sites met so far: `1771:28F5` the country browser ("team info",
  `1771:26B9`), `000E:75D1` the main menu (`main_menu_loop` `000E:7439`), `214B:09C4` the Y/N questions
  (`214B:09A7` under `214B:0566`, F030), `214B:157C` the menu reader `214B:1560` (the match menu), `0791:041A`
  the match board.
- `press(key)` answers the wait as 08DD would return the key and no other key were waiting: `DS:A976` and
  `DS:A977` := the key, AL := the key, `retf`. The key is the code 08DD stores (kit `screens.py`): the character,
  or an extended key's scan code adjusted (Left -1, Right -2, End..PgDn -3) plus 0x64; F10 is 0xA8. F5 (0xA3) is
  refused: 08DD prints the screen and reads another key (0957-0964).
- [designed] **A poll answers "no key"** unless a key is queued for its screen (T103, below). [confirmed: F030] A
  timed prompt is a count of polls with the calibrated delay `214B:1E09` between them, so it advances by itself on
  the original's own clock (the image's `DS:A9FF`, never rewritten): the captain prompt passes after its 1000 polls
  (`KeyWait.polls` counts them per poll site, `0791:CC54` for `wait_or_key`).
- A read with the pushed-back flag `DS:79AE` set is not a wait: 08DD returns without reading (08E3-08EF), so the
  guest's own code runs.

## Screens: the kind at each read and each poll (T103)

[designed: owner, 2026-10-22, #308; estimate 99, G9] `goal2/core/screens.py` maps each **read site** (the return
address of a 214B:08DD call) and each **poll site** (the return address of a 214B:0723 call) to a screen kind, read
from the original's stack and memory. The text page is never read to identify a screen; the tests check the table
against it (`goal2/tests/test_core_screens_t103.py`: kinds.tsv's text rules, and the quotes below).

- **Kinds** are named as in goal2-archaeology `static/screens/kinds.tsv`; each lists the keys the screen accepts,
  the `screen` rows of `catalogue.tsv`, as 08DD's codes. `KeyWait.kind` is the wait's kind, `KeyWait.view` its
  cursor or selection (the menu item, the country browsed, the fixture highlighted, the tactics row, the squad
  slot and its player).
- **Shared sites** are told apart by the caller frames the original pushed: the Y/N reader `214B:09C4` by the
  caller of `214B:0566` (`1771:091C` quit-confirm, `1771:0932` save-game-prompt); the menu reader `214B:157C` by
  its caller (`0791:EE9F` the match menu, whose own caller F20A, 9AE3 or F331 says before, at half time or after
  the match; `1771:1A24` the tactics screen; `1771:9022` the tournament view); `wait_or_key 0791:CC54` by its
  near caller (CC7B the captain prompt with role 1, 0B7C the timed questions, C50C the substitution notice).
- **Where frames are not enough, a cited field decides** [confirmed: the listings named]: the tactics screen edits
  only a managed country (`1771:0B77`, +0x2E > 0x80) with `DS:0C20` clear, else it is the view
  (`named/seg_1771_02.c` 1771:1981, the country its argument `[bp+6]`); the fixture list's hint comes from the
  highlighted fixture (`[bp-6] + [bp-8] - 1`, `fixtures` `DS:A92B`): neither country managed and the first byte
  0xFF "watch match", 0xFE "auto result", else none (`named/seg_000E_01.c` 000E:0000); the board `0791:041A` is the
  summary when it draws the man of the match (`DS:9A3F` clear and `DS:7C3A` set, `named/seg_0791_01.c` 0106);
  SELECT TEAM `0791:E61F` offers "take off this player" with substitutions open and the cursor `DS:0C1B` below 12
  (`0791:E44F`, `E2A0`); the team-info browser is `1771:26B9`'s mode 1 (`[bp+6]`) with its players view closed.
- **Polled screens** read a key only after "key pressed?" says one waits: the captain prompt (polls `0791:CC54`,
  `0791:CEDE`, reads at CEE8), play (`0791:93C2`, reads at 93CE), the timed questions (`0791:0BE1`) and notices
  (`0791:C5C8`). Each wait lists those passed since the last (`KeyWait.passed`: kind, polls, the text at its first
  poll, the queued keys read there). `core.queue(kind, key)` answers the next poll of that kind "a key waits"; the
  original's next read takes the key, as `press` gives it. Polls of other kinds answer "no key" meanwhile. A key
  the kind does not list is refused. The queue and a key a poll announced are saved and loaded with the core.
- **An unknown site stops**: a read or a poll whose site has no entry, or whose entry knows no kind for what the
  frames and memory show, raises `UnknownScreen(site, text)` and the core runs no further.

[designed] goal2 kinds, for screens no kinds.tsv rule names; their keys are the hints they print. The text quoted
is what the tests check the screen holds (the tours of `test_core_screens_t103.py`, E006-r0001 and E010-r0001):

| kind | site | record | quoted text |
| --- | --- | --- | --- |
| `team-info` | `1771:28F5` (1771:26B9 mode 1, from main_menu_loop 000E:7682) | E006-r0001's first wait | "Use ←→↑↓ to select" "Hit ◄┘ for fixtures" "spacebar-players T-tactics" |
| `fixture-list` | `000E:016C` (000E:0000), the own match highlighted | E006-r0001, Esc Down Enter | "and results" "Use ↑↓ to scroll" "Esc-exit" |
| `match-board` | `0791:041A` (0791:0106) without the man of the match: half time, match stats, a quick result | E010-r0001's first wait | "Scorers" "hit any key" "Esc,◄┘-bench" |
| `team-tactics-view` | `214B:157C` from `1771:1A24`, another country | E006-r0001, the match menu's right team tactics | "team─tactics" "hit any key" |
| `history` | `1771:25E4` (1771:1D5C, a country's history) | E006-r0001, the manager menu's history (T105) | "STATISTICS" "SUCCESSES" "TOP─SCORERS" "Esc-exit" |
| `history-browse` | `1771:28F5` (1771:26B9 mode 3, from main_menu_loop's item 4) | E006-r0001, Esc from the history (T105) | "Hit ◄┘ for team history" "Esc to exit" |
| `tournament` | `214B:157C` from `1771:9022` | E010-r0001, the match menu's tournament | "Use ↓↑ to select group" "Use ←→ to select display" "Esc-exit" |
| `action-replay-prompt` | poll `0791:CC54` / `0791:0BE1` (0B7C from 0C65 at 0C87) | E006-r0001, a watched second half | "Do you want an action replay? (Y/N)" |
| `substitution-notice` | poll `0791:CC54` / `0791:C5C8` (0791:C50C) | E006-r0001, a watched second half | "SUBSTITUTION" "press any key" |

**Not reached yet**, so not in the table:
- `country-select` and the new-game screens (`title-load-prompt`, `title-player-count`,
  `country-select-name-entry`): no kept savestate stops there at an INT 16h read (E006-r0001 starts at the team-info
  browser, E011-r0001 and the title checkpoints are refused by `Core.start`), and leaving the menu calls INT 10h.
  G10 needs a new-game savestate from goal2-archaeology.
- The other kinds.tsv screens no tour met (`round-playing`, `round-results`, `match-watch-prompt`,
  `match-commentary`, the other substitution screens, `save-game-name-entry`, `file-not-found-prompt`) and the
  other cases of the shared sites (the taker prompts, the pause and extra-time menus, SELECT TEAM outside a match)
  stop with `UnknownScreen` until a screen task maps them (G10-G14).
- Interrupts other than the key reads stay unserved (T100).

## Where the run starts (R1)

[confirmed: E021 `notes.md` section 1 (e2a46a4)] The savestate's `CPU` component holds the registers (layout
calibrated in E021), so the image does carry the CPU. At E006-r0001 it is inside the BIOS's INT 16h
(F000:CFAA), which DOSBox-X serves with code Unicorn cannot run. [confirmed: `seg_214B_02.asm` 08DD-08FF] 08DD
reached it through `Intr` (`235C:000B`, called at 08FF, returning to `214B:0904`) after `push bp; mov bp, sp;
sub sp, 0x14` and three argument pushes (AL 0x16, SS, DI = BP-0x14). [derived] The core finds that far return
on the savestate's own stack, checks the three argument words, and restarts the guest at 08DD's entry: SP = 08DD's
BP + 2, BP = the BP it saved, CS:IP = `214B:08DD`, DS = ES = the program's data segment. Every return address is
the guest's own; E006-r0001's chain is 08DD <- `1771:28F0` (team info) <- `000E:767D` (`main_menu_loop`) <-
`0000:00C6`. A savestate stopped anywhere else is refused (`CoreError`); no main-menu routine is entered with a
made-up stack, and no byte of the image is patched.

[confirmed: F001; `runtime/driver/savestate.py` (ea4dba8)] The text page lives in the savestate's `Vga`
component (stream offset 0x86024, 8 bytes per cell), not in `Memory`; [derived] the core copies its 4000 bytes to
B800:0000, where the guest's own far pointer `DS:A96A` writes the screen. That page is E006-r0001's recorded main
screen to the byte (its record's digest `18190236…`).

## Stopping rather than guessing

- [designed] **The instruction budget**: a run that executes more than `budget` instructions (default
  10,000,000,000; a watched first half needs between 3e9 and 4e9, measured T100) without a key read raises
  `BudgetExceeded`, naming the PC (listing address and CS:IP) and the text page. It never presses a key for the
  original.
- [designed] **Interrupts**: the core serves none. The first INT the guest calls stops the run with
  `InterruptError` (its number, AX, the PC and the text page). The menus, the match menu and a whole watched
  first half called none; quitting (F10, Y, N) calls INT 10h and then DOS, and stops there.
- After either error the core runs no further (`core.stopped`); start again or load a save.
- The kit's build guard runs at `start`: an image of another GOAL.EXE is refused (`ValueError`).

## Saving

[derived: F029, a savestate's memory is the master] `core.save()` is `G2C1`, a JSON header (the registers, the
load segment, the Memory component's header, the seeds `DS:7B62` and `DS:7B64` (F004), the key log since the
template, the budget, the template's SHA-256, the wait's polls) and the zlib-compressed memory (1 MiB, the HMA
and the rest of the Memory component). `Core.load` rebuilds the machine and the wait; the same keys then give the
same waits and the same memory, byte for byte. `core.memory_component()` is the memory in the form the kit's
`Image` reads.

## Requirements and cost

`import goal2.core` needs the standard library only; `Core.start` needs `unicorn` (`pip install -e
'.[watched]'`) and says so when it is missing. Menu keys take milliseconds; pressing **play** runs the captain
prompt and a whole first half at the image's own delay calibration, about 110 s under the instruction count.
`python3 -m unittest goal2.tests.test_core_runner_t100 -v` checks all of this on E006-r0001, and
`python3 -m unittest goal2.tests.test_core_screens_t103 -v` the screen table; both need `.cache/` and the
goal2-archaeology checkout, and skip without them. [designed: #316] The tests that run the original past its first
screen are slow tests: they run with `GOAL2_SLOW=1` (the screen tours play a whole watched match, about eight to
eleven minutes; the captain prompt's two cases about three), and the pre-merge gate runs them whenever `goal2/core/`
or either module changes (`SLOW_PATHS`, docs/process.md). The default run keeps one real case of each module.
