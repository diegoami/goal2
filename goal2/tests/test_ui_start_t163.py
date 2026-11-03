"""[designed: owner, 2026-11-03, #526, #527; T163, #537] The new window's start and new game: S01 to S05 and home.

The claim it protects: a career started or loaded in the new window is the same career the Python route's model
makes, `DesktopModel.new_campaign` or the model's validating loader with the same inputs. Visited here: S02's
Continue, load and failed load over named saves; S03's managers and its starting year by NG-9; S04's list, ranking,
players and name line; S05's pages; S01's manifest; S22's size; and the flow from S02 to home.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/`, as the desktop tests do,
and skip when they are absent (goal2/tests/requires.py). The S01 and S05 tests use stand-ins of their own.
"""
import datetime
import hashlib
import re
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import STAGES, DesktopModel  # noqa: E402
from goal2.ui import s03_new_game, saves, start_look, theme  # noqa: E402
from goal2.ui.home import HomeScreen  # noqa: E402
from goal2.ui.s01_import import ImportScreen  # noqa: E402
from goal2.ui.s02_start import StartScreen  # noqa: E402
from goal2.ui.s03_new_game import NewGameScreen  # noqa: E402
from goal2.ui.s04_country import CountryScreen, PlayersScreen  # noqa: E402
from goal2.ui.s05_bulletin import BulletinScreen  # noqa: E402
from goal2.ui.s22_help import HelpScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t163-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = data_setup.Paths(self.tmp / "goal2")
        clock = mock.patch.object(s03_new_game, "clock_year", return_value=2026)
        clock.start()
        self.addCleanup(clock.stop)

    def data(self):
        """The new window's two files, copied from .cache/ into the data folder."""
        self.target.data.mkdir(parents=True, exist_ok=True)
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(CACHE / name, self.target.data / name)

    def window(self):
        window = Window(self.target, choose=lambda: getattr(self, "offered", None))
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def key(self, window, key, times=1):
        for _ in range(times):
            QTest.keyClick(window, key)
            self.app.processEvents()

    def type(self, window, text):
        QTest.keyClicks(window, text)
        self.app.processEvents()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def fits(self, window):
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(window), [])

    def reference(self, country, year, name):
        model = DesktopModel.open(self.target.data / data_setup.TEMPLATE_NAME, self.target.goal_dat,
                                  self.tmp / "reference.g2game", country=country)
        model.new_campaign(country, year)
        model.rename_manager(name)
        return model

    def same_career(self, career, reference):
        a, b = career.state, reference.state
        self.assertEqual(a.managed_country, b.managed_country)
        self.assertEqual(a.manager_name, b.manager_name)
        self.assertEqual((a.campaign.start_year, a.campaign.stage), (b.campaign.start_year, b.campaign.stage))
        self.assertEqual(a.campaign.fixtures, b.campaign.fixtures)
        self.assertEqual(a.managed_squad, b.managed_squad)
        self.assertEqual(a, b, "the whole state is the model's")

    def to_country_screen(self, window):
        window.start()
        self.assertIsInstance(window.current(), StartScreen)
        self.key(window, Qt.Key.Key_N)
        self.assertIsInstance(window.current(), NewGameScreen)
        self.key(window, Qt.Key.Key_Return)
        screen = window.current()
        self.assertIsInstance(screen, CountryScreen)
        return screen


