"""T107 (#308's G12, #328): the Team and Pool pages over the core: the squad, the player card, the team tactics, the
pool, the driver's team actions and the desktop's Team and Pool pages on the core route.

The text page is the oracle: each view (goal2/core/views.py, read from memory only) must equal what the original
prints on its own screen at the same state, the driver taking the original there by its own keys (E006-r0001, and a
new game booted at the DOS date call, T106). No test writes guest memory. Nothing of the original is in this file:
it reads .cache/ and skips without.

[designed: #316] The tests that run more than a few screens are slow tests (GOAL2_SLOW=1; the gate runs them when
goal2/core/ or this module changes, tools/check_premerge.py SLOW_PATHS); the E006 text oracle is the module's one
real case in the default run.
"""
import os
import re
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

TEMPLATE, DATE_CALL = "e006-r0001-main.sav", "e039-r0005-date-call.sav"
NEEDS = {"modules": ("unicorn",), "files": (TEMPLATE, "GOAL.DAT")}
NEW_GAME = {"modules": ("unicorn",), "files": (DATE_CALL, "GOAL.DAT")}
DESKTOP = {"modules": ("unicorn", "PySide6"), "files": (TEMPLATE, "GOAL.DAT")}
# [confirmed: seg_214B_02.asm 08DD-0941] the codes 08DD returns, written out here apart from goal2/core as the oracle
ESC, ENTER, UP, DOWN, LEFT = 0x1B, 0x0D, 0x48 + 0x64, 0x50 - 3 + 0x64, 0x4B - 1 + 0x64
SIZES = ((1440, 900), (1050, 780), (900, 640), (2560, 1600))


def start():
    """A Driver at the manager menu: E006-r0001 by Esc from its team-info browser."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    requires.require(**NEEDS)
    driver = Driver(Core.start((requires.CACHE / TEMPLATE).read_bytes()).core)
    driver.to_menu()
    return driver


def new_game():
    """A new game (T106): the DOS date 1991-10-04 (start year 1992), N in the tune, Denmark, "bob"."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    requires.require(**NEW_GAME)
    wait = Core.boot((requires.CACHE / DATE_CALL).read_bytes(), (1991, 10, 4), goal_dat=requires.CACHE / "GOAL.DAT",
                     title_key="n")
    driver = Driver(wait.core)
    driver.new_game(7, "bob")
    return driver


def lines(wait):
    return wait.text.splitlines() + [""] * 25


def attr_run(wait, row, col, n):
    """How many cells from (row, col) are reverse video (0x70, the bars' fill, 214B:00DB and 214B:13C5)."""
    c = 0
    while c < n and wait.screen[2 * (row * 80 + col + c) + 1] == 0x70:
        c += 1
    return c


def screen_card(wait):
    """The player screen's fields as SELECT YOUR TEAM prints them (1771:42BC's template DS:486E)."""
    t = lines(wait)
    m = re.match(r"│(.{12})\s*│\s*(\d+)│\s*(\d+)│\s*(\d+)│\s*(\d+)'\s*(\d+)\" │(.{10})│(.{11})│", t[7])
    assert m, t[7]

    def seg(row):
        a = t[row].index("┼", 30) + 1
        return t[row][a:t[row].index("┤", a)]
    return {"name": m.group(1).rstrip("▒ "), "age": int(m.group(2)), "caps": int(m.group(3)),
            "goals": int(m.group(4)), "height": (int(m.group(5)), int(m.group(6))), "bias": m.group(7),
            "performance": m.group(8).strip(), "position_name": t[9][1:19].strip("│ "),
            "club_position_name": t[9][20:38].strip("│ "), "readiness": t[9][45:61].strip("│ "),
            "cards": t[9][39:44], "tactics": [seg(r).split("─")[-1] for r in range(11, 15)],
            "mark": seg(15).split("─")[-1],
            "characteristics": [(seg(r)[10:].lstrip("─").split("■")[0], attr_run(wait, r, 47, 14)) for r in range(18, 23)],
            "skills": [attr_run(wait, r, 10, 26) for r in range(11, 23)]}


def expected_card(c):
    return {"name": c["name"], "age": c["age"], "caps": c["caps"], "goals": c["goals"], "height": c["height"],
            "bias": c["foot"] if len(c["foot"]) > 6 else f"{c['foot']:<6}foot",
            "performance": "*" * (c["performance"] or 0), "position_name": c["position_name"],
            "club_position_name": c["club_position_name"], "readiness": c["readiness"],
            "cards": "".join(("■" if (i == 0 and "yellow" in c["cards"]) or (i == 2 and c["cards"].count("yellow") == 2)
                              or (i == 4 and "red" in c["cards"]) else " ") for i in range(5)),
            "tactics": [w + (" P" if own else "") for _, w, own in c["tactics"]], "mark": c["mark"],
            "characteristics": [(w, b) for _, w, b in c["characteristics"]], "skills": [v for _, v in c["skills"]]}


