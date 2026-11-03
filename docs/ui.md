# The new window (`goal2/ui`)

The rebuilt UI of [the design](design/ui-2026-11/README.md), in PySide6 widgets ([the technology](design/technology-2026-11/README.md),
the owner's decision D1, #527). It is built beside today's window, `goal2/desktop`, which stays the shipped window
and the portable build's default until T169 switches over. [designed: owner, 2026-11-03, #526, #527, #536]

    python -m goal2.ui [--data-root DIR] [--import FOLDER]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

It opens S01 while the per-user data folder lacks a file the new window needs, otherwise S02 Start. `--data-root`
names the per-user goal2 folder (its `data` holds the imported files). `--import FOLDER` imports FOLDER as S01 does
(`WINDOW_MANIFEST`, GOAL.HLP too when the folder has it), then starts; S22's message names it as the way to add
GOAL.HLP, and the desk's *re-import data* with a career open. `--screenshot` writes PNGs at 1440×900 from a
temporary data folder of its own and exits: S01, the placeholder home and S22 (with a stand-in help text) always;
S02 with two saves, S03, S04 on Holland with its twenty and the name line, S05 with stand-in pages (labelled so), S06
the desk, S07 team info, S11 fixtures, S12 tournament and S13 history with the new career, and S11 and S13 again after
its first round (the route's quick friendly), when it finds GOAL.DAT and the template in the data root's `data` or in
a checkout's `.cache/`.

## The journey

[designed: owner, 2026-11-03, #526, #527; T163, #537; T164, #538] S01 → S02 → (N) S03 → S04 → S06 the desk, or S02 →
(Enter or Y) S06, as the design's [section 1](design/ui-2026-11/README.md#1-the-players-journey). The screens run over the
Python route's state (`goal2/desktop/model.py` `DesktopModel`, the owner's route (b), D2): a career started or
loaded here is the one the model makes, and the screens copy no career rule.

- **What it needs.** `data_setup.WINDOW_MANIFEST`: GOAL.DAT and the E010 half-time template
  (`e010-r0008-halftime.sav`) a new career starts from, pinned by hash; GOAL.HLP stays optional. The Core's boot
  state is not asked for. `data_setup.MANIFEST`, the old window's, is unchanged; `problems`, `complete` and
  `import_folder` take the manifest to check.
- **The start year** [confirmed: NG-9]: S03's field, empty for the PC clock's year; the start year is that year + 1,
  rounded up to even, and its first stage is the model's (`campaign.opening_calendar`: 2 when divisible by 4, else
  5). `DesktopModel.new_campaign` takes every year `opening_calendar` takes; the old window still offers 1990 and
  1992.
- **Managers.** S03 shows 1 to 6; 2 to 6 say they come later (#551).
- **S04's list** [confirmed: T156-R1 steps 3–5, `t156-005-country-holland.png`; #559] is in the order of the ranking
  Ins selects (`s04_country.ordered`): under *continental* each continent's 32 by rank, Europe first (Denmark,
  Germany, Holland…), under *world* the world ranks. It opens on *continental*, at Denmark, as the original. The
  twenty's average age and caps are cut to whole numbers, not rounded: Holland's 28.6 shows as the capture's 28
  [derived: #559].
- **Bulletins** [designed: owner, 2026-11-03, #509]: the Python route has none yet, so a new career goes from S04
  straight to the desk; `Window.open_career(model, pages)` shows S05 first for a career that supplies pages.
- **The home** of an open career is the desk (S06). `goal2/ui/home.py` stays only as the screen with no career open
  (T162's tests and the screenshot tool's `home.png`).

## Saved games

[designed: owner decisions 4 and 8, #526; T163] Saves live in the data root's `saves` folder, one file per save,
`<derived name>.g2game`: a zip holding `goal2-save.json` (`{"format": "goal2-named-save", "version": 1, "name",
"saved"}`: the free name, at most 32 characters, and the time, ISO 8601 with its zone) and `session.g2save`, the
model's own session save byte for byte. The file name is derived from the free name (letters, digits, `-`, `_`; a
name Windows reserves gets `-save`; `-2`, `-3`… when another name derives the same), and S02 lists the stored name.
A save is read only by the model's validating loader (`DesktopModel.from_save`). `goal2/ui/saves.py` reads and writes
the format; T168 adds saving under a name from the desk (F7). The desk never saves through `DesktopModel.save`.

## The parts

| Module | What it holds |
| --- | --- |
| `goal2/ui/theme.py` | The palette, one named constant per role of the design's §3 table (`PALETTE` is the table); the vendored font, loaded with `QFontDatabase` from `goal2/ui/fonts/`; the text sizes (16 px, the font's 8×16 cell, and 32 px); the style sheet. |
| `goal2/ui/fonts/` | "PxPlus IBM VGA 8x16" (CC BY-SA 4.0) with its `LICENSE.TXT` and `PROVENANCE.md`; package data, so the wheel and the portable build carry the licence beside the font. |
| `goal2/ui/window.py` | `Window`: one main window holding one screen at a time on a stack. |
| `goal2/ui/screen.py` | `Screen`, the base class of every screen. |
| `goal2/ui/s01_import.py` | S01 Import your data, over `data_setup`'s check and copy. |
| `goal2/ui/s22_help.py` | S22 Help: the imported GOAL.HLP, over the screen F1 was pressed on, in a box that fills most of the screen (owner decision 13). |
| `goal2/ui/home.py` | The placeholder screen with no career open. |
| `goal2/ui/s02_start.py` | S02 Start: Continue, the named saves, Y load, N new game, a failed load's Y/N. |
| `goal2/ui/s03_new_game.py` | S03 New game: 1–6 managers (2–6 later, #551), the optional starting year by NG-9. |
| `goal2/ui/s04_country.py` | S04 Country and name: the card (`CountryCard`, shared with S07, with the twenty's average caps and age), the list in groups of 16 in the ranking's order (`ordered`), Ins, the name line; `PlayersScreen`, a country's twenty read only (Space) on T165's S08 card (`squad_card.PlayerCard`, bars without numbers). |
| `goal2/ui/s05_bulletin.py` | S05 Bulletin: pages *n of m*, any key onward. |
| `goal2/ui/s06_desk.py` | S06 The manager's desk (T164), and `ReimportScreen`, S01 over the data folder. |
| `goal2/ui/s07_team_info.py` | S07 Team info (T164): S04's card for any country, the list, the next opponent marked; a country's twenty and its tactics, read only. |
| `goal2/ui/s11_fixtures.py` | S11 Fixtures (T178): the coming round, or a country's coming fixtures. |
| `goal2/ui/s12_tournament.py` | S12 Tournament (T178): the displays and continents as tabs, a group's table beside its matches, the banner. |
| `goal2/ui/s13_history.py` | S13 History (T178): this career's results by season; the boxes without a source. |
| `goal2/ui/saves.py` | The named save format (Qt-free). |
| `goal2/ui/start_look.py` | The style S02–S05 add to the theme's sheet, and their shared parts (boxes, rows, typed lines). |

The rest of `goal2/ui` (`grid`, `plain_renderer`, `input` and the terminal screens) is the older terminal screen
framework; the new window does not use it.

## A screen

A screen subclasses `Screen` and fills `self.body_layout`. The base class gives it:

- **the title bar**: the GOAL2 corner and the screen's `title`; with `pre_game = True` (S01–S04) the corner's note
  "the 1993 game, rebuilt" and the name in normal text, as the mockups draw them;
- **the bottom bar**: every key the screen binds, with `bind(keys, text, handler)`, in the key-hint colour; at its
  right end the Enter hint, drawn as the original's highlight bar, saying what Enter does now: the highlighted
  option's `enter` text, or the screen's `set_enter(text, handler)`;
- **options**: `add_option(text, handler, key=None, enter=None)` returns a clickable option; ↑↓ move the highlight,
  Enter does the highlighted option, the option's key does it directly;
- **the "waiting for" line**: `wait_for(headline, detail)` says above the body what the screen waits for and which
  key answers it ([design §3, "Stops"](design/ui-2026-11/README.md#3-rules-for-the-whole-ui));
- **Esc**: `escape_text` names it on the bar and `escape()` does it; by default it returns to the screen underneath
  (`window.pop()`). S01 and S02 quit, the help closes, the home screen and S05 have none;
- **typed text**: a screen with a typed line defines `type_text(key, text)`; the window offers it each key's text
  first (S03's year, S04's name). Tab reaches the screens, never Qt's focus chain;
- **F1**: on every screen but the help itself, it opens S22 over the screen.

Keys and the mouse take one path [designed: owner, 2026-11-03, #526]: a key, a click on an option, a click on a key
of the bottom bar and a click on the Enter hint all reach the same handler.

## The window

`Window.push(screen)` opens a screen over the current one, `pop()` returns to the one underneath and
`replace_home(screen)` empties the stack and starts again from `screen`; `open_career(model, pages=())` makes `model`
the open career (`window.career`) and shows its pages (S05), then the home. Keys go to the current screen
(`Screen.handle_key`). The page is composed for 1440×900 and scales as a whole with the window: the central widget is
today's `goal2.desktop.fixed_page.FixedPage`, reused, which multiplies every length of the page, its style sheet's
text sizes included (T101). Its `problems(window)` check (no scroll bar, nothing clipped or squeezed) applies to every
screen of the new window too.

## The look

Colours come from `theme` only, by role; a colour that is not in the palette table is a design question for the
owner. Text sizes are whole multiples of the 16 px cell. The screens follow their mockups in
[docs/design/ui-2026-11/mockups](design/ui-2026-11/mockups/) (sizes, spacing, layout, words), and a departure from a
mockup is a design question too.

## Tests

`goal2/tests/test_ui_foundation_t162.py` visits the palette against the README's table, the font, the stack, a click
against its key, S01 and S22, offscreen. `goal2/tests/test_ui_start_t163.py` visits the journey from S02 to the desk
against the model's own careers, the start year, the managers, S04's keys, named saves, S01's manifest, S22's size
and S05's pages; its careers read GOAL.DAT and the template from `.cache/` and skip without them. It writes stand-in data files and a stand-in help text into temporary
folders: no byte of the original's files is in the tests (CLAUDE.md rule 14).

## Squad, pool and tactics: S08, S09, S10 (T165)

[designed: owner, 2026-11-03, #526, #527 D2; T165] Three screens over an open `DesktopModel` (route (b)). Every change
they make is the model's own call, so the screen and the model cannot disagree: the exchange (`exchange`), the position
(`set_position`, `club_position`), the player's own tactics (`own_tactic`), the team tactics (`set_team_tactic`) and
the name (`rename_player`). A later task puts them on the desk: `goal2.ui.s08_squad.open_squad(window, model)` and
`goal2.ui.s10_team_tactics.open_team_tactics(window, model)` push them.

| Module | What it holds |
| --- | --- |
| `goal2/ui/squad_card.py` | The parts the three share: the player card (every field of `goal2.game.player_card.card`), the strip on the right (the eleven, a gap, the bench; or a page of the pool), bars, label-value lines, table rows, the name line. |
| `goal2/ui/s08_squad.py` | S08 Squad and pool. |
| `goal2/ui/s09_player_tactics.py` | S09 Player tactics. |
| `goal2/ui/s10_team_tactics.py` | S10 Team tactics. |

- **S08**: ↑↓ the player, ←→ the squad or the pool. The pool's eighty are paged twenty at a time, as the original's
  pool list; ↑↓ go on to the next or previous page. Enter on a pool player picks him; the Enter hint then reads
  *Put here* and the screen says what it waits for; ← back and Enter on the player he replaces makes the exchange.
  Enter on the picked player again drops the pick. [T164, #555] Enter on a squad player and then on another squad
  player swaps them (`DesktopModel.swap`): a starter and a bench player swap in and out, the incoming one taking the
  starter's place in the eleven; two starters change places. It is how the eleven is chosen, and how an injured or
  suspended starter goes to the bench. Two bench players keep the squad's order, and the screen says so. **Ins** reads *coming later* and only says so, until the
  original's assistant (`0791:DC7E`) is ported [designed: owner, 2026-11-03, #509]. **R** / **Shift+R** the next or
  previous position, **C** the club position, **T** S09, **F2** the name line in the card's header (at most 12
  characters; Enter gives the name, Esc keeps the old one), **Esc** back.
- **S09**: between matches the original's four lines (position, possession, passing, tackling) with **P** on a line
  set for this player. The mark line comes with the match screens: the original shows it only with a match set up
  (`1771:49B8`, F010). Arrows choose, Enter alters, Esc returns to the card.
- **S10**: the eight lines with the value now and the other option; ↑↓ choose, Enter changes, Esc returns. The
  characteristics say "not decoded yet (G05)": the Python route has no team characteristics.
- **The mouse**: a click on a row (a player, a tactic line) moves the cursor there, and a click on the highlighted row
  is Enter. *Squad* and *Pool* above the card are ← and →.
- **Colours** are set on each part by itself, as colour only, from `theme`'s roles; the window's style sheet is
  T162's. The parts are all made with the screen and only change their texts, because the window scales a screen's
  lengths when it is pushed.

`goal2/tests/test_ui_squad_t165.py` drives each screen over a career from `DesktopModel.open` and makes the same
request on a copy of it through the model; it compares `view()` and the whole state. It skips without the `.cache/`
files. `tools/ui_squad_screenshots.py DIR` writes the screens' pictures (they are in
[design/ui-2026-11/T165-screens](design/ui-2026-11/T165-screens/)).

## The desk and team info: S06, S07 (T164)

[designed: owner, 2026-11-03, #526 decisions 1 and 14, #527 D2; T164, #538] A new career or a loaded save lands on S06,
the manager's desk, the career's home: every management screen returns to it with Esc, and it has no Esc of its own.

- **S06** shows the manager (name; rating *unknown*: the route keeps none), the team with its world and continental
  rankings, the next opponents with theirs and the match's kind (the route assigns no venue, T41a, so no home or
  away), the managers, and the twenty with role codes, the eleven above the bench; the competition at the title
  bar's right end, named as the original's hub names it (T178, #563: *2028 European Championship · QUALIFYING*). The
  six options in the original's order, the cursor on *team info*: *team info* (S07), *fixture list* (S11),
  *tournament* (S12), *history* (S13), *select squad* (S08, also Space) and *play next game* (T167's match
  screens). **T** S10, **F1** S22; **F3** comes with T167, **F4**, **F7** and **F10** with T168. A
  placeholder says which task brings it, on the desk, and does nothing else. *re-import data*, a goal2 addition
  (decision 14), is a seventh option under a "goal2 addition" tag: S01 over the data folder, Esc back to the desk.
- **S07** shows S04's card for the highlighted country, read from the career, beside the list in groups of 16, the next
  opponent marked. It opens on the world ranking at the next opponent. **↑↓** country, **←→** group, **Ins** the
  other ranking (the highlight stays), **Space** the country's twenty read only, **T** its tactics (S10 for your own
  country; the eight lines read only for another), **Enter** its fixtures (S11, T178; Esc back to S07), **Esc** the
  desk.

`goal2/tests/test_ui_desk_t164.py` visits the landing from a new career and a save, each option, Esc back from S07,
S08, S10 and S01, the swap against today's Team swap through `confirm`, S07's keys, and S04's order and average age
against `t156-005-country-holland`. The pictures are in [design/ui-2026-11/T164-screens](design/ui-2026-11/T164-screens/).

## Fixtures, tournament and history: S11, S12, S13 (T178)

[designed: owner, 2026-11-03, #526, #527 D2; T178, #560, #563] Three read-only screens the desk opens, over the
Python route's state. Every number they show is the model's (`DesktopModel`'s read-only calls, each tested), and a
stage the route has not reached says so instead of showing rows.

- **The model's calls.** `fixture_list(country=None)`: a round is what one *play next game* plays on this route, the
  world rows from the cursor up to the managed fixture after the next one, numbered by the career's match day; with
  a country, that country's coming fixtures. `tournament()`: every group of the stage being played, its table
  (`standings.group_table`, the managed one `competition_table`'s) and its matches; None after the opening stage.
  `history()`: this career's results by season (`campaign.results`). `competition(continent, phase)`: the banner's
  year, name and phase (`CHAMPIONSHIPS`, `PHASES`); `continent(country)`.
- **The banner** [confirmed: t156-013-hub, t156-227, t156-228, m244-finals-stage-hub, m244-world-qualifying-a]:
  *European Championship* and *American Championship* as the captures print them, *African* and *Asian
  Championship* from the adjectives at `DS:690A` [derived], *World Cup* from stage 5; QUALIFYING or FINALS by
  stage. Stage 6 (the play-offs) is in no capture and keeps the route's words.
- **S11** lists the round, each fixture's kind (*friendly*, *qualifying*), ✓ on your own match and what happens at
  kick-off (*your match*, *auto result*); **↑↓** scroll, **Esc** back. Enter on your own match says it is always
  watched (owner decision 1). The original's ✓ toggle on another country's match is not built: the engine plays only
  the managed country's match watched (`prepare_watched` refuses another fixture, and the world refuses a watched
  silent row), so Enter there says it comes later. *Cancel or rearrange* your own friendly has no call on the route
  and says so too. The two sides have no *home* and *away* headings: the route keeps no venue (T41a, #562).
- **S12**: the displays (Qualifying, Finals, Championship) and the continents (Europe, Africa, Americas, Asia) as
  tabs, a click on a tab as its key; the group's table P W D L F A T beside its twelve matches. **↑↓** group,
  **Space** continent, **←→** display, **Ins** the Championship results (not reached), **Esc** the desk. It opens on
  your group. Finals and Championship read *not reached yet* until T170.
- **S13**: the design's five boxes. The results box holds one row per season and competition (2027/28 EC: W D L F A
  of the competition's matches, the best place) and the season's results under it, friendlies too. Statistics,
  successes, top scorers, top caps and records say they are kept from a later version (#509 Track B): the route keeps
  no source for them, and nothing is read from the template's memory.

`goal2/tests/test_ui_boards_t178.py` visits the model's calls against the career's world schedule and results, each
screen's rows against them, the keys, Esc back, S07's Enter and the banner for a European and an American country.
The pictures are in [design/ui-2026-11/T178-screens](design/ui-2026-11/T178-screens/).
