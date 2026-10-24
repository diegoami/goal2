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
    "tournament": (3, ("tournament", "championship-browse")),
    "history": (4, ("history",)),
    "select-squad": (5, ("select-squad",)),     # [T107] main_menu_loop item 5: select_team_screen (000E:771A)
}
# The way back by Esc from each kind the routes reach: the kinds Esc may show next.
# [T107; confirmed: named/seg_0791_12.c E44F, seg_1771_04.c 4B61, seg_1771_02.c 1981] Esc on the pool list turns
# into Left (it shows the squad list); Esc on the squad list leaves SELECT YOUR TEAM; Esc leaves a player's own
# tactics for the list he was chosen from, and the team tactics for the browser that opened them. [confirmed:
# code/seg_0791_22.asm E641-E657] Esc while a player is marked only unmarks him (the list stays).
BACK = {"fixture-list": (MENU,), "fixtures-watch": (MENU,), "fixtures-auto": (MENU,), "tournament": (MENU,),
        "championship-browse": (MENU,),
        "history": ("history-browse",), "history-browse": (MENU,), "team-info": (MENU,),
        "select-squad": (MENU, "select-squad"), "select-squad-pool": ("select-squad", "select-squad-pool"),
        "own-tactics": ("select-squad", "select-squad-pool"), "team-tactics": ("team-info",)}
SQUAD, POOL_LIST = "select-squad", "select-squad-pool"
MAX_NOTICES = 1000           # [designed] a bound on the managed side's notices in one match (53 measured, T108)
SUBSTITUTION = ("squad-substitution-take-off", "squad-substitution-put-on")   # [T108] SELECT TEAM at half time
MAX_MOVES = 100              # [designed] cursor moves allowed for one target: the longest list is the pool's 80