@CAREER
class NewGame(App):
    def test_through_new_game_the_career_is_the_models(self):
        self.data()
        window = self.window()
        window.start()
        start = window.current()
        self.assertIsInstance(start, StartScreen)
        self.assertFalse(start.continue_box.isVisible(), "with no save, only New game")
        self.assertFalse(start.list_box.isVisible())
        self.assertFalse(start.load_item.isVisible())
        self.assertEqual(start.enter_text.text(), "New game")
        self.fits(window)
        with mock.patch.object(DesktopModel, "new_campaign", autospec=True,
                               side_effect=DesktopModel.new_campaign) as new_campaign:
            self.key(window, Qt.Key.Key_N)
            new_game = window.current()
            self.assertIsInstance(new_game, NewGameScreen)
            self.fits(window)
            self.key(window, Qt.Key.Key_Return)
            screen = window.current()
            self.assertIsInstance(screen, CountryScreen)
            self.key(window, Qt.Key.Key_Down, 3)
            screen.settle()
            self.assertEqual(screen.chosen(), (4, "Bulgaria"))
            self.assertEqual(screen.name.text(), "Bulgaria")
            self.key(window, Qt.Key.Key_Return)
            self.assertTrue(screen.naming)
            self.assertEqual(screen.enter_text.text(), "Start the career")
            self.type(window, "K Ees")
            self.assertEqual(screen.field.text, "K Ees")
            self.fits(window)
            self.key(window, Qt.Key.Key_Return)
            self.assertIn(4, [c.args[1] for c in new_campaign.call_args_list])
            self.assertEqual(new_campaign.call_args_list[-1].args[1:], (4, 2028),
                             "the default year, 2026 on the clock, starts in 2028 through new_campaign")
        home = window.current()
        self.assertIsInstance(home, HomeScreen, "no bulletin pages on the Python route: straight home (#509)")
        self.assertEqual(window.stack, [home])
        career = window.career
        self.assertIs(home.model, career)
        self.same_career(career, self.reference(4, 2028, "K Ees"))
        self.assertEqual((career.state.campaign.start_year, career.state.campaign.stage), (2028, 2))
        self.assertEqual(home.values["manager"].text(), "K Ees")
        self.fits(window)

    def test_the_default_year_starts_a_2028_career(self):
        self.data()
        window = self.window()
        screen = self.to_country_screen(window)
        self.assertEqual(screen.start_year, 2028)
        self.key(window, Qt.Key.Key_Return)
        self.type(window, "D Penev")
        self.key(window, Qt.Key.Key_Return)
        career = window.career
        self.assertEqual((career.state.campaign.start_year, career.state.campaign.stage), (2028, 2))
        self.same_career(career, self.reference(1, 2028, "D Penev"))

    def test_the_year_by_ng9_is_shown_before_enter(self):
        self.data()
        window = self.window()
        window.start()
        self.key(window, Qt.Key.Key_N)
        screen = window.current()
        shown = screen.start_year_shown()
        self.assertIn("starts in 2028", shown)
        self.assertIn(STAGES[2], shown, "2028 is divisible by 4: stage 2")
        self.assertIn("PC clock", shown)
        self.assertEqual(screen.year_field.shown.text(), "2026", "the empty field shows the clock's year")
        self.key(window, Qt.Key.Key_Tab)
        self.assertTrue(screen.year_field.active)
        self.type(window, "1991")
        self.assertEqual(screen.year_field.text, "1991")
        shown = screen.start_year_shown()
        self.assertIn("starts in 1992", shown)
        self.assertIn(STAGES[2], shown, "NG-9: 1992 is divisible by 4, stage 2 (E039: DOS 1990 -> 1992 stage 2)")
        self.key(window, Qt.Key.Key_Backspace)
        self.type(window, "3")
        shown = screen.start_year_shown()
        self.assertIn("starts in 1994", shown)
        self.assertIn(STAGES[5], shown, "NG-9: 1994 is not divisible by 4, stage 5 (E039: DOS 1992 -> 1994 stage 5)")
        self.key(window, Qt.Key.Key_Backspace)
        self.type(window, "1")
        self.fits(window)
        self.key(window, Qt.Key.Key_Return)
        country = window.current()
        self.assertIsInstance(country, CountryScreen)
        campaign = country.browser.state.campaign
        self.assertEqual((campaign.start_year, campaign.stage), (1992, 2))

    def test_a_year_out_of_dos_range_is_refused(self):
        self.data()
        window = self.window()
        window.start()
        self.key(window, Qt.Key.Key_N)
        screen = window.current()
        self.key(window, Qt.Key.Key_Tab)
        self.type(window, "1979")
        self.assertIn("a year from 1980 to 2099", screen.start_year_shown())
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), screen)
        self.assertIn("cannot be used", screen.note_text())
        self.key(window, Qt.Key.Key_Backspace, 4)
        self.assertIn("starts in 2028", screen.start_year_shown())

    def test_two_to_six_managers_come_later(self):
        self.data()
        window = self.window()
        window.start()
        self.key(window, Qt.Key.Key_N)
        screen = window.current()
        for n in range(2, 7):
            self.key(window, Qt.Key.Key_Right)
            self.assertEqual(screen.chosen, n)
            self.key(window, Qt.Key.Key_Return)
            self.assertIs(window.current(), screen, f"{n} managers stay on S03")
            self.assertIn("coming later", screen.note_text())
            self.assertIn("#551", screen.note_text())
        self.click(screen.digits[2])
        self.assertEqual(screen.chosen, 3, "a click chooses, as ←→ do")
        self.click(screen.enter_hint)
        self.assertIs(window.current(), screen)
        self.assertIn("Three managers are coming later", screen.note_text())
        self.click(screen.digits[0])
        self.assertEqual(screen.note_text(), "")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIsInstance(window.current(), StartScreen, "Esc goes back to S02")


