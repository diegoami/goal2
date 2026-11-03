# The new window (`goal2/ui`)

The rebuilt UI of [the design](design/ui-2026-11/README.md), in PySide6 widgets ([the technology](design/technology-2026-11/README.md),
the owner's decision D1, #527). It is built beside today's window, `goal2/desktop`, which stays the shipped window
and the portable build's default until T169 switches over. [designed: owner, 2026-11-03, #526, #527, #536]

    python -m goal2.ui [--data-root DIR]
    QT_QPA_PLATFORM=offscreen python -m goal2.ui --screenshot DIR

It opens S01 while the per-user data folder is not imported (`goal2/desktop/data_setup.py`), otherwise the home
screen, a placeholder until T163 builds S02. `--data-root` names the per-user goal2 folder (its `data` holds the
imported files); `--screenshot` writes PNGs of S01, the home screen and S22 at 1440×900 from a temporary data folder
of its own, with a stand-in help text, and exits.

## The parts

| Module | What it holds |
| --- | --- |
| `goal2/ui/theme.py` | The palette, one named constant per role of the design's §3 table (`PALETTE` is the table); the vendored font, loaded with `QFontDatabase` from `goal2/ui/fonts/`; the text sizes (16 px, the font's 8×16 cell, and 32 px); the style sheet. |
| `goal2/ui/fonts/` | "PxPlus IBM VGA 8x16" (CC BY-SA 4.0) with its `LICENSE.TXT` and `PROVENANCE.md`; package data, so the wheel and the portable build carry the licence beside the font. |
| `goal2/ui/window.py` | `Window`: one main window holding one screen at a time on a stack. |
| `goal2/ui/screen.py` | `Screen`, the base class of every screen. |
| `goal2/ui/s01_import.py` | S01 Import your data, over `data_setup`'s check and copy. |
| `goal2/ui/s22_help.py` | S22 Help: the imported GOAL.HLP, over the screen F1 was pressed on. |
| `goal2/ui/home.py` | The placeholder home screen (T163 replaces it with S02). |

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
  (`window.pop()`). S01 quits, the help closes, the home screen has none;
- **F1**: on every screen but the help itself, it opens S22 over the screen.

Keys and the mouse take one path [designed: owner, 2026-11-03, #526]: a key, a click on an option, a click on a key
of the bottom bar and a click on the Enter hint all reach the same handler.

## The window

`Window.push(screen)` opens a screen over the current one, `pop()` returns to the one underneath and
`replace_home(screen)` empties the stack and starts again from `screen`. Keys go to the current screen
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
against its key, S01 and S22, offscreen. It writes stand-in data files and a stand-in help text into temporary
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
  Enter on the picked player again drops the pick. **Ins** reads *coming later* and only says so, until the
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
