"""[designed: owner, 2026-11-09, #667; T210] The screens that are not yet on the 16 x 32 grid or still carry a card.

T210 built the frame (goal2/ui/frame.py: a rule with its lowercase label on it) and the grid check (goal2/ui/grid_check.py:
every rectangle a multiple of the cell, no card). No screen was reflowed in it, so every screen of the window starts here, and
each of the layout tasks that follow (T211 to T214) removes its screens when it lays them out on the grid with frames.

`assert_on_grid` is what a screen's test calls, as the T209 tests call `reflow_pending.assert_fits`:

- a screen that is **not** in `PENDING` must be on the grid with no card (`grid_check.violations` is empty);
- a screen that **is** in `PENDING` is exempt in these ordinary tests: no assertion either way, because how a layout rounds
  depends on the size of the window and on the platform's fonts. That it still violates is checked in dedicated tests at the
  canonical size 1440x1080, on the platform it was measured on (`test_ui_grid_t210.PendingGrid`), so a screen that is on the
  grid now must be removed. The list can only shrink.

A key is a screen class (`DeskScreen`), or a capture name `Class@name` for a screen that violates only in one state or size
(the capture name is looked up first). An entry in `ONLY_ON` violates only on that platform (`sys.platform`). Nothing else about
a test is loosened. The gate for merging the integration branch `ui/foundation-32` into main is
`test_ui_grid_t210.test_grid_pending_is_empty`: it fails while this list is not empty.
"""
import sys

# Screen -> why it is not on the grid yet. [measured: 1440x1080, Qt offscreen on Linux, `grid_check.violations`, the screenshot
# journey] Every screen of the window has widgets off the cell (the title bar, which T210 does not touch, is 77 px high and
# starts at x = 24) and most carry cards (`#box`, `#boxHeading`).
PENDING = {
    "BenchScreen": "220 widgets off the 16 x 38 cell, 8 cards (the title bar's brand and name are off the cell on every screen)",
    "BoardScreen": "69 widgets off the 16 x 38 cell, 7 cards (the title bar's brand and name are off the cell on every screen)",
    "BulletinScreen": "25 widgets off the 16 x 38 cell, 6 cards (the title bar's brand and name are off the cell on every screen)",
    "ChooseScreen": "178 widgets off the 16 x 38 cell, 6 cards (the title bar's brand and name are off the cell on every screen)",
    "CountryScreen": "174 widgets off the 16 x 38 cell, 11 cards (the title bar's brand and name are off the cell on every screen)",
    "CountryTacticsScreen": "not in the journey: the desk walk reaches it; the title bar is off the cell and it carries cards, as every screen does",
    "FixturesScreen": "126 widgets off the 16 x 38 cell, 2 cards (the title bar's brand and name are off the cell on every screen)",
    "FriendlyScreen": "83 widgets off the 16 x 38 cell, 4 cards (the title bar's brand and name are off the cell on every screen)",
    "HelpScreen": "24 widgets off the 16 x 38 cell, 0 cards (the title bar's brand and name are off the cell on every screen)",
    "HistoryScreen": "47 widgets off the 16 x 38 cell, 12 cards (the title bar's brand and name are off the cell on every screen)",
    "HomeScreen": "12 widgets off the 16 x 38 cell, 1 card (the title bar's brand and name are off the cell on every screen)",
    "ImportScreen": "33 widgets off the 16 x 38 cell, 1 card (the title bar's brand and name are off the cell on every screen)",
    "MenuScreen": "120 widgets off the 16 x 38 cell, 5 cards (the title bar's brand and name are off the cell on every screen)",
    "NewGameScreen": "42 widgets off the 16 x 38 cell, 2 cards (the title bar's brand and name are off the cell on every screen)",
    "PitchScreen": "48 widgets off the 16 x 38 cell, 3 cards (the title bar's brand and name are off the cell on every screen)",
    "PlayerTacticsScreen": "188 widgets off the 16 x 38 cell, 8 cards (the title bar's brand and name are off the cell on every screen)",
    "PlayersScreen": "199 widgets off the 16 x 38 cell, 6 cards (the title bar's brand and name are off the cell on every screen)",
    "QuestionScreen": "23 widgets off the 16 x 38 cell, 0 cards (the title bar's brand and name are off the cell on every screen)",
    "RecordingNameScreen": "23 widgets off the 16 x 38 cell, 0 cards (the title bar's brand and name are off the cell on every screen)",
    "RecordingsScreen": "26 widgets off the 16 x 38 cell, 2 cards (the title bar's brand and name are off the cell on every screen)",
    "ReimportScreen": "not in the journey: the desk walk reaches it; the title bar is off the cell and it carries cards, as every screen does",
    "RoundScreen": "85 widgets off the 16 x 38 cell, 2 cards (the title bar's brand and name are off the cell on every screen)",
    "SaveScreen": "24 widgets off the 16 x 38 cell, 0 cards (the title bar's brand and name are off the cell on every screen)",
    "SavedGoalMenu": "51 widgets off the 16 x 38 cell, 6 cards (the title bar's brand and name are off the cell on every screen)",
    "SavedPitchScreen": "48 widgets off the 16 x 38 cell, 3 cards (the title bar's brand and name are off the cell on every screen)",
    "SquadScreen": "211 widgets off the 16 x 38 cell, 6 cards (the title bar's brand and name are off the cell on every screen)",
    "StartScreen": "77 widgets off the 16 x 38 cell, 11 cards (the title bar's brand and name are off the cell on every screen)",
    "TeamInfoScreen": "163 widgets off the 16 x 38 cell, 10 cards (the title bar's brand and name are off the cell on every screen)",
    "TeamPlayersScreen": "not in the journey: the desk walk reaches it; the title bar is off the cell and it carries cards, as every screen does",
    "TeamTacticsScreen": "169 widgets off the 16 x 38 cell, 8 cards (the title bar's brand and name are off the cell on every screen)",
    "TournamentScreen": "141 widgets off the 16 x 38 cell, 4 cards (the title bar's brand and name are off the cell on every screen)",
}

# The entries that violate only on one platform (`sys.platform`).
ONLY_ON = {}


def screen_keys(window, capture=None):
    """The keys under which `window`'s current screen may be listed, most specific first. `capture` names what the screen
    shows when one class has several states and only some violate."""
    if capture is not None:
        return [capture]
    current = getattr(window, "current", None)
    screen = current() if current is not None else None
    name = type(screen).__name__ if screen is not None else type(window).__name__
    return [f"{name}@{window.width()}x{window.height()}", name]


def listed(window, capture=None):
    """The `PENDING` key that covers `window`'s current screen here, or None."""
    return next((key for key in screen_keys(window, capture)
                 if key in PENDING and ONLY_ON.get(key, sys.platform) == sys.platform), None)


def listed_name(name):
    """The `PENDING` key for the screen class `name` here (as a class, whatever its capture), or None."""
    return next((key for key in PENDING if key.split("@")[0] == name and ONLY_ON.get(key, sys.platform) == sys.platform), None)


def assert_on_grid(testcase, window, message=None, capture=None):
    """`assertEqual(grid_check.violations(window), [])`, except for a screen listed in `PENDING`, which is exempt."""
    from goal2.ui import grid_check   # here, not at import: a module without PySide6 is skipped, not an error
    if listed(window, capture) is not None:
        return
    where = f"{screen_keys(window, capture)[0]}" + (f" {message}" if message is not None else "")
    testcase.assertEqual(grid_check.violations(window), [], where)