@CAREER
class CountryKeys(App):
    def test_groups_ranking_players_and_the_name_line(self):
        self.data()
        window = self.window()
        screen = self.to_country_screen(window)
        countries = screen.browser.countries()
        self.assertEqual(screen.visible_names(), [c[1] for c in countries[:16]])
        self.assertEqual(screen.visible_ranks(), [str(c[2]) for c in countries[:16]])
        self.assertIn("16 of 128", screen.group_note.text())
        self.key(window, Qt.Key.Key_Right)
        self.assertEqual(screen.visible_names(), [c[1] for c in countries[16:32]])
        self.assertEqual(screen.chosen()[0], 17)
        self.assertIn("32 of 128", screen.group_note.text())
        self.key(window, Qt.Key.Key_Left)
        self.assertEqual(screen.visible_names(), [c[1] for c in countries[:16]])
        self.assertIn("WORLD RANK", screen.list_heading.text())
        self.key(window, Qt.Key.Key_Insert)
        self.assertIn("CONTINENTAL RANK", screen.list_heading.text())
        self.assertEqual(screen.visible_ranks(), [str(c[4]) for c in countries[:16]])
        self.key(window, Qt.Key.Key_Insert)
        self.assertIn("WORLD RANK", screen.list_heading.text())
        self.click(screen.rows[3])
        self.assertEqual(screen.chosen()[0], 4, "a click highlights a country, as ↑↓ do")
        self.key(window, Qt.Key.Key_Space)
        players = window.current()
        self.assertIsInstance(players, PlayersScreen)
        self.assertEqual(len(players.cards), 20)
        self.assertEqual([c["id"] for c in players.cards], list(screen.browser.state.managed_squad))
        self.key(window, Qt.Key.Key_Down)
        self.assertEqual(players.player_name.text(), players.cards[1]["full_name"])
        self.fits(window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen)
        self.key(window, Qt.Key.Key_Return)
        self.assertTrue(screen.naming)
        self.type(window, "Ab")
        self.key(window, Qt.Key.Key_Right)
        self.assertEqual(screen.chosen()[0], 4, "on the name line the arrows do not move the list")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), screen, "Esc on the name line keeps the country list")
        self.assertFalse(screen.naming)
        self.assertEqual(screen.field.text, "")
        self.assertEqual(screen.enter_text.text(), "Choose Bulgaria")
        self.key(window, Qt.Key.Key_Return)
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), screen, "an empty name does not start a career")
        self.assertIn("Type the manager", screen.name_note.text())
        self.type(window, "A Name Too Long For Goal")
        self.assertEqual(screen.field.text, "A Name Too Lon", "14 characters at most")
        self.key(window, Qt.Key.Key_Escape)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIsInstance(window.current(), NewGameScreen, "Esc again goes back to S03")