def strip(wait):
    """The list on the right of SELECT YOUR TEAM: [(name, code)] (1771:2F37 rows at column 0x41)."""
    return [m.groups() for row in lines(wait)[2:23] for m in [re.search(r"│([^│]{12})│(.)│$", row)] if m]


class Oracle:
    def check_select_squad(self, driver, cards=20):
        """The squad, each squad card, the pool window and each pool card against SELECT YOUR TEAM."""
        from goal2.core import views
        state = driver.wait.state
        team, pool = views.team(state), views.pool(state)
        wait = driver.goto("select-squad")
        team = views.team(wait.state)            # E44F sorts the squad by position on entry (it holds no draft)
        self.assertEqual(strip(wait), [(r["name"][:12].ljust(12), r["code"]) for r in team["squad"]])
        rule = [i for i, row in enumerate(lines(wait)[2:24]) if row.endswith("├────────────┼─┤")]
        self.assertEqual(rule, [11])            # the eleven, the rule, the bench
        for _ in range(cards):
            self.assertEqual(screen_card(wait), expected_card(views.player_card(wait.state, wait.view["player"])))
            wait = driver.press(DOWN, expect=("select-squad",))
        wait = driver.press(LEFT, expect=("select-squad-pool",))
        pool = views.pool(wait.state)
        top = pool["top"]
        self.assertEqual(strip(wait), [(r["name"][:12].ljust(12), r["code"])
                                       for r in pool["rows"][top - 1:top + 20]])
        self.assertIn("pool of players", lines(wait)[0])
        for _ in range(cards):
            self.assertEqual(wait.view["player"], pool["rows"][wait.view["item"] - 1]["player"])
            self.assertEqual(screen_card(wait), expected_card(views.player_card(wait.state, wait.view["player"])))
            wait = driver.press(DOWN, expect=("select-squad-pool",))
        driver.to_menu()
        return team

    def check_team_tactics(self, driver):
        from goal2.core import views
        country = views.team(driver.wait.state)["country"]
        driver.goto("team-info")
        driver._browse_info(country)
        wait = driver.press("t", expect=("team-tactics",))
        view = views.team_tactics(wait.state)
        t = lines(wait)
        shown = [t[r][t[r].index("─", 36):t[r].index("┤", 36)].split("──")[-1].strip("─") for r in range(8, 17)
                 if r != 11]
        self.assertEqual(shown, [r["word"] for r in view["rows"]])
        self.assertEqual([r["element"] for r in view["rows"]], [5, 6, 7, 1, 2, 3, 4, 8])
        # [T107's amendment] the key the screen prints, docs/core.md "Keys the screen prints"
        self.assertIn("Use ↑↓ to move", t[2])
        driver.to_menu()
        return view


@requires.need(**NEEDS)
class TextOracleE006(Oracle, unittest.TestCase):
    """The module's one real case in the default run."""

    def test_the_views_equal_select_squad_and_the_team_tactics_at_e006(self):
        driver = start()
        team = self.check_select_squad(driver, cards=4)
        self.assertEqual(team["name"], "Denmark")
        self.check_team_tactics(driver)


@requires.need(**NEW_GAME, slow=True)
class TextOracleNewGame(Oracle, unittest.TestCase):
    def test_the_views_equal_the_screens_of_a_new_game(self):
        driver = new_game()
        self.check_select_squad(driver)
        self.check_team_tactics(driver)


def replay(log):
    """The same keys pressed on a fresh E006 core directly: each pressed key with Core.press, each key the original
    read at a polled screen queued (Core.queue) before the press that led there."""
    from goal2.core import Core
    from goal2.core.screens import KINDS
    core = Core.start((requires.CACHE / TEMPLATE).read_bytes()).core
    for i, (kind, key) in enumerate(log):
        if KINDS[kind].polled:
            continue
        for later_kind, later in log[i + 1:]:
            if not KINDS[later_kind].polled:
                break
            core.queue(later_kind, later)
        core.press(key)
    return core


def model():
    from goal2.desktop.core_model import CoreModel
    requires.require(**NEEDS)
    return CoreModel.open(requires.CACHE / TEMPLATE, requires.CACHE / "GOAL.DAT",
                          Path(tempfile.gettempdir()) / "t107.g2core")


