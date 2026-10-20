"""[designed: T86] Fixed match scripts for the fictional lane; no simulation.

A script lists goals and injuries as (side, minute, starter index). Everything
else is derived from it: running score, the event stream, kit-2 result
dictionary, pitch frames and the published candidate. Poses are a closed
arithmetic pattern with no football meaning. Output has the existing schemas;
it is never evidence of original behaviour.
"""
from __future__ import annotations

import copy
import hashlib
import json

from goal2.engine.original_match.match import Event
from goal2.scenario import ENGINE, MARK
from goal2.scenario.factory import COUNTRIES, player_name, squad_of

M, O = 'managed', 'opponent'
SCRIPTS = {
    'win': {'goals': [(M, 23, 8), (O, 57, 8), (M, 71, 9)], 'injuries': []},
    'draw': {'goals': [(O, 38, 9), (M, 64, 10)], 'injuries': []},
    'injury': {'goals': [(M, 52, 9)], 'injuries': [(M, 30, 6)]},
    'regulation': {'goals': [(M, 12, 8), (M, 80, 9)], 'injuries': []},
    'extra_time': {'goals': [(M, 30, 8), (O, 75, 9), (M, 104, 10)], 'injuries': []},
    'shootout': {'goals': [(O, 95, 8), (M, 112, 9)], 'injuries': [],
                 'kicks': [(M, True), (O, True), (M, True), (O, False), (M, False),
                           (O, True), (M, True), (O, False), (M, True), (O, True)]},
}
DEFAULT = {'original:1': 'injury', 'original:2': 'draw', 'original:3': 'regulation',
           'original:4': 'shootout', 'original:5': 'win'}
TICKS = 24
EXTRA_TICKS = 8
SENTINEL = 0x7F7F


def script_for(fixture_id, name=None):
    name = DEFAULT.get(fixture_id, 'win') if name is None else name
    if name not in SCRIPTS:
        raise ValueError(f'unknown fictional script {name!r}')
    return name, SCRIPTS[name]


def _xi(state, country):
    return list(state.starting_eleven) if country == state.managed_country else squad_of(country)[:11]


def _squad(state, country):
    return list(state.managed_squad) if country == state.managed_country else squad_of(country)


def _incidents(state, teams, script):
    """[designed: T86] Map side labels to team index 0/1 and starter words."""
    side = {M: teams.index(state.managed_country), O: 1 - teams.index(state.managed_country)}
    def rows(key):
        return [(side[s], minute, _xi(state, teams[side[s]])[index]) for s, minute, index in script.get(key, [])]
    return rows('goals'), rows('injuries'), [(side[s], scored) for s, scored in script.get('kicks', [])]


def score_at(goals, minute):
    out = [0, 0]
    for team, at, _ in goals:
        if at <= minute:
            out[team] += 1
    return out


def halftime(state, fixture, name=None):
    """[derived: T86 from QuickJobs.validate_halftime] The exact quick preview keys."""
    _, script = script_for(fixture.fixture_id, name)
    teams = [fixture.side_a, fixture.side_b]
    goals, injuries, _ = _incidents(state, teams, script)
    injured = {w for t, m, w in injuries if m <= 45}
    eleven = list(state.starting_eleven)
    bench = [w for w in state.managed_squad if w not in eleven]
    from goal2.game import eligibility
    available = [w for w in eleven + bench if not eligibility.reasons(state.players[w]) and w not in injured]
    return {'eleven': eleven, 'bench': bench, 'available': available, 'captain': state.captain, 'kind': 1,
            'removed': [], 'changes': [], 'score': score_at(goals, 45), 'teams': teams}


def _played(state, teams, injuries, changes=()):
    """[designed: T86] Energy -8 for starters and incoming players, zero when injured."""
    played = {w for c in teams for w in _xi(state, c)} | {on for _, on in changes}
    hurt = {w for _, _, w in injuries}
    return {w: (0 if w in hurt else max(1, state.players[w][14] - 8)) for w in played}


def quick_candidate(state, fixture, name=None, changes=()):
    """[designed: T86] Child-owned fictional quick continuation; parent re-validates it."""
    _, script = script_for(fixture.fixture_id, name)
    if 'kicks' in script or any(m > 90 for _, m, _ in script['goals']):
        raise ValueError('fictional quick friendly cannot play extra time')
    teams = [fixture.side_a, fixture.side_b]
    goals, injuries, _ = _incidents(state, teams, script)
    candidate = copy.deepcopy(state)
    for word, energy in _played(state, teams, injuries, changes).items():
        record = bytearray(candidate.players[word]);record[14] = energy
        candidate.players[word] = bytes(record)
    score = score_at(goals, 90)
    candidate.match_count += 1
    candidate.last_match = {'engine': ENGINE, 'mode': 'quick', 'teams': teams, 'score': score,
                            'half_time_score': score_at(goals, 45),
                            'goals': [{'team': t, 'minute': m, 'player': w} for t, m, w in goals],
                            'substitutions': [list(c) for c in changes]}
    candidate.campaign.complete_fixture(fixture.fixture_id)
    candidate.campaign.results.append({'fixture_id': fixture.fixture_id, 'teams': teams, 'score': score,
                                       'engine': ENGINE, 'mode': 'quick'})
    return candidate


