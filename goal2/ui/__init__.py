"""goal2's screens. Two parts live in this package:

- **The new window** [designed: owner, 2026-11-03, #526, #527, #536] (docs/ui.md): the rebuilt UI of
  docs/design/ui-2026-11 in PySide6 widgets. `theme` (palette, font, style sheet), `screen` (the `Screen` base
  class), `window` (the main window and its screen stack), `s01_import`, `s22_help`, `home` (a placeholder until
  T163) and `__main__` (`python -m goal2.ui`). It sits beside `goal2/desktop`, which stays the shipped window until
  T169.
- **The terminal screen framework** [confirmed: plan.md, the owner's 2026-10-12 decision]: screens drawn into a
  character grid (80x25 cells: character, foreground, background), never straight to a terminal, with a plain-text
  renderer for tests and logs (`grid`, `plain_renderer`, `input` and the terminal screens `country_select`,
  `squad`, `tactics`, `preview`, `result`, `next_action`). A screen is tested by its grid, not its pixels.

Importing the package needs no Qt: only the new window's modules import PySide6.
"""
