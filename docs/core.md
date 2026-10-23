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
  the match; `1771:1A24` the tactics screen; `1771:9022` the tournament view, the interactive `tournament` or,
  with 1771:958D's mode byte `[bp+10]` 0 (from 0791:E929 after a fixture), the one pass `tournament-table`;
  `0791:E86E` the watch prompt of 0791:E80D, T108); `wait_or_key 0791:CC54` by its near caller (CC7B the captain
  prompt with role 1, 0B7C the timed questions, C50C the substitution notice); SELECT TEAM `0791:E61F` by its
  caller (the manager menu's 000E:7625 or 771F, or E949's `0791:E99C` from a match's menu, T108); the message box
  read `214B:098A` by the routine that called 214B:1765 (0791:DBFA's DC3D and DC68; 0791:E022's `E0CB`, "Illegal
  substitution", `squad-substitution-illegal`; 0791:EA09's `EB82`, "... has an ineligible player in the first
  team", and `EBD7`, "... has too many goalkeepers", `eleven-refused`).
- **Where frames are not enough, a cited field decides** [confirmed: the listings named]: the tactics screen edits
  only a managed country (`1771:0B77`, +0x2E > 0x80) with `DS:0C20` clear, else it is the view
  (`named/seg_1771_02.c` 1771:1981, the country its argument `[bp+6]`); the fixture list's hint comes from the
  highlighted fixture (`[bp-6] + [bp-8] - 1`, `fixtures` `DS:A92B`): neither country managed and the first byte
  0xFF "watch match", 0xFE "auto result", else none (`named/seg_000E_01.c` 000E:0000); the board `0791:041A` is the
  summary when it draws the man of the match (`DS:9A3F` clear and `DS:7C3A` set, `named/seg_0791_01.c` 0106);
  SELECT TEAM `0791:E61F` from E949 is SELECT YOUR TEAM before the kick-off (`DS:0C1F` clear: `select-squad`, its
  swaps then `resort_pitch_and_bench`), and in a match offers "take off this player" with substitutions open and the
  cursor `DS:0C1B` below 12, "put on this player" from 12 (`0791:E44F`, `E2A0`), and "no more substitutes" with
  `DS:9B3A` + side 0 (DS:2538, `substitutions-used`); the round's results (`000E:6C4F`) show the fixtures from
  max(last - 15, route_fixture's first, `[its bp - 6]`) to the one before `+0x26` (T108); the team-info browser is `1771:26B9`'s mode 1 (`[bp+6]`) with its players view closed.
- **Polled screens** read a key only after "key pressed?" says one waits: the captain prompt (polls `0791:CC54`,
  `0791:CEDE`, reads at CEE8), play (`0791:93C2`, reads at 93CE), the timed questions (`0791:0BE1`) and notices
  (`0791:C5C8`), and the round's other fixtures (`round-playing`, polls `000E:6B89` and, in its delay loop,
  `000E:6BF7`, T108). Each wait lists those passed since the last (`KeyWait.passed`: kind, polls, the text at its first
  poll, the queued keys read there). `core.queue(kind, key)` answers the next poll of that kind "a key waits"; the
  original's next read takes the key, as `press` gives it. Polls of other kinds answer "no key" meanwhile. A key
  the kind does not list is refused. The queue and a key a poll announced are saved and loaded with the core.
  [designed: T108] `core.stop_at(kind, ...)` makes each poll of those polled kinds a wait (`KeyWait.poll`), so that
  the driver reads the screen before each key (the captain prompt's highlight, CC7B's `[bp-5]`): `press` then
  answers that poll "a key waits" and the original's next read takes the key. A poll while a key is in flight is not
  a wait; `stop_at()` stops at none; `core.unqueue(kind)` drops the keys queued for a kind no poll took.
- **An unknown site stops**: a read or a poll whose site has no entry, or whose entry knows no kind for what the
  frames and memory show, raises `UnknownScreen(site, text)` and the core runs no further.

[designed] goal2 kinds, for screens no kinds.tsv rule names; their keys are the hints they print. The text quoted
is what the tests check the screen holds (the tours of `test_core_screens_t103.py`, E006-r0001 and E010-r0001):

| kind | site | record | quoted text |
| --- | --- | --- | --- |
| `championship-bracket` | `1771:9567` (9509 from 958D, continental mode 0) | T111's real E006 continuation, after fixture 1345 | "TOP SCORERS" "winner" "hit any key" |
| `championship-browse` | `1771:9567` (the same, mode 1) | T111's private continental checkpoint, manager menu's tournament | "winner" "Use ←→ to select display" "Esc-exit" |
| `substitution-request` | `0791:E61F` (E44F, DS:9B41 clear) | E006-r0001, watched play, Enter, Players (T109) | "tactics and" "substitutions" "request substitution" "Esc-exit" |
| `substitution-requested` | `0791:E61F` (E44F, DS:9B41 clear, DS:9B40 set) | E006-r0001, Enter on substitution-request (T109) | "cancel substitution request" "Esc-exit" |
| `substitution-refused` | `214B:098A` (E022's box, return E167) | E006-r0001, T109's watched half-time bench, attempting to put a substituted player back on | "cannot play" "PRESS ANY KEY" |
| `team-info` | `1771:28F5` (1771:26B9 mode 1, from main_menu_loop 000E:7682) | E006-r0001's first wait | "Use ←→↑↓ to select" "Hit ◄┘ for fixtures" "spacebar-players T-tactics" |
| `fixture-list` | `000E:016C` (000E:0000), the own match highlighted | E006-r0001, Esc Down Enter | "and results" "Use ↑↓ to scroll" "Esc-exit" |
| `match-board` | `0791:041A` (0791:0106) without the man of the match: half time, match stats, a quick result | E010-r0001's first wait | "Scorers" "hit any key" "Esc,◄┘-bench" |
| `team-tactics-view` | `214B:157C` from `1771:1A24`, another country | E006-r0001, the match menu's right team tactics | "team─tactics" "hit any key" |
| `history` | `1771:25E4` (1771:1D5C, a country's history) | E006-r0001, the manager menu's history (T105) | "STATISTICS" "SUCCESSES" "TOP─SCORERS" "Esc-exit" |
| `history-browse` | `1771:28F5` (1771:26B9 mode 3, from main_menu_loop's item 4) | E006-r0001, Esc from the history (T105) | "Hit ◄┘ for team history" "Esc to exit" |
| `tournament` | `214B:157C` from `1771:9022` | E010-r0001, the match menu's tournament | "Use ↓↑ to select group" "Use ←→ to select display" "Esc-exit" |
| `action-replay-prompt` | poll `0791:CC54` / `0791:0BE1` (0B7C from 0C65 at 0C87) | E006-r0001, a watched second half | "Do you want an action replay? (Y/N)" |
| `substitution-notice` | poll `0791:CC54` / `0791:C5C8` (0791:C50C) | E006-r0001, a watched second half | "SUBSTITUTION" "press any key" |
| `title-tune` | polls `1771:0723`, `1771:0782` (1771:06F3, the title's tune) | E039's traces (T106) | "THE international soccer management game" "Do you want to load a saved game? (Y/N)" |
| `select-squad` | `0791:E61F` (0791:E44F from main_menu_loop 000E:771A or 7620, or from E949 before a match's kick-off, DS:0C1F clear, `[bp-5]` 1) | E006-r0001, the manager menu's select squad (T107); the match menu's players before the kick-off (T108) | "SELECT YOUR TEAM" "Hit Ins for assistant's recommended 20" |
| `select-squad-pool` | `0791:E61F` (the same, `[bp-5]` 2: the pool list, 0791:E2E6) | E006-r0001, Left on select squad (T107) | "SELECT YOUR TEAM" "pool of players" |
| `own-tactics` | `214B:157C` from `1771:4C0A` (1771:4B61 from E44F's T, return 0791:E75D, DS:0C1F clear) | E006-r0001, T on select squad (T107) | "↓↑←→-select" "◄┘-alter tactic" |
| `player-name-entry` | polled `214B:0DB9`, read `214B:112B` (the editor 214B:1086 from 1771:4859, return 1771:48A0, from E44F's F2, return 0791:E700) | E006-r0001, F2 on select squad (T107) | "Type in characters (maximum 12)" "◄┘-accept Esc-abort" |
| `squad-change-refused` | `214B:098A` (214B:0983 under the box 214B:04F8, return 054E, under 214B:1765, return 1793, from 0791:DBFA at DC3D or DC68) | not visited: no kept state is in a finals or tour window (T107; F031) | "cannot alter squad" "PRESS ANY KEY" |
| `fixture-result` | `000E:6A89` (simulate_fixture 000E:6970, a fixture marked to watch and declined: its first byte 0xFE) | E006-r0001's round 3, N at the watch prompt (T108) | "location:" "hit any key" |
| `tournament-table` | `214B:157C` from `1771:9022` (8E9A under 1771:958D with its mode byte `[bp+10]` 0, from 0791:E929 after a fixture) | E006-r0001's round 2, after the own qualifier (T108) | "P W D L" "hit any key" |
| `substitutions-used` | `0791:E61F` (0791:E44F from E949 in a match, DS:9B3A + side 0: DS:2538) | E006-r0001's round 1, the bench at half time after five substitutions (T108) | "no more substitutes" "Esc-exit" |
| `eleven-refused` | `214B:098A` (the box 214B:04F8 under 214B:1765, from 0791:EA09 at EB7D or EBD2: return EB82 or EBD7) | E006-r0001's round 10, play on the match menu (T108); round 1 at half time after a goalkeeper came on | "location:" "PRESS ANY KEY" |

[T108] SELECT YOUR TEAM's hint line reads "◄┘-move player" until a player is marked and "◄┘-put here" after, so its
two kinds quote neither (E006-r0001's round 9, the pre-match swap, showed the second).

[designed: owner, 2026-10-22, T107's amendment] **Keys the screen prints.** A kinds.tsv kind accepts its catalogue
`screen` and `owner` rows and also a key its own screen's hint prints at a kept state (`screens.PRINTED`), quoted here
with the state and the text row (0-based) it is printed on; a catalogue `burst` row (a key a recorded run read on that
screen) backs each. `test_core_screens_t103.py` checks the union and the quotes; `test_core_team_t107.py` checks the
quote on the screen.

| kind | keys | state | row | quoted text |
| --- | --- | --- | --- | --- |
| `team-tactics` | ↑↓ | E006-r0001, team info's T on the managed country (1771:1981 moves DS:0D8E; burst "team-tactics Up", E015-r0007 state 119) | row 2 | "Use ↑↓ to move" |

[designed: owner, 2026-10-23, T108's amendment] **Keys the original's code reads.** A kinds.tsv kind also accepts a
key that its screen's routine reads and acts on, cited in the named listing, when a recorded run read it on that
screen (a catalogue `burst` row) (`screens.CODE_READ`). `test_core_screens_t103.py` checks the union, the citation and
the burst row:

| kind | keys | routine | recorded run |
| --- | --- | --- | --- |
| `squad-substitution-take-off` | ↑↓ | named/seg_0791_11.c select_team_screen 0791:E44F: with the squad list up any other key goes to `u214b_menu_move_word_wrap(0x14, 0xC1B)`, the cursor; in a match E44F draws no hint for it (template 0x1B42 only with in_match_menu_used clear) | burst rows of catalogue.tsv: Down at E015-r0007 state 76, Up at E015-r0007 state 79 |
| `squad-substitution-put-on` | ↑↓ | named/seg_0791_11.c select_team_screen 0791:E44F, the same branch | burst rows of catalogue.tsv: Down at E015-r0007 state 82, Up at E015-r0007 state 131 |

The new game's kinds.tsv kinds (T106) [confirmed: F032, E038-r0001's savestates and trace; catalogue.tsv's keys]:
`title-load-prompt` (read `1771:085F`, 1771:080C from the main program), `title-player-count` (read `1771:0081`,
manager_count_menu 1771:0021; its view is the count DS:0C4E), `country-select` (read `1771:28F5`, 1771:26B9 mode 2
from set_managed_countries 1771:2D15; its view adds the column DS:0DB4, the index and the manager choosing),
`country-select-name-entry` (polled: the cursor wait 214B:0D90 polls at `214B:0DB9` for the line editor 214B:1086,
which reads at `214B:112B`; called by 1771:09A0 from 1771:2D15) and the two `bulletin`s at `000E:0629` (000E:05F6
near-called by welcome_new_manager 000E:68A4 and announce_stage_to_manager 000E:60CB). A key pressed during the
title's tune ends it (06F3 returns at a key) and the title's read takes it; `Core.boot`'s `title_key` queues one so.

**Not reached yet**, so not in the table:
- The other kinds.tsv screens no tour met (`match-commentary`, `squad-substitution-tactic`,
  `save-game-name-entry`, `file-not-found-prompt`) and the other cases of the shared sites stop with `UnknownScreen`
  until a screen task maps them: the taker prompts and extra-time menus, the other players' screen of E949 (another country's, 1771:50F1), E022's other
  messages ("There is no player here" E062, "Nice try" E19F) and EA09's (EC22, EC60,
  ECEB), the space bar's pause box of the round (214B:04F8 from 000E:6BD0), a watched match of the round (Y at
  the watch prompt) and World Cup finals/bracket cases. Continental finals and the bracket at 1771:9567 are
  mapped and visited by T111 (below). The summary with the man of the match and its save prompt are mapped (T103)
  and reached by the watched route (T109); the quick result shows neither (F030).
- **Mapped, not visited**: `squad-change-refused`, 0791:DBFA's refusal of a pool exchange ("cannot alter squad" +
  " during finals" from DC38, return DC3D, or " whilst on tour" from DC63, return DC68, in the box 214B:04F8, F031). No
  kept state has the managed country in a restricted finals or tour window (T111's continental checkpoints have
  an unqualified manager; the managed finals flag `[A923]+0x13+m` is clear), and
  no test writes guest memory to reach one; the driver's `exchange` answers it with a key and returns the message.
- Interrupts other than the new game's (below) stay unserved.

[designed: owner, 2026-10-23, T108's amendment] **A text rule narrower than its screen.** When a site is clearly a
kinds.tsv kind (its routine and frames say so) but the kind's text rule misses a case, the kind stays and the gap is
recorded here; the oracle's exception covers only this case. `round-results`: kinds.tsv's rule asks for
`friendly`, which the round's results print only when a friendly is among them; a round of qualifiers alone shows
`hit any key` over rows like `----------Nepal  1v2  Singapore------   qualifying` and no `friendly`. The site
(`000E:6C4F`, 000E:6C21 after simulate_fixture) is the same. The rule fix proposed to goal2-archaeology:
`+hit any key ;; -THE SOCCER BULLETIN ;; -MAN OF THE MATCH ;; -location: ;; -P W D L ;; -Scorers`, the round's
results with any fixture kinds, which the round's other "hit any key" screens (the boards, the fixture result, the
table) each fail.

## The driver and the views (T105, #308's G11)

[designed: owner, 2026-10-23; T109] At the original's match-summary save question, the desktop offers a readable
summary export. Saving writes the desktop's UTF-8 text file; skipping writes nothing. Both then send N to the
original, bypassing its DOS summary writer without changing guest code. This is the owner's selected presentation
of that prompt.

[confirmed: code/seg_0791_15.asm 9571-9708, 944D-945B; named/seg_0791_12.c E44F] Live play polls after each of
22 player updates. The watched desktop reads the complete pose at the last poll, before advancing, and Enter
opens the pause menu. Its Players screen, with DS:9B41 clear, accepts Enter to request a substitution (DS:9B40),
or cancel the request; it does not select a pair. At the next substitution opportunity the original offers the
bench that makes the pair. Goal2's `substitution-request` kind names this screen, and accepts only its printed
Enter and Esc. `Core.advance()` answers one poll with no key, keeping the next poll as a wait; `release()` retains
its T108 meaning of passing the screen. These are manager inputs, with no guest-memory patch.

[designed: owner, 2026-10-22, #308, #321; decision 7 of docs/redesign-253/vision-reconciliation.md] The desktop
and, later, the bot move the original only by its own keys, through one path, `goal2/core/driver.py`:

```python
from goal2.core.driver import Driver
from goal2.core import views
driver = Driver(Core.start(savestate).core)
driver.to_menu()                      # Esc from the team-info browser: the manager menu
views.desk(driver.wait.state)         # the manager's desk, read from memory
wait = driver.goto("history")         # Down x3, Enter: the routes are team-info, fixture-list, tournament, history
driver.back()                         # Esc, Esc (the history's country browser, then the menu)
```

- `press(key, expect=...)` sends a key only when the wait's kind lists it (`KINDS`), else `RefusedKey` and nothing
  reaches the original; a next screen outside `expect` raises `UnexpectedScreen` (kind, site, text); an unmapped
  site stops the core itself (`UnknownScreen`). It reads only the wait's kind and view, so the same calls give the
  same keys (`driver.log`) and the same memory. [confirmed: `named/seg_000E_05.c` main_menu_loop] The menu's item is
  DS:00B0, moved by Up and Down; Enter opens team info (1), the fixture list (2), the tournament (3) or the history
  (4, `country_list_screen(3)`, which first shows the managed country's history `1771:1D5C`).
- `goal2/core/views.py` reads, through the kit's `Image`, never the text page: `desk` (the manager menu: name,
  rating, team and rankings, next opponent, its rankings and the fixture's kind, the managers, the year and stage
  word, the squad strip), `fixture_list` (000E:0000's rows from the fixture index on: kind, sides, mark, played
  flag and score), `tournament` (the qualifying display's group tables and group fixtures of the managed country's
  continent; the finals, bracket and play-off displays are not read yet, no kept state reaches them) and `history`
  (1771:1D5C: successes, results by season, statistics, records, top scorers and caps). Each field cites the
  routine and the address it reads in the function's docstring.
- [confirmed: `named/seg_1771_02.c` 1D5C, 1B2E] The top scorers and top caps are computed only on display: 1D5C
  fills the tables at [DS:A93B] and [DS:A937] from the squad (and a manager's pool) and puts the kept ones back
  before its key read, so no copy is in memory at the wait, and visiting the screen would not give them without
  parsing its text. `views._top` runs 1B2E's insertion over the same player records instead; the text oracle checks
  it against the screen.
- `python3 -m unittest goal2.tests.test_core_desktop_t105 -v` checks every view against the original's own screen
  (E006-r0001 and E010-r0001's half time played on to the next manager menu), the driver, and the desktop over
  the core (docs/desktop-management.md, "The core route").

## The Team and Pool route (T107, #308's G12)

[designed: owner, 2026-10-22, #308, #328; decisions 5 and 7] The manager menu's select squad (item 5) opens SELECT
YOUR TEAM (0791:E44F), team info's T on the managed country the team tactics (1771:1981). The driver's team actions
each start at the manager menu, press the original's keys closed-loop (the vendored kit's method, never its match
plans) and return to it; each reads the screen's state before each key:

```python
driver.swap(a, b)                     # Enter on a, Enter on b: the squad words swap, then E44F sorts the squad
driver.exchange(squad_player, pool_player)   # Enter, Left, Enter: 0791:DBFA may refuse (F031); returns the message
driver.set_position(player, code)     # C (his club position, 1771:4952) or R (+1, wrapping 0..13, 1771:4925)
driver.set_own_tactic(player, e, v)   # T, the row e, Enter cycles: the team's, his own clear, his own set (4B61)
driver.set_marking(player, opponent)  # refused: 4B61 offers row 5 only with a match set up (4 rows here)
driver.rename(player, "mo salah")     # F2: the editor's keys queued; 1771:4859 keeps "M O Salah"
driver.set_tactic(element, on)        # team info, the managed country, T, ↑↓ to DS:6BBF's row, Enter, Esc, Esc
```

- [confirmed: named/seg_0791_12.c E44F, DEA6; code/seg_0791_22.asm E641-E657] On SELECT YOUR TEAM Enter marks a player
  ([bp-1], his list [bp-7], his slot or pool index [bp-9]) and Enter on another swaps their words; Left and Right
  toggle the squad list and the pool list ([bp-5]); Esc unmarks a marked player, turns into Left on the pool list and
  leaves on the squad list; on leaving, E44F sorts the pool (sort_pool_by_position). Entering sorts the squad by
  position: visiting the screen changes memory as the original does.
- The views (`goal2/core/views.py`): `team` (the squad in its order, the eleven then the bench, with the codes),
  `player_card` (every field of 1771:42BC: the words, the 26-cell skill bars of 1771:3947, the characteristics'
  words and 14-cell bars, the four tactics with " P", the mark, the status word, the performance stars of 1771:3827),
  `team_tactics` (the byte +0x2D, its rows in DS:6BBF's order with their words) and `pool` (F011: the eighty words
  from DS:6D18[m], the list's top and row). `python3 -m unittest goal2.tests.test_core_team_t107 -v` checks them
  against the screens (E006-r0001 and a new game), each action against the same keys pressed on the core directly,
  the refusal, the keys, save and resume, and the desktop's Team and Pool pages (docs/desktop-management.md).
- Each action takes 120-570 ms under Unicorn, so the desktop runs it as a background job (`CoreJobs`).

## The round (T108, #308's G14a)

[designed: owner, 2026-10-22, #308, #331; decision 7] Play next game plays the original's round by its own keys, from
the manager menu to the next one. The driver stops only where the original asks the manager and answers the rest as a
manager who only plays: Enter on each "hit any key" screen, N at the watch prompt (a watched match under the core is
G14b), and R at the first poll of play, the original's quick result, which still stops at half time.

```python
driver.round_start()                   # play next game: the round's other fixtures, their results, to the match menu
driver.kick_off(captain=player)        # play, the captain prompt (None: C, the original's own), the first half
driver.substitute(off, on)             # at half time: players, Enter on each, Esc: the original makes or refuses it
driver.play_on()                       # the second half, the full-time board, exit, the table, the bulletins
driver.prematch_swap(a, b)             # an eleven the original refused before the kick-off, fixed on SELECT YOUR TEAM
driver.play_round(captain=None, substitutions=(), fix_eleven=None)   # all of it
driver.pages                           # the screens passed: (kind, view), read from memory at each
```

- [confirmed: named/seg_000E_05.c play_round 000E:70B9, route_fixture 6CA7, simulate_fixture 6970, 6C21] item 6
  plays the fixtures from `+0x26` through route_fixture until one of a managed country is played: each other fixture
  is simulated (`round-playing`, its polls answered "no key") and, before the own fixture, the round's results wait
  for a key (`round-results`). A fixture marked to watch, or of a kind the original offers (a group of the managed
  continent), asks `match-watch-prompt`; N writes 0xFE and simulates it with its result (`fixture-result`) and the
  table (`tournament-table`, after a non-friendly). The own match is run_match 0791:F1F6: the match menu, the
  captain prompt, play, the half-time board and menu, the full-time board and menu, the table after a non-friendly,
  then the bulletin (000E:4E0E).
- [confirmed: named/seg_0791_10.c CC7B] The captain prompt highlights the stored captain's slot (local_7) and
  moves it by Up and Down (`u214b_menu_move_word_wrap(0xB)`); Enter takes the highlighted player, C the original's
  best leader. The driver reads the highlight at each poll (`stop_at`) and presses Up or Down to the chosen slot.
- [confirmed: named/seg_0791_11.c E44F, E022; seg_0791_12.c ED8A, EA09] At half time the match menu's **players**
  (item 2 or 7 of the managed side, ED8A: 1..5 are DS:9B36's) opens SELECT TEAM in the match: Enter on one of the
  eleven marks him, Enter on a bench player swaps them (E022) and counts DS:9B3A + side down; a pair of the same
  block is refused ("Illegal substitution"); with none left E44F shows "no more substitutes" and offers no take-off.
  `play` asks EA09 first: it refuses an ineligible eleven ("<country> has an ineligible player in the first team")
  or too many goalkeepers, in a box any key closes; the menu waits again. Before the kick-off the same menu's
  players is SELECT YOUR TEAM, where Enter, Enter swaps two players (0791:DEA6).
- The views (`goal2/core/views.py`): `match_sides` (DS:9B34, DS:9B36, the managed side, its eleven and bench, the
  captain DS:9978 + 10 t), `captain_choice`, `bench` (the counter, the original's own line DS:2538 when none is left,
  read from its template by 214B:0147's format), `board` (0791:0106: the score DS:9B3C, the scorers 0x7BD1 + 0x21 t +
  3 k, the man of the match and the statistics when not a quick result), `round_results` (1771:7812's rows) and
  `fixture_result`. `python3 -m unittest goal2.tests.test_core_round_t108 -v` checks them against the original's
  printed screens, every wait's kind against its text rule, a substitution against the same keys pressed on the core
  directly, the counter, the original's refusals, the captain, rounds through a refused eleven, save and resume at
  half time, and the desktop's round (docs/desktop-management.md).
- A round takes 35 to 60 s under Unicorn (each half of the quick result about 17 s, the other fixtures up to 14 s), so
  the desktop runs each step as a background job (`CoreJobs`).

## Bulletin presentation (T110, #308's G13a)

[designed: T110; confirmed: F032/E038, named/seg_000E_01.c 038E, 05F6, 062F, 070B, 075F] Launch and the round
share `goal2/desktop/bulletin_page.py`: the left, middle and right papers each retain their masthead and every
line returned by `views.bulletin`, in order, as literal plain text. The round no longer flattens the three stories
into an eighteen-row board. Next keeps the existing page sequence; the component has no driver or game state.
It fits the same fixed page and four-size bounds as the other core pages. This presentation slice changes no
screen kind or year-transition logic; the not-reached catalogue cases above remain the later G13 slices.

## Continental continuation (T111, #308's G13b)

[confirmed: goal2-archaeology at 53d7ef5, named/seg_1771_06.c 9028, 8A87, 883F, 8CCF;
seg_1771_07.c 91CE/9509/958D; real E006 continuation] The finals menu read is `214B:157C` from `1771:91BE`,
with the passed 958D frame: country -8, competition flag -9, group -4, mode +10. Continental mode 1 is `tournament`,
mode 0 `tournament-table`. The bracket read is `1771:9567`, near return 964B, with the same passed frame;
mode 1 is `championship-browse`, mode 0 `championship-bracket`. Its printed browse keys are Space, Left/Right and
Esc; the post-fixture page says "hit any key". The driver keeps the post-fixture page and presses Enter.

[derived: the cited writers] `views.tournament` reads continental finals table 1 (two groups, six fixtures each)
and the copied top-scorer records at A93F. `views.bracket` reads fixture indices 7..10 at A933 + continent·1C0 +
55E + 2·index, the draw coordinates at 1137/113D/1142/1148, and stored winner selector +3 (5C94/5CCB). Initially
only the semi-finals exist; the original later creates the third-place fixture and final. Goal2 interprets these
stored fields and never decides a winner. The desktop draws a structured bracket with these fields, top scorers
and places, through `desktop/bracket_page.py`, without reading the guest text page.

[confirmed: named/seg_000E_04/05.c; code/seg_000E_07/08.asm] Bulletin returns 57DF (retirement), 5CCE (5AC5's news)
and 6863 (winner's news) use the same 05F6 page/read as the already mapped bulletins. T111's private checkpoints,
hashes and original-key provenance are in [the manifest](evidence/T111/artifacts.json); the original bytes live on
the owner's Drive. Its tests follow 2→3 and 4→5 through the original, checking F016 for the managed twenty plus
eighty pool players and the bracket against the original's displayed text. World Cup finals/bracket and remaining
decision prompts are following slices; archaeology #390 requests their existing evidence.

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
- [designed] **Interrupts**: the core serves only the new game's (T106, "The new game" below). Any other INT the
  guest calls, or any other request through `Intr`/`MsDos`, stops the run with
  `InterruptError` (its number, AX, the PC and the text page). The menus, the match menu and a whole watched
  first half called none; quitting (F10, Y, N) calls INT 10h and then DOS, and stops there.
- After either error the core runs no further (`core.stopped`); start again or load a save.
- The kit's build guard runs at `start`: an image of another GOAL.EXE is refused (`ValueError`).

## The new game (T106, #308's G10)

[designed: owner, 2026-10-22, #308; T106] A new game runs the original's own code from before its title, so the
start year is the original's and the seed its own:

```python
from goal2.core import Core
from goal2.core.driver import Driver
wait = Core.boot(open(".cache/e039-r0005-date-call.sav", "rb").read(), (1990, 10, 4),
                 dos_time=(10, 0, 20, 95), goal_dat=".cache/GOAL.DAT")   # the title's read, 1771:085F
driver = Driver(wait.core)
driver.new_game(7, "bob")      # N, Enter (one manager), the country by its arrows, the name, Enter on each bulletin
```

- **Booting at the DOS date call** [confirmed: F033, E039, NG-9, NG-10]: `Core.boot(state, date)` is the core's
  second entry kind, resume at a DOS call. It checks that the state's CPU is at the `int 21h` of GetDate
  `235C:0071` with AH 2Ah, answers it as DOS does (CX year, DH month, DL day, AL weekday, 0 Sunday), continues at
  `235C:0073` and runs to the first key read, the title's. The program keeps the year at DS:A9FD; at a new game
  1771:9B85 sets the start year (+0x3A) to year + 1 rounded up to even and the stage (+0x3C) to 2 when it is
  divisible by 4, else 5 (DOS 1990 → 1992 stage 2, 1992 → 1994 stage 5). [designed: owner, 2026-10-22] The player
  chooses the start year by the date the core answers, as a player setting the PC clock would; the date is an
  input to the interrupt, never written into memory, and kept in the core save. DOS answers 1980–2099 only.
  Between the date call and the title's read the original makes no other interrupt: 333 polls of the title's tune
  (`title-tune`, answered "no key", about a minute under Unicorn) and speaker port I/O, which Unicorn drops (an OUT) or
  reads as 0 (an IN), as E039's trace answered them.
- **The interrupts served** [confirmed: F032, E038-r0001, NG-7, NG-8]: from the title's read to the first manager
  menu, GOAL.DAT's open, ten reads and close (INT 21h 3Dh/3Fh/3Eh) through Turbo Pascal's `MsDos` 235C:0000 and
  `Intr` 235C:000B, and INT 21h AH=2Ch at 23E4:11D9. `Intr` enters the vector by a far return with no `int`
  instruction, so a Unicorn interrupt hook never sees it: the core hooks `Intr` at its entry (MsDos falls through
  into it), reads the register record (AX BX CX DX BP SI DI DS ES Flags) and the vector from the stack, serves the
  request, writes the record back and returns `retf 6`. GOAL.DAT is read at run time from the path the player gives
  (`goal_dat`, the desktop's `--data`), checked against the released file's SHA-256, never from the repository;
  only the name GOAL.DAT is opened. An `int` instruction is served only for INT 21h AH=2Ch.
- **The DOS time is an input** [designed: T106]: AH=2Ch answers `dos_time=(hours, minutes, seconds, hundredths)`
  given to `Core.start` or `Core.boot`; the default is 10:00:00.00, the hour E038 and E039 set. The original stores
  CX at DS:7B62 (hour·256 + minute, the seed) and DX at DS:7B64 (F004), after the key that leaves the first bulletin
  (NG-8). The time is kept in the core save, so a game replays exactly.
- [confirmed: seg_235C_01.asm 0045; #327] The record's Flags are the CPU's flags with the carry clear, as Intr's
  return path stores them (pushf); the date call sets CX, DX and AL only (`runner.date_registers`).
- **Refusals**: any other request through `Intr` or `MsDos`, any other `int`, a file other than GOAL.DAT, or
  GOAL.DAT with no path given stops the core with `InterruptError`, naming the vector (`number`), the function
  (`ah`), the route (`via`: int, Intr or MsDos), the site and the text page. Loading a saved game at the title
  (DOS's current drive, AH=19h through MsDos) and quitting (INT 10h AH=02h) stop so.
- **Byte for byte**: from `e038-r0001-title-keywait.sav` with E038-r0001's keys and DOS time (10:00:20.95), the core
  reaches `e038-r0001-manager-menu.sav`'s screen, DS:7B62/7B64 and player and country arrays exactly, and the rest
  of conventional memory differs only where E038's own trace differed from DOSBox-X (the BIOS keyboard buffer and
  tick, DOS's 0815E, the stack below SS:SP). Each wait's kind, site and screen are E038's at that step.
- [designed: T106; derived: measured by the test] **A key in the tune**: `Core.boot(..., title_key="n")` answers the
  tune's first poll with N, so the title's read takes it and boot returns at the player count, under a second. The
  new game then differs from one after the whole tune only in the tune's counters DS:7966 and DS:7968; the desktop
  boots so.
- **The driver**: `Driver.new_game(country, manager_name, managers=1, on_bulletin=None)` plays N at the load
  question, the player count by Left/Right and Enter, the country by the browser's arrows (Left/Right move the column
  of 16, Up/Down the row, 1771:26B9), the name's letters and Enter queued for the polled name entry, and Enter on
  each bulletin; it starts from wherever the core is on that way. One manager only: other new-game paths are not
  traced (NG-7). The line editor keeps the first character, upper-cased, as the initial and the rest after one
  blank (or one other character) as the surname: "bob" becomes "B Ob". `log` lists queued keys where the original
  read them.
- **The views**: `views.country_select` (the browser's 128 countries in its order, the browsed one, the start year
  and stage), `views.country_card` (a country as the browser's panel shows it, in the desktop card's shape) and
  `views.bulletin` (each story's masthead and lines, read from the page buffer [DS:A96E] that 000E:070B, 062F and
  075F compose and 000E:05F6 moves to the screen; the template's filler rows of ≡ and ░ are left out).

## Saving

[derived: F029, a savestate's memory is the master] `core.save()` is `G2C1`, a JSON header (the registers, the
load segment, the Memory component's header, the DOS time and the date it was booted with (version 2; a version 1
save loads with the default time), whether the wait is at a poll and the polled kinds that stop (version 3, T108),
the seeds `DS:7B62` and `DS:7B64` (F004), the key log since the
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
`goal2.tests.test_core_new_game_t106` (T106) keeps E038's byte-for-byte new game (about a second) in the default
run; its slow cases boot E039's two dates through the whole title tune (about a minute each) and drive Launch's new
career to the main window. `goal2.tests.test_core_desktop_t105` (T105) is guarded the same way, with `goal2/desktop/core_*`; its default run
keeps the E006 text oracle, and its slow cases play E010-r0001's second half (about 20 s) and open the window. `goal2.tests.test_core_team_t107` (T107) likewise keeps its E006 text oracle (about a second) in the default run;
its slow cases (about 20 s) run the actions, the new game's oracle and the Team and Pool pages.
`goal2.tests.test_core_round_t108` (T108) keeps #327's runner checks in the default run; its slow cases play E006's
first two rounds (about two minutes), the half-time bench, rounds through a refused eleven (about eight minutes) and
the desktop's round, guarded with `goal2/desktop/fixtures_page.py` and `bench_page.py`.
