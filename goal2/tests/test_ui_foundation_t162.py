"""[designed: owner, 2026-11-03, #526, #536] T162: the new window's foundation (goal2/ui, docs/ui.md).

The claim it protects: every screen is drawn in the original's palette and the VGA font, says what it waits for,
and works with both keys and mouse. Visited here: the palette against the README's own table, the vendored font as
the application's font, the screen stack with its bottom bar and Enter hint, a click and its key reaching the same
handler, S01 over data_setup's check and copy, and S22 with a stand-in help text.

Nothing of the original is in this file (CLAUDE.md rule 14): the data files and the help text are stand-ins written
into temporary folders, checked against a stand-in manifest as test_import_help_hlp does.
"""
import hashlib
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from goal2.tests import requires
from goal2.tests.reflow_pending import assert_fits

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QFontDatabase  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup, fixed_page  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.home import HomeScreen  # noqa: E402
from goal2.ui.s01_import import ImportScreen  # noqa: E402
from goal2.ui.s02_start import StartScreen  # noqa: E402
from goal2.ui.s22_help import HelpScreen  # noqa: E402
from goal2.ui.screen import Screen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "docs" / "design" / "ui-2026-11" / "README.md"

STAND_IN = {"GOAL.DAT": b"stand-in data file\n", "e010-r0008-halftime.sav": b"stand-in template\n"}
STAND_IN_MANIFEST = tuple((name, hashlib.sha256(raw).hexdigest()) for name, raw in STAND_IN.items())
HELP = b"stand-in help file\n"
STAND_IN_OPTIONAL = (("GOAL.HLP", hashlib.sha256(HELP).hexdigest()),)
# A stand-in help text of this test's own: code page 437 bytes (0xC4 is a box-drawing line, 0x82 an e acute), CR LF
# line ends and the DOS end-of-file mark with bytes after it.
HELP_TEXT = (b"\xc4\xc4 T162 stand-in help \xc4\xc4\r\nfirst line, caf\x82\r\n"
             + b"".join(b"line %d\r\n" % n for n in range(60)) + b"\x1aafter the end mark")


def readme_palette():
    """The README's §3 palette table: role -> colour, as the table reads."""
    text = README.read_text(encoding="utf-8")
    section = text.split("**Colours**", 1)[1].split("- Role codes", 1)[0]
    rows = re.findall(r"^\s*\| ([^|`]+?) \| `(#[0-9a-f]{6})` \|", section, flags=re.M)
    return dict(rows)