def _stats(goals):
    shots = [2 + 3 * sum(1 for g in goals if g[0] == t) for t in (0, 1)]
    zero = [0, 0]
    return {'corners': [3, 2], 'free_kicks': [5, 6], 'penalties': zero, 'shots': shots,
            'on_target': [s - 1 for s in shots], 'saves': [2, 1], 'fouls': [4, 7], 'bookings': zero,
            'red_cards': zero, 'injuries': zero}


def match(state, fixture, image_sha256, *, competitive, name=None):
    """[designed: T86] Scripted events, kit-2 result, seeds and memory blob for one job."""
    script_name, script = script_for(f'original:{fixture.index}', name)
    teams = [fixture.first, fixture.second]
    goals, injuries, kicks = _incidents(state, teams, script)
    extra = any(m > 90 for _, m, _ in goals) or bool(kicks)
    if not competitive and extra:
        raise ValueError('fictional friendly cannot play extra time')
    end = 120 if extra else 90
    names = lambda w: player_name(w)
    stamps = []  # (minute, order, Event)

    def at(minute, order, kind, data=None):
        stamps.append((minute, order, kind, data or {}))
    for minute in (1, 15, 30, 45, 60, 75, 90) + ((105, 120) if extra else ()):
        at(minute, 0, 'minute')
    at(1, 3, 'commentary', {'text': f'Kick-off: {COUNTRIES[teams[0]]} against {COUNTRIES[teams[1]]} (fictional scenario)',
                            'template': 1, 'team': 0, 'players': [0, 0]})
    for team, minute, word in goals:
        at(minute, 1, 'goal', {'team': team, 'country': teams[team], 'player': word, 'name': names(word)})
        at(minute, 3, 'commentary', {'text': f'Goal for {COUNTRIES[teams[team]]}: {names(word)}',
                                     'template': 2, 'team': team, 'players': [word, 0]})
    for team, minute, word in injuries:
        at(minute, 2, 'injury', {'team': team, 'player': word, 'name': names(word)})
    managed = teams.index(state.managed_country)
    eleven = _xi(state, state.managed_country)
    at(45, 4, 'decision', {'context': 'half_time', 'eleven': eleven,
                           'bench': [w for w in state.managed_squad if w not in eleven],
                           'injured': [w for t, m, w in injuries if t == managed and m <= 45],
                           'positions': [[w, state.players[w][6]] for w in state.managed_squad],
                           'substitutions_left': 5, 'tactics': state.country_tactics})
    at(45, 5, 'half_time')
    if extra:
        at(90, 6, 'extra_time')
    score = score_at(goals, end)
    shootout = None
    if kicks:
        at(120, 6, 'shootout', {'score_120': list(score)})
        tally, rounds, rows = [0, 0], [0, 0], []
        for team, scored in kicks:
            rounds[team] += 1;tally[team] += int(scored)
            word = _xi(state, teams[team])[10 - (rounds[team] - 1) % 11]
            row = {'team': team, 'player': word, 'name': names(word), 'scored': scored, 'round': rounds[team]}
            rows.append(row)
            at(120, 7, 'shootout_kick', dict(row, shootout_score=list(tally)))
        shootout = {'score': tally, 'kicks': rows}
    ticks = TICKS + (EXTRA_TICKS if extra else 0)
    final = [score[i] + (shootout['score'][i] if shootout else 0) for i in (0, 1)]
    mom = goals[-1][2] if goals else eleven[0]
    board = {'statistics': _stats(goals), 'bars': [[20 + 3 * len(goals), 18], [17, 21]],
             'man_of_the_match': mom, 'final_score': final,
             'screen_sha256': hashlib.sha256(f'{MARK}:{fixture.index}:{script_name}'.encode()).hexdigest(),
             'ticks': ticks, 'seed': 4660 + fixture.index}
    at(end, 8, 'full_time', copy.deepcopy(board))
    at(end, 9, 'end')
    events, running = [], [0, 0]
    for minute, _, kind, data in sorted(stamps, key=lambda s: (s[0], s[1])):
        if kind == 'goal':
            running[data['team']] += 1
        events.append(Event(kind, minute, tuple(running), data))
    decided = shootout['score'] if shootout else score
    winner = 2 if decided[0] == decided[1] else int(decided[1] > decided[0])
    hurt = _played(state, teams, injuries)
    rows = []
    for team, country in enumerate(teams):
        for word in _squad(state, country):
            record = state.players[word]
            delta = 0 if winner == 2 else (2 if winner == team else -2)
            energy = hurt.get(word, record[14])
            rows.append({'player': word, 'team': team, 'confidence': [record[12], max(0, min(255, record[12] + delta))],
                         'energy': [record[14], energy], 'status': [record[16], record[16]],
                         'suspended': bool(record[16] & 0x80), 'carried_booking': bool(record[16] & 0x08),
                         'injured': energy == 0})
    seeds = (4660 + fixture.index, 33590 + fixture.index)

    def incident(team, minute, word, goal):
        row = {'team': team, 'player': word, 'name': names(word), 'minute': minute}
        if goal:
            row.update(country=teams[team], minute_byte=minute if minute <= 255 else None)
        if competitive and minute > 90:
            row['extra_time'] = True
        return row
    result = {
        'first': teams[0], 'second': teams[1], 'managed': state.managed_country, 'index': fixture.index,
        'score': score, 'half_time_score': score_at(goals, 45),
        'goals': [incident(t, m, w, True) for t, m, w in goals], 'goals_disallowed': [],
        'goal_counts': list(score), 'bookings': [], 'sendings_off': [],
        'injuries': [incident(t, m, w, False) for t, m, w in injuries], 'substitutions': [],
        'man_of_the_match': mom, 'man_of_the_match_name': names(mom), 'board': board,
        'commentary': [{'minute': e.minute, 'template': e.data['template'], 'players': e.data['players'],
                        'team': e.data['team'], 'text': e.data['text']} for e in events if e.kind == 'commentary'],
        'decisions': [{'context': 'half_time', 'minute': 45, 'answer': {
            'substitutions': [], 'tactics': [], 'positions': [], 'marking': [], 'own_tactics': [],
            'quick': False, 'speed': None}}],
        'inputs': [], 'ticks': ticks, 'kickoff_seed': 4660, 'seed_after': seeds[0], 'image_sha256': image_sha256,
        'kit': '2', 'draws': 0, 'draws_digest': None,
        'squads_after': {str(c): _squad(state, c) for c in teams},
        'kind': fixture.kind, 'winner': winner, 'score_90': score_at(goals, 90) if extra else None,
        'extra_time': extra, 'substitution_budget': [5, 5], 'shootout': shootout, 'players': rows}
    ratings = {str(c): [[w, 40 + (w * 7 + fixture.index) % 50] for w in _xi(state, c)] for c in teams}
    memory = json.dumps({'mark': MARK, 'image_sha256': image_sha256, 'seeds': list(seeds), 'ratings': ratings},
                        sort_keys=True).encode()
    return {'events': events, 'result': result, 'seeds': seeds, 'memory': memory, 'engine_year': 1}


