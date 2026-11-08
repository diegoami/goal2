"""[designed: owner, 2026-11-03, #526; T168, #542] S21: save under a name (F7), quit (F10), and the close button.

The claim it protects: a career saved in the new window loads back equal, and nothing the player did since the last
save is lost without a question.
Visited here:
- **Round trip:** a new career, changed by a swap on S08, saved with F7 under a typed name, loads back from S02 with
  `view()` equal, and the name is listed on S02 and proposed by F7 again;
- **Replace:** a name another save has asks first: N keeps the old file, Y replaces it; the career's own name asks
  nothing;
- **Quit:** F10 then N stays; F10, Y with nothing unsaved quits with no second question; with unsaved progress it asks
  to save: Y saves then quits, N quits without writing;
- **Close button:** with unsaved progress it asks: Esc stays with the state as it was, Y saves and closes, N closes;
  with nothing unsaved it closes at once; a screen with something running is ended and leaves before the question;
- **Never the session file:** no code of the new window calls the model's save on `save_path`; saving twice keeps
  both saves readable on S02;
- **A failed save** (an unwritable folder) says why and leaves the earlier save as it was, its progress unsaved.

The careers read GOAL.DAT and the E010 half-time template from the git-ignored `.cache/` and skip without them
(goal2/tests/requires.py); nothing of the original is in this file (CLAUDE.md rule 14).
"""
import copy
import os
import re
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.ui import s03_new_game, saves  # noqa: E402
from goal2.ui.s02_start import StartScreen  # noqa: E402
from goal2.ui.s06_desk import DeskScreen  # noqa: E402
from goal2.ui.s08_squad import SquadScreen  # noqa: E402
from goal2.ui.s21_save import QUIT_TEXT, SAVE_QUESTION, QuestionScreen, SaveScreen  # noqa: E402
from goal2.ui.screen import Screen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

CACHE = requires.CACHE
CAREER = requires.need(**requires.HALFTIME)
HOLLAND = 20
UI = Path(__file__).resolve().parents[1] / "ui"
_BASE = {}


def holland():
    """A fresh copy of one new Holland career starting in 2028 (opened once per run)."""
    if "model" not in _BASE:
        folder = tempfile.mkdtemp(prefix="goal2-t168-")
        _BASE["folder"] = folder
        model = DesktopModel.open(CACHE / data_setup.TEMPLATE_NAME, CACHE / data_setup.DATA_NAME,
                                  Path(folder) / "new-career.g2game", country=HOLLAND)
        model.new_campaign(HOLLAND, 2028)
        model.rename_manager("K Ees")
        _BASE["model"] = model
    return copy.deepcopy(_BASE["model"])


def tearDownModule():
    if "folder" in _BASE:
        shutil.rmtree(_BASE["folder"], ignore_errors=True)


def a_swap(model):
    """A starter and a bench player change places, as S08's Enter, Enter does (`DesktopModel.swap`)."""
    state = model.state
    out = state.starting_eleven[3]
    incoming = next(w for w in state.managed_squad if w not in state.starting_eleven)
    model.swap(out, incoming)


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t168-ui-"))
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

    def desk(self, model=None):
        window = self.window()
        return window, window.open_career(model or holland())

    def key(self, window, key, times=1):
        for _ in range(times):
            QTest.keyClick(window, key)
            self.app.processEvents()

    def type(self, window, text):
        QTest.keyClicks(window, text)
        self.app.processEvents()

    def bar(self, screen):
        return dict((caps, text) for caps, text in screen.key_texts())

    def fits(self, window):
        self.app.processEvents()
        self.assertEqual(fixed_page.problems(window), [])

    def files(self):
        return sorted(p.name for p in self.target.saves.glob("*")) if self.target.saves.is_dir() else []

    def save_with_f7(self, window, name, clear=False):
        """F7, type `name` (over the proposal), Enter."""
        self.key(window, Qt.Key.Key_F7)
        box = window.current()
        self.assertIsInstance(box, SaveScreen)
        if clear:
            self.key(window, Qt.Key.Key_Backspace, len(box.field.text))
        self.type(window, name)
        self.key(window, Qt.Key.Key_Return)
        return box

    def saved_career(self, name="Kept career"):
        """A career whose progress is saved: nothing unsaved."""
        model = holland()
        saves.write(model, self.target.saves, name)
        self.assertFalse(model.unsaved)
        return model

    def assertQuestion(self, window, text):
        screen = window.current()
        self.assertIsInstance(screen, QuestionScreen)
        self.assertIn(text, screen.text.text())
        return screen