@requires.need(**NEEDS, slow=True)
class Actions(unittest.TestCase):
    def test_each_action_is_the_originals_keys_and_shows_its_effect(self):
        from goal2.core import views
        m = model()
        team = [r["player"] for r in m.team()["squad"]]
        pool = [r["player"] for r in m.pool()["rows"]]
        a, b = team[0], team[12]

        def same_as_direct():
            self.assertEqual(replay(list(m.driver.log)).memory_sha256(), m.memory_sha256())
        # swap: the bench player moved into the eleven, the other out (then E44F's sort)
        squad = m.act("swap", a, b)
        same_as_direct()
        self.assertIn(b, squad[:11]);self.assertIn(a, squad[11:])
        # exchange: the pool player is in the squad, the squad player in the pool
        out, incoming = team[5], pool[40]
        result = m.act("exchange", out, incoming)
        same_as_direct()
        self.assertIsNone(result["refused"])
        self.assertIn(incoming, result["squad"]);self.assertIn(out, result["pool"]);self.assertNotIn(out, result["squad"])
        # set_position: R steps to the code, C to the club position
        p = team[3]
        card = m.act("set_position", p, 7)
        same_as_direct()
        self.assertEqual(card["position"], 7)
        card = m.act("set_position", p, card["club_position"])
        same_as_direct()
        self.assertEqual(card["position"], card["club_position"])
        # set_own_tactic: his own possession, the other word, " P"
        p = team[4]
        before = m.card(p)["tactics"][1]
        card = m.act("set_own_tactic", p, 2, not (m.team_tactics()["byte"] >> 1 & 1))
        same_as_direct()
        self.assertTrue(card["tactics"][1][2]);self.assertNotEqual(card["tactics"][1][1], before[1])
        card = m.act("set_own_tactic", p, 2, None)
        same_as_direct()
        self.assertEqual(card["tactics"][1], before)
        # rename: 1771:4859 keeps the initial and the surname
        p = team[6]
        self.assertEqual(m.act("rename", p, "mo salah"), "M O Salah")
        same_as_direct()
        # set_tactic: the offside word
        view = m.act("set_tactic", 7, True)
        same_as_direct()
        self.assertEqual(next(r["word"] for r in view["rows"] if r["element"] == 7), "offside trap")
        # Its effects are what the original shows: the squad, the card's position and name, the tactic word.
        wait = m.driver.goto("select-squad")
        names = [n.strip() for n, _ in strip(wait)]
        self.assertIn(views.Memory(wait.state).player_name(incoming)[:12], names)
        self.assertIn("M O Salah", names)
        while wait.view["player"] != team[3]:
            wait = m.driver.press(DOWN, expect=("select-squad",))
        shown = screen_card(wait)
        self.assertEqual(shown["position_name"], views.player_card(wait.state, team[3])["club_position_name"])
        m.driver.to_menu()
        oracle = Oracle();oracle.assertEqual, oracle.assertIn = self.assertEqual, self.assertIn
        self.assertEqual(oracle.check_team_tactics(m.driver)["rows"][2]["word"], "offside trap")

    def test_a_refusal_shows_the_originals_reason_and_changes_nothing_else(self):
        """Man-marking outside a match: 1771:4B61 offers four rows, no row 5 (a refusal E006 reaches). The finals and
        tour locks (0791:DBFA) are reached by no kept state: docs/core.md lists them as not visited."""
        m = model()
        p = m.team()["squad"][5]["player"]
        def held():           # the records, not their order: E44F sorts the squad by position on entry itself
            return (sorted(r["player"] for r in m.team()["squad"]), sorted(r["player"] for r in m.pool()["rows"]),
                    m.team_tactics(), m.card(p))
        before = held()
        with self.assertRaises(ValueError) as caught:
            m.act("set_marking", p, m.team()["squad"][6]["player"])
        self.assertIn("4 rows", str(caught.exception))
        self.assertIn("man-marking", str(caught.exception))
        self.assertEqual(m.core.wait.kind, "manager-menu")
        # memory: only what the original changed itself on the way (the same keys pressed directly give it)
        self.assertEqual(replay(list(m.driver.log)).memory_sha256(), m.memory_sha256())
        self.assertEqual(held(), before)


