"""[designed: #896] A finished assistant request frees the shared engine before its result is visible.

`best_twenty_jobs` posted the result and released the shared engine's claim afterwards, in `finally`.
The squad screen could read the result in between; an A pressed at once then failed to claim the engine
and S08 said "The assistant is not available right now". Under the parallel gate's load the gap was wide
enough for `test_ui_selected_squad_t239` to hit it (#896). The test below holds the release back on
purpose: a second request started right after the first result must still start.
"""
import threading
import time
import unittest

from goal2.tests import requires
from goal2.tests.test_assistant_pipe_t183c import model

HOLD = 3.0   # seconds the release is held back: far wider than any scheduling gap


@requires.need(**requires.HALFTIME)
class ReleaseBeforeResult(unittest.TestCase):
    def test_a_second_request_starts_as_soon_as_the_first_result_is_read(self):
        from goal2.game.best_twenty_jobs import for_model
        m = model()
        jobs = for_model(m)
        self.addCleanup(jobs.close)
        shared = jobs.shared
        release, gate = shared.release, threading.Event()
        self.addCleanup(gate.set)

        def held_release(handle):
            gate.wait(HOLD)
            release(handle)

        shared.release = held_release
        self.addCleanup(setattr, shared, "release", release)
        token = jobs.start()
        deadline, result = time.monotonic() + 120, None
        while result is None:
            self.assertLess(time.monotonic(), deadline, "the first request did not finish")
            result = jobs.poll(token)
            time.sleep(0.01)
        self.assertEqual(result["status"], "complete")
        try:
            second = jobs.start()   # before #896's fix: ValueError, the engine still claimed by the first
        finally:
            gate.set()
        self.assertIsNotNone(second)
        self.assertTrue(jobs.cancel(second))
        deadline = time.monotonic() + 120
        while jobs.poll(second) is None:
            self.assertLess(time.monotonic(), deadline, "the second request did not end")
            time.sleep(0.01)


if __name__ == "__main__":
    unittest.main()