@CAREER
class RoundTrip(App):
    def test_a_new_career_swapped_on_s08_saved_with_f7_loads_back_equal(self):
        window, desk = self.desk()
        model = desk.model
        self.key(window, Qt.Key.Key_Space)
        squad = window.current()
        self.assertIsInstance(squad, SquadScreen)
        before = list(model.state.starting_eleven)
        while squad.cursor["squad"] < 3:
            self.key(window, Qt.Key.Key_Down)
        self.key(window, Qt.Key.Key_Return)
        while squad.cursor["squad"] < 14:
            self.key(window, Qt.Key.Key_Down)
        self.key(window, Qt.Key.Key_Return)
        self.assertNotEqual(model.state.starting_eleven, before, "the swap changed the eleven")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)
        self.assertTrue(model.unsaved)
        # F7: the box over the desk, with no name proposed for a new career.
        self.key(window, Qt.Key.Key_F7)
        box = window.current()
        self.assertIsInstance(box, SaveScreen)
        self.assertEqual(box.name_label.text(), "manager's desk · save", "as the mockup's title")
        self.assertEqual(box.field.text, "", "a new career proposes no name")
        self.assertEqual(self.bar(box), {("Esc",): "cancel"})
        self.assertEqual(box.enter_text.text(), "Save")
        self.fits(window)
        name = "Holland after round 1"
        self.type(window, name)
        self.assertEqual(box.field.text, name)
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), desk)
        self.assertIn(f"Saved as “{name}”", desk.note.text())
        self.assertFalse(model.unsaved, "saved: nothing unsaved")
        self.assertEqual(model.save_path.suffix, saves.SUFFIX)
        self.assertEqual(saves.read_meta(model.save_path)[0], name)
        # S02 lists it at once, newest first, and loads it back equal.
        again = self.window()
        again.start()
        start = again.current()
        self.assertIsInstance(start, StartScreen)
        self.assertEqual(start.rows[0].cells[0].text(), name)
        self.key(again, Qt.Key.Key_Return)
        loaded = again.current()
        self.assertIsInstance(loaded, DeskScreen)
        self.assertEqual(loaded.model.view(), model.view())
        self.assertEqual(loaded.model.state, model.state)
        self.assertFalse(loaded.model.unsaved)
        # F7 on the loaded career proposes its name; the first key typed replaces the proposal.
        self.key(again, Qt.Key.Key_F7)
        box = again.current()
        self.assertEqual(box.field.text, name)
        self.type(again, "X")
        self.assertEqual(box.field.text, "X", "the first key typed replaces the proposal (t156-237)")
        self.key(again, Qt.Key.Key_Escape)
        self.assertIs(again.current(), loaded, "Esc cancels")
        self.assertEqual(self.files(), ["holland-after-round-1.g2game"])


@CAREER
class Replace(App):
    def test_another_saves_name_asks_n_keeps_y_replaces(self):
        other = holland()
        a_swap(other)
        older = saves.write(other, self.target.saves, "Other career")
        kept = older.read_bytes()
        window, desk = self.desk()
        model = desk.model
        box = self.save_with_f7(window, "Other career")
        self.assertIs(window.current(), box, "the box asks before replacing")
        self.assertIn("Replace it?", box.text.text())
        self.assertEqual(self.bar(box), {("Y",): "replace", ("N",): "keep it", ("Esc",): "cancel"})
        self.assertFalse(box.field.isVisible())
        self.fits(window)
        self.key(window, Qt.Key.Key_N)
        self.assertIs(window.current(), box, "N returns to the name")
        self.assertTrue(box.field.isVisible())
        self.assertEqual(older.read_bytes(), kept, "N keeps the old file")
        self.assertTrue(model.unsaved)
        self.key(window, Qt.Key.Key_Return)
        self.assertIn("Replace it?", box.text.text())
        self.key(window, Qt.Key.Key_Y)
        self.assertIs(window.current(), desk)
        self.assertNotEqual(older.read_bytes(), kept, "Y replaces it")
        self.assertEqual(saves.load(older, self.target.goal_dat).state, model.state)
        self.assertEqual(self.files(), ["other-career.g2game"])
        # The career's own name asks nothing.
        a_swap(model)
        self.key(window, Qt.Key.Key_F7)
        self.assertEqual(window.current().field.text, "Other career")
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), desk, "its own save is replaced without a question")
        self.assertEqual(saves.load(older, self.target.goal_dat).state, model.state)


