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
from goal2.core.screens import DOWN, ESCAPE, F2, LEFT, RETURN, RIGHT, UP


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
    "select-squad": (5, ("select-squad",)),     # [T107] main_menu_loop item 5: select_team_screen (000E:771A)
}
# The way back by Esc from each kind the routes reach: the kinds Esc may show next.
# [T107; confirmed: named/seg_0791_12.c E44F, seg_1771_04.c 4B61, seg_1771_02.c 1981] Esc on the pool list turns
# into Left (it shows the squad list); Esc on the squad list leaves SELECT YOUR TEAM; Esc leaves a player's own
# tactics for the list he was chosen from, and the team tactics for the browser that opened them. [confirmed:
# code/seg_0791_22.asm E641-E657] Esc while a player is marked only unmarks him (the list stays).
BACK = {"fixture-list": (MENU,), "fixtures-watch": (MENU,), "fixtures-auto": (MENU,), "tournament": (MENU,),
        "history": ("history-browse",), "history-browse": (MENU,), "team-info": (MENU,),
        "select-squad": (MENU, "select-squad"), "select-squad-pool": ("select-squad", "select-squad-pool"),
        "own-tactics": ("select-squad", "select-squad-pool"), "team-tactics": ("team-info",)}
SQUAD, POOL_LIST = "select-squad", "select-squad-pool"
MAX_MOVES = 100              # [designed] cursor moves allowed for one target: the longest list is the pool's 80


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
            self.press(ESCAPE, expect=BACK[wait.kind])
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

    # -- the Team and Pool route (T107) -----------------------------------------------------------------------------
    # [designed: owner, 2026-10-22, #308; T107] Each team action starts at the manager menu, presses the original's own
    # keys on SELECT YOUR TEAM (0791:E44F), a player's own tactics (1771:4B61) or the team tactics (1771:1981), reads
    # the screen's state (the cursor, the marked player, the record a key changed) before each key, and returns to the
    # manager menu. The method is the vendored kit's closed loop (goal2/engine/original_match/screens.py, PROVENANCE.md),
    # whose match-only plans it does not use. It never writes a byte; a key a screen does not list is refused (press).
    def _menu_first(self):
        if self.core.wait.kind != MENU:
            raise UnexpectedScreen((MENU,), self.core.wait)

    def _move(self, current, target, key_down=DOWN, key_up=UP, expect=None):
        """One cursor step toward `target`, the kinds the screen may then show in `expect`."""
        return self.press(key_down if target > current else key_up, expect=expect)

    def _team(self):
        from goal2.core import views
        return [row["player"] for row in views.team(self.core.wait.state)["squad"]]

    def _pool(self):
        from goal2.core import views
        return [row["player"] for row in views.pool(self.core.wait.state)["rows"]]

    def _to_player(self, player):
        """On SELECT YOUR TEAM, highlight `player` on the list that holds him (Left or Right toggles the lists;
        the squad cursor DS:0C1B, the pool's top and row, 214B:15B1): returns the wait."""
        wait = self.core.wait
        squad, pool = self._team(), self._pool()
        if player in squad:
            side, target = 1, squad.index(player) + 1
        elif player in pool:
            side, target = 2, pool.index(player) + 1
        else:
            raise DriverError(f"player {player} is neither in the managed squad nor in the manager's pool")
        if wait.view["side"] != side:
            wait = self.press(LEFT, expect=(SQUAD, POOL_LIST))
        field = "slot" if side == 1 else "item"
        for _ in range(MAX_MOVES):
            if wait.view[field] == target:
                if wait.view["player"] != player:
                    raise DriverError(f"the list shows player {wait.view['player']} where {player} was read")
                return wait
            wait = self._move(wait.view[field], target, expect=(wait.kind,))
        raise DriverError(f"the cursor did not reach player {player}")

    def _open_squad(self):
        self._menu_first()
        return self.goto("select-squad")

    def swap(self, a, b):
        """Swap squad players `a` and `b` (eleven and bench, or two of either) on SELECT YOUR TEAM: Enter on one
        marks him, Enter on the other swaps their squad words, and the original then sorts the squad by position
        (0791:DEA6, sort_squad_by_position: the squad list asks no gate, F031 C25). Returns the squad after it."""
        self._menu_first()
        squad = self._team()
        if a == b or a not in squad or b not in squad:
            raise DriverError(f"swap needs two different players of the managed squad, not {a} and {b}")
        self._open_squad()
        self._to_player(a)
        wait = self.press(RETURN, expect=(SQUAD,))
        if wait.view["marked"] != (1, squad.index(a) + 1):
            raise DriverError(f"the original did not mark player {a}: {wait.view['marked']}")
        self._to_player(b)
        self.press(RETURN, expect=(SQUAD,))
        self.to_menu()
        return self._team()

    def exchange(self, squad_player, pool_player):
        """Exchange a squad player with a pool player: Enter on the squad player, Left to the pool list, Enter on the
        pool player. With the pool list up the original asks 0791:DBFA first (F031): it refuses "during finals" or
        "whilst on tour" in a message box (squad-change-refused), which a key closes. Returns {"refused": None or the
        original's message, "squad": ..., "pool": ...}."""
        self._menu_first()
        if squad_player not in self._team() or pool_player not in self._pool():
            raise DriverError(f"exchange needs a squad player and a pool player, not {squad_player} and {pool_player}")
        self._open_squad()
        self._to_player(squad_player)
        wait = self.press(RETURN, expect=(SQUAD,))
        if wait.view["marked"] is None:
            raise DriverError(f"the original did not mark player {squad_player}")
        self._to_player(pool_player)
        wait = self.press(RETURN, expect=(POOL_LIST, "squad-change-refused"))
        refused = None
        if wait.kind == "squad-change-refused":
            refused = wait.view["message"]
            self.press(RETURN, expect=(POOL_LIST,))
        self.to_menu()
        return {"refused": refused, "squad": self._team(), "pool": self._pool()}

    def set_position(self, player, code):
        """Set the position +6 of a squad or pool player: C when `code` is his club position +7 (1771:4952 copies
        it), else R, each a step +1 wrapping 0..13 (1771:4925), until +6 is `code`."""
        from goal2.core import views
        if not 0 <= code <= 13:
            raise DriverError(f"a position code is 0..13, not {code}")
        self._open_squad()
        wait = self._to_player(player)
        card = views.player_card(wait.state, player)
        if card["position"] != code and card["club_position"] == code:
            wait = self.press("c", expect=(wait.kind,))
        for _ in range(14):
            if views.player_card(wait.state, player)["position"] == code:
                break
            wait = self.press("r", expect=(wait.kind,))
        else:
            raise DriverError(f"position {code} was not reached")
        self.to_menu()
        return views.player_card(self.core.wait.state, player)

    def _own_tactics(self, player):
        self._open_squad()
        self._to_player(player)
        return self.press("t", expect=("own-tactics",))

    def set_own_tactic(self, player, element, value):
        """Set a player's own setting of tactic `element` 1..4 to `value` (True, False, or None for the team's) on
        his own tactics (1771:4B61): Enter on row e cycles no own setting, his own with e clear, his own with e set."""
        from goal2.core import views
        if element not in (1, 2, 3, 4) or value not in (None, False, True):
            raise DriverError(f"own tactics are elements 1..4 set to True, False or None, not {element}={value!r}")
        wait = self._own_tactics(player)
        for _ in range(MAX_MOVES):
            if wait.view["row"] == element:
                break
            wait = self._move(wait.view["row"], element, expect=("own-tactics",))

        def state(w):
            r = views.player_card(w.state, player)["own_tactics"]
            return None if not r >> (element + 3) & 1 else bool(r >> (element - 1) & 1)
        for _ in range(3):
            if state(wait) == value:
                break
            wait = self.press(RETURN, expect=("own-tactics",))
        else:
            raise DriverError(f"own tactic {element} did not reach {value!r}")
        self.to_menu()
        return views.player_card(self.core.wait.state, player)

    def set_marking(self, player, opponent):
        """Man-mark `opponent` with `player`: row 5 of his own tactics (1771:4B61 calls 1771:49B8 on it). The original
        offers that row only with a match set up (4B61's row count cVar1 + 4); on the manager menu's route it shows
        four rows, so the driver refuses, after Esc, naming the original's rows."""
        wait = self._own_tactics(player)
        rows = wait.view["rows"]
        self.to_menu()
        if rows < 5:
            raise DriverError(f"the original's own tactics show {rows} rows here: man-marking (row 5) is offered only "
                              f"with a match set up (1771:4B61), so {player} cannot mark {opponent} from the menu")
        raise DriverError("man-marking in a match is the match flow's (G14)")

    def rename(self, player, text):
        """F2's new name (1771:4859): the line editor 214B:1086 takes the typed characters (the first replaces the
        old name) and Enter; 4859 keeps the first as the initial and the rest after one blank (or one other
        character), its first letter upper-cased, as the surname when there is one."""
        from goal2.core import views
        if not isinstance(text, str) or not 1 <= len(text) <= 12 or any(not 0x20 <= ord(ch) < 0x7F for ch in text):
            raise DriverError(f"a new name is 1..12 characters of ASCII 32..126, not {text!r}")
        self._open_squad()
        wait = self._to_player(player)
        for ch in text + "\r":
            self.queue("player-name-entry", ord(ch))
        self.press(F2, expect=(wait.kind,))
        self.to_menu()
        return views.Memory(self.core.wait.state).player_name(player)

    def set_tactic(self, element, on):
        """Set element 1..8 of the managed country's team tactics +0x2D on the team tactics screen (1771:1981):
        team info (the manager menu's item 1), the managed country in the browser, T, the row whose element is
        DS:6BBF[row], Enter (it toggles the element, F010), Esc, Esc."""
        from goal2.core import views
        if element not in range(1, 9):
            raise DriverError(f"a tactic element is 1..8, not {element}")
        self._menu_first()
        country = views.team(self.core.wait.state)["country"]
        self.goto("team-info")
        self._browse_info(country)
        wait = self.press("t", expect=("team-tactics", "team-tactics-view"))
        if wait.kind != "team-tactics":
            raise DriverError(f"the original shows the team tactics of {country} for viewing only")
        rows = views.team_tactics(wait.state, country)["rows"]
        target = next(r["row"] for r in rows if r["element"] == element)
        for _ in range(MAX_MOVES):
            if wait.view["row"] == target:
                break
            wait = self._move(wait.view["row"], target, expect=("team-tactics",))
        if bool(views.team_tactics(wait.state, country)["byte"] >> (element - 1) & 1) != bool(on):
            wait = self.press(RETURN, expect=("team-tactics",))
        self.to_menu()
        return views.team_tactics(self.core.wait.state, country)

    def _browse_info(self, country):
        """The team-info browser to `country` by its arrows (1771:26B9, as _browse; the column DS:0DB4, the row
        DS:0DB6, the order DS:9B56)."""
        from goal2.core import views
        wait = self.core.wait
        for _ in range(MAX_MOVES):
            view = views.country_select(wait.state)
            order = [c["country"] for c in view["countries"]]
            target = order.index(country) + 1
            top, row = (target - 1) // 16 * 16 + 1, (target - 1) % 16 + 1
            if view["top"] != top:
                wait = self.press(RIGHT if view["top"] < top else LEFT, expect=(wait.kind,))
            elif view["row"] != row:
                wait = self.press(DOWN if view["row"] < row else UP, expect=(wait.kind,))
            else:
                if wait.view["country"] != country:
                    raise DriverError(f"the browser shows country {wait.view['country']}, not {country}")
                return wait
        raise DriverError(f"the browser did not reach country {country}")