@requires.need(**NEEDS, slow=True)
class Keys(unittest.TestCase):
    def test_the_driver_refuses_an_unlisted_key_and_stops_at_an_unexpected_screen(self):
        from goal2.core.driver import RefusedKey, UnexpectedScreen
        driver = start()
        wait = driver.goto("select-squad")
        sha = driver.core.memory_sha256()
        with self.assertRaises(RefusedKey):
            driver.press("x")                       # SELECT YOUR TEAM lists no X
        with self.assertRaises(RefusedKey):
            driver.press(0xA2)                      # nor F4
        self.assertEqual(driver.core.memory_sha256(), sha)
        self.assertEqual(driver.wait, wait)
        with self.assertRaises(UnexpectedScreen) as caught:
            driver.press(LEFT, expect=("select-squad",))
        self.assertEqual(caught.exception.kind, "select-squad-pool")
        with self.assertRaises(RefusedKey):
            driver.press(0xB6)                      # Ins: the pool list does not print it
        driver.to_menu()
        from goal2.core.driver import DriverError
        with self.assertRaises(DriverError):
            driver.swap(1, 1)                       # not two squad players: nothing pressed
        with self.assertRaises(DriverError):
            driver.rename(driver._team()[0], "a name too long for it")
        self.assertEqual(driver.wait.kind, "manager-menu")


@requires.need(**NEEDS, slow=True)
class Determinism(unittest.TestCase):
    def test_save_and_resume_after_edits_give_the_same_views_and_memory(self):
        from goal2.desktop.core_model import CoreModel
        m = model()
        team = [r["player"] for r in m.team()["squad"]]
        m.act("swap", team[1], team[15]);m.act("set_tactic", 4, False);m.act("rename", team[2], "Qx Yz")
        path = Path(tempfile.mkdtemp()) / "edits.g2core"
        m.save(path)

        def look(x):
            return (x.team(), x.pool(), x.team_tactics(), [x.card(w) for w in team], x.memory_sha256())
        resumed = CoreModel.from_save(path, requires.CACHE / "GOAL.DAT")
        self.assertEqual(look(resumed), look(m))
        # and the same calls on both give the same memory again
        m.act("set_position", team[9], 3);resumed.act("set_position", team[9], 3)
        self.assertEqual(look(resumed), look(m))


