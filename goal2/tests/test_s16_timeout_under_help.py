"""[designed: T167; confirmed: F030, the taker's 10 s wait] S16's wait running out while F1's help is open returns to S17.

S16's wait keeps running under S22 (F1 is on S16's bar), and `MatchDay._chosen` popped one screen, "S16, back to
S17". With help on top that pop removed S22: the match resumed underneath while S16 stayed on top, done, with no Esc
and Enter/C ignored, a dead end over the running match.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import QEventLoop, Qt, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.ui import match_day, s16_choose, theme  # noqa: E402
from goal2.ui.s22_help import HelpScreen  # noqa: E402
from goal2.ui.screen import Screen  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

APP = QApplication.instance() or QApplication([])
CACHE = requires.CACHE


class Pitch(Screen):
    """Stands in for S17: it records the answer it is resumed with."""
    title = "pitch"

    def __init__(self, window):
        super().__init__(window)
        self.resumed = []

    def resume(self, value):
        self.resumed.append(value)


@requires.need(**requires.HALFTIME)
class TimeoutUnderHelp(unittest.TestCase):
    def setUp(self):
        theme.install(APP)
        root = Path(tempfile.mkdtemp(prefix="goal2-s16-help-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "data").mkdir()
        for name in (data_setup.DATA_NAME, data_setup.TEMPLATE_NAME):
            shutil.copy(CACHE / name, root / "data" / name)
        self.target = data_setup.Paths(root)
        model = DesktopModel.open(self.target.data / data_setup.TEMPLATE_NAME, self.target.goal_dat,
                                  root / "x.g2game", country=20)
        model.new_campaign(20, 2028)
        model.rename_manager("K Ees")
        self.model = model

    def test_the_wait_running_out_under_help_returns_to_the_pitch(self):
        window = Window(self.target)
        self.addCleanup(window.deleteLater)
        window.open_career(self.model)
        pitch = window.push(Pitch(window))
        day = match_day.MatchDay(window, self.model)
        eleven = list(self.model.state.starting_eleven)
        with patch.object(s16_choose, "WAIT_MS", 50):
            choose = window.push(s16_choose.ChooseScreen(window, self.model, "taker", eleven, eleven[0],
                                                         lambda word: day._chosen(pitch, {"taker": word}), role=2))
        choose.handle_key(Qt.Key.Key_F1)
        self.assertIsInstance(window.current(), HelpScreen)
        loop = QEventLoop()
        QTimer.singleShot(400, loop.quit)
        loop.exec()
        self.assertEqual(pitch.resumed, [{"taker": None}])
        self.assertIs(window.current(), pitch, [type(s).__name__ for s in window.stack])


if __name__ == "__main__":
    unittest.main()
