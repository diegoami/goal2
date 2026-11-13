"""T223 (#428, #455): the original's delay 214B:1E09 served at its entry, and its milliseconds waited by the window.

The career is T140's: Italy, 2028, from the recorded date-call state (e039-r0005-date-call.sav) through the original's
own new game (CoreNewGame), watched from its first match. [confirmed: #455 comment 2026-10-27T09:15:47Z, #429 comment
2026-10-27T08:51:02Z] At speed 2 its pose 421 is Signori's wide shot ("just wide of post", "GOAL KICK", the whistle's
1,708 calls of 214B:1E09(1) from 214B:1F81) and pose 893 Di Chiara's goal, followed by the action replay question
(0791:0B7C: wait_or_key's 600 polls with 214B:1E09(10) after each). GOAL.DAT and the state are read from .cache/
(docs/artifacts.md); nothing of the original is in this file.

Done-when 1 is `Equal`: each run is played twice from the same core, (a) with `Core.delays_served = False` (the loop
executes) and (b) served, and every wait is compared: kind, site, polls, the screens passed, the milliseconds asked,
the text page, the pitch and the commentary read from memory, the registers and the whole memory. The fast gate plays
the two bounded stretches; `GOAL2_SLOW=1` plays a whole first half at each speed 0..5. `Serve` checks the served
routine against its loop call by call, and `Window` (Done-when 3) the window's note and the replay countdown.
"""
import hashlib
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.tests import requires

NEEDS = dict(modules=("unicorn",), files=("e039-r0005-date-call.sav", "GOAL.DAT"))
WIDE, GOAL = 421, 893           # the poses of the wide shot and of the goal at speed 2 (module docstring)
WHISTLE_MS = 1708               # [confirmed: #455's trace] the wide shot's whistle: 1,708 calls of 214B:1E09(1)
PROMPT_MS = 600 * 10            # [confirmed: F030; seg_0791_02.asm 0BD0] wait_or_key(600), 214B:1E09(10) per poll
_SAVES = {}


def scratch():
    return Path(tempfile.gettempdir()) / "unused-t223.g2core"


def career():
    """The manager menu of T140's career (a core save, made once)."""
    if "menu" not in _SAVES:
        from goal2.desktop.core_model import CoreNewGame
        model, _ = CoreNewGame(requires.CACHE / "e039-r0005-date-call.sav", requires.CACHE / "GOAL.DAT",
                               scratch()).start(2028, 16, "A Test")
        _SAVES["menu"] = model.core.save()
    return load(_SAVES["menu"])


def load(blob):
    from goal2.core import Core
    return Core.load(blob, goal_dat=requires.CACHE / "GOAL.DAT")


def kick_off(core, speed):
    from goal2.core.driver import Driver
    d = Driver(core)
    d.round_start(watch=True)
    with core.live_frames():
        d.kick_off(watch=True, speed=speed)
    return d


def step(d):
    """One watched step as the desktop takes it: the computer's taker, no key at a live poll, the replay question left
    to end by itself. False at half time (or any other stop)."""
    kind = d.wait.kind
    with d.core.live_frames():
        if kind == "set-piece-select":
            d.taker_key("c")
        elif kind == "match-live":
            d.live_step()
        elif kind in d.REPLAY_KINDS:
            d.replay_timeout()
        else:
            return False
    return True


def at_pose(n, speed=2):
    """A core save at the n-th wait of the first half at `speed` (served), made once."""
    key = (n, speed)
    if key not in _SAVES:
        d = kick_off(career(), speed)
        for _ in range(n):
            if not step(d):
                raise AssertionError(f"the half ended before wait {n}")
        _SAVES[key] = d.core.save()
    return _SAVES[key]


def record(d, cursor):
    """What a wait is: everything compared between the two runs."""
    from goal2.core import views
    w, core = d.wait, d.core
    cursor, lines = views.commentary(w.state, cursor)
    pitch = views.pitch(w.state, 0, 0) if w.kind == "match-live" else None
    snap = core.m.snapshot()
    return cursor, dict(kind=w.kind, site=w.site, poll=w.poll, polls=w.polls, delay_ms=w.delay_ms,
                        passed=[(p.kind, p.polls, p.text, p.keys) for p in w.passed], text=w.text, pitch=pitch,
                        commentary=lines, regs=snap["regs"], memory=hashlib.sha256(snap["memory"]).hexdigest())


def play(blob, served, until=None, steps=None):
    """The waits from the core save `blob` with the delays served or executed, for `steps` steps or to `until`."""
    core = load(blob)
    core.delays_served = served
    from goal2.core.driver import Driver
    d = Driver(core)
    asked = []
    core.on_delay = lambda ms, sound: asked.append((ms, sound))
    cursor, out = 0, []
    while True:
        cursor, rec = record(d, cursor)
        out.append(rec)
        if (steps is not None and len(out) > steps) or d.wait.kind == until or not step(d):
            break
    end = core.memory()[core.m.DS * 16:core.m.DS * 16 + 0x10000]
    return out, asked, end, d


