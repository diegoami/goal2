"""T105 (#308's G11, #321): the desktop over the core: the driver, the views and the core route of the desktop.

The text page is the oracle: each view (goal2/core/views.py, read from memory only) must equal what the original
prints on its own screen at the same state, the driver taking the original there by its own keys. The states:
E006-r0001 (a new game's first screen) and E010-r0001's half time played on to the manager menu that follows.
Nothing of the original is in this file: it reads .cache/ and skips without.

[designed: #316] The tests that run the original are slow tests (GOAL2_SLOW=1; the gate runs them whenever
goal2/core/ or this module changes, tools/check_premerge.py SLOW_PATHS), but the E006 text oracle, the module's one
real case in the default run.
"""
import hashlib
import os
import re
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

TEMPLATE, HALFTIME = "e006-r0001-main.sav", "e010-r0001-halftime.sav"
NEEDS = {"modules": ("unicorn",), "files": (TEMPLATE, HALFTIME, "GOAL.DAT")}
DESKTOP = {"modules": ("unicorn", "PySide6"), "files": (TEMPLATE, "GOAL.DAT")}
# [confirmed: seg_214B_02.asm 08DD-0941] the codes 08DD returns, written out here apart from goal2/core as the oracle
ESC, ENTER, UP, DOWN, LEFT = 0x1B, 0x0D, 0x48 + 0x64, 0x50 - 3 + 0x64, 0x4B - 1 + 0x64
SIZES = ((1440, 900), (1050, 780), (900, 640), (2560, 1600))


def savestate(name):
    requires.require(**NEEDS)
    return (requires.CACHE / name).read_bytes()


def start(name=TEMPLATE):
    """A Driver at the manager menu: E006-r0001 by Esc from its team-info browser."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    driver = Driver(Core.start(savestate(name)).core)
    driver.to_menu()
    return driver


def after_halftime():
    """E010-r0001 from its half-time board to the manager menu after the match, by the screens' own keys: Enter
    (the board), Enter on the match menu's play, Enter (the full-time board), Enter on exit, Enter (the bulletin)."""
    from goal2.core import Core
    from goal2.core.driver import Driver
    driver = Driver(Core.start(savestate(HALFTIME)).core)
    assert driver.wait.kind == "match-board", driver.wait.kind
    wait = driver.press(ENTER, expect=("match-menu-halftime",))
    assert wait.view["label"] == "play", wait.view
    driver.press(ENTER, expect=("match-board",))
    wait = driver.press(ENTER, expect=("match-menu-fulltime",))
    assert wait.view["label"] == "exit", wait.view
    driver.press(ENTER, expect=("bulletin",))
    driver.press(ENTER, expect=("manager-menu",))
    return driver


def pair(segment):
    """A fixture as the original draws it ('--------Denmark  0v1  Sweden---------'): (first, s1, s2, second)."""
    m = re.match(r"\s*-*(.+?)\s+(\d*)v(\d*)\s+(.+?)-*\s*$", segment)
    assert m, segment
    return m.group(1), m.group(2), m.group(3), m.group(4)


def lines(wait):
    return wait.text.splitlines() + [""] * 25