@CAREER
class Load(App):
    def saved(self, country, year, name, when):
        model = DesktopModel.open(self.target.data / data_setup.TEMPLATE_NAME, self.target.goal_dat,
                                  self.tmp / "unused.g2game", country=country)
        model.new_campaign(country, year)
        model.rename_manager("K Ees")
        return saves.write(model, self.target.saves, name, saved=when), model

    def test_two_named_saves_continue_and_load(self):
        self.data()
        now = saves.now()
        older, older_model = self.saved(4, 1990, "Bulgaria, World Cup run", now - datetime.timedelta(hours=3))
        newer, newer_model = self.saved(20, 1992, "Holland after the draw", now)
        self.assertNotEqual(newer.stem, "Holland after the draw", "the file name is derived from the name")
        window = self.window()
        window.start()
        start = window.current()
        self.assertIsInstance(start, StartScreen)
        rows = [[cell.text() for cell in row.cells] for row in start.rows if row.isVisible()]
        self.assertEqual([r[0] for r in rows], ["Holland after the draw", "Bulgaria, World Cup run"], "newest first")
        self.assertEqual([r[1] for r in rows], ["Holland", "Bulgaria"])
        self.assertEqual(rows[0][2], f"1992 · {STAGES[2]}")
        self.assertEqual(rows[1][2], f"1990 · {STAGES[5]}")
        self.assertEqual(rows[0][3], newer_model.summary()["next"])
        self.assertTrue(rows[0][4].startswith("today ") or re.match(r"\d+ \w+", rows[0][4]))
        self.assertIn("Continue Holland", start.continue_text.text())
        self.assertEqual(start.enter_text.text(), "Continue")
        self.fits(window)
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), HomeScreen)
        self.assertEqual(window.career.state, newer_model.state, "Enter continues the newest save")
        again = self.window()
        again.start()
        self.key(again, Qt.Key.Key_Down)
        self.key(again, Qt.Key.Key_Y)
        self.assertIsInstance(again.current(), HomeScreen)
        self.assertEqual(again.career.state, older_model.state, "Y loads the highlighted save")
        self.assertEqual(again.career.save_path, older)

    def test_a_save_that_cannot_be_opened_says_why_with_y_and_n(self):
        self.data()
        good, _ = self.saved(4, 1990, "A good save", saves.now() - datetime.timedelta(hours=1))
        broken = self.target.saves / f"broken{saves.SUFFIX}"
        with zipfile.ZipFile(broken, "w") as archive:
            archive.writestr(saves.META, '{"format": "goal2-named-save", "version": 1, "name": "Broken career", '
                                         f'"saved": "{saves.now().isoformat()}"}}')
            archive.writestr(saves.SESSION, b"{not a session save")
        window = self.window()
        window.start()
        start = window.current()
        names = [row.cells[0].text() for row in start.rows if row.isVisible()]
        self.assertEqual(names, ["Broken career", "A good save"])
        self.assertEqual(start.rows[0].cells[1].text(), "cannot be opened")
        self.assertIn("Continue Bulgaria", start.continue_text.text(), "Continue opens the newest save that opens")
        self.key(window, Qt.Key.Key_Y)
        self.assertIs(window.current(), start)
        self.assertTrue(start.problem.isVisible())
        self.assertIn("“Broken career” cannot be opened: Cannot resume game", start.problem.text())
        self.assertIn("Y: try again", start.problem.text())
        bar = dict((caps, text) for caps, text in start.key_texts())
        self.assertEqual((bar[("Y",)], bar[("N",)]), ("try again", "back"))
        self.fits(window)
        self.key(window, Qt.Key.Key_Y)
        self.assertIs(window.current(), start, "trying again fails again")
        self.assertTrue(start.problem.isVisible())
        self.key(window, Qt.Key.Key_N)
        self.assertIs(window.current(), start, "N returns to the list")
        self.assertFalse(start.problem.isVisible())
        bar = dict((caps, text) for caps, text in start.key_texts())
        self.assertEqual((bar[("Y",)], bar[("N",)]), ("load a saved game", "new game"))
        self.key(window, Qt.Key.Key_Down)
        self.key(window, Qt.Key.Key_Y)
        self.assertIsInstance(window.current(), HomeScreen)
        self.assertEqual(window.career.save_path, good)

    def test_a_file_that_is_no_save_is_listed_with_its_reason(self):
        self.data()
        self.target.saves.mkdir(parents=True)
        (self.target.saves / f"junk{saves.SUFFIX}").write_bytes(b"not a zip")
        window = self.window()
        window.start()
        start = window.current()
        self.assertEqual(start.rows[0].cells[0].text(), "junk")
        self.assertFalse(start.continue_box.isVisible())
        self.assertEqual(start.enter_text.text(), "New game")
        self.key(window, Qt.Key.Key_Y)
        self.assertIn("not a goal2 save", start.problem.text())