@requires.need(**NEEDS)
class Equal(unittest.TestCase):
    """Done-when 1: the same waits, frames, commentary, score and DS whether the delay runs or is served."""

    def assert_same(self, a, b):
        self.assertEqual(len(a[0]), len(b[0]))
        for i, (x, y) in enumerate(zip(a[0], b[0])):
            self.assertEqual(x, y, f"wait {i}")
        self.assertEqual(a[1], b[1], "the delays asked")
        self.assertEqual(a[2], b[2], "DS at the end")

    def test_the_wide_shot_transition(self):
        blob = at_pose(WIDE - 6)
        t = time.perf_counter()
        executed = play(blob, False, steps=40)
        slow = time.perf_counter() - t
        t = time.perf_counter()
        served = play(blob, True, steps=40)
        fast = time.perf_counter() - t
        self.assert_same(executed, served)
        texts = [line["text"] for rec in served[0] for line in rec["commentary"]]
        self.assertIn("just wide of post", texts)
        self.assertIn("*** GOAL KICK ***", texts)
        whistle = [ms for ms, sound in served[1] if sound == "whistle"]
        self.assertEqual((sum(whistle), len(whistle)), (WHISTLE_MS, WHISTLE_MS))
        self.assertLess(fast, slow, (fast, slow))

    def test_a_goal_and_its_replay_prompt(self):
        blob = at_pose(GOAL - 3)
        executed = play(blob, False, steps=20)
        served = play(blob, True, steps=20)
        self.assert_same(executed, served)
        kinds = [rec["kind"] for rec in served[0]]
        self.assertIn("action-replay-prompt", kinds)
        texts = [line["text"] for rec in served[0] for line in rec["commentary"]]
        self.assertIn("**** GOAL **** by Di Chiara", texts)
        prompt = kinds.index("action-replay-prompt")
        # the question's 600 polls, with the per-slot pacing of the pose that follows it
        self.assertEqual(sum(ms for ms, _ in served[1] if ms == 10), PROMPT_MS)
        self.assertEqual(served[0][prompt + 1]["kind"], "match-live")
        self.assertGreaterEqual(served[0][prompt + 1]["delay_ms"], PROMPT_MS)

    @requires.need(slow=True)
    def test_a_whole_first_half_at_each_speed(self):
        from goal2.core import views
        for speed in range(6):
            with self.subTest(speed=speed):
                d = kick_off(career(), speed)
                blob = d.core.save()
                executed = play(blob, False, until="match-menu-halftime")
                served = play(blob, True, until="match-menu-halftime")
                self.assertEqual(served[3].wait.kind, "match-menu-halftime")
                self.assert_same(executed, served)
                self.assertEqual(views.board(executed[3].wait.state)["score"], views.board(served[3].wait.state)["score"])
                self.assertEqual(views.match_speed(served[3].wait.state), speed)