class Oracle:
    """The comparisons of each view with its screen's text page."""

    def check_desk(self, wait, desk):
        t = lines(wait)
        self.assertEqual(wait.kind, "manager-menu")
        self.assertRegex(t[1], r"│%d│" % desk["year"])
        self.assertIn(desk["stage_word"], t[3])
        self.assertIn(f"│{desk['manager']:<14}│{desk['rating']:<15}│", t[7])
        self.assertIn(f"│{desk['team']['name']}", t[10])
        for row, label, value in ((12, "World", "world_rank"), (13, desk["team"]["continent"], "continent_rank")):
            self.assertRegex(t[row], r"│%s\s*:\s*%d│" % (label, desk["team"][value]))
        managers = {int(m.group(1)): m.group(2).rstrip() for row in t[10:16]
                    for m in [re.search(r"│(\d)│(.{14})│", row)] if m}
        self.assertEqual(managers, {n: next((m["name"] for m in desk["managers"] if m["number"] == n), "")
                                    for n in range(1, 7)})
        opponent = desk["opponent"]
        self.assertIsNotNone(opponent)
        self.assertIn(f"│{opponent['name']}", t[16])
        for row, label, value in ((18, "World", "world_rank"), (19, opponent["continent"], "continent_rank")):
            self.assertRegex(t[row], r"│%s\s*:\s*%d│" % (label, opponent[value]))
        self.assertIn(f"│{desk['fixture_kind']:<15}│", t[21])
        strip = [m.groups() for row in t[2:23] for m in [re.search(r"│([^│]{12})│(.)│$", row)] if m]
        self.assertEqual(strip, [(p["name"][:12].ljust(12), p["code"]) for p in desk["squad"]])

    def check_fixtures(self, wait, view):
        t = lines(wait)
        self.assertIn(wait.kind, ("fixture-list", "fixtures-watch", "fixtures-auto"))
        self.assertEqual(wait.view["fixture"], view["first"])          # the highlight starts at the first row
        shown = [row for row in t[7:23] if row[12:13] == "│"]
        self.assertEqual(len(shown), min(16, len(view["rows"])))
        for text, row in zip(shown, view["rows"]):
            first, s1, s2, second = pair(text[13:52])
            self.assertEqual((first, second), (row["first_name"], row["second_name"]), text)
            self.assertEqual((s1, s2), tuple(str(n) for n in row["score"]) if row["played"] else ("", ""), text)
            self.assertEqual(text[54:66].rstrip(), row["kind_name"], text)
            self.assertEqual(text[67] == "√", row["mark"], text)

    def check_tournament(self, wait, view):
        t = lines(wait)
        self.assertEqual(wait.kind, "tournament")
        self.assertEqual(view["display"], "qualifying")
        letter = re.search(r"Group (\w)", t[8]).group(1)
        group = next(g for g in view["groups"] if g["group"] == letter)
        self.assertTrue(any(r["country"] == view["country"] for r in group["rows"]))
        rows = [re.search(r"│(.{15})║(\d)│(\d)│(\d)│(\d)║\s*(\d+)│\s*(\d+)║\s*(\d+)│", row) for row in t[10:14]]
        self.assertEqual([(m.group(1).rstrip("-"),) + tuple(int(x) for x in m.groups()[1:]) for m in rows],
                         [(r["name"], r["played"], r["won"], r["drawn"], r["lost"], r["for"], r["against"],
                           r["points"]) for r in group["rows"]])
        shown = [pair(row[38:76]) for row in t[7:19] if row[38:76].strip()]
        self.assertEqual(shown, [(f["first_name"], *((str(f["score"][0]), str(f["score"][1])) if f["played"]
                                                     else ("", "")), f["second_name"]) for f in group["fixtures"]])

    def check_history(self, wait, view):
        t = lines(wait)
        self.assertEqual(wait.kind, "history")
        self.assertIn(view["name"], t[19])
        stats = {m.group(1): [int(x) for x in re.findall(r"\d+", m.group(2))] for row in t[2:6]
                 for m in [re.search(r"│(consecutive wins|consecutive defeats|games without a win|games without "
                                     r"defeat)\s*│((?:\s*\d+│){6})", row)] if m}
        self.assertEqual(stats, view["statistics"])
        successes = {m.group(1): [int(x) for x in re.findall(r"\d+", m.group(2))] for row in t[2:6]
                     for m in [re.search(r"│(WC|CH)│((?:\s*\d+\s*│){4})", row)] if m}
        self.assertEqual(successes, {"WC": view["successes"]["world_cup"], "CH": view["successes"]["championship"]})
        results = [m.groups() for row in t[8:18] for m in [re.match(
            r"│(\d{4}/\d\d)│(\w\w)│\s*(\d+)│\s*(\d+)│\s*(\d+)│\s*(\d+)│\s*(\d+)│\s*(.*?)\s*│", row)] if m]
        self.assertEqual(results, [(r["season"], r["competition"], str(r["won"]), str(r["drawn"]), str(r["lost"]),
                                    str(r["for"]), str(r["against"]), r["best"]) for r in view["results"]])
        self.assertTrue(results)
        tops = [re.search(r"│([^│]{15})│\s*(\d*)│([^│]{15})│\s*(\d*)│$", row) for row in t[8:18]]
        scorers = [(m.group(1).rstrip(), int(m.group(2))) for m in tops if m and m.group(2)]
        caps = [(m.group(3).rstrip(), int(m.group(4))) for m in tops if m and m.group(4)]
        self.assertEqual(scorers, [(r["name"], r["count"]) for r in view["top_scorers"]])
        self.assertEqual(caps, [(r["name"], r["count"]) for r in view["top_caps"]])
        for row, where in zip(t[20:23], ("home", "away", "neutral")):
            m = re.match(r"│%s\s*│(.{26})│(.{26})│" % where, row)
            for cell, what in ((m.group(1), "wins"), (m.group(2), "defeats")):
                record = view["records"][what][where]
                score = re.search(r"(\d*)v(\d*)", cell)
                names = cell[score.end():].strip().rstrip("-").strip()
                if record is None:
                    self.assertEqual((score.groups(), names), (("", ""), ""), cell)
                else:
                    expected = tuple(str(n) for n in record["score"]) if record["score"] else ("", "")
                    self.assertEqual(score.groups(), expected, cell)
                    self.assertEqual(names, " ".join(record["opponents"]), cell)

    def tour(self, driver):
        """The manager menu, then each screen by the driver, each compared with its view, and back."""
        from goal2.core import views
        self.check_desk(driver.wait, views.desk(driver.wait.state))
        state = driver.wait.state
        expected = {"fixtures": views.fixture_list(state), "tournament": views.tournament(state),
                    "history": views.history(state)}
        wait = driver.goto("fixture-list")
        self.assertEqual(views.fixture_list(wait.state), expected["fixtures"])   # the view holds at any screen
        self.check_fixtures(wait, expected["fixtures"])
        driver.back()
        self.check_tournament(driver.goto("tournament"), expected["tournament"])
        driver.back()
        self.check_history(driver.goto("history"), expected["history"])
        driver.back()
        self.assertEqual(driver.wait.kind, "manager-menu")
        return expected


