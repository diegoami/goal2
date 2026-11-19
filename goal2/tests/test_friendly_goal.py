"""[designed: T177] A watched standalone friendly (S02's F) plays on past its goals.

S17 hands a painted goal to its match day (`self.day.goal`), and `MatchController` stops polling the engine until
the goal is dismissed. The standalone friendly has no match day: its stand-in held only `stop`, so its first goal
raised AttributeError on every tick and the pitch froze; only R (quick result) got past it. T177's friendly test
presses R at once, so it never met a goal. Here a controller that has painted a goal is ticked once.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from goal2.tests import requires

requires.require(modules=("PySide6",))

from PySide6.QtWidgets import QApplication  # noqa: E402

from goal2.desktop import data_setup  # noqa: E402
from goal2.desktop.match_view import PLAYBACK_RATE, Display  # noqa: E402
from goal2.ui import theme  # noqa: E402
from goal2.ui.friendly import friendly_pitch, new_friendly  # noqa: E402
from goal2.ui.kits import Kits  # noqa: E402
from goal2.ui.window import Window  # noqa: E402

APP = QApplication.instance() or QApplication([])
CACHE = requires.CACHE
GOAL = {"kind": "goal", "minute": 12, "score": [1, 0], "data": {"player": 1, "team": 0}}


class GoalPaintedController:
    """MatchController after `painted` found a goal behind the watermark (`goal` set, not quick)."""

    def __init__(self):
        self.display = Display("t")
        self.display.countries, self.display.managed, self.display.kind = ["Holland", "Germany"], 0, "friendly"
        self.display.pitch_rate, self.display.roles = PLAYBACK_RATE, {}
        self.pending = self.error = self.outcome = self.notice = self.refusal = self.stop = None
        self.quick = self.finished = self.commentary_paused = self.edit_pending = False
        self.running, self.note, self.goal, self.dismissed = True, "", dict(GOAL), 0

    def shown(self):
        return []

    def frame_or_event(self):
        return 12, [1, 0]

    def tick(self, now):
        return False

    def painted(self, sequence):
        pass

    def dismiss_goal(self):
        self.goal = None
        self.dismissed += 1

    def cancel(self):
        self.finished = True


class Bridge:
    def close(self):
        pass


@requires.need(files=("GOAL.DAT", data_setup.TEMPLATE_NAME))
class FriendlyGoal(unittest.TestCase):
    def setUp(self):
        theme.install(APP)
        self.root = Path(tempfile.mkdtemp(prefix="goal2-friendly-goal-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "data").mkdir()
        for name in (data_setup.DATA_NAME, data_setup.TEMPLATE_NAME):
            shutil.copy(CACHE / name, self.root / "data" / name)
        self.target = data_setup.Paths(self.root)

    def test_a_painted_goal_is_dismissed_and_play_goes_on(self):
        import goal2.ui.s17_pitch as s17
        model = new_friendly(self.target, 20)
        window = Window(self.target)
        self.addCleanup(window.deleteLater)
        controller = GoalPaintedController()
        kits = s17.for_fixture
        s17.for_fixture = lambda m, f: Kits((4, 15), (2, 2))
        self.addCleanup(setattr, s17, "for_fixture", kits)
        pitch = window.push(friendly_pitch()(window, model, controller, Bridge()))
        pitch.timer.stop()
        pitch.tick()
        self.assertIsNone(controller.goal, "the friendly's goal was never dismissed: the engine is no longer polled")
        self.assertEqual(controller.dismissed, 1)
        self.assertIs(window.current(), pitch)


if __name__ == "__main__":
    unittest.main()