class SaveFormat(unittest.TestCase):
    def test_file_names_are_derived_safely_and_the_name_is_stored(self):
        self.assertEqual(saves.file_stem("Holland after round 1"), "holland-after-round-1")
        self.assertEqual(saves.file_stem("../../etc/passwd"), "etc-passwd")
        self.assertEqual(saves.file_stem("CON"), "con-save")
        self.assertEqual(saves.file_stem("¡¿?"), "save")
        with self.assertRaises(saves.SaveError):
            saves.clean_name("   ")
        with self.assertRaises(saves.SaveError):
            saves.clean_name("x" * (saves.NAME_MAX + 1))
        tmp = Path(tempfile.mkdtemp(prefix="goal2-t163-names-"))
        self.addCleanup(shutil.rmtree, tmp, True)

        class Model:
            save_path = None

            def save(self, path):
                Path(path).write_bytes(b"{}")

        first = saves.write(Model(), tmp, "Same / name")
        second = saves.write(Model(), tmp, "Same ? name")
        self.assertEqual((first.name, second.name), ("same-name.g2game", "same-name-2.g2game"))
        self.assertEqual(saves.read_meta(second)[0], "Same ? name")
        self.assertEqual(saves.write(Model(), tmp, "Same / name"), first, "the same name saves over its own file")

    def test_when_reads_as_the_mockup(self):
        today = datetime.date(2026, 11, 3)
        moment = datetime.datetime(2026, 11, 3, 21, 4).astimezone()
        self.assertEqual(saves.when(moment, today), "today 21:04")
        self.assertEqual(saves.when(datetime.datetime(2026, 10, 29, 9, 0).astimezone(), today), "29 Oct")
        self.assertEqual(saves.when(datetime.datetime(2025, 10, 29, 9, 0).astimezone(), today), "29 Oct 2025")


STAND_IN = {"GOAL.DAT": b"stand-in data file\n", "e010-r0008-halftime.sav": b"stand-in template\n",
            "e039-r0005-date-call.sav": b"stand-in boot state\n"}


class ImportManifest(App):
    def test_s01_needs_the_template_and_not_the_boot_state(self):
        self.assertEqual(data_setup.MANIFEST, (
            ("GOAL.DAT", "bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca"),
            ("e039-r0005-date-call.sav", "0d9c683023c7327f17bfc29900f2eff4e703641d21d3f353693f09654688494b"),
        ), "the old window's manifest is unchanged")
        self.assertEqual(data_setup.WINDOW_MANIFEST, (
            ("GOAL.DAT", "bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca"),
            ("e010-r0008-halftime.sav", "ae2935b9c490745450462b981eb133e611bc72de4abfb11aba3e850caf4e9949"),
        ))
        stand_in = tuple((name, hashlib.sha256(STAND_IN[name]).hexdigest()) for name, _ in data_setup.WINDOW_MANIFEST)
        with mock.patch.object(data_setup, "WINDOW_MANIFEST", stand_in), \
                mock.patch.object(data_setup, "OPTIONAL", (("GOAL.HLP", hashlib.sha256(b"help\n").hexdigest()),)):
            window = self.window()
            window.start()
            screen = window.current()
            self.assertIsInstance(screen, ImportScreen)
            self.assertIn(data_setup.TEMPLATE_NAME, screen.cells)
            self.assertNotIn(data_setup.BOOT_NAME, screen.cells)
            texts = [w.text() for w in screen.findChildren(type(screen.name_label)) if w.isVisible()]
            self.assertNotIn(data_setup.BOOT_NAME, texts)
            without = self.tmp / "without-template"
            without.mkdir()
            for name in ("GOAL.DAT", "e039-r0005-date-call.sav"):
                (without / name).write_bytes(STAND_IN[name])
            self.offered = str(without)
            self.key(window, Qt.Key.Key_Return)
            self.assertIs(window.current(), screen, "the boot state does not stand in for the template")
            self.assertEqual(screen.check_text(data_setup.TEMPLATE_NAME), "✗ missing in this folder")
            folder = self.tmp / "offered"
            folder.mkdir()
            for name in ("GOAL.DAT", "e010-r0008-halftime.sav"):
                (folder / name).write_bytes(STAND_IN[name])
            self.offered = str(folder)
            self.key(window, Qt.Key.Key_Return)
            self.assertIsInstance(window.current(), StartScreen, "imported without the boot state: S02")
            self.assertFalse((self.target.data / data_setup.BOOT_NAME).exists())
            self.assertTrue(data_setup.complete(self.target.data, stand_in))
            self.assertFalse(data_setup.complete(self.target.data), "the old window's check is its own")


