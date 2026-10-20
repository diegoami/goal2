"""[designed: T86] The scenario runtime passed as `runtime=` to the real controllers.

It replaces only the steps that need original memory: the quick matchup check,
the session codec, the watched candidate builder and the completion board.
Token, ordering, stale-owner, ACK and once-only publication guards remain the
controllers' and `WatchedPublication`'s own code.
"""
from __future__ import annotations

import copy
import hashlib
import json
import secrets

from goal2.game.watched_match import WatchedOutcome
from goal2.game.watched_publication import WatchedJob, WatchedPublication
from goal2.game.watched_schema import resolution, validate_result
from goal2.scenario import ENGINE, MARK, TEMPLATE, require_scenario
from goal2.scenario import factory


def _require_owner(owner, action):
    require_scenario(owner, action)
    if owner.template_bytes != TEMPLATE:
        raise ValueError(f'{action} refused: fictional state with a foreign template')


def _completed(state, fixture, outcome, template, competitive):
    """[designed: T86] Validate the scripted outcome against its job, then build the candidate."""
    if not isinstance(outcome, WatchedOutcome):
        raise ValueError('completed watched outcome required')
    result = outcome.result
    validate_result(result, competitive=competitive)
    kinds = [getattr(e, 'kind', None) for e in outcome.events]
    if (not kinds or kinds[-1] != 'end' or kinds.count('end') != 1 or kinds.count('full_time') != 1
            or (result['first'], result['second'], result['index'], result['managed'])
            != (fixture.first, fixture.second, fixture.index, state.managed_country)):
        raise ValueError('watched completion differs from the pending fixture or is incomplete')
    if competitive and result['kind'] != fixture.kind:
        raise ValueError('completed kind differs from competitive job')
    if result['image_sha256'] != hashlib.sha256(factory.encode(state, template)).hexdigest():
        raise ValueError('watched completion differs from the declared input image')
    try:
        memory = json.loads(outcome.memory)
    except ValueError as exc:
        raise ValueError('fictional completion memory is not scenario data') from exc
    if (not isinstance(memory, dict) or memory.get('mark') != MARK
            or memory.get('image_sha256') != result['image_sha256']
            or tuple(memory.get('seeds', ())) != tuple(outcome.seeds) or result['seed_after'] != outcome.seeds[0]):
        raise ValueError('fictional completion memory differs from its result')
    candidate = copy.deepcopy(state)
    managed = [fixture.first, fixture.second].index(state.managed_country)
    for row in result['players']:
        if row['team'] == managed:
            record = bytearray(candidate.players[row['player']])
            record[12], record[14], record[16] = row['confidence'][1], row['energy'][1], row['status'][1]
            candidate.players[row['player']] = bytes(record)
    teams, score = [fixture.first, fixture.second], list(result['score'])
    compact = resolution(result) if competitive else None
    candidate.match_count += 1
    candidate.last_match = {'engine': ENGINE, 'mode': 'competitive' if competitive else 'watched',
                            'teams': teams, 'score': score, 'half_time_score': list(result['half_time_score']),
                            'goals': [{'team': g['team'], 'minute': g['minute'], 'player': g['player']}
                                      for g in result['goals']],
                            'resolution': compact, 'man_of_the_match': result['man_of_the_match']}
    fixture_id = f'original:{fixture.index}'
    candidate.campaign.complete_fixture(fixture_id, resolution=compact, score=score)
    candidate.campaign.results.append({'fixture_id': fixture_id, 'teams': teams, 'score': score,
                                       'engine': ENGINE, 'mode': candidate.last_match['mode'],
                                       'resolution': compact})
    return candidate


class _Preparation:
    """[designed: T86] Same private-run shape as the real completion preparation."""
    def __init__(self, inputs, competitive):
        self.inputs, self.competitive = inputs, competitive
        self.candidate = self.error = None
        self.ready = False

    def run(self):
        try:
            self.candidate = _completed(*self.inputs, self.competitive)
        except BaseException as exc:
            self.error = exc
        finally:
            self.ready = True


class ScenarioPublication(WatchedPublication):
    """[designed: T86] Inherits token/stale/once-only guards; no original image is prepared."""
    def __init__(self, owner):
        _require_owner(owner, 'Fictional publication')
        super().__init__(owner)

    def begin(self, fixture):
        if self._pending is not None:
            raise ValueError('a watched job is already pending')
        _require_owner(self.owner, 'Fictional publication')
        fixture = copy.deepcopy(fixture)
        original = self.owner.state
        pending = original.campaign.next_fixture
        if (pending is None or pending.fixture_id != f'original:{fixture.index}'
                or [pending.side_a, pending.side_b] != [fixture.first, fixture.second]
                or pending.kind != fixture.kind or (pending.kind == 1) == self._competitive):
            raise ValueError('fictional job differs from the scheduled fixture')
        candidate = copy.deepcopy(original)
        job = WatchedJob(secrets.token_hex(24), copy.deepcopy(candidate), copy.deepcopy(fixture))
        self._pending = (job.token, original, copy.deepcopy(original), candidate, fixture,
                         bytes(self.owner.template_bytes))
        return job

    def prepare_completion(self, token, outcome):
        pending = self._pending_for(token)
        if self._preparation is not None:
            raise ValueError('watched completion is already preparing')
        try:
            self._check_owner(pending)
        except Exception:
            self.cancel()
            raise
        _, _, _, candidate, fixture, template = pending
        self._preparation = _Preparation((candidate, fixture, outcome, template), self._competitive)
        return self._preparation


class ScenarioCompetitivePublication(ScenarioPublication):
    _competitive = True


class ScenarioRuntime:
    """[designed: T86] Duck-typed runtime for QuickJobs/WatchedJobs/CompetitiveJobs/WatchedController."""
    encode = staticmethod(factory.encode)
    load = staticmethod(factory.load)

    @staticmethod
    def check(state, template):
        from goal2.game import eligibility
        require_scenario(state, 'Fictional quick match')
        if template != TEMPLATE:
            raise ValueError('Fictional quick match refused: foreign template')
        pending = state.campaign.next_fixture
        if pending is None or pending.kind != 1:
            raise ValueError('Quick supports scheduled friendlies only in the fictional scenario')
        eligibility.require_available(state.players, state.starting_eleven)

    @staticmethod
    def publication(owner, competitive=False):
        return (ScenarioCompetitivePublication if competitive else ScenarioPublication)(owner)

    @staticmethod
    def require_watch():
        """[designed: T86] The fictional viewer/engine children need no optional package."""

    @staticmethod
    def require_competitive():
        """[designed: T86] The fictional competitive child needs no optional package."""

    @staticmethod
    def completion(outcome, names):
        """[designed: T86] Same keys as match_view.completion, read from the fictional memory blob."""
        memory = json.loads(outcome.memory)
        if memory.get('mark') != MARK:
            raise ValueError('fictional completion memory is not scenario data')
        result = outcome.result
        ratings = [[{'player': w, 'name': names[w], 'word': raw & 0xFFFF, 'raw': raw}
                    for w, raw in memory['ratings'][str(country)]]
                   for country in (result['first'], result['second'])]
        return {'board': copy.deepcopy(result['board']), 'ratings': ratings,
                'man_of_the_match': result['man_of_the_match_name']}


RUNTIME = ScenarioRuntime()
