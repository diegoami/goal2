"""The driver: the player's actions as the original's own key presses, through the screen catalogue (T105, #308's G11).

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
u214b_menu_move_word_wrap(6, 0xB0) on Up and Down; Enter on item 1 calls country_list_screen(1) (team info), on item 2 calls the fixture list 000E:0000, on item 3
the tournament 1771:958D(country, ..., 1), on item 4 country_list_screen(3), whose first screen is the managed
country's history (1771:1D5C) and whose Esc returns to the menu.
"""
from __future__ import annotations

from goal2.core.runner import CoreError
from goal2.core import screens as _screens
from goal2.core.screens import DOWN, ESCAPE, LEFT, RETURN, RIGHT, UP


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
    "team-info": (1, ("team-info",)),
    "fixture-list": (2, ("fixture-list", "fixtures-watch", "fixtures-auto")),
    "tournament": (3, ("tournament",)),
    "history": (4, ("history",)),
}
# The way back by Esc from each kind the routes reach: the kind Esc shows next.
BACK = {"fixture-list": MENU, "fixtures-watch": MENU, "fixtures-auto": MENU, "tournament": MENU,
        "history": "history-browse", "history-browse": MENU, "team-info": MENU}


class Driver:
    """Presses keys into a Core (`core.wait` is where it is). `log` lists (kind, key) of every key it pressed and every
    queued key the original read, in the order the original read them."""

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
        # [designed: T106] keys the original read from the queue on the way (a polled screen's), in its order
        self.log.extend((p.kind, k) for p in new.passed for k in p.keys)
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

    # -- the new game (T106) -----------------------------------------------------------------------------------------
    def new_game(self, country, manager_name, managers=1, on_bulletin=None):
        """Play the original's new game by its own keys, from wherever the core is on its way (the title's load
        question, the player count, the country browser) to the first manager menu; returns that wait.

        [confirmed: F032, E038-r0001's keys `n Enter Enter b o b Enter Enter Enter`; catalogue.tsv's screen rows]
        N at the load question; the player count by Left and Right (manager_count_menu 1771:0021 turns them into Up
        and Down over DS:0C4E), Enter; the country by the browser's arrows (`_browse`), Enter; the name's letters and
        Enter queued for the polled name entry, which reads each after its poll says a key waits (F032); Enter on
        each bulletin, after `on_bulletin(wait)` when given. [designed: NG-7 traced one manager] Only one manager:
        a new game of several managers is a path the archaeology has not traced, refused here.
        `manager_name`: what the player types (1..14 characters, ASCII 32..126); the line editor 1771:09A0 keeps
        the first as the initial, upper-cased, and the rest after one blank or one other character as the surname."""
        if managers != 1:
            raise DriverError("the new game is traced for one manager only (NG-7); several managers are not served")
        if not isinstance(manager_name, str) or not 1 <= len(manager_name) <= 14 or \
                any(not 0x20 <= ord(ch) < 0x7F for ch in manager_name):
            raise DriverError(f"a manager's name is 1..14 characters of ASCII 32..126, not {manager_name!r}")
        wait = self.core.wait
        if wait.kind == "title-load-prompt":
            wait = self.press("n", expect=("title-player-count",))
        if wait.kind == "title-player-count":
            while wait.view["managers"] != managers:
                wait = self.press(LEFT if wait.view["managers"] > managers else RIGHT, expect=("title-player-count",))
            wait = self.press(RETURN, expect=("country-select",))
        if wait.kind != "country-select":
            raise UnexpectedScreen(("title-load-prompt", "title-player-count", "country-select"), wait)
        self._browse(country)
        for ch in manager_name + "\r":
            self.queue("country-select-name-entry", ord(ch))
        wait = self.press(RETURN, expect=("bulletin",))
        for _ in range(8):                      # [designed] a bound: one manager's new game shows two (F032)
            if wait.kind != "bulletin":
                return wait
            if on_bulletin is not None:
                on_bulletin(wait)
            wait = self.press(RETURN, expect=("bulletin", MENU))
        raise DriverError("the new game's bulletins did not end")

    def queue(self, kind, key):
        """Queue `key` for the next poll of the polled screen `kind` (Core.queue); `log` lists it when the original
        reads it (press)."""
        key = ord(key) if isinstance(key, str) else int(key)
        k = _screens.KINDS.get(kind)
        if k is None or not k.accepts(key):
            raise RefusedKey(kind, key)
        self.core.queue(kind, key)

    def _browse(self, country):
        """Move the country browser to `country` by its arrows [confirmed: named/seg_1771_02.c 26B9]: Left and Right
        move the column DS:0DB4 by 16 keeping the row; Up and Down move the row DS:0DB6 within the column."""
        from goal2.core import views
        wait = self.core.wait
        order = [c["country"] for c in views.country_select(wait.state)["countries"]]
        if country not in order:
            raise DriverError(f"the browser lists no country {country}")
        target = order.index(country) + 1
        top, row = (target - 1) // 16 * 16 + 1, (target - 1) % 16 + 1
        while wait.view["top"] != top:
            wait = self.press(RIGHT if wait.view["top"] < top else LEFT, expect=("country-select",))
        while wait.view["row"] != row:
            wait = self.press(DOWN if wait.view["row"] < row else UP, expect=("country-select",))
        if wait.view["country"] != country:
            raise DriverError(f"the browser shows country {wait.view['country']}, not {country}")
        return wait
