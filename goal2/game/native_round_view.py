"""[designed: T170av/#876, T170aw/#880] S14 data from verified native rounds."""

from goal2.core.views import Memory
from goal2.engine.original_match.image import Image
from goal2.game import engine_tables


FIELDS = {'fixture', 'first', 'second', 'kind', 'score', 'winner_flag'}


class RoundFixtureRows:
    def __init__(self, state, country_names):
        self.names = country_names
        image = Image.from_state(state, engine_tables.load())
        self.kind_name = Memory(image).kind_name

    def row(self, index, first, second, kind, score):
        # [confirmed: 1771:7812/77C3 and Core round_results] The second
        # native side (+6) and its score (+1) are drawn first.
        return {'fixture_id': index, 'kind': kind, 'kind_name': self.kind_name(kind),
                'home': second, 'away': first,
                'home_name': self.names[second], 'away_name': self.names[first],
                'score': None if score is None else (score[1], score[0])}

    def rows(self, observation):
        fixtures = observation['played_fixtures']
        if type(fixtures) is not tuple:
            raise ValueError('Native results need an ordered fixture delta.')
        result = []
        for value in fixtures:
            if not isinstance(value, dict) or set(value) != FIELDS:
                raise ValueError('Invalid native fixture result fields.')
            index, first, second, kind, score, winner = (
                value[key] for key in ('fixture', 'first', 'second', 'kind', 'score', 'winner_flag'))
            if (type(index) is not int or index < 1 or type(kind) is not int or not 0 <= kind <= 255
                    or type(winner) is not int or not 0 <= winner <= 255
                    or type(score) is not tuple or len(score) != 2
                    or any(type(goals) is not int or not 0 <= goals <= 255 for goals in score)):
                raise ValueError('Invalid native fixture result.')
            if kind == 0 or score[0] >= 254:
                continue
            if any(type(side) is not int or not 1 <= side <= 128 for side in (first, second)) or first == second:
                raise ValueError('Invalid native fixture sides.')
            result.append(self.row(index, first, second, kind, score))
        return result


class NativeRoundResults:
    def __init__(self, entry, fixture, country_names, number):
        observation = entry['observation']
        if observation['status'] != 'match':
            raise ValueError('Native round results need the pending managed fixture.')
        self.identity = observation['call_number'], observation['input_hash']
        self.fixture = fixture
        self.fixture_rows = RoundFixtureRows(entry['state'], country_names)
        self.number = number
        self.before = {'round': number, 'results': self.fixture_rows.rows(observation),
                       'match': self.fixture_rows.row(fixture.index, fixture.side_a, fixture.side_b, fixture.kind, None)}

    def after(self, packet):
        observation = packet['observation']
        if (observation['call_number'], observation['input_hash']) != self.identity:
            raise ValueError('Native results belong to another round.')
        rows = self.fixture_rows.rows(observation)
        fixture = self.fixture
        if not rows or (rows[0]['fixture_id'], rows[0]['away'], rows[0]['home'], rows[0]['kind']) != (
                fixture.index, fixture.side_a, fixture.side_b, fixture.kind):
            raise ValueError('Native results are missing the managed fixture.')
        return {'round': self.number, 'match': rows[0], 'results': rows[1:]}


def completed_round_results(packet, country_names, number):
    """Project just the verified fixture delta from an advance-only boundary."""
    observation = packet['observation']
    if observation['status'] not in ('complete', 'deferred-rollover'):
        raise ValueError('Native round results need a completed or deferred boundary.')
    rows = RoundFixtureRows(packet['state'], country_names).rows(observation)
    return {'round': number, 'results': rows, 'match': None}
