"""[designed: T165] While S08's name line is open (F2), a click on another row does not move the cursor.

The keys are held while the name is typed (↑↓ do nothing), but `click_row` moved the cursor, and Enter then gave
the typed name to the player clicked, not to the one F2 opened the line for.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup  # noqa: E402
from goal2.desktop.model import DesktopModel  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.s08_squad import open_squad  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

APP = QApplication.instance() or QApplication([])
CACHE = requires.CACHE


@requires.need(**requires.HALFTIME)
class ClickWhileRenaming(unittest.TestCase):
    def test_enter_renames_the_player_f2_opened(self):
        theme.install(APP)
        root = Path(tempfile.mkdtemp(prefix="goal2-s08-rename-"))
        self.addCleanup(shutil.rmtree, root, True)
        (root / "data").mkdir()
        for name in (data_setup.DATA_NAME, data_setup.TEMPLATE_NAME):
            shutil.copy(CACHE / name, root / "data" / name)
        target = data_setup.Paths(root)
        model = DesktopModel.open(target.data / data_setup.TEMPLATE_NAME, target.goal_dat, root / "x.g2game",
                                  country=20)
        model.new_campaign(20, 2028)
        model.rename_manager("K Ees")
        window = Window(target)
        self.addCleanup(window.deleteLater)
        window.open_career(model)
        squad = open_squad(window, model)
        first = squad.current()
        other = model.state.managed_squad[5]
        squad.handle_key(Qt.Key.Key_F2)
        squad.card.name_line.edit.setText("Zzzname")
        squad.strip.rows[5].chosen.emit(5)              # a click on the sixth row while the line is open
        self.assertEqual(squad.current(), first)
        squad.handle_key(Qt.Key.Key_Return)
        self.assertEqual(model.goaldat.player_names[first].split()[-1], "Zzzname")
        self.assertNotIn("Zzzname", model.goaldat.player_names[other])


if __name__ == "__main__":
    unittest.main()
