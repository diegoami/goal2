"""[designed: T167; S15/S20 design] S15's *match stats* opens S20 at every menu time that offers it.

S15 is built with phase "stop" after S18's substitution notice and "pause" after S17's bench request, and its
*match stats* option stays enabled there (goal2/ui/match_day.py, `show_stats`). S20 named only half, extra and
full time, so those two raised KeyError and the stats never opened.
"""
import unittest

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.ui import s15_match_menu, s20_board  # noqa: E402

APP = QApplication.instance() or QApplication([])


class StubWindow:
    family = None

    def open_help(self):
        pass

    def pop(self):
        pass


class Kits:
    def colour(self, team):
        return "#ffffff"


class BoardAtEveryMenuTime(unittest.TestCase):
    def test_every_phase_with_match_stats_has_a_board_time(self):
        # "before" is refused by show_stats itself: no statistics before kick-off.
        for phase in set(s15_match_menu.TIMES) - {"before"}:
            with self.subTest(phase=phase):
                data = s20_board.board([], phase, False)
                screen = s20_board.BoardScreen(StubWindow(), None, ["A", "B"], "FRIENDLY", phase, data,
                                               lambda note: None, Kits())
                self.assertIn(s20_board.TIMES[phase].lower(), screen.title)
                screen.deleteLater()


if __name__ == "__main__":
    unittest.main()
