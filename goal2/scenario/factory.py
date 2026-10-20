"""[designed: T86] Fictional scenario factory and its marked JSON codec.

Countries, players and cards are invented by closed formulas. Player records
use the rebuild's 20-byte record layout ([0] country, [4] ability, [6] position
code, [12] confidence, [14] energy, [16] status flags), so the real
`eligibility` and `team_morale` functions read them. The values carry no
original meaning; no GOAL.DAT, savestate or vision-266 illustration is read.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from goal2.game.campaign import Fixture
from goal2.scenario import MARK, TEMPLATE

COUNTRIES = ('', 'Northmarch', 'Eastvale', 'Southmere', 'Westholm', 'Lowfield')
MANAGED = 1
RESERVES = tuple(range(101, 111))
N_WORDS = 111
POSITIONS = ('Goalkeeper', 'Defence', 'Midfield', 'Attack')
_INITIALS = 'ABCDEFGHJKLMNPRST'
_STEMS = ('Var', 'Tol', 'Bre', 'Ost', 'Lun', 'Mar', 'Hed')
_ENDS = ('berg', 'vik', 'dahl', 'holm', 'sen', 'mark', 'holt', 'lund',
         'gaard', 'by', 'stad', 'fjell', 'ness', 'vall', 'ström', 'rud')
# [designed: T86] Per-squad position codes: 2 GK, 6 DEF, 7 MID, 5 ATT.
_SHAPE = (0,) * 2 + (1,) * 6 + (2,) * 7 + (3,) * 5
START_ELEVEN = (1, 3, 4, 5, 6, 9, 10, 11, 12, 16, 17)
CAPTAIN = 9
TACTICS = 0x24
INJURED_AT_START = 19
# [designed: T86] Kind 4 is outside the adapter's KINDS: the unsupported branch.
FIXTURES = (
    Fixture('original:1', 1, 1, 2, 1, 1, 2),
    Fixture('original:2', 1, 1, 2, 1, 3, 1),
    Fixture('original:3', 1, 1, 2, 2, 1, 4),
    Fixture('original:4', 1, 1, 2, 200, 5, 1),
    Fixture('original:5', 1, 1, 2, 4, 1, 2),
)


class Names:
    """[designed: T86] The `goaldat` names surface the controllers read."""
    def __init__(self):
        self.country_names = list(COUNTRIES)
        self.player_names = [''] + [player_name(w) for w in range(1, N_WORDS)]


def player_name(word):
    """[designed: T86] Unique for words 1..111: (word % 7, word // 7 % 16) is a bijection."""
    return f'{_INITIALS[word % 17]} {_STEMS[word % 7]}{_ENDS[word // 7 % 16]}'


def country_of(word):
    return MANAGED if word in RESERVES else (word - 1) // 20 + 1


def squad_of(country):
    return list(range((country - 1) * 20 + 1, country * 20 + 1))


def _record(word):
    out = bytearray(20)
    out[0] = country_of(word)
    out[4] = 40 + word * 37 % 50
    out[6] = _SHAPE[(word - 1) % 20] if word not in RESERVES else _SHAPE[word * 3 % 20]
    out[12] = 20 + word * 13 % 60
    out[14] = 0 if word == INJURED_AT_START else 60 + word * 7 % 60
    out[16] = 0x08 if word == 20 else 0
    return bytes(out)


def card(state, word):
    """[designed: T86] Complete fictional card; skills/characteristics are illustrative only."""
    from goal2.game import eligibility
    record = state.players[word]
    return {'id': word, 'name': player_name(word), 'country': COUNTRIES[record[0]],
            'position': POSITIONS[record[6]], 'age': 19 + word * 5 % 16, 'caps': word * 11 % 70,
            'goals': word * 3 % 17 if record[6] else 0,
            'skills': [(word * (k + 3) + k * 7) % 25 for k in range(12)],
            'characteristics': [(word * (k + 5)) % 31 for k in range(5)],
            'ability': record[4], 'energy': record[14], 'confidence': record[12],
            'availability': eligibility.info(record),
            'evidence': '[designed: T86] fictional values; no original meaning'}


@dataclass
class ScenarioCalendar:
    """[designed: T86] Ordered fictional fixtures with a once-only completion ledger."""
    fixtures: tuple
    completed_fixture_ids: list = field(default_factory=list)
    results: list = field(default_factory=list)
    world = None
    stage = 2

    @property
    def next_fixture(self):
        done = set(self.completed_fixture_ids)
        return next((f for f in self.fixtures if f.fixture_id not in done), None)

    def complete_fixture(self, fixture_id, *, resolution=None, score=None):
        """[designed: T86] Next fixture only; competitive needs a valid resolution."""
        pending = self.next_fixture
        if pending is None or fixture_id != pending.fixture_id:
            raise ValueError(f'expected next fixture {getattr(pending, "fixture_id", None)!r}')
        if pending.kind != 1:
            from goal2.game.watched_schema import validate_resolution
            if resolution is None:
                raise ValueError('competitive completion needs its resolution')
            validate_resolution(resolution, score, pending.kind)
        elif resolution is not None:
            raise ValueError('friendly completion cannot have competitive resolution')
        self.completed_fixture_ids.append(fixture_id)


@dataclass
class ScenarioState:
    """[designed: T86] Owner state surface the controllers use, marked fictional."""
    scenario: str
    managed_country: int
    managed_squad: list
    reserves: list
    players: list
    starting_eleven: list
    captain: int
    country_tactics: int
    campaign: ScenarioCalendar
    match_count: int = 0
    last_match: dict | None = None


def new_state():
    """[designed: T86] The fixed opening of the fictional session."""
    players = [bytes(20)] + [_record(w) for w in range(1, N_WORDS)]
    return ScenarioState(MARK, MANAGED, squad_of(MANAGED), list(RESERVES), players,
                         list(START_ELEVEN), CAPTAIN, TACTICS, ScenarioCalendar(FIXTURES))


def to_data(state):
    if getattr(state, 'scenario', None) != MARK:
        raise ValueError('not a fictional scenario state')
    campaign = state.campaign
    return {'scenario': MARK, 'managed_country': state.managed_country,
            'managed_squad': list(state.managed_squad), 'reserves': list(state.reserves),
            'players': [r.hex() for r in state.players], 'starting_eleven': list(state.starting_eleven),
            'captain': state.captain, 'country_tactics': state.country_tactics,
            'match_count': state.match_count, 'last_match': copy.deepcopy(state.last_match),
            'campaign': {'fixtures': [f.__dict__ for f in campaign.fixtures],
                         'completed_fixture_ids': list(campaign.completed_fixture_ids),
                         'results': copy.deepcopy(campaign.results)}}


def from_data(data):
    if not isinstance(data, dict) or data.get('scenario') != MARK:
        raise ValueError('not a fictional scenario state')
    c = data['campaign']
    fixtures = tuple(Fixture(**f) for f in c['fixtures'])
    for f in fixtures:
        f.validate()
    players = [bytes.fromhex(r) for r in data['players']]
    if len(players) != N_WORDS or any(len(r) != 20 for r in players):
        raise ValueError('invalid fictional player records')
    return ScenarioState(MARK, data['managed_country'], data['managed_squad'], data['reserves'], players,
                         data['starting_eleven'], data['captain'], data['country_tactics'],
                         ScenarioCalendar(fixtures, c['completed_fixture_ids'], c['results']),
                         data['match_count'], data['last_match'])


def encode(state, template):
    """[designed: T86] Deterministic marked JSON; any template is stored, the state must be marked."""
    if not isinstance(template, (bytes, bytearray)):
        raise ValueError('template bytes required')
    payload = {'format': MARK, 'template': bytes(template).hex(), 'state': to_data(state)}
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def decode(raw):
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f'not a fictional scenario file: {exc}') from exc
    if not isinstance(payload, dict) or payload.get('format') != MARK:
        raise ValueError('not a fictional scenario file')
    return from_data(payload['state']), bytes.fromhex(payload['template'])


def load(path):
    return decode(Path(path).read_bytes())


__all__ = ['TEMPLATE', 'Names', 'new_state', 'encode', 'decode', 'load', 'card']
