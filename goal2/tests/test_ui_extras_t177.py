"""[designed: owner, §6 item 18 (docs/design/ui-2026-11, 2026-11-03); T177, #557] The four extras the new window keeps
from today's window, though the original lacks them.

The claim it protects: each extra does exactly what today's window does through the model. Visited offscreen:
- **Search and filter (S08):** typing "muller" after / lists the pool rows `pool_view(query="muller")` lists, Müller
  among them (accents folded); P's position filter lists `pool_view(position=…)`'s rows, alone and with the search;
  the two Enters exchange from a filtered list as `model.exchange` does with the same pair; R, C, T, F2, Ins, Enter
  and Esc keep their meaning, and the bar names / and P.
- **Standalone friendly (S02):** F, two countries chosen with the keys, S17 to full time (R, every stop answered by
  default), back on S02 with the result; no save is written and the friendly is never the window's career.
- **Rename (S06):** *manager's name* gives the name `rename_manager` gives, 14 characters at most, and the career is
  unsaved; Esc keeps the old name.
- **New career (S06):** with unsaved progress it asks *Do you want to save this game?* first: Y saves through the
  name box then shows S03, N shows S03 and writes nothing, Esc stays; with nothing unsaved it shows S03 at once.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them; the
friendly's engine runs under PyPy 3.11 and its test skips without it. Nothing of the original is in this file
(CLAUDE.md rule 14).
"""
import copy
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires

requires.require(modules=("PySide6",))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QLabel  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.game import campaign_pool  # noqa: E402
from goal2.ui import s03_new_game, saves  # noqa: E402
from goal2.ui.s02_start import StartScreen  # noqa: E402
from goal2.ui.s03_new_game import NewGameScreen  # noqa: E402
from goal2.ui.s06_desk import DeskScreen  # noqa: E402
from goal2.ui.s08_squad import SquadScreen  # noqa: E402
from goal2.ui.s21_save import SAVE_QUESTION, QuestionScreen, SaveScreen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND, GERMANY = 20, 12
WAIT = 900   # seconds for a whole match under PyPy on a loaded runner
_BASE = {}


def career(country):
    """A fresh copy of a new career of `country` starting in 2028, its manager named (opened once per run)."""
    if country not in _BASE:
        folder = _BASE.setdefault("folder", tempfile.mkdtemp(prefix="goal2-t177-"))
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "unused.g2game", country=country)
        model.new_campaign(country, 2028)
        model.rename_manager("K Ees")
        model.mark_saved()
        _BASE[country] = model
    return copy.deepcopy(_BASE[country])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


def ids(rows):
    return [row["id"] for row in rows]


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t177-ui-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.target = data_setup.Paths(self.tmp / "goal2")
        clock = mock.patch.object(s03_new_game, "clock_year", return_value=2026)
        clock.start()
        self.addCleanup(clock.stop)
        self.target.data.mkdir(parents=True, exist_ok=True)
        for name, _ in data_setup.WINDOW_MANIFEST:
            shutil.copyfile(CACHE / name, self.target.data / name)

    def window(self):
        window = Window(self.target)
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: (window.leave(), window.deleteLater(), self.app.processEvents()))
        return window

    def desk(self, model):
        window = self.window()
        return window, window.open_career(model)

    def key(self, window, key, times=1, modifier=Qt.KeyboardModifier.NoModifier):
        for _ in range(times):
            QTest.keyClick(window, key, modifier)
            self.app.processEvents()

    def type(self, window, text):
        QTest.keyClicks(window, text)
        self.app.processEvents()

    def bar(self, screen):
        return dict((caps, text) for caps, text in screen.key_texts())

    def fits(self, window):
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(window), [])

    def tagged(self, screen, text):
        """The screen marks the extra as a goal2 addition, as the desk's re-import."""
        tags = [w.text() for w in screen.findChildren(QLabel, "tagNew") if w.isVisible()]
        self.assertTrue(any(text in tag for tag in tags), tags)

    def files(self):
        return sorted(p.name for p in self.target.saves.glob("*")) if self.target.saves.is_dir() else []

    def option(self, desk, text):
        return next(i for i, o in enumerate(desk.options) if o.text_label.text() == text)