@requires.need(**NEEDS)
class TextOracleE006(Oracle, unittest.TestCase):
    """The module's one real case in the default run."""

    def test_each_view_equals_its_screen_at_e006(self):
        driver = start()
        expected = self.tour(driver)
        self.assertEqual(expected["fixtures"]["rows"][0]["first_name"], "Denmark")


@requires.need(**NEEDS, slow=True)
class TextOracleE010(Oracle, unittest.TestCase):
    def test_each_view_equals_its_screen_after_e010s_match(self):
        driver = after_halftime()
        expected = self.tour(driver)
        # The match played: a defeat at home, the caps of those who played.
        self.assertEqual(expected["history"]["records"]["defeats"]["home"]["score"], (0, 1))
        self.assertTrue(expected["history"]["top_caps"])


@requires.need(**NEEDS, slow=True)
class DriverTests(unittest.TestCase):
    def test_goto_reaches_each_screen_and_returns(self):
        driver = start()
        for kind, shows in (("team-info", {"team-info"}), ("fixture-list", {"fixture-list", "fixtures-watch",
                                                                           "fixtures-auto"}),
                            ("tournament", {"tournament"}), ("history", {"history"})):
            self.assertIn(driver.goto(kind).kind, shows)
            self.assertEqual(driver.back().kind, "manager-menu")
        # Every key it pressed is one its screen lists (screens.py KINDS).
        from goal2.core.screens import KINDS
        self.assertTrue(all(KINDS[kind].accepts(key) for kind, key in driver.log))
        self.assertEqual([key for _, key in driver.log], driver.core.keys)

    def test_it_refuses_a_key_the_screen_does_not_list(self):
        from goal2.core.driver import RefusedKey
        driver = start()
        sha = driver.core.memory_sha256()
        with self.assertRaises(RefusedKey):
            driver.press("x")                          # the manager menu lists no X
        self.assertEqual(driver.core.memory_sha256(), sha)    # nothing reached the original
        driver.goto("history")
        with self.assertRaises(RefusedKey):
            driver.press(ENTER)                        # the history lists Esc only
        self.assertEqual(driver.core.keys, [k for _, k in driver.log])
        self.assertNotIn(ord("x"), driver.core.keys)
        self.assertEqual(driver.wait.kind, "history")

    def test_it_stops_at_an_unexpected_screen(self):
        from goal2.core import UnknownScreen
        from goal2.core.driver import DriverError, UnexpectedScreen
        driver = start()
        with self.assertRaises(UnexpectedScreen) as caught:
            driver.press(DOWN, expect=("tournament",))
        self.assertEqual((caught.exception.kind, caught.exception.site), ("manager-menu", "000E:75D1"))
        self.assertIn("find option", caught.exception.text)
        with self.assertRaises(DriverError):
            driver.goto("select squad")                # no route by that name: stated, nothing pressed
        driver.select(5)                               # [T107] select squad is mapped now: SELECT YOUR TEAM
        self.assertEqual(driver.press(ENTER).kind, "select-squad")
        driver.to_menu()
        driver.goto("tournament")
        self.assertEqual(driver.press(LEFT).kind, "championship-browse")
        driver.to_menu()
        from goal2.tests.test_core_save_t121 import UNKNOWN_NAME, unmapped
        requires.require(files=(UNKNOWN_NAME,))
        stopped, error = unmapped()
        self.assertEqual(error.site, "214B:09C4")
        self.assertFalse(error.poll)
        self.assertIn("file not found", error.text)
        self.assertIs(stopped.stopped, error)
        with self.assertRaises(DriverError):
            from goal2.core.driver import Driver
            Driver(stopped).press(27)  # no wait after the unknown caller; no guessed continuation

    def test_the_same_calls_give_the_same_keys_and_memory(self):
        runs = []
        for _ in range(2):
            driver = start()
            for kind in ("history", "tournament", "fixture-list", "team-info"):
                driver.goto(kind)
                driver.back()
            runs.append((list(driver.log), driver.core.memory_sha256()))
        self.assertEqual(runs[0], runs[1])
        self.assertGreater(len(runs[0][0]), 10)