@requires.need(**NEEDS)
class Serve(unittest.TestCase):
    """Item 1: the served routine leaves the registers, flags, stack and memory its loop leaves, call by call."""

    def test_served_and_executed_calls_agree(self):
        from goal2.core.delay import COUNT_HIGH, COUNT_LOW
        core = career()
        m = core.m
        base = m.snapshot()
        ss, sp = m.reg("ss"), (m.reg("sp") - 0x100) & 0xFFFF
        back = m.lin("0000:0000")
        for n in (0, 1, 3):
            for count in (5, 0x10002):
                after = []
                for served in (False, True):
                    m.restore(base)
                    m.wr(COUNT_LOW, count & 0xFFFF)
                    m.wr(COUNT_HIGH, count >> 16)
                    m.far_call("214B:1E09", [n], "0000:0000", ss, sp)
                    m.set_reg("bp", 0x1234)
                    m.set_reg("eflags", 0x0ED7 | 0x0202)     # every arithmetic flag set, and DF: the served ones
                    m.set_reg("eax", 0xABCD0000)
                    core.delays_served = served
                    m.uc.emu_start(m.pc(), back, count=10_000_000)
                    self.assertEqual(m.pc(), back)
                    after.append(m.snapshot())
                with self.subTest(n=n, count=count):
                    self.assertEqual(after[0]["regs"], after[1]["regs"])
                    self.assertEqual(after[0]["memory"], after[1]["memory"])
                    self.assertEqual(m.reg("sp"), (sp + 6) & 0xFFFF)
                    self.assertEqual(m.reg("bp"), 0x1234)
                    if n:
                        self.assertEqual(m.reg("eax"), 0xABCD0000 | n)
                        self.assertEqual(m.reg("dx"), count >> 16)

    def test_a_served_delay_takes_the_core_under_a_millisecond(self):
        """Done-when 2's bound, on the whistle's 1,708 calls: the core's whole handling of a call (the hook, the count,
        the listener, the served state), its mean and 99th percentile; a single call may meet the host's scheduler."""
        from goal2.core.runner import Core
        spent, real = [], Core._on_delay

        def timed(core, replay):
            t = time.perf_counter()
            try:
                return real(core, replay)
            finally:
                spent.append(time.perf_counter() - t)
        with patch.object(Core, "_on_delay", timed):
            play(at_pose(WIDE - 1), True, steps=2)
        spent.sort()
        self.assertGreaterEqual(len(spent), WHISTLE_MS)
        self.assertLess(sum(spent) / len(spent), 1e-3)
        self.assertLess(spent[len(spent) * 99 // 100], 1e-3)


@requires.need(**(NEEDS | dict(modules=("unicorn", "PySide6"))))
class Window(unittest.TestCase):
    """Done-when 3 and item 2: the window waits the milliseconds, names the sound, and counts the question down."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self, blob):
        from goal2.desktop.core_model import CoreModel
        from goal2.desktop.core_window import CoreWindow
        m = CoreModel(load(blob), requires.CACHE / "GOAL.DAT", scratch())
        w = CoreWindow(m)
        self.addCleanup(w.close)
        w.core_round.watch_suspended = True          # no pitch viewer: the round page shows the stop
        w.show()
        self.app.processEvents()
        return m, w

    def pump(self, w, seconds=None, until=None):
        end = time.monotonic() + (seconds if seconds is not None else 60)
        while time.monotonic() < end:
            self.app.processEvents()
            if until is not None and until():
                return True
            time.sleep(0.002)
        return False

    def test_a_headless_model_does_not_wait(self):
        from goal2.desktop.core_model import CoreModel
        m = CoreModel(load(at_pose(WIDE - 1)), requires.CACHE / "GOAL.DAT", scratch())
        t = time.monotonic()
        m.round_step("live_step")
        self.assertLess(time.monotonic() - t, WHISTLE_MS / 1000)

    def test_the_whistle_is_waited_and_named(self):
        m, w = self.window(at_pose(WIDE - 1))
        self.assertTrue(m.pacing)
        notes = []

        def done():
            notes.append((m.sounding, w.status.text()))
            return not w.core_jobs.busy
        t = time.monotonic()
        self.assertTrue(w.run_core("live_step"))
        self.assertTrue(self.pump(w, until=done))
        took = time.monotonic() - t
        asked = sum(ms for _, ms in m.waited)
        self.assertGreaterEqual(asked, WHISTLE_MS)
        self.assertGreaterEqual(took, asked / 1000)
        self.assertIn(["whistle", WHISTLE_MS], m.waited)
        shown = [text for sound, text in notes if sound == "whistle"]
        self.assertTrue(shown and any("whistle" in text for text in shown), notes[-5:])
        self.assertIsNone(m.sounding)
        self.assertNotIn("whistle", w.status.text())

    def test_the_replay_question_counts_down_at_its_pace(self):
        from goal2.core.delay import timed_left_ms
        blob = at_pose(GOAL + 1)
        m, w = self.window(blob)
        r = w.core_round
        self.assertTrue(self.pump(w, 5, until=lambda: r.views.currentWidget() is r.replays.view))
        self.assertEqual(timed_left_ms(m.core), PROMPT_MS)
        before = m.core.save()
        first = r.replays.left()
        self.assertGreater(first, PROMPT_MS / 1000 - 0.5)
        self.pump(w, 0.5)
        second = r.replays.left()
        self.assertAlmostEqual(first - second, 0.5, delta=0.15)
        self.assertRegex(r.replays.countdown.text(), r"asks for \d\.\d s more; then the match goes on without a replay")
        self.assertEqual(m.core.save(), before)       # the original waits at its poll meanwhile (T140)
        self.assertFalse(w.core_jobs.busy)
        r.replays.deadline = time.monotonic()        # the countdown's end, without its remaining seconds here
        self.assertTrue(self.pump(w, 2, until=lambda: w.core_jobs.busy or (r.state or {}).get("stop") == "live"))
        self.assertEqual(w.core_jobs.name, "replay_timeout")
        self.assertTrue(self.pump(w, 30, until=lambda: not w.core_jobs.busy and (r.state or {}).get("stop") == "live"))
        self.assertFalse(r.state["replay"])
        self.assertEqual(m.core.wait.kind, "match-live")


if __name__ == "__main__":
    unittest.main()