class Help(App):
    def test_the_help_box_fills_most_of_the_page(self):
        self.target.data.mkdir(parents=True)
        self.target.help.write_bytes(b"stand-in help\r\n" * 80 + b"\x1a")
        window = self.window()
        window.replace_home(HomeScreen(window))
        self.key(window, Qt.Key.Key_F1)
        screen = window.current()
        self.assertIsInstance(screen, HelpScreen)
        self.app.processEvents()
        self.assertGreaterEqual(screen.viewer.height(), 0.7 * window.page.height())
        self.fits(window)
        window.resize(720, 450)
        self.app.processEvents()
        self.assertGreaterEqual(screen.viewer.height(), 0.7 * window.page.height(), "at every scale")


class Bulletin(App):
    def page(self, n):
        return {"left": {"masthead": f"LEFT {n}", "lines": ["a side story"]},
                "middle": {"masthead": f"FRONT {n}", "lines": ["A HEADLINE", "a line"]},
                "right": {"masthead": f"RIGHT {n}", "lines": ["another story"]}}

    def test_three_pages_n_of_m_then_on(self):
        window = self.window()
        done = []
        screen = window.replace_home(BulletinScreen(window, [self.page(n) for n in (1, 2, 3)],
                                                    lambda: done.append(True)))
        self.assertEqual(screen.count_text(), "FRONT PAGE · 1 OF 3")
        self.assertIn("FRONT 1", screen.panels["middle"][2].text())
        self.assertEqual(screen.enter_text.text(), "Next page (any key)")
        self.fits(window)
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(screen.count_text(), "FRONT PAGE · 2 OF 3")
        self.key(window, Qt.Key.Key_K)
        self.assertEqual(screen.count_text(), "FRONT PAGE · 3 OF 3", "any key turns the page")
        self.assertIn("RIGHT 3", screen.panels["right"][2].text())
        self.assertEqual(done, [])
        self.click(screen.enter_hint)
        self.assertEqual(done, [True], "Enter after the last page goes on")

    def test_a_career_with_pages_shows_them_before_home(self):
        window = self.window()

        class Career:
            manager = "K Ees"

            def summary(self):
                return dict.fromkeys(("country", "manager", "campaign", "next", "then", "team"), "x")

        career = Career()
        window.open_career(career, [self.page(1)])
        self.assertIsInstance(window.current(), BulletinScreen)
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), HomeScreen)
        self.assertIs(window.current().model, career)
        window.open_career(career)
        self.assertIsInstance(window.current(), HomeScreen, "no pages: straight home")


class Look(unittest.TestCase):
    def test_the_added_sheet_uses_the_palette_and_whole_cells(self):
        sheet = start_look.stylesheet()
        colours = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", sheet)}
        self.assertTrue(colours)
        self.assertLessEqual(colours, set(theme.PALETTE.values()))
        sizes = [int(s) for s in re.findall(r"font-size:\s*(\d+)px", sheet)]
        self.assertEqual([s for s in sizes if s % theme.CELL], [])

    def test_ng9_start_years(self):
        self.assertEqual([s03_new_game.start_year(y) for y in (1989, 1990, 1991, 2026, 2027)],
                         [1990, 1992, 1992, 2028, 2028])
        self.assertEqual(s03_new_game.first_competition(2028), STAGES[2])
        self.assertEqual(s03_new_game.first_competition(1994), STAGES[5])


if __name__ == "__main__":
    unittest.main()
