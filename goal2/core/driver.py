"""The driver: the player's actions as the original's own key presses, through the screen catalogue (T105, G10).

[designed: owner, 2026-10-22, #308, #321; docs/redesign-253/vision-reconciliation.md decision 7] The desktop (and
later the bot) moves the original from one screen to another only by pressing the keys the original reads. The
driver is that one path:

    from goal2.core import Core
    from goal2.core.driver import Driver
    driver = Driver(Core.start(savestate).core)
    driver.to_menu()                 # from the team-info browser of a new game: Esc
    wait = driver.goto("tournament") # Down, Down, Enter from the manager menu
    driver.back()                    # Esc, to the manager menu

- [designed] Every key it sends is one the current kind accepts (`goal2/core/screens.py` KINDS, the screen rows of
  goal2-archaeology `static/screens/catalogue.tsv` and the hints goal2 kinds print); anything else is refused with
  `RefusedKey` before the original sees it.
- [designed] A screen it does not expect after a key stops it with `UnexpectedScreen` (the kind, the site and the
  text page); a site the table does not know stops the core itself with `UnknownScreen` (docs/core.md). It never
  guesses and never presses on.
- [designed] It is deterministic: it reads only the wait's kind and view (the screen's cursor, read from memory),
  so the same calls give the same keys (`log`).

[confirmed: named/seg_000E_05.c main_menu_loop 000E:7439] The manager menu's item is DS:00B0 (1..6), moved by
u214b_menu_move_word_wrap(6, 0xB0) on Up and Down; Enter on item 2 calls the fixture list 000E:0000, on item 3
the tournament 1771:958D(country, ..., 1), on item 4 country_list_screen(3), whose first screen is the managed
country's history (1771:1D5C) and whose Esc returns to the menu.
"""
from __future__ import annotations

from goal2.core.runner import CoreError
from goal2.core import screens as _screens
from goal2.core.screens import DOWN, ESCAPE, RETURN, UP


class DriverError(CoreError):
    """The driver was asked for something the original's screens do not offer from where it is."""


class RefusedKey(DriverError):
    """A key the current screen kind does not accept: never pressed."""

    def __init__(self, kind, key):
        self.kind, self.key = kind, key
        super().__init__(f"{kind} does not accept the key {key:#04x}; the driver never presses it")


class UnexpectedScreen(DriverError):
    """After a key the original shows a screen the driver did not expect: it stops, naming the kind, site and text."""

    def __init__(self, expected, wait):
        self.expected, self.kind, self.site, self.text = tuple(expected), wait.kind, wait.site, wait.text
        super().__init__(f"expected {' or '.join(self.expected)}, the original shows {wait.kind} at {wait.site}\n"
                         f"{wait.text}")


MENU = "manager-menu"
# [confirmed: main_menu_loop 000E:7439 (above); the kinds of goal2/core/screens.py] Each route of the manager menu:
# its item, the kinds Enter may show (the fixture list's kind depends on its highlighted fixture, 000E:0000), and the
# kinds Esc passes on the way back to the menu.
ROUTES = {
    "fixture-list": (2, ("fixture-list", "fixtures-watch", "fixtures-auto")),
    "tournament": (3, ("tournament",)),
    "history": (4, ("history",)),
}
# The way back by Esc from each kind the routes reach: the kind Esc shows next.
BACK = {"fixture-list": MENU, "fixtures-watch": MENU, "fixtures-auto": MENU, "tournament": MENU,
        "history": "history-browse", "history-browse": MENU, "team-info": MENU}


class Driver:
    """Presses keys into a Core (`core.wait` is where it is). `log` lists (kind, key) of every key it pressed."""

    def __init__(self, core):
        self.core = core
        self.log = []

    @property
    def wait(self):
        return self.core.wait

    def press(self, key, expect=None):
        """Press `key` if the current kind accepts it (else RefusedKey); with `expect`, the kinds the next screen
        may be (else UnexpectedScreen). Returns the new wait."""
        wait = self.core.wait
        if wait is None:
            raise DriverError("the original is not waiting for a key")
        key = ord(key) if isinstance(key, str) else int(key)
        kind = _screens.KINDS.get(wait.kind)
        if kind is None or kind.polled or not kind.accepts(key):
            raise RefusedKey(wait.kind, key)
        self.log.append((wait.kind, key))
        new = self.core.press(key)
        if expect is not None and new.kind not in expect:
            raise UnexpectedScreen(expect, new)
        return new

    def to_menu(self):
        """Back to the manager menu by Esc from a screen the routes know (BACK); refuses any other."""
        for _ in range(len(BACK) + 1):
            wait = self.core.wait
            if wait.kind == MENU:
                return wait
            if wait.kind not in BACK:
                raise DriverError(f"no known way back to the manager menu from {wait.kind} at {wait.site}\n{wait.text}")
            self.press(ESCAPE, expect=(BACK[wait.kind],))
        raise DriverError("the way back to the manager menu did not end")      # BACK has no cycle

    back = to_menu

    def select(self, item):
        """Move the manager menu's highlight to `item` (1..6) by Down or Up, the shorter way without wrapping."""
        wait = self.core.wait
        if wait.kind != MENU:
            raise UnexpectedScreen((MENU,), wait)
        if not 1 <= item <= len(_screens.MANAGER_NAMES):
            raise DriverError(f"the manager menu has items 1..{len(_screens.MANAGER_NAMES)}, not {item}")
        while wait.view["item"] != item:
            wait = self.press(DOWN if wait.view["item"] < item else UP, expect=(MENU,))
        return wait

    def goto(self, kind):
        """From the manager menu to the screen `kind` (a key of ROUTES) by the menu's own keys; returns its wait."""
        if kind not in ROUTES:
            raise DriverError(f"the driver has no route to {kind!r}; it knows {', '.join(ROUTES)}")
        item, shows = ROUTES[kind]
        self.select(item)
        return self.press(RETURN, expect=shows)
