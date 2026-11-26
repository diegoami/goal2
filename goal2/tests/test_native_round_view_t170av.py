"""[designed: T170av] Verified S14 rows for a supplied native round."""

from copy import deepcopy
from types import SimpleNamespace
import unittest


def result(index, first, second, score, kind=1):
    return dict(fixture=index, first=first, second=second, kind=kind, score=score, winner_flag=0)


class Projection(unittest.TestCase):
    def test_displays_home_score_kind_and_actual_delta_order_without_mutation(self):
        from goal2.core.views import round_results
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.native_round_view import NativeRoundResults
        from goal2.tests.test_prematch_preview_t170s import reference_raw

        image = Image.from_bytes(reference_raw())
        state = image.state(engine_tables.load())
        fixture = SimpleNamespace(index=9, side_a=7, side_b=19, kind=1)
        identity = dict(call_number=41, input_hash='supplied')
        prior = (result(6, 20, 25, (2, 3)), result(8, 31, 32, (254, 0)), result(7, 22, 27, (1, 0)))
        final = (result(9, 7, 19, (4, 2)), result(10, 28, 30, (1, 5), kind=2))
        entry = {'state': state, 'observation': dict(identity, status='match', played_fixtures=prior)}
        packet = {'observation': dict(identity, status='complete', played_fixtures=final)}
        source = deepcopy((entry, packet))
        names = tuple(f'Country {i}' for i in range(129))
        projected = NativeRoundResults(entry, fixture, names, None)
        self.assertIsNone(projected.before['round'])
        self.assertEqual([row['fixture_id'] for row in projected.before['results']], [6, 7])
        self.assertEqual(projected.before['results'][0]['score'], (3, 2))
        self.assertEqual(projected.before['match']['home_name'], 'Country 19')
        self.assertIsNone(projected.before['match']['score'])
        after = projected.after(packet)
        self.assertEqual(after['match']['score'], (2, 4))
        self.assertEqual(after['results'][0]['score'], (5, 1))
        self.assertEqual(after['match']['kind_name'], round_results(image, 1, 1)['rows'][0]['kind_name'])
        self.assertEqual((entry, packet), source)
        with self.assertRaises(ValueError):
            projected.after({'observation': dict(packet['observation'], played_fixtures=final[1:])})
        with self.assertRaises(ValueError):
            projected.after({'observation': dict(packet['observation'], call_number=42)})

    def test_invalid_delta_does_not_turn_an_unplayed_row_into_a_score(self):
        from goal2.game.native_round_view import NativeRoundResults
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.tests.test_prematch_preview_t170s import reference_raw

        state = Image.from_bytes(reference_raw()).state(engine_tables.load())
        fixture = SimpleNamespace(index=9, side_a=7, side_b=19, kind=1)
        entry = {'state': state, 'observation': dict(status='match', call_number=1, input_hash='supplied',
                                                    played_fixtures=(result(6, 20, 25, (True, 3)),))}
        with self.assertRaises(ValueError):
            NativeRoundResults(entry, fixture, tuple(str(i) for i in range(129)), None)