class App(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.font_before = cls.app.font()

    @classmethod
    def tearDownClass(cls):
        cls.app.setFont(cls.font_before)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="goal2-t162-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        for name, value in (("WINDOW_MANIFEST", STAND_IN_MANIFEST), ("OPTIONAL", STAND_IN_OPTIONAL)):
            patcher = mock.patch.object(data_setup, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.target = data_setup.Paths(self.tmp / "goal2")
        self.offered = None

    def window(self):
        window = Window(self.target, choose=lambda: self.offered)
        window.resize(fixed_page.WIDTH, fixed_page.HEIGHT)
        window.show()
        self.app.processEvents()
        self.addCleanup(lambda: (window.close(), window.deleteLater(), self.app.processEvents()))
        return window

    def key(self, window, key):
        QTest.keyClick(window, key)
        self.app.processEvents()

    def click(self, widget):
        QTest.mouseClick(widget, Qt.MouseButton.LeftButton)
        self.app.processEvents()

    def folder(self, name, files):
        folder = self.tmp / name
        folder.mkdir()
        for file, raw in files.items():
            (folder / file).write_bytes(raw)
        return folder


class Look(App):
    def test_the_palette_is_the_readme_table(self):
        table = readme_palette()
        self.assertEqual(len(table), 20, "the README's palette table has 20 roles")  # [#583: the side colours are the kits]
        self.assertEqual(theme.PALETTE, table)
        named = {"ground": theme.GROUND, "text, bright": theme.TEXT_BRIGHT, "highlight bar": theme.HIGHLIGHT,
                 "key hints, magenta": theme.KEY_HINT, "headings, cyan": theme.HEADING, "values, yellow": theme.VALUE,
                 "goalkeeper": theme.GOALKEEPER, "defence": theme.DEFENCE, "midfield": theme.MIDFIELD,
                 "attack": theme.ATTACK}
        for role, colour in named.items():
            self.assertEqual(colour, table[role], role)

    def test_every_colour_of_the_style_sheet_is_the_palette(self):
        colours = set(re.findall(r"#[0-9a-fA-F]{6}\b", theme.stylesheet()))
        self.assertTrue(colours)
        self.assertLessEqual({c.lower() for c in colours}, set(theme.PALETTE.values()))

    def test_there_is_one_text_size(self):
        """[designed: owner, 2026-11-08, #667; T209] supersedes #598's 24 px text and 32 px headings."""
        sizes = [int(s) for s in re.findall(r"font-size:\s*(\d+)px", theme.stylesheet())]
        self.assertEqual(set(sizes), {theme.TEXT})
        self.assertEqual(theme.TEXT, 32)

    def test_the_font_is_the_vendored_pxplus_loaded_from_the_package(self):
        package_fonts = Path(theme.__file__).resolve().parent / "fonts"
        self.assertEqual(theme.FONT_FILE.resolve().parent, package_fonts)
        self.assertTrue((package_fonts / "LICENSE.TXT").is_file(), "CC BY-SA 4.0 ships beside the font")
        self.assertTrue((package_fonts / "PROVENANCE.md").is_file())
        self.assertEqual(hashlib.sha256(theme.FONT_FILE.read_bytes()).hexdigest(),
                         "c99fb740581471c2bd239a200c9f7a6c12f60a7099b0f0af795e405281bc2c5f")
        family = theme.install(self.app)
        self.assertEqual(family, "PxPlus IBM VGA 8x16")
        self.assertEqual(self.app.font().family(), family)
        self.assertEqual(self.app.font().pixelSize(), round(theme.TEXT * theme.STRETCH), "the one text size, 1.2 taller")
        self.assertEqual(self.app.font().stretch(), theme.stretch_percent(), "and narrowed back to one cell wide")
        self.assertEqual(QFontDatabase.applicationFontFamilies(theme.font_id()), [family])
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertRegex(pyproject, r'"goal2\.ui" = \[[^\]]*"fonts/\*\.ttf"[^\]]*"fonts/LICENSE\.TXT"')

    def test_the_page_scales_as_a_whole_with_the_window(self):
        window = self.window()
        window.start()
        window.resize(720, 540)   # the 4:3 page at half size
        self.app.processEvents()
        self.assertAlmostEqual(window.frame.scale, 0.5)
        self.assertEqual((window.page.width(), window.page.height()), (720, 540))
        self.assertIn(f"font-size: {round(theme.TEXT * theme.STRETCH * 0.5)}px", window.page.styleSheet(),
                      "32 px text, stretched 1.2, at half the page size")
        window.resize(1440, 900)
        self.app.processEvents()
        assert_fits(self, window)
class Probe(Screen):
    """A test screen: two options, one with its own key, recording what their handler did."""
    title = "probe"

    def __init__(self, window, log):
        super().__init__(window)
        self.log = log
        self.alpha = self.add_option("Alpha", lambda: self.chose("alpha"), key=Qt.Key.Key_A, enter="Do alpha")
        self.beta = self.add_option("Beta", lambda: self.chose("beta"), key=Qt.Key.Key_B, enter="Do beta")
        for option in (self.alpha, self.beta):
            self.body_layout.addWidget(option)
        self.body_layout.addStretch(1)

    def chose(self, what):
        self.log.append(what)
        return what


class Stack(App):
    def test_a_pushed_screen_lists_its_keys_and_esc_pops_it(self):
        window = self.window()
        home = window.replace_home(HomeScreen(window))
        log = []
        probe = window.push(Probe(window, log))
        self.assertIs(window.current(), probe)
        self.assertIs(window.page.currentWidget(), probe)
        self.assertEqual(probe.key_texts(), [(("F1",), "help"), (("Esc",), "back"), (("A",), "Alpha"),
                                             (("B",), "Beta"), (("↑", "↓"), "choose")])
        shown = [w.text() for w in probe.key_bar.findChildren(type(probe.name_label)) if w.isVisible()]
        for caption in ("F1", "help", "Esc", "back", "A", "Alpha", "B", "Beta", "↑", "↓", "choose"):
            self.assertIn(caption, shown)
        self.assertEqual(probe.name_label.text(), "probe")
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), home)
        self.assertEqual(window.stack, [home])
        self.assertEqual(log, [])

    def test_the_enter_hint_is_the_highlighted_options_action(self):
        window = self.window()
        window.replace_home(HomeScreen(window))
        log = []
        probe = window.push(Probe(window, log))
        self.assertTrue(probe.enter_hint.isVisible())
        self.assertEqual(probe.enter_text.text(), "Do alpha")
        self.assertEqual(probe.alpha.property("on"), True)
        self.key(window, Qt.Key.Key_Down)
        self.assertEqual(probe.enter_text.text(), "Do beta")
        self.assertEqual((probe.alpha.property("on"), probe.beta.property("on")), (False, True))
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(log, ["beta"])
        self.key(window, Qt.Key.Key_Up)
        self.assertEqual(probe.enter_text.text(), "Do alpha")

    def test_a_screen_says_what_it_waits_for(self):
        window = self.window()
        probe = window.replace_home(Probe(window, []))
        self.assertFalse(probe.wait_box.isVisible())
        probe.wait_for("Choose your option", "Enter: the highlighted option.")
        self.app.processEvents()
        self.assertTrue(probe.wait_box.isVisible())
        self.assertEqual(probe.wait_head.text(), "Choose your option")
        self.assertIn("Enter: the highlighted option.", probe.wait_detail.text())


