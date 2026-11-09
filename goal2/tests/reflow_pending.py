"""[designed: owner, 2026-11-09, #667; T209] The screens that do not yet fit the 90 x 28 page at the one 32 px text.

T209 made the cell 16 x 32 and the text one size; a screen composed for 24 px text and a 1440 x 900 page does not fit
the page any more (`fixed_page.problems` is not empty). Each such screen is a layout task (T210 and its successors) and
is listed here, with the reason measured at 1440 x 1080 (the page at scale 1, `tools/ui_readability_screenshots.py`),
and **never** fixed by shrinking, clipping or dropping text.

The tests that used to assert `fixed_page.problems(window) == []` call `assert_fits` instead:

- a screen that is **not** in `PENDING` must have no problems, as before;
- a screen that **is** in `PENDING` passes only while it really still has problems, so a screen that now fits fails the
  test until its entry is removed. The list can only shrink.

A key is a screen class (`DeskScreen`), or a capture name `Class@WIDTHxHEIGHT` (the window's size) for a screen that
overflows at some sizes only; the capture name is looked up first. Nothing else about a test is loosened: no threshold
moves and nothing is skipped. The gate for merging the integration branch `ui/foundation-32` into main is
`goal2.tests.test_ui_cell_t209.PendingReflow.test_pending_reflow_is_empty`: it fails while this list is not empty.
"""

# Screen -> why it does not fit yet. The text is the screen-level problem at 1440x1080: the size the screen needs
# ("squeezed below WxH") against the page it has.
PENDING = {
    "ImportScreen": "box 1260x648 squeezed below 1315x648",
    "StartScreen": "optionText text needs 76 px, has 42",
    "FriendlyScreen": "screen 1440x1080 squeezed below 1064x1111",
    "NewGameScreen": "box 900x793 squeezed below 903x537",
    "PlayersScreen": "screen 1440x1080 squeezed below 1132x1119",
    "CountryScreen": "screen 1440x1080 squeezed below 1688x1176",
    "DeskScreen": "screen 1440x1080 squeezed below 1531x1203",
    "SquadScreen": "screen 1440x1080 squeezed below 1281x1232",
    "TeamInfoScreen": "screen 1440x1080 squeezed below 1337x1229",
    "FixturesScreen": "screen 1440x1080 squeezed below 1274x1222",
    "TournamentScreen": "screen 1440x1080 squeezed below 1456x938",
    "HistoryScreen": "screen 1440x1080 squeezed below 1444x734",
    "RoundScreen": "screen 1440x1080 squeezed below 1541x937",
    "MenuScreen": "screen 1440x1080 squeezed below 1535x1026",
    "ChooseScreen": "screen 1440x1080 squeezed below 1132x1138",
    "PitchScreen": "screen 1440x1080 squeezed below 1453x1065",
    "BoardScreen": "screen 1440x1080 squeezed below 1416x1088",
    "SavedGoalMenu": "screen 1440x1080 squeezed below 610x1185",
    "SavedPitchScreen": "screen 1440x1080 squeezed below 1453x1065",
    "BenchScreen": "screen 1440x1080 squeezed below 1208x1207",
    "ReimportScreen": "box 1260x648 squeezed below 1538x648",
    "TeamTacticsScreen": "screen 1440x1080 squeezed below 1398x1149",
    "CountryTacticsScreen": "screen 1440x1080 squeezed below 969x1119",
    "PlayerTacticsScreen": "screen 1440x1080 squeezed below 1400x1194",
    "TeamPlayersScreen": "screen 1440x1080 squeezed below 1132x1119",
    "HelpScreen@720x450": "help viewer 311 px high, 69 % of the 450 px page, under the 70 % it must fill (it fits, with no problems)",
}


def screen_keys(window, capture=None):
    """The keys under which `window`'s current screen may be listed, most specific first. `capture` names what the
    screen shows when one class has several states and only some overflow (a name never listed is a screen that fits)."""
    if capture is not None:
        return [capture]
    current = getattr(window, "current", None)
    screen = current() if current is not None else None
    name = type(screen).__name__ if screen is not None else type(window).__name__
    return [f"{name}@{window.width()}x{window.height()}", name]


def listed(window, capture=None):
    """The `PENDING` key that covers `window`'s current screen at its size, or None."""
    return next((key for key in screen_keys(window, capture) if key in PENDING), None)


def assert_fits(testcase, window, message=None, capture=None):
    """`assertEqual(fixed_page.problems(window), [])`, except for a screen listed in `PENDING`, which must still
    have problems (the list can only shrink)."""
    from goal2.desktop import fixed_page   # here, not at import: a module without PySide6 is skipped, not an error
    found = fixed_page.problems(window)
    key = listed(window, capture)
    where = f"{screen_keys(window, capture)[0]}" + (f" {message}" if message is not None else "")
    if key is None:
        testcase.assertEqual(found, [], where)
    else:
        testcase.assertNotEqual(
            found, [], f"{where}: listed in reflow_pending.PENDING ({PENDING[key]}) but now fits; remove it")


def assert_fills(testcase, window, widget, fraction, message=None):
    """`assertGreaterEqual(widget.height(), fraction * window.page.height(), message)`, except for a screen listed in
    `PENDING`, where the widget must still fall short."""
    need, have = fraction * window.page.height(), widget.height()
    key = listed(window)
    where = f"{screen_keys(window)[0]}" + (f" {message}" if message is not None else "")
    if key is None:
        testcase.assertGreaterEqual(have, need, where)
    else:
        testcase.assertLess(have, need, f"{where}: listed in reflow_pending.PENDING ({PENDING[key]}) but now fills; remove it")


def assert_room(testcase, window, have, need, message=None):
    """`assertGreaterEqual(have, need, message)` for a size a screen's own layout must give a widget (a row of cells is as
    wide as its glyphs), except for a screen listed in `PENDING`: it overflows, so its widgets are squeezed (the same
    exemption as `assert_fits`, whose call in the same step still requires the overflow)."""
    where = f"{screen_keys(window)[0]}" + (f" {message}" if message is not None else "")
    if listed(window) is None:
        testcase.assertGreaterEqual(have, need, where)
