# The new window (`goal2/ui`)

The rebuilt UI of [the design](design/ui-2026-11/README.md), in PySide6 widgets ([the technology](design/technology-2026-11/README.md),
the owner's decision D1, #527). It is built beside today's window, `goal2/desktop`, which stays the shipped window
and the portable build's default until T169 switches over. [designed: owner, 2026-11-03, #526, #527, #536]

    python -m goal2.ui [--data-root DIR] [--import FOLDER]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

It opens S01 while the per-user data folder lacks a file the new window needs, otherwise S02 Start. `--data-root`
names the per-user goal2 folder (its `data` holds the imported files). `--import FOLDER` imports FOLDER as S01 does
(`WINDOW_MANIFEST`, GOAL.HLP too when the folder has it), then starts; S22's message names it as the way to add
GOAL.HLP, and the desk's *re-import data* with a career open. `--screenshot` writes PNGs at 1440×1080 (the 4:3 page at its own size, `theme.PICTURE`) from a
temporary data folder of its own and exits: S01, the placeholder home and S22 (with a stand-in help text) always;
S02 with two saves, S03, S04 on Holland with its twenty and the name line, S05 with stand-in pages (labelled so), S06
the desk, S07 team info, S11 fixtures, S12 tournament and S13 history with the new career, the match day of the career's
first friendly under PyPy 3.11 on a copy of the career (S14 before and after the match, S15 before kick-off and at half
time, S16 the captain and a set-piece taker, S17 at kick-off and in play, S20 at half time and full time), S11 and S13 again after its first
round (the route's quick friendly), S21's save box, quit question and save question over the desk, and T177's extras
(S02's standalone friendly with its country chosen, S08's pool search, the desk's manager's name line), and T181's
goal questions/replay/name box, summary question/name box and F3/F4 lists, when it finds GOAL.DAT and the template in the data root's `data` or in a checkout's `.cache/`.

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
the format; `saves.write` is the only writer, and F7 saves through it (S21, below). [designed: T168, #542] The model's
`save_path` is the `.g2game` file, so nothing calls `DesktopModel.save` on it: `write` has the model save its session
into a temporary folder and stores it in the zip, which replaces an older file only once complete. A save that fails
raises `SaveError` saying why, leaves the folder's files as they were and restores the model's saved mark, so its
progress stays unsaved. `model.save_name` is the name a career was last saved or loaded under (`saves.last_name`).

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
| `goal2/ui/s02_start.py` | S02 Start: Continue, the named saves, Y load, N new game, a failed load's Y/N; F the standalone friendly (T177). |
| `goal2/ui/friendly.py` | The standalone friendly (T177): two countries chosen, played on S17, back to S02; nothing saved. |
| `goal2/ui/s03_new_game.py` | S03 New game: 1–6 managers (2–6 later, #551), the optional starting year by NG-9. |
| `goal2/ui/s04_country.py` | S04 Country and name [designed: T211b: on the 16 × 32 grid]: the card (`CountryCard`, shared with S07: two columns of frames, with the twenty's average caps and age), the list in groups of 16 in the ranking's order (`ordered`) in a frame, Ins, the name line in a frame under it; `PlayersScreen`, a country's twenty read only (Space) on T165's S08 card (`squad_card.PlayerCard`, bars without numbers). |
| `goal2/ui/s05_bulletin.py` | S05 Bulletin: pages *n of m*, any key onward. |
| `goal2/ui/s06_desk.py` | S06 The manager's desk (T164), its *manager's name* and *new career* (T177), and `ReimportScreen`, S01 over the data folder. |
| `goal2/ui/s07_team_info.py` | S07 Team info (T164; on the 16 × 32 grid, T211b): S04's card for any country, the list, the next opponent marked; a country's twenty and its tactics, read only. |
| `goal2/ui/s11_fixtures.py` | S11 Fixtures (T178; on the 16 × 32 grid, T211b): the coming round, or a country's coming fixtures. |
| `goal2/ui/s12_tournament.py` | S12 Tournament (T178): the displays and continents as tabs, a group's table beside its matches, the banner. |
| `goal2/ui/s13_history.py` | S13 History (T178): this career's results by season; the boxes without a source. |
| `goal2/ui/match_day.py` | The match day (T167): `MatchDay`, the window's bridges and the order of S14, S15, S16, S17 and S20; the desk's `play_next_game`; the watch question's rule (`asks_watch`). |
| `goal2/ui/s14_round.py` | S14 Round results (T167). |
| `goal2/ui/s15_match_menu.py` | S15 Match menu (T167). |
| `goal2/ui/s16_choose.py` | S16 Choose a player: the captain, a set-piece taker, the penalty order (T167). |
| `goal2/ui/s17_pitch.py` | S17 Pitch (T166): the screen, `MatchController` over the match day's bridge, the suggested captain (`best_leader`). |
| `goal2/ui/s20_board.py` | S20 Match board (T167). |
| `goal2/ui/pitch.py` | S17's pitch widget: lines, surround, marks coloured by side, the ball, the enlarged commentary. |
| `goal2/ui/saves.py` | The named save format (Qt-free). |
| `goal2/ui/s21_save.py` | S21 Save and quit (T168): F7's name box, the replace question, F10's two questions and the close button's. |
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
(`Screen.handle_key`). Closing the window first calls `closing()` on every screen on the stack that has one (S17
cancels its match) [designed: T166]. The page is composed for 90 × 28 cells of 16 × 32 (1440×896) and scales as a whole with the window, presented at 4:3
[designed: owner, 2026-11-08, #667; T209; docs/design/ui-2026-11/README.md §3] — the central widget is
today's `goal2.desktop.fixed_page.FixedPage` with its stretch (the legacy window keeps it uniform), which multiplies every
length of the page, its style sheet's text size included, by the scale (vertical ones by 1.2 × the scale) and sets the
font stretch that keeps a glyph one cell wide (T101). The text is one size, `theme.TEXT` (32 px). Its `problems(window)` check (no scroll bar, nothing clipped or squeezed) applies to every
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
| `goal2/ui/cells.py`, `goal2/ui/cell_parts.py` | [designed: T211] The grid's parts: text and panels placed by cell (`CellLabel`, `CellPara`, `Cells`), and the strip, card, bars and typed line S06 and S08 are made of (S09 and S10 keep `squad_card`'s until they are reflowed). [designed: T211b] `CellTableRow`: a row of a list or a table, its cells at columns, the highlight bar behind them (S04 and S07's lists, S11's rows). |
| `goal2/ui/country_parts.py` | [designed: T211b] The country card's parts on the grid (S04, S07): the four lines' bars, the strips, the characteristics' rows, the caps and age on a line, a panel as a frame over cells (`framed`). S10 keeps `team_card`'s and `country_header`'s until it is reflowed. |
| `goal2/ui/squad_card.py` | The parts the three share: the player card (every field of `goal2.game.player_card.card`), the strip on the right (the eleven, a gap, the bench; or a page of the pool), bars, label-value lines, table rows, the name line. |
| `goal2/ui/s08_squad.py` | S08 Squad and pool. [designed: T211] On the 16 × 32 grid: the card (`cell_parts.GridCard`: the name and the facts as rules with their values under them, the skills, the tactics over the characteristics) and the twenty (`GridStrip`) side by side, a cell apart; the pool's filters and the goal2 addition's tag above the card; the message under it and what a pick waits for across the foot. |
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
  characters; Enter gives the name, Esc keeps the old one), **Esc** back. **/** and **P**, the pool's search and
  position filter, are T177's (below).
- **S09**: between matches the original's four lines (position, possession, passing, tackling) with **P** on a line
  set for this player. The mark line comes with the match screens: the original shows it only with a match set up
  (`1771:49B8`, F010). Arrows choose, Enter alters, Esc returns to the card.
- **S10**: [confirmed: original1771:1981→157D; F036–F038; owner611/646] the full TEAM header,
  skills, original XI caps/age and characteristics remain beside the eight editable tactics. The first
  three are TEAM TACTICS and the last five PLAYER DEFAULTS. ↑↓ choose, Enter changes, Esc returns;
  a changed match tactic waits for authoritative confirmation. Current stopped-match records supply
  the live panels; performance appears only with its observed original visibility flags. Legacy decisions
  without those observations retain an explicit fallback. Red roster names marked * are injured.
  [derived: F024/F034; designed: T92, #653] The TEAM manager follows the country's selected
  manager; the active named human uses the session identity. The unnamed country preview retains
  its existing default name. Decoding additional imported human identities is outside this overlay.
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

[designed: owner, 2026-11-09, #667; T211b] S07 is on the grid too: the card (60 cells: the frames *team*, *skills*, *team tactics* in a column of 34 and *ranking*, *line-up*, *characteristics*, *player defaults* in one of 25, a cell apart, one row between them; *performance* under the skills when the card is in a match context) and at its right the original's heading of the list (*check out all the competitors*) over the sixteen countries in a frame, 29 cells, their names right-aligned and *next opponent* in the cells after the highlighted one's; S04 is the same card and list under the prompt, the level of difficulty and the first match, with the manager's name in a frame under the list (a line, then what it says in three rows). The lists' ranking is on S04's frame rule (*continental rank*, *world rank*) and in S07's note under the list.

[designed: owner, 2026-11-09, #667; T211] The desk is laid out on the 16 × 32 grid, in cells (90 columns, the 25 rows between the one-row
title and the two key rows), three columns a cell apart and no card: at the left the frames *manager*, *team*, *next opponents* and
*managers* (a rule with its lowercase label, goal2/ui/frame.py) with the hint and the screen's message under them; in the middle the
six options as boxes of two rows (a row between them, as the original's) and under the *GOAL2 ADDITION* tag the extras as boxes; at the
right the twenty in a frame named for the country. Its pieces are `goal2/ui/cells.py` and `goal2/ui/cell_parts.py`; the rules are in
[design/ui-2026-11/README.md §3](design/ui-2026-11/README.md#3-rules-for-the-whole-ui).

- **S06** shows the manager (name; rating *unknown*: the route keeps none), the team with its world and continental
  rankings, the next opponents with theirs and the match's kind with home or away (*friendly away*, T167, #562), the managers, and the twenty with role codes, the eleven above the bench; the competition at the title
  bar's right end, named as the original's hub names it (T178, #563: *2028 European Championship · QUALIFYING*). The
  six options in the original's order, the cursor on *team info*: *team info* (S07), *fixture list* (S11),
  *tournament* (S12), *history* (S13), *select squad* (S08, also Space) and *play next game* (the match day, T167, below). **T** S10, **F1** S22, **F7** save and **F10** quit (S21, T168, below); **F3** lists saved goals and **F4** saved match summaries (T181). Under a "goal2
  addition" tag, on one row after the six: *manager's name* and *new career* (T177, below) and *re-import data*
  (decision 14), S01 over the data folder, Esc back to the desk.
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
- **S11** (on the 16 × 32 grid, T211b: the list in a frame across the 90 columns, its heading on the rule, the column names in brown over sixteen rows, the original's own number) lists the round, each fixture's kind (*friendly*, *qualifying*), ✓ on your own match and what happens at
  kick-off (*your match*, *auto result*); **↑↓** scroll, **Esc** back. Enter on your own match says it is always
  watched (owner decision 1). The original's ✓ toggle on another country's match is not built: the engine plays only
  the managed country's match watched (`prepare_watched` refuses another fixture, and the world refuses a watched
  silent row), so Enter there says it comes later. *Cancel or rearrange* your own friendly has no call on the route
  and says so too. The two sides have no *home* and *away* headings yet; the model knows the home side since T167 (`DesktopModel.home`, #562).
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

## The pitch: S17 (T166)

[designed: owner, 2026-11-03, #526 decision 2, #527 D3; T166, #540] Your own friendly, watched in the main window with the
commentary always beside it. What S17 shows is the engine's samples and events, in order, paced by S17's own
acknowledgements, and the match the player watched is the match the engine published.

- **Over the bridge.** `MatchController` plays one match on the match day's `WatchedJobs` (a friendly) or
  `CompetitiveJobs` (a qualifier, T176) ([watched-jobs.md](watched-jobs.md)), started with the pitch samples, the
  bench and the player prompts (`frames=True, bench=True, prompts=True`, delay byte 0, draws recorded). A 4 ms timer
  on the window's thread polls it: `poll` for the events, `poll_frames` while the view holds at most 32 samples, then
  the next sample is selected when the speed says it is due (`goal2/desktop/match_view.py` `Display`, its six
  `SPEEDS`). The pitch acknowledges a sample (`ack_frames`) only after painting it, so the engine is never more than
  `LEAD` samples ahead of what was drawn; a stalled or hidden pitch stalls the engine. The bridge is the match day's
  and stays open after the match [designed: T167, D3; T166 made one per match].
- **Shows** (s17-pitch.html): the two sides, each in its kit as the original computes it (`goal2/ui/kits.py`, #583), the score, the minute, the match's kind,
  the last two events; the pitch (`goal2/ui/pitch.py`: the lines and boxes of the samples' grid, the green surround,
  one character per grid cell in the original's drawing order, keepers as faces, the ball on an empty cell); the
  commentary, the speed, the display and your side's colour. The home side is the fixture's side B, named first
  (`DesktopModel.home`, #562; T167).
- **Keys** [confirmed: E031 C39–C40, C08; T156-R1 steps 45, 267]: **←→** speed, **↑↓** the five display styles
  (role codes first), **Space** a larger commentary reading panel and back, **R** quick result (every sample is
  acknowledged as it arrives; *HANG ON A TICK* stands where *R result* was, `t156-267-quick-hang-on`), **F9** says
  goal2 has no sound and does nothing else, **Esc** / **Enter** request the bench (`pause`).
- **The stops** [designed: T167; T180]: once every sample before it is shown, the controller holds the decision the
  match waits on (`stop`) and the match day shows it (below): no stop keeps a default answer. The other side's
  substitution (S18's notice) and a bench answer's report that refuses a pair (S19) hold the display until a key; the
  engine then waits within its pacing. In a quick result a set-piece taker gets no key (no card), and the other
  side's substitutions show no notice. The captain is chosen on S16
  (the match day), its highlight on the original's suggestion as T143 picks it (`best_leader`, T143's rule over the
  route's player records; the Core's own function needs Unicorn to import).
- **Closing the window** during the match cancels it through the bridge (`cancel_and_reap`); the desk then closes the
  match day's bridges: nothing is published and the engine process ends. With unsaved progress the window then asks
  to save over the desk (S21, below).
- **The pygame viewer** stays for today's window (owner decision 17): S17 reuses its drawing constants
  (`pygame_viewer.GRID`, `MARGIN`, `DRAW_ORDER`, `MARKS`, `glyph`), which move with S17 when the viewer is retired.

`goal2/tests/test_ui_pitch_t166.py` plays the friendly from the desk through the match day to full time on S17 and
compares its events with the bridge's and the published career with the same match through the bridge with the same
answers; it checks the pacing with painting stalled, the keys, the close mid-match (no engine process within 5 s,
nothing published), the sides' colours on the painted pitch and `best_leader` against T143's function. It needs PyPy
3.11 and the `.cache/` files and
skips without them. The pictures are in [design/ui-2026-11/T166-screens](design/ui-2026-11/T166-screens/).

## The match day: S14, S15, S16, S20 (T167)

[designed: owner, 2026-11-03, #526 decisions 1 and 3, #527 D3; T167, #541, #562; confirmed: T156-R1 steps 36–48,
56–58, 118–119, 191–198, 262–270, 310–313] *play next game* on the desk runs the original's match day in the window,
in the original's order (`goal2/ui/match_day.py`): S14 → S15 → S16 → S17 → S20 (half time) → S15 → S17 → S20 (full
time) → S15 *exit* → S14 → the desk, for a friendly and a qualifier alike. Every answer given on these screens is the
answer the engine receives, sent once, through the bridge, in the order the engine asked.

- **One bridge for the window's life** (D3): `MatchDay` keeps the owner's `WatchedJobs` and `CompetitiveJobs` open
  between matches, so all the window's matches play in one engine process; the desk closes them when the window
  closes (`DeskScreen.closing`), and with them the process.
- **S14** lists the round's results the route resolves before your match (`DesktopModel.round_before`, on a copy:
  the publication resolves the same rows from the same state), one by one, your match last; after *exit*, your
  result and the results resolved after it (`round_after`). **Space** pauses, **←→** the pace, **Enter** onward.
  The home side is named first.
- **S15** shows the score, the kind, the location (the home side), the time and both formations and elevens; the
  options with *play* highlighted first: each side's team tactics and players (yours open S10 and S08 before
  kick-off, also **T** and **Space**; at a break *players* opens S19 and managed team tactics remain editable, owner #610),
  the tournament, the match stats, and *play* ("choose your captain, then kick-off", "second half") or *exit*.
  **Ins** turns the automatic action replay on or off, stored in the data root's `settings.json`; the replay itself
  is T181's. The watch question comes only where the original asks it (`asks_watch`: kinds 8, 200, 201, 203, and
  101, 103 with a manager on side B's continent, F030), with **Y**/**N**; N plays a quick result (S17 with R pressed).
- **S16** asks the captain before kick-off ("Choose your captain to kick off"; the highlight on T143's pick; **↑↓**,
  **Enter**, **C** the computer's), confirmed through `DesktopModel.confirm` before the engine is asked; a set-piece
  taker during play (the engine's `set_piece` decision, over the bridge and the pipe: `prompts`); and the shoot-out
  order (Enter adds, **Esc** undoes). With no key the current pick stands after the original's wait, 10 s (F030).
- **S20** shows what the events and the outcome give: the score, the half-time score, the scorers and minutes; at full
  time the original's board as the engine read it (its nine counters, the bars' raw words, the man of the match); at
  half time bookings and red cards from the events, and the rest say *at full time*. After a quick result the QUICK
  RESULT banner stands in place of the statistics. **Enter** continues; **Esc** opens the bench (S19) at half time
  and before extra time (T180); at full time it continues.
- **The home side** (#562) is the fixture's side B (`DesktopModel.home`, `venue`): the original's hub writes *away*
  for side A and *home* for side B (F031 "Venue", `000E:724A`); S14, S15, S17 and S20 name it first and draw it light
  red, and the desk says *friendly home* or *friendly away*.

`goal2/tests/test_ui_match_day_t167.py` plays two match days in one window (the friendly with a chosen captain and a
chosen taker, R in the second half; the qualifier with N to a stand-in watch question and C on the captain) and
compares each published career with the same match through the bridge with the same answers, the chosen taker with
`pypy_engine.drive`, and the qualifier's no-key takers with the match played without the prompts; it checks the order
of the screens, the stored captain, one engine pid and the home side. It needs PyPy 3.11 and the `.cache/` files and
skips without them. The pictures are in [design/ui-2026-11/T167-screens](design/ui-2026-11/T167-screens/).

## The match stops and the bench: S18, S19, S09's mark line (T180)

[designed: owner, 2026-11-03, #526; T180, #574; confirmed: T156-R1 steps 67–68, 74–81, 124–133, 149–150; E031
C39–C41k] The stops T167 left on a default answer are the original's screens. The claim: every substitution the
player makes on S19 is the pair the engine receives, and every refusal the player sees is the engine's.

- **S18** (`goal2/ui/s18_stop.py`) is a box over the pitch (`PitchScreen.stop_box`): *SUBSTITUTION OPPORTUNITY* (your
  player injured, or the stoppage after a request; the original's refused eleven is said there), any key to S15
  (phase *stop*), whose *players* opens S19; the other side's substitution (*SUBSTITUTION X on for Y*), any key plays
  on; the penalty shoot-out's notice before S16's order. T181's goal questions use the same box (below).
- **S19** (`goal2/ui/s19_bench.py`) shows the card, live eleven/bench and the engine's remaining budget.
  [designed: owner playtest2026-11-05, #599; supersedes T180's queued/deferred UI] At a legal stop, **Enter** on
  two players in either order sends one edit-only answer. The original's returned decision updates the squad
  and counter immediately, before Play; repeat input is held until that reply. Refused pairs stay at the usable
  stopped squad with honest on/off feedback. Esc returns to S15; Play or a further Esc continues. [confirmed: original
  T156-R1 steps124–137] Half-time exchanges already appear in SELECT TEAM before Play.
- **Legal stopped bench cue** [confirmed: owner #608; original `t156-124-halftime-bench.png`]: **MAKE SUBSTITUTIONS NOW** blinks bright green while another immediate swap can be made. The text keeps its space and accessible name during the dark phase. It stops blinking while an edit is awaiting confirmation, with no substitutions left, or when the bench is hidden. [designed: #608] Paint phases are 500 ms; the original cadence has not been measured.
- **Esc or Enter on S17** requests an ordinary in-play pause and opens the own player list directly over the match menu [designed: owner T203/#662]. Player Enter or the explicit request/cancel button toggles only the authoritative request latch; it never selects a pair or creates a ball stoppage. Bench Esc returns to the visible menu; Play or Esc there resumes with that request retained/cancelled as acknowledged. Team tactics remain accessible on the menu [designed: owner #610/#612]. Substitution pairs cannot be queued at that pause; supported **R**, **C** positions and **T** personal tactics remain available. The obsolete bench-request
  note clears as soon as the engine acknowledges the stop (or drops it). At pause, half-time, substitution and extra-time menus, managed team tactics confirm each changed flag through the original before Play. Esc on an in-match menu follows original0791:ED8A, validating the XI and resuming; a held key cannot fall through screens and request another pause. Extra-time substitution availability remains separately tracked in the required fidelity audit611.
- Accepted personal settings/marks and known live injury labels survive a squad refresh. An already applied
  pair is cleared and cannot be resubmitted by reopening the screen or pressing Play. The engine kit's older
  queue behavior is retained for reference clients; the player's new-window route does not request it.
- **S09's mark line**: from S19's T, S09 edits the bench's answer, with a fifth line, *mark* (—, nobody, or one of the
  opponent's outfield players, read from the latest pitch sample); the mark is the engine's `marking`. After the
  match the answer is gone and S09 has four lines again, as the original clears the marks.
- **BM-7** [designed: owner, #73]: a watched friendly plays with 255 substitutions a side
  (`watched_match.FRIENDLY_SUBSTITUTIONS`, the Core's `owner-substitutions-v1`), a qualifier with five.

`goal2/tests/test_ui_bench_t180.py` plays two match days of a 2028 Austria career: the friendly (an injury stop, the
half-time bench with five immediate edits, a mark and a refused re-entry, the other side's notice, compared with the same match
through the bridge) and the qualifier (a request during play made at the next stoppage, the counter five then four).
The pictures are in [design/ui-2026-11/T180-screens](design/ui-2026-11/T180-screens/).

## Save and quit: S21 (T168)

[designed: owner, 2026-11-03, #526 decision 8; T168, #542; confirmed: T156-R1 steps 233–241, E031 C23–C26b] S21 is a
box over the screen it came from, that screen dimmed under it as S22's, titled *manager's desk · save* (or *· quit*).

- **F7** (the desk): *Please enter the name of the saved game.* The box proposes the name the career was last saved or
  loaded under (none for a new career); the first key typed replaces the proposal and Backspace edits it, as the
  original's (t156-233, t156-237). **Enter** saves through `saves.write`, **Esc** cancels; once saved, the desk says
  *Saved as "name"*. A name another save already has asks *Replace it? (Y/N)*: **N** returns to the name and keeps
  the old file, **Y** replaces it; the career's own save is replaced without a question. A failed save says why in
  the box and nothing is replaced.
- **F10**: *Are you sure you want to quit? (Y/N)*; **N** (or Esc) stays. **Y** quits at once when nothing is
  unsaved; otherwise *Do you want to save this game? (Y/N)*: **Y** the name box, then quit; **N** quit; **Esc**
  stays.
- **The close button** (`Window.closeEvent`): screens with something running end it first (S17 cancels its match,
  T166) and leave the stack; then, with unsaved progress, the window stays and asks *Do you want to save this game?*
  as above (**Y** save and close, **N** close, **Esc** stay). With nothing unsaved it closes at once.
  `Window.leave()` closes once the player has answered.
- *Unsaved* is the model's own `unsaved`: progress since the career was created, loaded or saved (T87).

`goal2/tests/test_ui_save_t168.py` visits the round trip (a swap on S08, F7 under a typed name, S02 loads it back
with `view()` equal), the replace question, F10's answers, the close button's, the model's save never called on a
`.g2game` file, and a failed save in an unwritable folder. The pictures are in
[design/ui-2026-11/T168-screens](design/ui-2026-11/T168-screens/).

## The extras kept from today's window (T177)

[designed: owner, §6 item 18 (design/ui-2026-11, 2026-11-03); T177, #557] Four of today's extras stay, though the
original lacks them. Each is tagged *GOAL2 ADDITION* on its screen, as the desk's re-import, and does what today's
window does through the model ([desktop-management.md](desktop-management.md)); no key the original uses on that
screen changes meaning.

- **The pool's search and position filter (S08).** **/** opens the search line over the pool (from the squad side
  too): typing filters by name, accents folded (`campaign_pool.fold`: "muller" finds "Müller"), Backspace edits,
  Enter keeps the search and closes the line, Esc clears it. **P** steps the position filter through the original's
  fourteen position codes and back to all, **Shift+P** the other way. The rows are `pool_view(query, position)`'s, and
  the two Enters exchange from a filtered list as from the whole pool (`exchange`). A click on the search line or the
  filter is its key. The original's S08 uses ←→, ↑↓, Enter, Ins, F2, R, C, T and Esc [confirmed: E031 C06, C27,
  C29–C31], not / or P. The bar has no room for two more items at 1440 px, so R stands over C and / over P, two to a
  column.
- **A standalone friendly (S02, F).** `goal2/ui/friendly.py`: the 128 countries in groups of 16 by world rank, ↑↓
  and ←→ as on S04; Enter chooses your country, then the opponent, and kicks off; Esc steps back. The friendly is a
  private `DesktopModel.new_friendly` (no campaign), with the original's suggested captain as *play next game* sets
  it, played watched on S17 through the bridge (`s17_pitch.MatchController`), your country first; the engine's fixture
  index is the template's own. At full time (or a cancel) S17 returns to S02 with its result line. It is never the
  window's career, so nothing asks to save and nothing is saved. The original's title takes only Y and N
  [confirmed: T156-R1 steps 0, 242–244; E031 C11–C12].
- **Renaming the manager (S06, *manager's name*).** A name line in the manager's box, 14 characters at most as S04's;
  Enter gives the name through `rename_manager`, Esc keeps the old one. The career is then unsaved.
- **A new career (S06, *new career*).** With anything unsaved it asks S21's *Do you want to save this game?* first
  (`ask_to_save`, titled *new career*): Y the name box, then S03; N S03 without saving; Esc stays. With nothing
  unsaved it goes straight to S03. S03 opens over the desk: Esc returns to the desk and its career, and a career
  started on S04 replaces it.

`goal2/tests/test_ui_extras_t177.py` visits each against the model: the search and the filter against `pool_view`,
an exchange from a filtered list against `exchange`, the original's S08 keys, the rename against `rename_manager`,
the new career's three answers and the straight path, and the friendly from S02 to full time and back with no save
(it needs PyPy 3.11 and skips without it). The pictures are in
[design/ui-2026-11/T177-screens](design/ui-2026-11/T177-screens/).

## Action replay and recorded goals and boards (T181)

[designed: owner, #575; confirmed: T156-R1 steps 175–178, 198–199, 245–256] After a watched goal, S18 asks
*Do you want an action replay?* **Y** redraws the goal's samples on S17 with **REPLAY** in place of **R result**, then
S18 asks *Do you want to save this goal?* **Y** opens S21's name box. **N** declines each question. With S15's automatic
action replay flag on, playback starts without the first question. A quick result asks neither. The questions and
playback hold the live display and its acknowledgements, keeping the bridge's LEAD pacing: replay paints never
acknowledge a live sample. Once answered, play resumes from the held live sample. No replay asks the engine to play
again or changes a bench answer.

[designed: T181] S17 retains at most **600 already painted samples**, ten seconds at the normal 60 samples/s: the
recent attack, with memory independent of match length. Repainting for a resize adds no duplicate. A new goal after
the last goal starts a fresh window. Playback waits for every selected sample to be painted before advancing,
including the last; it never skips samples to catch up.

Named goals (`.g2goal`) and match summaries (`.g2summary`) use goal2's versioned JSON format in the data root's
`recordings` folder, beside `saves`. These are not the original's files. Writes replace a file only when complete;
a duplicate name asks before replacing, and a failed write leaves the prior recording intact. S21 accepts a free
name, **Enter** saves, **Esc** returns without saving.

**F3** on the desk lists saved goals by name; arrows select and scroll, **Enter** opens S15's saved-goal menu, and
*play* opens S17. **Esc** returns through the menu and list to the desk. The saved goal keeps the exact samples,
countries, score, minute, scorer, kits and role display. Its menu freezes the kick-off lineups. The recording is
read only: live tactics, players, tournament and match-stat actions are absent because it has no career to inspect
or change. **Esc/Enter** during saved playback return to the menu.

At a watched match's full time, S20 asks *Do you want to save the match summary?* **Y** opens S21 for a name; **N**
continues to the full-time menu. **F4** on the desk lists the named summaries; **Enter** shows the saved S20, **Esc**
returns. The record freezes the counts, bars, score, scorer names, minutes, man of the match, countries and kits, so
loading another career does not change what it shows. A quick result has no summary-save question.

`test_ui_replay_t181` checks bounded recording, every replayed paint in order, the manual/automatic/quick paths,
named-goal F3 playback, atomic replacement, damaged-file refusal and F4's frozen board. Its slow case plays an actual
watched match with replay and compares the published career and result to the same bridge match with the same
answers. `python -m goal2.ui --screenshot DIR` adds the goal questions, replay, name boxes, summary question,
saved-goal menu and F3/F4 lists.

### Returning from a stopped match

[confirmed: original0791:ED8A; measurements/610-live-team-tactics/original-esc-v1; owner #610/#612] Esc returns from player tactics to the squad, and from the squad to the match menu. At an active pause, half-time, substitution or extra-time menu, Esc resumes through the same XI validation as Play. Before kick-off and after full time, Esc selects and explains Play/Exit. A held Esc/Enter does not repeat across these transitions; directional repeats and later discrete key presses remain usable. Stop arrival consumes the outstanding “bench requested” status; dropped/failed requests and match cancellation cannot retain that obsolete note. Pending edits keep their screen until the engine confirms or refuses them. The manual/player-card audit (#611) remains separate required work.

[designed: owner611; T193, based on original1771:42BC/T156] Player cards use aligned labelled cells for age/caps/goals/height/foot/performance, then position/club/cards. Fact headings use the red card-heading palette role, attribute labels brown, and values the player-line colour. Facts retain the one text size (`theme.TEXT`), all20roster rows and existing rename/selection/readiness/bench controls. Compact bench spacing allows long card statuses and refusal text to fit at fractional native font metrics. This presentation change does not make saved player data live; that snapshot contract remains separate611 work.

[confirmed: original1771:3827; T192] Player cards display the original1–9 performance stars and leave the0x7FFF sentinel blank. The raw stored word remains available internally; the visible card no longer calls that known encoding undecoded. This display rule does not certify live-match data freshness: #611 separately requires a current engine player-record snapshot.