class MouseEqualsKey(App):
    def test_clicking_an_option_and_pressing_its_key_call_the_same_handler(self):
        window = self.window()
        window.replace_home(HomeScreen(window))
        clicked, pressed = [], []
        probe = window.push(Probe(window, clicked))
        with mock.patch.object(probe, "chose", wraps=probe.chose) as chose:
            self.click(probe.beta)
            self.assertEqual(clicked, ["beta"])
            self.assertEqual(chose.call_args_list, [mock.call("beta")])
            self.assertEqual(probe.enter_text.text(), "Do beta", "the click highlights the option, as its key does")
            probe.log = pressed
            probe.highlight(0)
            self.key(window, Qt.Key.Key_B)
            self.assertEqual(pressed, ["beta"])
            self.assertEqual(chose.call_args_list, [mock.call("beta"), mock.call("beta")])
            self.assertEqual(probe.enter_text.text(), "Do beta")

    def test_the_enter_hint_and_the_bar_keys_click_as_their_keys(self):
        window = self.window()
        home = window.replace_home(HomeScreen(window))
        log = []
        probe = window.push(Probe(window, log))
        self.click(probe.enter_hint)
        self.key(window, Qt.Key.Key_Return)
        self.assertEqual(log, ["alpha", "alpha"])
        esc = [item for item in probe.key_bar.findChildren(type(probe.enter_hint))
               if getattr(item, "binding", None) is not None and item.binding.text == "back"]
        self.assertEqual(len(esc), 1)
        self.click(esc[0])
        self.assertIs(window.current(), home)


