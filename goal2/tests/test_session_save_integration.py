"""Cached E010 proof that saving after one friendly preserves continuation. [designed: T33]"""
import unittest
from pathlib import Path

from goal2.engine.savestate import Savestate
from goal2.game.quick_match import run_full_match
from goal2.game.session_save import decode, encode
from goal2.game.state import from_savestate, to_savestate


FIXTURE = Path(__file__).resolve().parents[2] / ".cache" / "e010-r0001-halftime.sav"


@unittest.skipUnless(FIXTURE.is_file(), "cached E010-r0001 halftime fixture is not staged")
class E010SaveContinuation(unittest.TestCase):
    def test_saved_second_friendly_matches_uninterrupted_continuation(self):
        template_bytes = FIXTURE.read_bytes()
        uninterrupted = from_savestate(template_bytes)
        first_template = to_savestate(uninterrupted, original=template_bytes)
        first_result = run_full_match(Savestate(first_template), uninterrupted, retain_state=True)
        self.assertEqual(uninterrupted.match_count, 1)
        self.assertEqual((uninterrupted.rng_seed_7b62, uninterrupted.rng_seed_8336),
                         (first_result["seed_DS7B62"], first_result["seed_DS8336"]))

        resumed, stored_template = decode(encode(uninterrupted, template_bytes))
        self.assertEqual(stored_template, template_bytes)
        resumed_template = to_savestate(resumed, original=stored_template)
        resumed_result = run_full_match(Savestate(resumed_template), resumed, retain_state=True)

        next_template = to_savestate(uninterrupted, original=template_bytes)
        uninterrupted_result = run_full_match(Savestate(next_template), uninterrupted, retain_state=True)
        self.assertEqual(resumed_result, uninterrupted_result)
        self.assertEqual(resumed.players, uninterrupted.players)
        self.assertEqual(resumed.countries, uninterrupted.countries)
        self.assertEqual((resumed.rng_seed_7b62, resumed.rng_seed_8336),
                         (uninterrupted.rng_seed_7b62, uninterrupted.rng_seed_8336))
        self.assertEqual((resumed.match_count, resumed.last_match),
                         (uninterrupted.match_count, uninterrupted.last_match))


if __name__ == "__main__":
    unittest.main()
