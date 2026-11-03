# The new window (`goal2/ui`)

The rebuilt UI of [the design](design/ui-2026-11/README.md), in PySide6 widgets ([the technology](design/technology-2026-11/README.md),
the owner's decision D1, #527). It is built beside today's window, `goal2/desktop`, which stays the shipped window
and the portable build's default until T169 switches over. [designed: owner, 2026-11-03, #526, #527, #536]

    python -m goal2.ui [--data-root DIR]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

It opens S01 while the per-user data folder lacks a file the new window needs, otherwise S02 Start. `--data-root`
names the per-user goal2 folder (its `data` holds the imported files). `--screenshot` writes PNGs at 1440×900 from a
temporary data folder of its own and exits: S01, the placeholder home and S22 (with a stand-in help text) always;
S02 with two saves, S03, S04 with the name line, S05 with stand-in pages (labelled so) and the home with the new
career when it finds GOAL.DAT and the template in the data root's `data` or in a checkout's `.cache/`.

## The journey

[designed: owner, 2026-11-03, #526, #527; T163, #537] S01 → S02 → (N) S03 → S04 → home, or S02 → (Enter or Y)
home, as the design's [section 1](design/ui-2026-11/README.md#1-the-players-journey). The screens run over the
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
- **Bulletins** [designed: owner, 2026-11-03, #509]: the Python route has none yet, so a new career goes from S04
  straight home; `Window.open_career(model, pages)` shows S05 first for a career that supplies pages.
- **The home** is a placeholder with the career's summary until T164 builds the desk (S06).

## Saved games

[designed: owner decisions 4 and 8, #526; T163] Saves live in the data root's `saves` folder, one file per save,
`<derived name>.g2game`: a zip holding `goal2-save.json` (`{"format": "goal2-named-save", "version": 1, "name",
"saved"}`: the free name, at most 32 characters, and the time, ISO 8601 with its zone) and `session.g2save`, the
model's own session save byte for byte. The file name is derived from the free name (letters, digits, `-`, `_`; a
name Windows reserves gets `-save`; `-2`, `-3`… when another name derives the same), and S02 lists the stored name.
A save is read only by the model's validating loader (`DesktopModel.from_save`). `goal2/ui/saves.py` reads and writes
the format; T168 adds saving under a name from the desk.

## The parts

| Module | What it holds |
| --- | --- |
| `goal2/ui/theme.py` | The palette, one named constant per role of the design's §3 table (`PALETTE` is the table); the vendored font, loaded with `QFontDatabase` from `goal2/ui/fonts/`; the text sizes (16 px, the font's 8×16 cell, and 32 px); the style sheet. |
| `goal2/ui/fonts/` | "PxPlus IBM VGA 8x16" (CC BY-SA 4.0) with its `LICENSE.TXT` and `PROVENANCE.md`; package data, so the wheel and the portable build carry the licence beside the font. |
| `goal2/ui/window.py` | `Window`: one main window holding one screen at a time on a stack. |
| `goal2/ui/screen.py` | `Screen`, the base class of every screen. |
| `goal2/ui/s01_import.py` | S01 Import your data, over `data_setup`'s check and copy. |
| `goal2/ui/s22_help.py` | S22 Help: the imported GOAL.HLP, over the screen F1 was pressed on, in a box that fills most of the screen (owner decision 13). |
| `goal2/ui/home.py` | The placeholder home screen: the open career's summary, until T164's desk. |
| `goal2/ui/s02_start.py` | S02 Start: Continue, the named saves, Y load, N new game, a failed load's Y/N. |
| `goal2/ui/s03_new_game.py` | S03 New game: 1–6 managers (2–6 later, #551), the optional starting year by NG-9. |
| `goal2/ui/s04_country.py` | S04 Country and name: the card, the list in groups of 16, Ins, the name line; `PlayersScreen`, the twenty read only (Space). |
| `goal2/ui/s05_bulletin.py` | S05 Bulletin: pages *n of m*, any key onward. |
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
against its key, S01 and S22, offscreen. `goal2/tests/test_ui_start_t163.py` visits the journey from S02 to home
against the model's own careers, the start year, the managers, S04's keys, named saves, S01's manifest, S22's size
and S05's pages; its careers read GOAL.DAT and the template from `.cache/` and skip without them. It writes stand-in data files and a stand-in help text into temporary
folders: no byte of the original's files is in the tests (CLAUDE.md rule 14).