@CAREER
class SearchAndFilter(App):
    def squad(self):
        model = career(GERMANY)
        same = copy.deepcopy(model)
        window, desk = self.desk(model)
        self.key(window, Qt.Key.Key_Space)
        screen = window.current()
        self.assertIsInstance(screen, SquadScreen)
        return window, screen, model, same

    def test_typing_muller_lists_the_rows_pool_view_lists_accents_folded(self):
        window, screen, model, _ = self.squad()
        self.tagged(screen, "GOAL2 ADDITION")
        self.assertEqual(self.bar(screen).get(("/",)), "search")
        self.assertEqual(self.bar(screen).get(("P",)), "position")
        self.fits(window)
        self.key(window, Qt.Key.Key_Slash)
        self.assertEqual(screen.side, "pool", "/ opens the pool with the search line")
        self.assertTrue(screen.searching)
        self.type(window, "muller")
        expected = model.pool_view(query="muller")["reserves"]
        self.assertTrue(expected, "the German pool has a Müller")
        self.assertTrue(all("ü" in row["name"].lower() for row in expected), "found through the folded accent")
        self.assertEqual(ids(screen.rows()), ids(expected))
        shown = [texts[1] for texts in screen.strip.shown_texts()]
        self.assertEqual(len(shown), len(expected))
        self.assertTrue(all("Müller" in name for name in shown), shown)
        self.assertEqual(screen.enter_text.text(), "Keep search")
        self.fits(window)
        # Typed letters are the search's, not R, C, T: nothing of the player changed.
        self.assertEqual(screen.query, "muller")
        # Backspace edits; Esc clears the search and closes the line.
        self.key(window, Qt.Key.Key_Backspace)
        self.assertEqual(ids(screen.rows()), ids(model.pool_view(query="mulle")["reserves"]))
        self.key(window, Qt.Key.Key_Escape)
        self.assertFalse(screen.searching)
        self.assertEqual(screen.query, "")
        self.assertEqual(ids(screen.rows()), ids(model.pool_view()["reserves"]))
        self.assertIs(window.current(), screen, "Esc on the search line does not leave S08")

    def test_the_position_filter_lists_the_rows_pool_view_lists(self):
        window, screen, model, _ = self.squad()
        self.key(window, Qt.Key.Key_P)
        self.assertEqual(screen.side, "pool")
        self.assertEqual(screen.position, 0)
        self.assertEqual(ids(screen.rows()), ids(model.pool_view(position=0)["reserves"]))
        self.assertTrue(screen.rows())
        for code in range(1, 14):
            self.key(window, Qt.Key.Key_P)
            self.assertEqual(screen.position, code)
            self.assertEqual(ids(screen.rows()), ids(model.pool_view(position=code)["reserves"]), code)
        self.key(window, Qt.Key.Key_P)
        self.assertIsNone(screen.position, "after the fourteenth code, all again")
        self.assertEqual(ids(screen.rows()), ids(model.pool_view()["reserves"]))
        self.key(window, Qt.Key.Key_P, modifier=Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(screen.position, 13, "Shift+P steps back")
        # A click on the filter is P.
        QTest.mouseClick(screen.position_button, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertIsNone(screen.position)
        # The search and the filter together.
        self.key(window, Qt.Key.Key_P)
        self.key(window, Qt.Key.Key_Slash)
        self.type(window, "m")
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(ids(screen.rows()), ids(model.pool_view(query="m", position=0)["reserves"]))
        self.fits(window)

    def test_an_exchange_from_a_filtered_list_equals_the_model_s_exchange(self):
        window, screen, model, same = self.squad()
        self.key(window, Qt.Key.Key_Slash)
        self.type(window, "muller")
        self.key(window, Qt.Key.Key_Return)
        self.assertFalse(screen.searching, "Enter keeps the search and closes the line")
        incoming = screen.current()
        self.assertEqual(incoming, model.pool_view(query="muller")["reserves"][0]["id"])
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(screen.picked, ("pool", incoming))
        self.assertEqual(screen.enter_text.text(), "Put here")
        self.key(window, Qt.Key.Key_Left)
        outgoing = screen.current()
        self.key(window, Qt.Key.Key_Return)
        self.assertIsNone(screen.picked)
        same.exchange(outgoing, incoming)
        self.assertEqual(model.state, same.state)
        self.assertEqual(model.view(), same.view())
        self.assertIn(incoming, model.state.managed_squad)

    def test_the_original_s_keys_keep_their_meaning(self):
        window, screen, model, same = self.squad()
        bar = self.bar(screen)
        for caps, text in ((("Ins",), "coming later"), (("R",), "next position"), (("C",), "club position"),
                           (("T",), "his tactics"), (("F2",), "new name"), (("Esc",), "desk"),
                           (("↑", "↓"), "player"), (("←", "→"), "squad / pool")):
            self.assertEqual(bar.get(caps), text, caps)
        word = screen.current()
        self.key(window, Qt.Key.Key_R)
        same.set_position(word, 1)
        self.assertEqual(model.state, same.state, "R is still the next position")
        self.key(window, Qt.Key.Key_C)
        same.club_position(word)
        self.assertEqual(model.state, same.state, "C is still the club position")


@CAREER
class Rename(App):
    def test_renaming_on_the_desk_equals_rename_manager_and_the_career_is_unsaved(self):
        model = career(HOLLAND)
        same = copy.deepcopy(model)
        window, desk = self.desk(model)
        self.tagged(desk, "GOAL2 ADDITION")
        self.assertFalse(model.unsaved)
        desk.highlight(self.option(desk, "manager's name"))
        self.key(window, Qt.Key.Key_Return)
        self.assertTrue(desk.naming)
        self.assertTrue(desk.name_field.isVisible())
        self.assertEqual(desk.enter_text.text(), "Give this name")
        self.fits(window)
        self.type(window, "Rinus Michels Senior")   # 20 characters: the line keeps 14, as S04's
        self.assertEqual(desk.name_field.text, "Rinus Michels "[:14])
        self.key(window, Qt.Key.Key_Return)
        self.assertFalse(desk.naming)
        self.assertEqual(model.manager, same.rename_manager("Rinus Michels "))
        self.assertEqual(model.state, same.state)
        self.assertTrue(model.unsaved, "the new name is unsaved progress")
        self.assertEqual(desk.manager["name"].text(), model.manager)
        self.assertIs(window.current(), desk)

    def test_esc_keeps_the_old_name(self):
        model = career(HOLLAND)
        window, desk = self.desk(model)
        desk.highlight(self.option(desk, "manager's name"))
        self.key(window, Qt.Key.Key_Return)
        self.type(window, "Cruijff")
        self.key(window, Qt.Key.Key_Escape)
        self.assertFalse(desk.naming)
        self.assertEqual(model.manager, "K Ees")
        self.assertFalse(model.unsaved)
        self.assertIs(window.current(), desk)


@CAREER
class NewCareer(App):
    def unsaved_desk(self):
        model = career(HOLLAND)
        model.rename_manager("Rinus Michels")
        self.assertTrue(model.unsaved)
        window, desk = self.desk(model)
        desk.highlight(self.option(desk, "new career"))
        self.key(window, Qt.Key.Key_Return)
        question = window.current()
        self.assertIsInstance(question, QuestionScreen)
        self.assertIn(SAVE_QUESTION, question.text.text())
        self.assertEqual(question.name_label.text(), "manager's desk · new career")
        self.fits(window)
        return window, desk, model

    def test_y_saves_first_then_shows_s03(self):
        window, desk, model = self.unsaved_desk()
        self.key(window, Qt.Key.Key_Y)
        box = window.current()
        self.assertIsInstance(box, SaveScreen)
        self.type(window, "Before the new career")
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), NewGameScreen)
        self.assertEqual(len(self.files()), 1)
        self.assertEqual(saves.read_meta(self.target.saves / self.files()[0])[0], "Before the new career")
        self.assertFalse(model.unsaved)
        # Esc on S03 returns to the desk and its career.
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)

    def test_n_shows_s03_without_saving(self):
        window, desk, model = self.unsaved_desk()
        self.key(window, Qt.Key.Key_N)
        self.assertIsInstance(window.current(), NewGameScreen)
        self.assertEqual(self.files(), [])
        self.assertTrue(model.unsaved)

    def test_esc_stays_on_the_desk(self):
        window, desk, model = self.unsaved_desk()
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)
        self.assertEqual(self.files(), [])

    def test_nothing_unsaved_goes_straight_to_s03(self):
        model = career(HOLLAND)
        self.assertFalse(model.unsaved)
        window, desk = self.desk(model)
        desk.highlight(self.option(desk, "new career"))
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), NewGameScreen)
        self.assertEqual(self.files(), [])