class ImportData(App):
    def screen(self, window):
        window.start()
        screen = window.current()
        self.assertIsInstance(screen, ImportScreen)
        return screen

    def test_the_first_start_opens_s01_with_every_file_and_its_keys(self):
        window = self.window()
        screen = self.screen(window)
        self.assertEqual(screen.name_label.text(), "first start")
        self.assertEqual(screen.enter_text.text(), "Choose folder…")
        self.assertEqual(screen.key_texts(), [(("F1",), "help"), (("Esc",), "quit")])
        texts = [w.text() for w in screen.findChildren(type(screen.name_label)) if w.isVisible()]
        for name in ("GOAL.DAT", "GOAL.HLP", "e010-r0008-halftime.sav"):
            self.assertIn(name, texts)
            self.assertEqual(screen.check_text(name), "not checked yet")
        self.assertIn("the original's help (F1), optional", texts)
        assert_fits(self, window)
    def test_a_folder_missing_goal_dat_shows_it_missing_and_does_not_continue(self):
        window = self.window()
        screen = self.screen(window)
        self.offered = str(self.folder("offered", {"e010-r0008-halftime.sav": STAND_IN["e010-r0008-halftime.sav"]}))
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), screen, "S01 refuses to continue")
        self.assertEqual(screen.check_text("GOAL.DAT"), "✗ missing in this folder")
        self.assertEqual(screen.cells["GOAL.DAT"].property("check"), "bad")
        self.assertEqual(screen.check_text("e010-r0008-halftime.sav"), "✓ found, verified")
        self.assertEqual(screen.check_text("GOAL.HLP"), "not in this folder (optional)")
        self.assertIn("GOAL.DAT is missing", screen.message, "data_setup's plain words are kept")
        self.assertTrue(screen.error.isVisible())
        self.assertFalse(self.target.root.exists(), "nothing is copied from a refused folder")
        assert_fits(self, window)
    def test_a_complete_folder_imports_and_continues(self):
        window = self.window()
        self.screen(window)
        self.offered = str(self.folder("offered", dict(STAND_IN, **{"GOAL.HLP": HELP})))
        self.click(window.current().enter_hint)
        self.assertIsInstance(window.current(), StartScreen)
        self.assertEqual(len(window.stack), 1)
        self.assertTrue(data_setup.complete(self.target.data, data_setup.WINDOW_MANIFEST))
        self.assertEqual(self.target.help.read_bytes(), HELP)

    def test_a_wrong_help_file_is_refused_and_a_missing_one_accepted(self):
        window = self.window()
        screen = self.screen(window)
        self.offered = str(self.folder("wrong", dict(STAND_IN, **{"GOAL.HLP": b"another file\n"})))
        self.key(window, Qt.Key.Key_Return)
        self.assertIs(window.current(), screen)
        self.assertEqual(screen.check_text("GOAL.HLP"), "✗ not the right file")
        self.assertIn("GOAL.HLP in", screen.message)
        self.assertIn("not the right file", screen.message)
        self.assertFalse(self.target.root.exists())
        self.offered = str(self.folder("without", STAND_IN))
        self.key(window, Qt.Key.Key_Return)
        self.assertIsInstance(window.current(), StartScreen)
        self.assertFalse(self.target.help.exists())

    def test_esc_quits_and_an_imported_folder_starts_at_home(self):
        window = self.window()
        self.screen(window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertFalse(window.isVisible())
        data_setup.import_folder(self.folder("offered", STAND_IN), self.target, data_setup.WINDOW_MANIFEST)
        again = self.window()
        again.start()
        self.assertIsInstance(again.current(), StartScreen)


class Help(App):
    def test_f1_opens_the_stand_in_help_and_esc_returns_to_the_same_screen(self):
        self.target.data.mkdir(parents=True)
        self.target.help.write_bytes(HELP_TEXT)
        window = self.window()
        home = window.replace_home(HomeScreen(window))
        probe = window.push(Probe(window, []))
        self.key(window, Qt.Key.Key_F1)
        screen = window.current()
        self.assertIsInstance(screen, HelpScreen)
        self.assertIs(screen.under, probe)
        text = screen.shown_text()
        self.assertTrue(text.startswith("── T162 stand-in help ──\nfirst line, café\nline 0\n"), text[:60])
        self.assertNotIn("\r", text)
        self.assertNotIn("after the end mark", text)
        self.assertEqual(screen.viewer.font().family(), theme.FONT_FAMILY)
        self.assertEqual(screen.key_texts(), [(("Esc",), "close"), (("↑", "↓"), "scroll"),
                                              (("PgUp", "PgDn"), "page")])
        bar = screen.viewer.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0, "the text scrolls")
        self.key(window, Qt.Key.Key_Down)
        line = screen.line_step()
        self.assertEqual(line, round(theme.TEXT * 1.35), "a line of the owner's normal text at the existing line height")
        self.assertEqual(bar.value(), line)
        self.key(window, Qt.Key.Key_PageDown)
        self.assertEqual(bar.value(), line + bar.pageStep())
        self.key(window, Qt.Key.Key_Up)
        self.assertEqual(bar.value(), bar.pageStep())
        assert_fits(self, window)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), probe)
        self.assertEqual(window.stack, [home, probe])
        self.key(window, Qt.Key.Key_F1)
        self.click(window.current().close_button)
        self.assertIs(window.current(), probe, "the Close button does what Esc does")

    def test_without_goal_hlp_f1_says_so_and_how_to_add_it(self):
        window = self.window()
        home = window.replace_home(HomeScreen(window))
        self.key(window, Qt.Key.Key_F1)
        screen = window.current()
        self.assertIsInstance(screen, HelpScreen)
        text = screen.shown_text()
        self.assertIn("GOAL.HLP was not imported", text)
        self.assertIn("import that folder again", text)
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), home)

    def test_f1_works_on_s01_before_anything_is_imported(self):
        window = self.window()
        window.start()
        s01 = window.current()
        self.key(window, Qt.Key.Key_F1)
        self.assertIn("GOAL.HLP was not imported", window.current().shown_text())
        self.key(window, Qt.Key.Key_Escape)
        self.assertIs(window.current(), s01)


if __name__ == "__main__":
    unittest.main()