@CAREER
class Quit(App):
    def test_f10_then_n_stays(self):
        window, desk = self.desk()
        self.key(window, Qt.Key.Key_F10)
        question = self.assertQuestion(window, QUIT_TEXT)
        self.assertEqual(question.name_label.text(), "manager's desk · quit")
        self.assertEqual(self.bar(question), {("Y",): "yes", ("N",): "no", ("Esc",): "no"})
        self.fits(window)
        self.key(window, Qt.Key.Key_N)
        self.assertIs(window.current(), desk)
        self.assertTrue(window.isVisible())

    def test_f10_y_with_nothing_unsaved_quits_with_no_second_question(self):
        window, desk = self.desk(self.saved_career())
        pushed = []
        with mock.patch.object(window, "push", side_effect=lambda s: (pushed.append(s), Window.push(window, s))[1]):
            self.key(window, Qt.Key.Key_F10)
            self.key(window, Qt.Key.Key_Y)
        self.assertFalse(window.isVisible(), "quit")
        self.assertEqual([type(s) for s in pushed], [QuestionScreen], "one question only")

    def test_f10_y_with_unsaved_progress_asks_y_saves_then_quits(self):
        window, desk = self.desk()
        self.key(window, Qt.Key.Key_F10)
        self.key(window, Qt.Key.Key_Y)
        question = self.assertQuestion(window, SAVE_QUESTION)
        self.assertEqual(self.bar(question), {("Y",): "yes", ("N",): "no", ("Esc",): "cancel"})
        self.fits(window)
        self.key(window, Qt.Key.Key_Y)
        self.assertIsInstance(window.current(), SaveScreen)
        self.assertTrue(window.isVisible())
        self.type(window, "Before quitting")
        self.key(window, Qt.Key.Key_Return)
        self.assertFalse(window.isVisible(), "saved, then quit")
        self.assertEqual(self.files(), ["before-quitting.g2game"])
        self.assertEqual(saves.load(self.target.saves / "before-quitting.g2game", self.target.goal_dat).state,
                         desk.model.state)

    def test_f10_y_with_unsaved_progress_n_quits_without_writing(self):
        window, desk = self.desk()
        self.key(window, Qt.Key.Key_F10)
        self.key(window, Qt.Key.Key_Y)
        self.assertQuestion(window, SAVE_QUESTION)
        self.key(window, Qt.Key.Key_N)
        self.assertFalse(window.isVisible())
        self.assertEqual(self.files(), [])