@CAREER
class StandaloneFriendly(App):
    def test_from_s02_to_full_time_on_s17_and_back_with_nothing_saved(self):
        from goal2.tests.test_pypy_worker_t152 import pypy
        from goal2.ui.friendly import FriendlyScreen
        from goal2.ui.s17_pitch import PitchScreen
        pypy()
        window = self.window()
        window.start()
        start = window.current()
        self.assertIsInstance(start, StartScreen)
        self.assertEqual(self.bar(start).get(("F",)), "friendly")
        self.tagged(start, "GOAL2 ADDITION")
        self.key(window, Qt.Key.Key_F)
        chooser = window.current()
        self.assertIsInstance(chooser, FriendlyScreen)
        self.tagged(chooser, "STANDALONE FRIENDLY")
        self.fits(window)
        names = chooser.browser.goaldat.country_names

        def pick(number):
            while chooser.highlighted_country() != number:
                position = next(i for i, c in enumerate(chooser.order) if c[0] == number)
                self.key(window, Qt.Key.Key_Down if position > chooser.index else Qt.Key.Key_Up)
            self.key(window, Qt.Key.Key_Return)

        pick(HOLLAND)
        self.assertEqual(chooser.chosen, [HOLLAND])
        self.assertEqual(chooser.sides["yours"].text(), names[HOLLAND])
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(chooser.chosen, [HOLLAND], "a country cannot play itself")
        self.assertIs(window.current(), chooser)
        written = []
        with mock.patch.object(saves, "write", side_effect=lambda *a, **k: written.append(a)), \
                mock.patch.object(DesktopModel, "save", side_effect=lambda *a, **k: written.append(a)):
            pick(GERMANY)
            pitch = window.current()
            self.assertIsInstance(pitch, PitchScreen)
            model = pitch.model
            self.assertIsNot(model, window.career)
            self.assertIsNone(window.career, "the friendly is no career")
            self.assertIsNone(model.state.campaign, "outside a career: DesktopModel.new_friendly's state")
            self.assertEqual(model.state.managed_country, HOLLAND)
            self.assertEqual(pitch.controller.display.countries, [names[HOLLAND], names[GERMANY]])
            before = model.state.match_count
            self.key(window, Qt.Key.Key_R)
            deadline = time.monotonic() + WAIT
            while window.current() is pitch:
                self.assertLess(time.monotonic(), deadline, "the friendly did not reach full time")
                self.app.processEvents()
                time.sleep(.001)
        self.assertIsNone(pitch.controller.error)
        self.assertIsNotNone(pitch.controller.outcome, "full time, published")
        self.assertIs(window.current(), start, "back on S02")
        self.assertEqual(model.state.match_count, before + 1)
        result = model.result_text().split("\n", 1)[0]
        self.assertIn("Full time:", start.message.text())
        self.assertIn(result, start.message.text())
        self.assertEqual(written, [], "nothing saved")
        self.assertEqual(self.files(), [])
        self.assertIsNone(window.career)
        self.fits(window)


if __name__ == "__main__":
    unittest.main()