class Driver:
    """Presses keys into a Core (`core.wait` is where it is). `log` lists (kind, key) of every key it pressed and every
    queued key the original read, in the order the original read them."""

    def __init__(self, core):
        self.core = core
        self.log = []
        self.pages = []               # [T108] the round's screens passed: (kind, view)
        self.trail = None             # [T108] a list to keep every wait reached (the tests' text oracle), or None

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
        self.core.stops.add(_screens.TAKER_SELECT)  # [designed: T120] never silently time out a manager's taker
        self.log.append((wait.kind, key))
        new = self.core.press(key)
        # [designed: T106] keys the original read from the queue on the way (a polled screen's), in its order
        self.log.extend((p.kind, k) for p in new.passed for k in p.keys)
        if self.trail is not None:
            self.trail.append(new)
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

    # -- the round (T108) ----------------------------------------------------------------------------------------
    # [designed: owner, 2026-10-22, #308, #331; decision 7] Play next game plays the original's round by its own keys,
    # from the manager menu to the next one. The driver stops only where the original asks the manager (the captain,
    # the half-time menu and its bench, the managed side's substitution notice at a stoppage, an eleven the original
    # refuses) and answers the rest as a manager who only plays: Enter on each "hit any key" screen, N at the watch
    # prompt (the watched match is G14b), R at the first poll of play (the original's quick result, which still stops
    # at half time), no key at the other side's notices. Each screen it passes is kept in `pages` as (kind, view),
    # read from memory at that screen.
    # [confirmed: named/seg_000E_05.c play_round 000E:70B9, route_fixture 6CA7, simulate_fixture 6970,
    # maybe_ask_watch_match 6C21; seg_0791_12.c in_match_menu ED8A, run_match F1F6, first_team_valid EA09;
    # seg_0791_10.c choose_captain_or_taker CC7B; seg_0791_11.c select_team_screen E44F, E022; code/seg_0791_13.asm
    # 7FCF, 8062 (the managed side's notice and the menu it opens)]
    INTERVAL_KINDS = ("match-menu-halftime", "match-menu-extra-time", "match-menu-extra-halftime")
    MATCH_MENU_KINDS = ("match-menu", "match-menu-fulltime") + INTERVAL_KINDS
    # the screens of a round the driver passes with Enter (each prints "hit any key"), and the kinds a key may lead to
    PASSING = ("round-results", "fixture-result", "tournament-table", "championship-bracket", "bulletin", "match-board", "match-summary")
    ROUND_KINDS = PASSING + MATCH_MENU_KINDS + ("match-watch-prompt", "eleven-refused", "substitution-notice",
                                                "captain-select", "match-live", "match-summary-save-prompt", "round-paused",
                                                "shootout-announcement", "shootout-order",
                                                _screens.TAKER_SELECT, _screens.TAKER_PITCH, MENU)
    # the stops of a match the steps return at: the half-time menu, the menu of a stoppage, the managed side's notice
    STOPS = INTERVAL_KINDS + ("substitution-notice", _screens.TAKER_SELECT, _screens.TAKER_PITCH)

    def _page(self, wait):
        from goal2.core import views
        kind = wait.kind
        if kind == "round-results":
            view = views.round_results(wait.state, wait.view["first"], wait.view["last"])
        elif kind == "fixture-result":
            view = views.fixture_result(wait.state)
        elif kind == "tournament-table":
            view = views.tournament(wait.state, **{k:wait.view[k] for k in ('country','world','display')})
            view['selected_group'] = wait.view['group']
        elif kind == "championship-bracket":
            view = views.bracket(wait.state, wait.view['country'], world=wait.view['world'])
        elif kind == "bulletin":
            view = views.bulletin(wait.state)
        elif kind in ("match-board", "match-summary"):
            view = views.board(wait.state)
        else:
            return
        self.pages.append((kind, view))

    def _side_items(self, wait):
        """The managed side's first item of the match menu (ED8A: 1..5 are DS:9B36's side, 6..10 DS:9B34's)."""
        from goal2.core import views
        return 1 if views.match_sides(wait.state)["managed_side"] == 1 else 6

    def _menu_item(self, label):
        """Move the match menu's highlight to the managed side's `label` (MATCH_MENU_ITEMS; play reads 'exit' after
        the match) by Up and Down; returns the wait."""
        wait = self.core.wait
        if wait.kind not in self.MATCH_MENU_KINDS:
            raise UnexpectedScreen(self.MATCH_MENU_KINDS, wait)
        names = list(_screens.MATCH_MENU_ITEMS)
        target = self._side_items(wait) + names.index("play" if label == "exit" else label)
        for _ in range(MAX_MOVES):
            if wait.view["item"] == target:
                return wait
            wait = self.press(DOWN if wait.view["item"] < target else UP, expect=(wait.kind,))
        raise DriverError(f"the match menu's highlight did not reach {label}")

    def stoppage(self):
        """True at the match menu of a stoppage (ED8A called by 0791:8062 at 8100, after the managed side's notice)."""
        wait = self.core.wait
        return wait.kind == "match-menu" and wait.view.get("context") in ("stoppage", "pause")

    def _pass(self, until, watch=False):
        """Enter on each screen of PASSING (keeping its page), N at the watch prompt, no key at the other side's
        substitution notice, until a kind of `until` (or the managed side's notice, or a stoppage's menu)."""
        for _ in range(500):            # [designed] a bound: a round passes a few dozen screens
            wait = self.core.wait
            if wait.kind == "substitution-notice":
                if wait.view.get("managed"):
                    return wait
                self._release()           # the other side's: as with no key (C50C's own timeout)
                continue
            if self.watching and wait.kind in ("match-live", "match-summary-save-prompt"):
                return wait
            if wait.kind in until or wait.kind in ("round-paused", "shootout-announcement", "shootout-order",
                                                  _screens.TAKER_SELECT, _screens.TAKER_PITCH) or self.stoppage():
                return wait
            if wait.kind == "match-watch-prompt":
                # [designed: T109] Watch is the own match's presentation; other-country watch flags are G13.
                self.press("n", expect=self.ROUND_KINDS)
                continue
            if wait.kind not in self.PASSING:
                raise UnexpectedScreen(until, wait)
            self._page(wait)
            self.press(RETURN, expect=self.ROUND_KINDS)
        raise DriverError("the round did not reach " + " or ".join(until))

    def _release(self):
        self.core.stops.add(_screens.TAKER_SELECT)
        wait = self.core.release()
        if self.trail is not None:
            self.trail.append(wait)
        return wait

    def round_start(self, watch=False):
        """From the manager menu, play next game (its item 6, Enter): the original plays the round's other fixtures
        and shows their results; the driver passes them to the own match's menu before the kick-off and returns that
        wait (or the manager menu when the round has no own match). `pages` starts empty here."""
        self._menu_first()
        self.core.stop_at(*(("match-live", "match-summary-save-prompt", "substitution-notice") if watch else ()))
        self.pages = []
        self.select(len(_screens.MANAGER_NAMES))
        self.press(RETURN, expect=self.ROUND_KINDS)
        return self._pass(("match-menu", MENU))

    def round_continue(self):
        """[designed: T115; confirmed: F030, 000E:6BD0 at 53d7ef5] Enter closes the original round's
        PAUSE box; pass subsequent results to the next manager decision, retaining their pages."""
        if self.wait.kind != "round-paused":
            raise UnexpectedScreen(("round-paused",), self.wait)
        self.press(RETURN, expect=self.ROUND_KINDS)
        return self._pass(("match-menu", MENU))

    def shootout_start(self):
        """[designed: T118; confirmed: A132/A180 at 53d7ef5] Original Enter closes the announcement.
        Keep every managed order decision; watch the original's kicks once its order is complete."""
        if self.wait.kind != "shootout-announcement":
            raise UnexpectedScreen(("shootout-announcement",),self.wait)
        self.core.stop_at('match-live','substitution-notice','match-summary-save-prompt')
        return self.press(RETURN,expect=self.ROUND_KINDS)

    def shootout_pick(self, player):
        """[designed: T118; confirmed: 9B93 at 53d7ef5] Navigate to an available unchosen XI player,
        then original Enter appends his pitch slot. The guest consumes its own pushed-back Down."""
        from goal2.core import views
        if self.wait.kind != 'shootout-order':
            raise UnexpectedScreen(('shootout-order',),self.wait)
        order=views.shootout_order(self.wait.state,self.wait.view)
        target=next((p for p in order['players'] if p['player']==player),None)
        if target is None or not target['available'] or target['rank'] is not None:
            raise DriverError('Choose an available XI player who is not already in the shootout order')
        for _ in range(MAX_MOVES):
            current=self.wait.view['slot']
            if current==target['slot']:
                return self.press(RETURN,expect=self.ROUND_KINDS)
            self.press(DOWN if current<target['slot'] else UP,expect=('shootout-order',))
        raise DriverError('The original shootout cursor did not reach the chosen player')

    def shootout_undo(self):
        """[designed: T118; confirmed: 9E65 at 53d7ef5] Original Esc removes the last pick."""
        if self.wait.kind != 'shootout-order':
            raise UnexpectedScreen(('shootout-order',),self.wait)
        return self.press(ESCAPE,expect=('shootout-order',))

    def _play(self):
        """Enter on the menu's play: EA09 may refuse the eleven in a box, which a key closes; returns the original's
        message then, else None."""
        wait = self.press(RETURN, expect=self.ROUND_KINDS)
        if wait.kind == "eleven-refused":
            message = wait.view["message"].strip()
            self.press(RETURN, expect=self.MATCH_MENU_KINDS)
            return message
        return None

    def kick_off(self, captain=None, watch=None, speed=None):
        """At the match menu before the kick-off: play, then the captain prompt (CC7B), then the first half as the
        quick result (R at the first poll of play) to its first stop: the half-time menu, or the managed side's
        substitution notice at a stoppage; returns that wait.

        `captain`: a player of the managed eleven, highlighted by the prompt's own Up and Down (its slot local_7, read
        at each of its polls: Core.stop_at) and taken by Enter; None takes the original's own choice by C
        (best_leader_available 0791:1F3C). [confirmed: F030] The prompt passes by itself after 1000 polls; the
        driver always answers it. When the original refuses the eleven (0791:EA09's message box) the driver closes
        the box (any key) and returns {"refused": the original's message} at the match menu, nothing else pressed.
        Optional `speed` selects 0..5 through original Left/Right keys before the first complete pose."""
        # [designed: owner, T116; confirmed: F030, 0791:9372] A requested speed is original Left/Right input,
        # queued before the first complete pose. Raw callers retain the original speed by default.
        if speed is not None and (type(speed) is not int or not 0 <= speed <= 5):
            raise ValueError('Original match speed is 0..5')
        if watch is not None:
            self.core.stop_at(*(("match-live", "match-summary-save-prompt", "substitution-notice") if watch
                                else ("substitution-notice",)))
        self._menu_item("play")
        if self.core.wait.kind != "match-menu" or self.stoppage():
            raise UnexpectedScreen(("match-menu",), self.core.wait)
        core = self.core
        self._stop("captain-select", "substitution-notice")
        if not self.watching:
            core.queue("match-live", ord("r"))
        try:
            refused = self._play()
            if refused is not None:
                core.unqueue("match-live")
                return {"refused": refused}
            if speed is not None:
                from goal2.core import views
                now = views.match_speed(self.wait.state)
                for _ in range(abs(now-speed)):
                    core.queue('match-live', RIGHT if speed < now else LEFT)
            for _ in range(MAX_MOVES):
                wait = self.core.wait
                if wait.kind != "captain-select":
                    break
                if captain is None:
                    self._press_poll("c")
                    continue
                from goal2.core import views
                eleven = views.match_sides(wait.state)["eleven"]
                if captain not in eleven:
                    raise DriverError(f"player {captain} is not in the managed eleven {eleven}")
                slot = eleven.index(captain) + 1
                self._press_poll(RETURN if wait.view["slot"] == slot else DOWN if wait.view["slot"] < slot else UP)
            else:
                raise DriverError("the captain prompt's highlight did not reach the captain")
            self._stop("substitution-notice")
            return self._pass(self.STOPS)
        finally:
            self._stop("substitution-notice")

    @property
    def watching(self):
        """[designed: T109] Live polling is part of the core save, so a watched round resumes in the same mode."""
        return "match-live" in self.core.stops

    def _stop(self, *kinds):
        self.core.stop_at(*(tuple(kinds) + (("match-live", "match-summary-save-prompt") if self.watching else ())))

    def live_step(self, key=None):
        """[designed: T109] One live poll: no key, or a catalogue key the manager pressed. Stop at the next live
        poll or at the original's next manager decision. Every displayed pose is read before this call."""
        if self.wait.kind != "match-live" or not self.wait.poll:
            raise UnexpectedScreen(("match-live",), self.wait)
        if key is None:
            self.core.stops.add(_screens.TAKER_SELECT)
            wait = self.core.advance()
            if self.trail is not None:
                self.trail.append(wait)
        else:
            self._press_poll(key)
        return self._pass(self.STOPS + ("match-menu-fulltime",))

    def summary_done(self):
        """[designed: T109] Decline the original's DOS summary file; the desktop owns exporting its summary.
        [confirmed: code/seg_0791_23.asm F331-F347] N skips 0791:0A6B's disk writer and continues the round."""
        if self.wait.kind != "match-summary-save-prompt":
            raise UnexpectedScreen(("match-summary-save-prompt",), self.wait)
        self._press_poll("n")
        return self._pass((MENU,))

    def notice(self, bench):
        """At the managed side's substitution notice (0791:7FCF, "SUBSTITUTION OPPORTUNITY press any key"): `bench`
        True presses a key and the original opens its match menu (ED8A from 8062, substitutions now), where
        substitute() and play_on() go on; False lets it pass as with no key (7FCF then takes it as Esc: no menu,
        unless the goalkeeper is unavailable, 80F0) to the next stop; past the full-time menu, as play_on, to the
        manager menu (finish). Returns the wait."""
        wait = self.core.wait
        if wait.kind != "substitution-notice" or not wait.view.get("managed"):
            raise UnexpectedScreen(("substitution-notice",), wait)
        self._stop("substitution-notice")
        if bench:
            self._press_poll(RETURN)
        else:
            self._release()
        wait = self._pass(self.STOPS + ("match-menu-fulltime",))
        return self.finish() if wait.kind == "match-menu-fulltime" else wait

    def _press_poll(self, key):
        """A key at a poll wait (Core.stop_at): the original's next read takes it."""
        wait = self.core.wait
        key = ord(key) if isinstance(key, str) else int(key)
        kind = _screens.KINDS.get(wait.kind)
        if not wait.poll or kind is None or not kind.accepts(key):
            raise RefusedKey(wait.kind, key)
        self.core.stops.add(_screens.TAKER_SELECT)
        self.log.append((wait.kind, key))
        new = self.core.press(key)
        self.log.extend((p.kind, k) for p in new.passed for k in p.keys)
        if self.trail is not None:
            self.trail.append(new)
        return new

    def taker_key(self, key):
        """[confirmed: T88/T89; CC7B at53d7ef5] Original choice key, or None for its remaining timeout.

        Space reaches a real blocking pitch read; its Return reaches the same selector. No host player/budget
        rule chooses a taker. A script must explicitly send C/Enter/Esc or let the original timer pass.
        """
        wait=self.wait
        if wait.kind not in (_screens.TAKER_SELECT,_screens.TAKER_PITCH):
            raise UnexpectedScreen((_screens.TAKER_SELECT,_screens.TAKER_PITCH),wait)
        if key is None and not wait.poll:raise DriverError('The pitch view is a blocking read, not a timeout')
        self._stop('substitution-notice',_screens.TAKER_SELECT)
        if key is None:
            self._release()
        elif wait.poll:self._press_poll(key)
        else:self.press(key,expect=self.ROUND_KINDS)
        return self._pass(self.STOPS+('match-menu-fulltime',))

    def taker_highlight(self, player):
        """[derived: T120] A mouse target is reached through the original Up/Down keys, never a cursor write."""
        from goal2.core import views
        if self.wait.kind!=_screens.TAKER_SELECT:raise UnexpectedScreen((_screens.TAKER_SELECT,),self.wait)
        players=[r['player'] for r in views.taker_choice(self.wait.state,self.wait.view)['players']]
        if player not in players:raise DriverError('The taker must be in this original eleven')
        target=players.index(player)+1
        for _ in range(11):
            if self.wait.view['slot']==target:return self.wait
            self.taker_key(DOWN if self.wait.view['slot']<target else UP)
        raise DriverError('The original taker highlight did not reach its target')

    def _open_bench(self):
        self._menu_item("players")
        return self.press(RETURN, expect=("squad-substitution-take-off", "squad-substitution-put-on",
                                          "substitutions-used", "substitution-request", "substitution-requested", SQUAD))

    def request_substitution(self):
        """[confirmed: named/seg_0791_12.c E44F, DS:4760/4812] At the pause, Enter on its players screen
        toggles DS:9B40. No pair is chosen until the original offers its next substitution opportunity."""
        if self.wait.kind != 'match-menu' or self.wait.view.get('context') != 'pause':
            raise UnexpectedScreen(('match-menu (pause)',), self.wait)
        from goal2.core import views
        wait = self._open_bench()
        if wait.kind == 'substitutions-used':
            message = views.bench(wait.state)['message']
            self.press(ESCAPE, expect=('match-menu',))
            return {'refused': message}
        self.press(RETURN, expect=('substitution-request', 'substitution-requested'))
        self.press(ESCAPE, expect=('match-menu',))
        return views.bench(self.wait.state)['requested']

    def _to_slot(self, slot):
        wait = self.core.wait
        for _ in range(MAX_MOVES):
            if wait.view["slot"] == slot:
                return wait
            wait = self.press(DOWN if wait.view["slot"] < slot else UP, expect=SUBSTITUTION)
        raise DriverError(f"the cursor did not reach slot {slot}")

    def round_position(self, player, key):
        """[confirmed: F030/F031; E44F/4925/4952 at 53d7ef5; T114 captures] R cycles position and C restores
        club position before kick-off, at half time or a stoppage. The original updates the player's position;
        these keys never ask the substitution routine to exchange personnel."""
        from goal2.core import views
        if key not in ('r', 'c'):
            raise DriverError('Position keys are R or C')
        wait = self.wait
        if wait.kind not in self.INTERVAL_KINDS and not (wait.kind == 'match-menu' and
                wait.view.get('context') in ('before', 'stoppage')):
            raise DriverError('Positions are offered before kick-off, at an interval or a stoppage')
        home = wait.kind
        squad = self._team()
        if player not in squad:
            raise DriverError(f'Player {player} is not in the managed squad')
        wait = self._open_bench()
        if wait.kind == 'substitutions-used':
            message = views.bench(wait.state)['message']
            self.press(ESCAPE, expect=(home,))
            return {'refused': message}
        if wait.kind == SQUAD:
            self._to_player(player)
        else:
            self._to_slot(squad.index(player)+1)
        self.press(key, expect=(SQUAD,)+SUBSTITUTION)
        self.press(ESCAPE, expect=(home,))
        return views.player_card(self.wait.state, player)

    def substitute(self, off, on):
        """At the half-time match menu, or a stoppage's: the bench (the managed side's players, E949 -> E44F), Enter
        on `off`, Enter on `on`, Esc back; the two in either order, as the original takes them (E022 marks the first and
        swaps on the second, E031 C41e-C41i). The pair goes to the original as it is: 0791:E022 makes it (the two squad
        words swap and the counter DS:9B3A + side counts down) or refuses it with its message ("Illegal substitution"
        for two of the same block), which a key closes. With no substitution left E44F offers none (DS:2538): the
        driver presses nothing there but Esc. Returns {"made", "refused" (the original's message or None), "left",
        "eleven", "bench"}, read from memory after the original's keys."""
        from goal2.core import views
        if self.wait.view.get('context') == 'pause':
            raise DriverError('At a pause request a substitution; choose the pair at the next opportunity')
        if self.core.wait.kind not in self.INTERVAL_KINDS and not self.stoppage():
            raise UnexpectedScreen(self.INTERVAL_KINDS+("match-menu",), self.core.wait)
        home = self.core.wait.kind
        before = views.bench(self.core.wait.state)["eleven"]
        wait = self._open_bench()
        refused = None
        if wait.kind == "substitutions-used":
            refused = views.bench(wait.state)["message"]
        else:
            squad = [r["player"] for r in views.team(wait.state)["squad"]]
            if off not in squad or on not in squad:
                self.press(ESCAPE, expect=(home,))
                raise DriverError(f"players {off} and {on} are not both in the managed squad")
            self._to_slot(squad.index(off) + 1)
            wait = self.press(RETURN, expect=SUBSTITUTION + ("squad-substitution-illegal", "substitution-refused"))
            if wait.kind in SUBSTITUTION:
                self._to_slot(squad.index(on) + 1)
                wait = self.press(RETURN, expect=SUBSTITUTION + ("squad-substitution-illegal", "substitution-refused", "substitutions-used"))
            if wait.kind in ("squad-substitution-illegal", "substitution-refused"):
                refused = wait.view["message"].strip()
                self.press(RETURN, expect=SUBSTITUTION)
        for _ in range(4):
            if self.core.wait.kind == home:
                break
            self.press(ESCAPE, expect=SUBSTITUTION + ("substitutions-used", home))
        else:
            raise DriverError("Esc did not leave the bench")
        bench = views.bench(self.core.wait.state)
        eleven = bench["eleven"]
        swapped = (off in before) != (off in eleven) and (on in before) != (on in eleven)
        return {"made": swapped and refused is None, "refused": refused,
                "left": bench["left"], "eleven": eleven, "bench": bench["bench"]}

    def play_on(self):
        """At the half-time menu or a stoppage's: play, and the match goes on (the quick result) to its next stop: the
        managed side's notice, the half-time menu (from a first-half stoppage), or past the full-time board and the
        menu's exit, the round's last screens (the table, the bulletins), the manager menu; returns its wait. When
        the original refuses the eleven (EA09, e.g. "has too many goalkeepers" after a substitution) the driver closes
        its box and returns {"refused": the original's message} at the same menu."""
        self._menu_item("play")
        if self.core.wait.kind not in self.INTERVAL_KINDS and not self.stoppage():
            raise UnexpectedScreen(self.INTERVAL_KINDS+("match-menu",), self.core.wait)
        self._stop("substitution-notice")
        refused = self._play()
        if refused is not None:
            return {"refused": refused}
        wait = self._pass(self.STOPS + ("match-menu-fulltime",))
        if wait.kind != "match-menu-fulltime":
            return wait
        return self.finish()

    def finish(self):
        """At the full-time match menu: exit, then the round's last screens (the table, the bulletins) to the manager
        menu; returns its wait."""
        if self.core.wait.kind != "match-menu-fulltime":
            raise UnexpectedScreen(("match-menu-fulltime",), self.core.wait)
        self._menu_item("exit")
        self.press(RETURN, expect=self.ROUND_KINDS)
        return self._pass((MENU,))

    def prematch_swap(self, a, b):
        """At the match menu before the kick-off: the managed side's players (E949 -> E44F, SELECT YOUR TEAM before
        the match, DS:0C1F clear), Enter on `a`, Enter on `b` (0791:DEA6 swaps them, then resort_pitch_and_bench),
        Esc back to the match menu; returns the squad. The fix for an eleven the original refused (EA09)."""
        if self.core.wait.kind != "match-menu" or self.stoppage():
            raise UnexpectedScreen(("match-menu",), self.core.wait)
        squad = self._team()
        if a == b or a not in squad or b not in squad:
            raise DriverError(f"a swap needs two different players of the managed squad, not {a} and {b}")
        self._open_bench()
        self._to_player(a)
        wait = self.press(RETURN, expect=(SQUAD,))
        if wait.view["marked"] is None:
            raise DriverError(f"the original did not mark player {a}")
        self._to_player(b)
        self.press(RETURN, expect=(SQUAD,))
        self.press(ESCAPE, expect=("match-menu",))
        return self._team()

    def play_round(self, watch=False, captain=None, substitutions=(), fix_eleven=None, on_notice=None,
                   on_stoppage=None, on_taker=None):
        """The whole round from the manager menu to the next: round_start, kick_off (the captain), at half time each
        (off, on) of `substitutions` (substitute), play_on. `fix_eleven(driver, message)` answers an eleven the
        original refuses (e.g. by prematch_swap before the kick-off, substitute at half time); without it a refusal
        raises DriverError with the original's message. `on_notice(driver, wait)` answers the managed side's notice:
        True for the bench (then `on_stoppage(driver)` at the stoppage's menu), False or None to let it pass, as a
        manager who presses nothing. T120's `on_taker(driver, wait)` returns an original key (or None for
        its remaining timer); without that explicit answer the script stops at the decision with DriverError.
        Returns {"pages", "substitutions", "refused", "notices"}."""
        wait = self.round_start(watch)
        out = {"substitutions": [], "refused": [], "notices": 0}
        if wait.kind == MENU:
            out["pages"] = self.pages
            return out
        for _ in range(8):
            result = self.kick_off(captain)
            if not isinstance(result, dict):
                break
            out["refused"].append(result["refused"])
            if fix_eleven is None:
                raise DriverError(f"the original refuses the eleven: {result['refused']}")
            fix_eleven(self, result["refused"])
        else:
            raise DriverError("the original kept refusing the eleven")
        half_time_done = False
        stops = 0
        live_polls = 0
        taker_keys = 0
        while True:
            wait = self.core.wait
            if wait.kind == MENU:
                break
            if wait.kind in (_screens.TAKER_SELECT,_screens.TAKER_PITCH):
                if on_taker is None:raise DriverError('The original awaits a taker decision; supply on_taker')
                taker_keys+=1
                if taker_keys>10000:raise DriverError('The taker callback exceeded 10000 keys')
                self.taker_key(on_taker(self,wait));continue
            if wait.kind == 'match-live':
                live_polls += 1
                if live_polls > 400000:
                    raise DriverError('The watched match exceeded 400000 live polls')
                self.live_step()
                continue
            if wait.kind == 'match-summary-save-prompt':
                self.summary_done()
                continue
            if wait.kind == "substitution-notice":
                # [confirmed: code/seg_0791_13.asm 8062-80A9] the original offers the notice at each stoppage while a
                # substitution is asked for (DS:9B40, which Esc does not clear): let pass, it comes again. [designed]
                # Its own bound: one notice per stoppage, at most MAX_NOTICES in a match.
                out["notices"] += 1
                if out["notices"] > MAX_NOTICES:
                    raise DriverError(f"the managed side's notice came more than {MAX_NOTICES} times")
                self.notice(bool(on_notice(self, wait)) if on_notice else False)
                continue
            stops += 1
            if stops > 16:              # [designed] the other stops: half time, the stoppages' menus, refusals
                raise DriverError("the match did not end")
            if wait.kind == "match-menu-fulltime":
                self.finish()
                continue
            if wait.kind == "match-menu-halftime" and not half_time_done:
                half_time_done = True
                for off, on in substitutions:
                    out["substitutions"].append(self.substitute(off, on))
            elif self.stoppage() and on_stoppage is not None:
                on_stoppage(self)
            result = self.play_on()
            if isinstance(result, dict):
                out["refused"].append(result["refused"])
                if fix_eleven is None:
                    raise DriverError(f"the original refuses the eleven: {result['refused']}")
                fix_eleven(self, result["refused"])
        out["pages"] = self.pages
        return out
