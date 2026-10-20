"""[designed: T86] Qt-free owner for the fictional session.

It offers the DesktopModel surface the controllers and window read (`state`,
`template_bytes`, `goaldat`, `match_pending`, `view`, `confirm`, `pool_view`,
`exchange`, `result_text`, `save`) with the same DTO keys. Reads are pure: a
view never advances the session. Saving into a career is refused.
"""
from __future__ import annotations

import copy

from goal2.game import eligibility
from goal2.game.campaign_confidence import team_morale
from goal2.scenario import ENGINE, MARK, TEMPLATE, require_scenario
from goal2.scenario import factory
from goal2.scenario.factory import COUNTRIES, POSITIONS


class ScenarioModel:
    """[designed: T86] Marked fictional owner; publishes validated candidates only."""
    scenario = MARK

    def __init__(self, state=None):
        self.goaldat = factory.Names()
        self.template_bytes = TEMPLATE
        self.save_path = None
        self.match_pending = False
        state = factory.new_state() if state is None else state
        self.view(state)
        self.state = state

    def view(self, state=None):
        """[designed: T86] DesktopModel.view keys; validates the candidate, mutates nothing."""
        state = self.state if state is None else state
        require_scenario(state, 'Fictional view')
        if state.managed_country not in range(1, len(COUNTRIES)) or len(state.managed_squad) != 20:
            raise ValueError('Invalid managed country or squad')
        rows = []
        for word in state.managed_squad:
            record = state.players[word]
            if len(record) != 20:
                raise ValueError('Invalid player record')
            rows.append({'id': word, 'name': self.goaldat.player_names[word], 'position': POSITIONS[record[6]],
                         'ability': record[4], 'energy': record[14], 'confidence': record[12],
                         'availability': eligibility.info(record)})
        self.result_text(state)
        fixture = state.campaign.next_fixture
        from goal2.engine.original_match.match import KINDS
        competitive = fixture is not None and fixture.kind != 1 and fixture.kind in KINDS
        label = ('Friendly' if fixture is not None and fixture.kind == 1
                 else ('Fictional competitive' if competitive else 'Unsupported fixture'))
        play = ('Play quick friendly' if fixture is None or fixture.kind == 1
                else 'Play fictional competitive' if competitive else 'Play unavailable')
        return {'countries': [(n, COUNTRIES[n]) for n in range(1, len(COUNTRIES))],
                'country': state.managed_country, 'country_name': COUNTRIES[state.managed_country],
                'players': rows, 'morale': team_morale(state.players, state.starting_eleven),
                'play_label': play,
                'fixture': None if fixture is None else
                f'{COUNTRIES[fixture.side_a]} — {COUNTRIES[fixture.side_b]} ({label})'}

    def card(self, word):
        if word not in self.state.managed_squad and word not in self.state.reserves:
            raise ValueError('No fictional card for that player')
        return factory.card(self.state, word)

    def confirm(self, eleven, captain, tactics):
        """[designed: T86] DesktopModel.confirm's validation order; atomic on refusal."""
        if (not isinstance(eleven, list) or len(eleven) != 11 or any(type(w) is not int for w in eleven)
                or len(set(eleven)) != 11 or not set(eleven) <= set(self.state.managed_squad)):
            raise ValueError('Choose eleven distinct players from this squad')
        if type(captain) is not int or captain not in eleven:
            raise ValueError('Captain must be in the starting eleven')
        if type(tactics) is not int or not 0 <= tactics <= 255:
            raise ValueError('Tactics must be an eight-bit integer')
        eligibility.require_available(self.state.players, eleven)
        candidate = copy.deepcopy(self.state)
        candidate.starting_eleven, candidate.captain, candidate.country_tactics = list(eleven), captain, tactics
        self.view(candidate)
        self.state = candidate

    def _window(self, state):
        pending = state.campaign.next_fixture
        if pending is None or pending.kind != 1:
            return {'allowed': False, 'reason': 'Exchange requires a pending managed friendly'}
        return {'allowed': True, 'reason': 'Between fictional friendlies'}

    def pool_view(self, *, query='', position=None):
        """[designed: T86] Same keys as campaign_pool.view; position filter is the record code."""
        state = self.state
        if not isinstance(query, str) or (position is not None and (type(position) is not int
                                                                    or not 0 <= position < len(POSITIONS))):
            raise ValueError('invalid pool search or position')

        def row(w):
            record = state.players[w]
            return {'id': w, 'name': self.goaldat.player_names[w], 'ability': record[4], 'position': record[6],
                    'position_group': POSITIONS[record[6]], 'energy': record[14], 'confidence': record[12],
                    'availability': eligibility.info(record)}
        key = lambda w: (state.players[w][6], w)
        reserves = [row(w) for w in sorted(state.reserves, key=key)]
        reserves = [r for r in reserves if query.casefold() in r['name'].casefold()
                    and (position is None or r['position'] == position)]
        return {'squad': [row(w) for w in sorted(state.managed_squad, key=key)], 'reserves': reserves,
                'window': self._window(state)}

    def exchange(self, outgoing, incoming):
        """[designed: T86] Validated copy; the XI/captain keep the incoming player in the outgoing slot."""
        if not self._window(self.state)['allowed']:
            raise ValueError('Exchange window is closed')
        if outgoing not in self.state.managed_squad or incoming not in self.state.reserves:
            raise ValueError('Choose one squad player and one reserve')
        candidate = copy.deepcopy(self.state)
        candidate.managed_squad[candidate.managed_squad.index(outgoing)] = incoming
        candidate.reserves[candidate.reserves.index(incoming)] = outgoing
        if outgoing in candidate.starting_eleven:
            candidate.starting_eleven[candidate.starting_eleven.index(outgoing)] = incoming
        if candidate.captain == outgoing:
            candidate.captain = incoming
        self.view(candidate)
        self.state = candidate

    def competition_table(self):
        """[designed: T86] The fictional lane has no standings source."""
        return None

    def result_text(self, state=None):
        """[designed: T86] Validated fictional result, always labelled fictional."""
        state = self.state if state is None else state
        match = state.last_match
        if match is None:
            return 'No match played'
        if not isinstance(match, dict) or match.get('engine') != ENGINE:
            raise ValueError('Invalid fictional match result')
        teams, score = match['teams'], match['score']
        names = self.goaldat.player_names
        lines = [f'Fictional scenario — {COUNTRIES[teams[0]]} {score[0]} — {score[1]} {COUNTRIES[teams[1]]}',
                 f"Half-time: {match['half_time_score'][0]} — {match['half_time_score'][1]}"]
        lines += [f"{g['minute']}′ {names[g['player']]} ({COUNTRIES[teams[g['team']]]})" for g in match['goals']] or ['No goals']
        stages = match.get('resolution')
        if stages:
            for key, label in (('regulation', 'Regulation'), ('extra_time', 'Extra time'), ('penalties', 'Penalties')):
                if stages[key] is not None:
                    lines.append(f'{label}: {stages[key][0]} — {stages[key][1]}')
            winner = stages['winner']
            lines.append('Draw' if winner == 2 else f'Winner: {COUNTRIES[teams[winner]]}')
        return '\n'.join(lines)

    def save(self, path):
        """[designed: T86] A fictional session is never written as a career save."""
        raise ValueError('Saving refused: this is a fictional scenario, not a career')

    def resume(self, path):
        raise ValueError('Resume refused: the fictional scenario has no career saves')