@requires.need(**DESKTOP, slow=True)
class Desktop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_main(self, argv, check):
        """Run `python3 -m goal2.desktop argv` and call check(window) once its window is shown, then quit."""
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        from goal2.desktop.__main__ import main
        from goal2.desktop.core_window import CoreWindow
        seen = []

        def look():
            windows = [w for w in QApplication.topLevelWidgets() if isinstance(w, CoreWindow) and w.isVisible()]
            try:
                seen.append(check(windows[0]) if windows else None)
            finally:
                QApplication.instance().quit()
        QTimer.singleShot(0, look)
        self.assertEqual(main(argv), 0)
        self.assertTrue(seen and seen[0] is not None, "no core window was shown")
        return seen[0]

    def shown(self, window):
        """What the pages show: the boards' and labels' text."""
        return {"team": window.core_team_name.text(), "ranks": window.core_team.text(),
                "opponent": window.core_opponent_name.text(), "kind": window.core_fixture_kind.text(),
                "managers": window.core_managers.text(), "fixtures": window.core_fixture_board.text(),
                "group": window.core_group_board.text(), "results": window.core_results.text(),
                "records": window.core_records.text(), "squad": [r[1] for r in window.country_roster.rows]}

    def test_core_opens_the_window_with_the_views_and_fits_at_every_size(self):
        from goal2.core import views
        from goal2.desktop.fixed_page import problems
        save = Path(self.tmp.name) / "fit.g2core"

        def check(window):
            app = self.app
            desk = window.model.desk()
            self.assertEqual(desk, views.desk(window.model.core.wait.state))
            shown = self.shown(window)
            self.assertEqual(shown["team"], "Denmark")
            self.assertIn(f"World  :  {desk['team']['world_rank']:>2}", shown["ranks"])
            self.assertEqual((shown["opponent"], shown["kind"]), (desk["opponent"]["name"], desk["fixture_kind"]))
            self.assertEqual(shown["squad"], [p["name"] for p in desk["squad"]])
            first = window.model.fixture_list()["rows"][0]
            self.assertIn(f"{first['first_name']:>15}", shown["fixtures"].splitlines()[0])
            self.assertIn(first["second_name"], shown["fixtures"].splitlines()[0])
            self.assertIn("Group A", shown["group"])
            self.assertIn(window.model.history()["results"][0]["season"], shown["results"])
            found = []
            for size in SIZES:
                window.resize(*size);app.processEvents()
                for page, views_, index in ((0, window.country_views, 0), (0, window.country_views, 1),
                                            (3, window.fixture_views, 0), (3, window.fixture_views, 1),
                                            (4, None, None)):
                    window.navigate(page)
                    if views_ is not None:views_.show_view(index)
                    app.processEvents()
                    found += [f"{size} page {page} view {index}: {p}" for p in problems(window)]
                    # [designed: T105, #278] The fit holds with margin: the shown page asks for at most 90 % of
                    # the room the fixed page gives it, so wider platform metrics do not tip it over.
                    shown = window.pages[page];need = shown.minimumSizeHint()
                    if need.width() > 0.9 * shown.width() or need.height() > 0.9 * shown.height():
                        found.append(f"{size} page {page} view {index}: needs {need.width()}x{need.height()} of "
                                     f"{shown.width()}x{shown.height()}, more than 90 %")
            # The boards are measured in the bundled font, whatever the platform has installed (the Windows
            # workflow found boards measured in a wider fallback before the style loaded the font).
            from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF
            from goal2.desktop.style import load_fonts
            family = QFontDatabase.applicationFontFamilies(load_fonts()[0])[0]
            for board in (window.core_managers, window.core_statistics, window.core_fixture_board):
                font = QFont(family);font.setPixelSize(board.font_size)
                if abs(board.char - QFontMetricsF(font).horizontalAdvance("M")) > 0.01:
                    found.append(f"{board.objectName()} measured {board.char} px a column, not the bundled font's")
            return found
        self.assertEqual(self.run_main(["--core", str(requires.CACHE / TEMPLATE), "--data",
                                        str(requires.CACHE / "GOAL.DAT"), "--save", str(save)], check), [])

    def test_save_then_resume_gives_the_same_views_and_memory(self):
        save = Path(self.tmp.name) / "game.g2core"

        def before(window):
            self.assertTrue(window.save_core())
            model = window.model
            return (model.desk(), model.fixture_list(), model.tournament(), model.history(), model.memory_sha256(),
                    self.shown(window))
        saved = self.run_main(["--core", str(requires.CACHE / TEMPLATE), "--data", str(requires.CACHE / "GOAL.DAT"),
                               "--save", str(save)], before)
        self.assertTrue(save.read_bytes().startswith(b"G2C1"))

        def after(window):
            model = window.model
            return (model.desk(), model.fixture_list(), model.tournament(), model.history(), model.memory_sha256(),
                    self.shown(window))
        resumed = self.run_main(["--resume", str(save), "--data", str(requires.CACHE / "GOAL.DAT")], after)
        self.assertEqual(resumed, saved)
        # The core save holds the memory: the same SHA-256 as the core the window saved.
        from goal2.core import Core
        self.assertEqual(Core.load(save.read_bytes()).memory_sha256(), saved[4])
        self.assertEqual(hashlib.sha256(Core.load(save.read_bytes()).memory()).hexdigest(), saved[4])

    def test_the_disabled_route_names_its_g_task(self):
        def check(window):
            out = {}
            for name in ("nav2", "nav3"):
                button = next(b for b in window.navigation if b.objectName() == name)
                out[name] = (button.isEnabled(), button.text(), button.toolTip())
            for name in ("team info", "select squad", "play next game"):
                button = window.core_routes[name]
                out[name] = (button.isEnabled(), button.text(), button.toolTip())
            before = window.page_stack.currentIndex()
            window.navigate(1)
            out["stays"] = window.page_stack.currentIndex() == before
            return out
        out = self.run_main(["--core", str(requires.CACHE / TEMPLATE), "--data", str(requires.CACHE / "GOAL.DAT"),
                             "--save", str(Path(self.tmp.name) / "routes.g2core")], check)
        # [T107] Team, Pool, team info and select squad are served by the core now (G12); [T108] and play next game
        # (G14a): no route of the core waits for a G task any more (the pitch view's G14b is said on the round's page).
        for name in ("nav2", "nav3", "team info", "select squad", "play next game"):
            self.assertTrue(out[name][0], name)
            self.assertNotIn("G1", out[name][1], name)
            self.assertNotIn("G1", out[name][2], name)
        self.assertFalse(out["stays"])                  # the Team page opens


if __name__ == "__main__":
    unittest.main()
