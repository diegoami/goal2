"""[designed: T151] goal2's matches play on the sealed port engine, and each is the original's match.

The original engine is only this comparison's other arm: the same driver (`_drive_match`) on the prepared, unsealed
image with engine="original". A watched friendly with bench answers and a pause, and a World Cup knockout decided on
penalties, give the same result, events, seeds and memory on both, the screen excepted (port_parity). A match on the
route runs in a child where importing Unicorn fails."""
import copy
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.engine.original_match import Fixture, Image, Match
from goal2.game import watched_match
from goal2.tests import requires, port_parity

ROOT = Path(__file__).resolve().parents[2]


class OriginalArm(Match):
    def __init__(self, image, *args, **kw):
        kw["engine"] = "original"
        super().__init__(image, *args, **kw)


def original_arm(fn, *args, **kw):
    """`fn` with the driver on the original engine: the prepared image, unsealed."""
    with patch.object(watched_match, "sealed", lambda image: image), patch.object(watched_match, "Match", OriginalArm):
        return fn(*args, **kw)


class Policy:
    """Two substitutions at half time and one pause (goal2's T102 bench policy)."""

    def __init__(self):
        self.paused = False

    def decide(self, event):
        if event.data["context"] == "half_time":
            eleven, bench = event.data["eleven"], event.data["bench"]
            return [(eleven[9], bench[1]), (eleven[10], bench[2])]
        return []

    def pause_now(self, sequence):
        if sequence == 1500 and not self.paused:
            self.paused = True
            return True
        return False

    def pause_dropped(self, sequence):
        pass

    def answered(self, report):
        pass


class PortRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requires.require(**requires.WATCHED)
        from goal2.engine.original_match.assets import reference_image
        cls.raw = reference_image(ROOT / ".cache")

    def state(self, managed=7):
        from goal2.game.state import from_savestate
        s = from_savestate(self.raw)
        s.managed_country = managed;s.managed_squad = Image(s.mem).squad(managed)
        s.starting_eleven = s.managed_squad[:11];s.captain = 0
        s.country_tactics = s.countries[managed][0x2D]
        return s

    def both(self, run):
        t = time.process_time();port = run();port_cpu = time.process_time() - t
        t = time.process_time();original = original_arm(run);original_cpu = time.process_time() - t
        port_parity.assert_same_match(self, port.result, port.memory, port.events,
                                      original.result, original.memory, original.events)
        self.assertEqual(port.seeds, original.seeds)
        self.assertEqual(port.engine_year, original.engine_year)
        self.assertEqual(Image(port.memory).build_problems(), [])     # the code part is back for the next step
        print(f"cpu: port {port_cpu:.1f} s, original {original_cpu:.1f} s, score {port.result['score']}", flush=True)
        return port

    def test_a_watched_friendly_with_bench_answers_and_a_pause(self):
        s = self.state();before = copy.deepcopy(s);fixture = Fixture(7, 19, 21)

        def run():
            image = watched_match.prepare_watched(s, self.raw, fixture)
            return watched_match._drive_match(s, image, fixture, delay_byte=0, record_draws=True,
                                              _observe_pitch=lambda sample: None, policy=Policy())
        port = self.both(run)
        self.assertTrue(any(e.kind == "substitution" for e in port.events))
        self.assertEqual(s, before)

    @requires.need(slow=True)
    def test_a_world_cup_knockout_decided_on_penalties(self):
        from goal2.game.competitive_match import run_competitive_match
        s = self.state();fixture = Fixture(7, 19, 42, 200)
        port = self.both(lambda: run_competitive_match(s, self.raw, fixture, record_draws=True))
        self.assertTrue(port.result["extra_time"]);self.assertIsNotNone(port.result["shootout"])

    def test_the_route_needs_no_unicorn(self):
        code = ("import builtins,sys\n"
                "real=builtins.__import__\n"
                "def guard(name,*a,**kw):\n"
                " if name=='unicorn' or name.startswith('unicorn.'):raise ImportError('Unicorn denied')\n"
                " return real(name,*a,**kw)\n"
                "builtins.__import__=guard\n"
                "sys.path.insert(0,sys.argv[1])\n"
                "from goal2.engine.original_match import Fixture\n"
                "from goal2.engine.original_match.assets import reference_image\n"
                "from goal2.game.state import from_savestate\n"
                "from goal2.game.watched_match import run_watched_match\n"
                "raw=reference_image(sys.argv[1]+'/.cache');s=from_savestate(raw);s.captain=0\n"
                "o=run_watched_match(s,raw,Fixture(7,19,21),reference_seed=0x1234,delay_byte=0)\n"
                "assert 'unicorn' not in sys.modules\n"
                "print('score',o.result['score'])\n")
        r = subprocess.run([sys.executable, "-B", "-c", code, str(ROOT)], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        self.assertIn("score [1, 1]", r.stdout)


if __name__ == "__main__":
    unittest.main()