def _signed(value):
    return value - 256 if value > 127 else value


def frames(state, fixture, played):
    """[designed: T86] One schematic pose per tick; watermark = events up to that minute."""
    events, result = played['events'], played['result']
    ticks, end = result['ticks'], (120 if result['extra_time'] else 90)
    teams = [fixture.first, fixture.second]
    out = []
    for i in range(ticks):
        minute = max(1, -(-(i + 1) * end // ticks))
        watermark = sum(1 for e in events if e.minute <= minute)
        score = list(next((e.score for e in reversed(events) if e.minute <= minute), (0, 0)))
        players = []
        for slot in range(1, 23):
            team, number = (1, slot) if slot <= 11 else (0, slot - 11)
            word = _xi(state, teams[team])[number - 1]
            x = (slot * 7 + i * 3) % 41 - 20
            y = (slot * 11 + i * 5) % 61 - 30
            players.append([slot, team, number, word, x, y, (slot + i) % 256, False])
        threshold, remaining = 10 + i % 5, 20
        out.append({'version': 1, 'sequence': i, 'watermark': watermark, 'minute': minute, 'score': score,
                    'subtick': i % 4, 'threshold': threshold, 'remaining': remaining,
                    'selector': int(_signed(threshold) < remaining), 'attack': [1, -1],
                    'sentinel': SENTINEL, 'ball': [(i * 9) % 31 - 15, (i * 13) % 41 - 20, False],
                    'players': players})
    return out