@requires.need(**DESKTOP, slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        from goal2.desktop.core_window import CoreWindow
        w = CoreWindow(model());w.show();self.app.processEvents()
        return w

    def test_team_and_pool_fit_and_show_no_table_or_check_box(self):
        from PySide6.QtWidgets import QCheckBox, QTableWidget
        from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
        from goal2.desktop.fixed_page import problems
        from goal2.desktop.style import load_fonts
        w = self.window()
        self.assertTrue(w.navigation[1].isEnabled() and w.navigation[2].isEnabled())
        found = []
        for size in SIZES:
            w.resize(*size);self.app.processEvents()
            for page, index in ((1, 0), (1, 1), (1, 2), (2, None)):
                w.navigate(page)
                if index is not None:w.team_views.show_view(index)
                self.app.processEvents()
                shown = w.pages[page]
                found += [f"{size} page {page} view {index}: {p}" for p in problems(w)]
                need = shown.minimumSizeHint()
                if need.width() > 0.9 * shown.width() or need.height() > 0.9 * shown.height():
                    found.append(f"{size} page {page} view {index}: needs {need.width()}x{need.height()} of "
                                 f"{shown.width()}x{shown.height()}, more than 90 %")
                for kind in (QTableWidget, QCheckBox):
                    found += [f"page {page}: a {kind.__name__}" for x in shown.findChildren(kind) if x.isVisible()]
        self.assertEqual(found, [])
        for page in (1, 2):
            self.assertEqual([x for x in w.pages[page].findChildren(QTableWidget)], [])
            self.assertEqual([x for x in w.pages[page].findChildren(QCheckBox)], [])
        # Measured in the bundled font: the strip's names and the tactic rows' longest words fit it.
        family = QFontDatabase.applicationFontFamilies(load_fonts()[0])[0]
        font = QFont(family);font.setPixelSize(20);font.setBold(True)
        widest = max(QFontMetrics(font).horizontalAdvance(r[1]) for r in w.team_roster.rows)
        self.assertLess(40 + widest, 300 - 64 + 48)
        # no skill number is drawn on the card
        w.navigate(1);w.team_views.show_view(0);self.app.processEvents();w.team_card.repaint()
        self.assertTrue(w.team_card.drawn)
        self.assertFalse([t for t in w.team_card.drawn if t.strip().isdigit()])
        self.assertEqual(w.team_roster.rows[0][1], w.model.team()["squad"][0]["name"])

    def test_an_edit_runs_as_a_job_and_the_page_shows_the_original_afterwards(self):
        w = self.window()
        w.navigate(1);w.team_views.show_view(1)
        row = dict(w.tactics)[7]
        before = row.word
        row.click()
        self.assertTrue(w.core_jobs.busy)
        self.assertFalse(row.isEnabled())               # the page waits on the job without freezing
        answer = w.finish_core()
        self.assertEqual(answer[0], "done")
        self.assertNotEqual(row.word, before)
        self.assertEqual(row.word, next(r["word"] for r in w.model.team_tactics()["rows"] if r["element"] == 7))
        self.assertTrue(row.isEnabled())
        # a refusal shows the original's reason
        w.team_views.show_view(2);w.own_marking.click();answer = w.finish_core()
        self.assertEqual(answer[0], "refused")
        self.assertIn("man-marking", w.status.text())
        # rename from the card, and an exchange from the Pool page
        w.team_views.show_view(0);w.rename_text.setText("ab cd");w.rename.click();w.finish_core()
        self.assertEqual(w.team_card.card["full_name"], "A B Cd")      # 4859: initial A, surname "b Cd" upcased
        w.navigate(2)
        from goal2.desktop.pool_page import core_pool_enter, core_switch
        incoming = w.pool_selected()
        core_switch(w);out = w.pool_selected()
        core_pool_enter(w);core_switch(w);core_pool_enter(w)
        self.assertEqual(w.finish_core()[0], "done")
        squad = [r["player"] for r in w.model.team()["squad"]]
        self.assertIn(incoming, squad);self.assertNotIn(out, squad)

    def position_edit(self, w):
        """[designed: owner #423] Genuine original keys must change sorting without moving the editing row."""
        from goal2.desktop.squad_page import core_reposition
        w.navigate(1);w.team_roster.set_current(10)
        player = w.team_roster.rows[10][0]
        before = [r[0] for r in w.team_roster.rows]
        for _ in range(14):
            core_reposition(w, False)
            self.assertEqual(w.finish_core()[0], 'done')
            self.assertEqual([r[0] for r in w.team_roster.rows], before)
            self.assertEqual(w.team_roster.rows[w.team_roster.current][0], player)
            original = [r['player'] for r in w.model.team()['squad']]
            if original != before:return player, before
        self.fail('The genuine position cycle did not exercise a sort-changing edit')

    def test_reposition_stays_in_place_until_enter_without_marking(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.squad_page import core_reposition
        w = self.window();self.addCleanup(w.close)
        player, before = self.position_edit(w)
        position = w.model.card(player)['position']
        core_reposition(w, False);self.assertEqual(w.finish_core()[0], 'done')
        self.assertEqual(w.model.card(player)['position'], (position + 1) % 14)
        self.assertEqual([r[0] for r in w.team_roster.rows], before)
        QTest.keyClick(w.team_roster, Qt.Key.Key_Return)
        self.assertEqual([r[0] for r in w.team_roster.rows], [r['player'] for r in w.model.team()['squad']])
        self.assertEqual(w.team_roster.rows[w.team_roster.current][0], player)
        self.assertIsNone(w.core_marked)
        QTest.keyClick(w.team_roster, Qt.Key.Key_Return)
        self.assertEqual(w.core_marked, ('squad', player))

    def test_leaving_repositioned_player_follows_full_id_and_releases_order(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        w = self.window();self.addCleanup(w.close)
        player, before = self.position_edit(w)
        intended = w.team_roster.rows[w.team_roster.current + 1][0]
        QTest.keyClick(w.team_roster, Qt.Key.Key_Down)
        self.assertEqual([r[0] for r in w.team_roster.rows], [r['player'] for r in w.model.team()['squad']])
        self.assertEqual(w.team_roster.rows[w.team_roster.current][0], intended)
        self.assertIsNone(w.core_marked)

    def test_club_position_mouse_selection_and_leaving_page_release_order(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from goal2.desktop.squad_page import core_reposition
        w = self.window();self.addCleanup(w.close)
        player, before = self.position_edit(w)
        core_reposition(w, True);self.assertEqual(w.finish_core()[0], 'done')
        self.assertEqual(w.model.card(player)['position'], w.model.card(player)['club_position'])
        self.assertEqual([r[0] for r in w.team_roster.rows], before)
        target = w.team_roster.current + 1;intended = w.team_roster.rows[target][0]
        QTest.mouseClick(w.team_roster, Qt.MouseButton.LeftButton, pos=w.team_roster.row_rect(target).center())
        self.assertEqual(w.team_roster.rows[w.team_roster.current][0], intended)
        self.assertEqual([r[0] for r in w.team_roster.rows], [r['player'] for r in w.model.team()['squad']])
        self.position_edit(w)
        w.navigate(0)
        self.assertEqual([r[0] for r in w.team_roster.rows], [r['player'] for r in w.model.team()['squad']])


if __name__ == "__main__":
    unittest.main()