@CAREER
class CloseButton(App):
    def test_with_unsaved_progress_esc_stays_with_its_state(self):
        window, desk = self.desk()
        state = copy.deepcopy(desk.model.state)
        window.close()
        self.app.processEvents()
        self.assertTrue(window.isVisible(), "the window asks first")
        self.assertQuestion(window, SAVE_QUESTION)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)
        self.assertTrue(window.isVisible())
        self.assertEqual(desk.model.state, state)
        self.assertTrue(desk.model.unsaved)
        self.assertEqual(self.files(), [])

    def test_with_unsaved_progress_y_saves_and_closes(self):
        window, desk = self.desk()
        window.close()
        self.app.processEvents()
        self.assertQuestion(window, SAVE_QUESTION)
        self.key(window, Qt.Key.Key_Y)
        self.type(window, "Closing time")
        self.key(window, Qt.Key.Key_Return)
        self.assertFalse(window.isVisible())
        self.assertEqual(self.files(), ["closing-time.g2game"])

    def test_with_unsaved_progress_n_closes_without_writing(self):
        window, desk = self.desk()
        window.close()
        self.app.processEvents()
        self.assertQuestion(window, SAVE_QUESTION)
        self.key(window, Qt.Key.Key_N)
        self.assertFalse(window.isVisible())
        self.assertEqual(self.files(), [])

    def test_with_nothing_unsaved_it_closes_at_once(self):
        window, desk = self.desk(self.saved_career())
        window.close()
        self.app.processEvents()
        self.assertFalse(window.isVisible())

    def test_a_running_screen_is_ended_and_leaves_before_the_question(self):
        window, desk = self.desk()

        class Running(Screen):
            title = "running"
            ended = False

            def closing(self):
                self.ended = True
        running = window.push(Running(window))
        window.close()
        self.app.processEvents()
        self.assertTrue(running.ended, "what runs is ended first, as T166's close")
        self.assertQuestion(window, SAVE_QUESTION)
        self.assertEqual(window.stack[0], desk)
        self.assertNotIn(running, window.stack)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)


@CAREER
class NeverTheSessionFile(App):
    def test_no_code_of_the_new_window_saves_on_save_path(self):
        calls = []
        for path in sorted(UI.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            calls += [f"{path.name}: {m.group(0)}" for m in re.finditer(r"\.save\([^)]*save_path", text)]
        self.assertEqual(calls, [])

    def test_saving_twice_keeps_both_saves_readable_on_s02(self):
        window, desk = self.desk()
        model = desk.model
        written = []
        real = DesktopModel.save

        def recorded(self_, path):
            written.append((Path(path), Path(self_.save_path)))
            return real(self_, path)
        with mock.patch.object(DesktopModel, "save", recorded):
            self.save_with_f7(window, "First")
            a_swap(model)
            self.save_with_f7(window, "Second", clear=True)
            a_swap(model)
            self.save_with_f7(window, "Second", clear=True)   # its own name again
        self.assertEqual(len(written), 3)
        for path, session in written:
            self.assertNotEqual(path, session, "never the model's save_path")
            self.assertNotEqual(path.suffix, saves.SUFFIX, "never a save list's file")
            self.assertFalse(str(path).startswith(str(self.target.saves)))
        again = self.window()
        again.start()
        start = again.current()
        self.assertEqual([e.name for e in start.entries], ["Second", "First"])
        self.assertTrue(all(e.model is not None for e in start.entries), [e.error for e in start.entries])
        self.assertEqual(start.entries[0].model.state, model.state)


@CAREER
class FailedSave(App):
    def test_an_unwritable_folder_says_why_and_keeps_the_earlier_save(self):
        window, desk = self.desk()
        model = desk.model
        self.save_with_f7(window, "Kept career")
        earlier = self.target.saves / "kept-career.g2game"
        kept = earlier.read_bytes()
        a_swap(model)
        self.assertTrue(model.unsaved)
        # The folder cannot take a new file: its partial file's place is taken by a folder, and on POSIX the folder
        # is read only too (Windows ignores a folder's read-only mark).
        (self.target.saves / (earlier.name + ".part")).mkdir()
        mode = stat.S_IMODE(os.stat(self.target.saves).st_mode)
        if os.name == "posix":
            os.chmod(self.target.saves, stat.S_IRUSR | stat.S_IXUSR)
            self.addCleanup(os.chmod, self.target.saves, mode)
        self.key(window, Qt.Key.Key_F7)
        box = window.current()
        self.assertEqual(box.field.text, "Kept career")
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), box, "the box stays")
        self.assertTrue(box.problem.isVisible())
        self.assertIn("The game was not saved: cannot write", box.problem.text())
        self.assertIn("Nothing was replaced", box.problem.text())
        self.fits(window)
        self.assertEqual(earlier.read_bytes(), kept, "the earlier save is unchanged")
        self.assertTrue(model.unsaved, "the progress is still unsaved")
        self.assertEqual(model.save_path, earlier)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), desk)


if __name__ == "__main__":
    unittest.main()
