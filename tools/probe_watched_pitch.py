#!/usr/bin/env python3
"""[designed: T81] Read-only original pitch evidence probe; no production caller.

[confirmed: F013, kit424d599] Original drawing and movement execute in full.
Only diagnostic tick events are removed when comparing canonical outcomes.
"""
import argparse
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from watched_evidence import SOURCE, source_bytes, verify_vendor

# [confirmed: F013, kit424d599, named/seg_0791_07.c:465-480,904-930]
# Signed x advances text rows; signed y advances two-byte text columns.
ROW_BYTES, COLUMN_BYTES, DRAW_ORIGIN = 160, 2, 0x90E
# [confirmed: kit424d599, code/seg_0791_05.asm:535-598]
# These are predicates, not universal bounds on all lifecycle positions.
IN_PLAY = (8, 37)
MOVEMENT = (9, 39)
# [designed: T81] Fixed before measurement, inherited from main feasibility brief.
SEEDS = (0x0101, 0x1234)
FIXTURE = (7, 19, 21)
IMAGE_NAME = 'e0afff6751747233-e006-1000-r0001.sav'
IMAGE_SHA = 'e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d'
DAT_SHA = 'bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca'
STATIC = {
    'static/goal-exe/named/seg_0791_02.c': ['357-497: sorting and rebind', '718-724: slot side', '896-940: local slot and attack sign'],
    'static/goal-exe/named/seg_0791_07.c': ['352-449: movement/restart', '465-480: player draw', '904-931: ball draw'],
    'static/goal-exe/named/seg_0791_08.c': ['252-295: clock', '445-446: clock setup', '810-868: binding/initialization'],
    'static/goal-exe/named/seg_0791_09.c': ['4-49: pitch background loading'],
    'static/goal-exe/code/seg_0791_05.asm': ['2BE5-2C26: signed-byte half selector', '535-598: signed predicates'],
    'static/goal-exe/named/seg_0791_10.c': ['434-504: substitution refresh and sort'],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def signed(value):
    """[derived: signed-byte draw paths above] Normalize an accessor byte."""
    return value - 256 if value > 127 else value


def project_xy(x, y):
    """[derived: original draw formula] Return fixed screen column/row offsets.

    [designed] Unit scale here is original text cells, without half rotation.
    A renderer may choose pixel scale/translation separately.
    """
    return [y, x]


def draw_offset(x, y):
    """[derived: original draw formula] Original buffer byte offset, no access."""
    return DRAW_ORIGIN + ROW_BYTES * x + COLUMN_BYTES * y


def hidden_xy(x, y, sentinel):
    """[confirmed: 8537/8F10, kit424d599] Exact packed sentinel skips drawing."""
    return ((x & 255) | ((y & 255) << 8)) == sentinel


def project_player(item, sentinel):
    """[derived: A260/2974/2BB1/8537] Preserve word identity and explicit slot."""
    slot = item['slot']
    team = 1 if slot <= 11 else 0
    number = slot if slot <= 11 else slot - 11
    x, y = signed(item['x']), item['y']
    return dict(slot=slot, team=team, number=number, player=item['player'],
                x=x, y=y, screen=project_xy(x, y), state=item['state'],
                hidden=hidden_xy(x, y, sentinel))


def canonical_events(events):
    """[designed] Strip exactly diagnostic ticks; preserve all other content."""
    return [copy.deepcopy(event) for event in events if event['kind'] != 'tick']


def assert_fidelity(baseline, observed):
    """[designed] No tolerances: complete canonical events/result/Memory/seeds."""
    assert canonical_events(baseline['events']) == canonical_events(observed['events']), 'canonical events changed'
    assert baseline['result'] == observed['result'], 'complete result changed'
    assert baseline['memory'] == observed['memory'], 'complete Memory changed'
    assert baseline['seeds'] == observed['seeds'], 'both RNG seeds changed'


def predicate(x, y, bounds):
    return abs(x) <= bounds[0] and abs(y) <= bounds[1]


def observe_boundary(event):
    """[designed: T81] Terminal teardown is not a completed pitch frame.

    [confirmed: runtime identity-diagnostic-01.log] After all4279 original ticks,
    end exposes re-sorted squads alongside stale pitch bindings. Keep last tick.
    """
    return (event.kind in ('tick', 'half_time') or
            event.kind == 'decision' and event.data.get('context') == 'half_time')


def attack_selector(threshold, remaining):
    """[confirmed: kit424d599, 2BE5-2C26] Byte sign extends before comparison."""
    return int(signed(threshold) < remaining)


def source_receipt():
    """[designed] Hash upstream evidence without retaining original source bytes."""
    return dict(pin=SOURCE, observer_sha256=sha(Path(__file__).read_bytes()), files={path: dict(sha256=sha(source_bytes(path)), citations=cites)
                                 for path, cites in STATIC.items()},
                vendor_files_verified=verify_vendor())


def snapshot(match, event, sequence):
    """[designed] Read one stopped state, never replay earlier commentary poses."""
    from goal2.engine.original_match.match import PITCH, PITCH_SIZE, BALL
    m = match.m
    before = match.memory_component()
    rng = (m.rd(0x7B62), m.rd(0x8336))
    pitch = match.pitch()
    assert pitch == match.pitch(), 'repeated pitch reads differ'
    assert before == match.memory_component(), 'pitch reads changed complete guest Memory'
    assert rng == (m.rd(0x7B62), m.rd(0x8336)), 'pitch reads changed RNG'
    sentinel = m.rd(0x0640)
    players = [project_player(item, sentinel) for item in pitch['players']]
    squads = [match._squad(country) for country in FIXTURE[:2]]
    for item, raw_item in zip(players, pitch['players']):
        raw = m.read(m.DS * 16 + PITCH + PITCH_SIZE * item['slot'], PITCH_SIZE)
        assert raw[6] == item['slot'], 'slot byte identity differs'
        assert item['player'] == int.from_bytes(raw[13:15], 'little'), 'player word differs'
        assert item['player'] == squads[item['team']][item['number'] - 1], 'current squad identity mapping differs: ' + json.dumps(dict(sequence=sequence, kind=event.kind, minute=event.minute, item=item, squads=squads))
        assert item['team'] == raw_item['team'], 'accessor team differs from original slot binding'
        assert (item['x'], item['y']) == (signed(raw[0]), signed(raw[1])), 'signed coordinates differ'
        assert item['screen'] == [signed(raw[1]), signed(raw[0])], 'original draw axes differ'
        assert item['state'] == raw[18], 'state byte differs'
    ball_raw = m.read(m.DS * 16 + BALL, 2)
    ball = [signed(pitch['ball'][0]), pitch['ball'][1]]
    assert ball == [signed(ball_raw[0]), signed(ball_raw[1])], 'ball signed coordinates differ'
    threshold, remaining = m.rd(0x8319, 1), m.rd(0x831B)
    half_flag = attack_selector(threshold, remaining)
    table = [signed(value) for value in m.read(m.DS * 16 + 0x7920, 2)]
    return dict(sequence=sequence, stopped_at=event.kind, event_minute=event.minute,
                subtick=m.rd(0x831D), threshold=threshold, remaining=remaining,
                half_flag=half_flag, attack_by_team=[table[0 ^ half_flag], table[1 ^ half_flag]],
                sentinel_word=sentinel, initialization_word=m.rd(0x0644),
                ball=ball, ball_hidden=hidden_xy(*ball, sentinel), players=players, memory_sha256=sha(before), rng=list(rng))


def outcome_summary(outcome):
    return dict(canonical_events=len(canonical_events(outcome['events'])),
                canonical_sha256=digest(canonical_events(outcome['events'])),
                complete_result_sha256=digest(outcome['result']),
                complete_memory_sha256=sha(outcome['memory']), seeds=list(outcome['seeds']),
                ticks=outcome['result']['ticks'])


def run_case(raw, seed, sampled):
    from goal2.engine.original_match import Image, Fixture, Match
    start = time.monotonic()
    match = Match(Image.from_savestate(raw), Fixture(*FIXTURE), managed=7, seed=seed,
                  delay_byte=0, record_draws=True, ticks=sampled)
    events, previous, first, last = [], None, None, None
    transitions, rebindings, state_examples = [], [], {}
    stats = dict(ticks=0, changed_poses=0, player_changes=0, ball_changes=0,
                 outside_in_play=0, outside_movement=0, hidden=0, hidden_ball=0, repeated_reads=0)
    extrema = {kind: [128, -129, 128, -129] for kind in ('players', 'ball')}
    flags, minutes, bindings = set(), set(), {}
    for event in match.events():
        events.append(asdict(event))
        # [designed] Frames only at completed original tick boundaries. Event
        # transitions below are explicitly labelled stopped-state diagnostics.
        if sampled and observe_boundary(event):
            frame = snapshot(match, event, stats['ticks'])
            if event.kind != 'tick':
                transitions.append(dict(reason='event stopped state; not a historical event pose', sample=frame))
            else:
                stats['ticks'] += 1
                if stats['ticks'] % 1000 == 0:
                    print(f'observed seed={seed:#06x} ticks={stats["ticks"]} minute={event.minute}', flush=True)
                stats['repeated_reads'] += 1
                stats['hidden_ball'] += int(frame['ball_hidden'])
                flags.add(frame['half_flag'])
                minutes.add(frame['event_minute'])
                first = first or frame
                if previous:
                    if previous['half_flag'] != frame['half_flag']:
                        transitions.append(dict(reason='adjacent tick half flag change', before=previous, after=frame))
                    pc = sum((a['x'], a['y']) != (b['x'], b['y']) for a, b in zip(previous['players'], frame['players']))
                    bc = previous['ball'] != frame['ball']
                    stats['changed_poses'] += int(bool(pc or bc))
                    stats['player_changes'] += pc
                    stats['ball_changes'] += int(bc)
                for item in frame['players']:
                    key = item['slot']
                    if key in bindings and bindings[key] != item['player']:
                        rebindings.append(dict(sequence=frame['sequence'], slot=key, before=bindings[key], after=item['player']))
                    bindings[key] = item['player']
                    state_examples.setdefault(str(item['state']), dict(sequence=frame['sequence'], player=item))
                    stats['hidden'] += int(item['hidden'])
                for kind, points in [('players', [(p['x'], p['y']) for p in frame['players']]), ('ball', [frame['ball']])]:
                    for x, y in points:
                        e = extrema[kind]
                        e[:] = [min(e[0], x), max(e[1], x), min(e[2], y), max(e[3], y)]
                        stats['outside_in_play'] += int(not predicate(x, y, IN_PLAY))
                        stats['outside_movement'] += int(not predicate(x, y, MOVEMENT))
                previous = last = frame
        if event.kind == 'decision':
            match.answer()
    memory = match.memory_component()
    image = Image(memory)
    outcome = dict(events=events, result=copy.deepcopy(match.result()), memory=memory,
                   seeds=(image.rd(0x7B62), image.rd(0x8336)))
    if sampled:
        assert stats['ticks'] == outcome['result']['ticks'] > 0, 'runtime tick case skipped'
        assert flags == {0, 1} and min(minutes) == 0 and max(minutes) >= 90, 'both halves incomplete'
        assert stats['player_changes'] > 0 and stats['ball_changes'] > 0, 'movement not observed'
        assert any(t['reason'] == 'adjacent tick half flag change' for t in transitions), 'half transition absent'
    report = dict(seed=seed, sampled=sampled, seconds=round(time.monotonic()-start, 3),
                  outcome=outcome_summary(outcome), terminal_event_minute=events[-1]['minute'])
    if sampled:
        report.update(counts=stats, extrema=extrema, half_flags=sorted(flags),
                      first=first, last=last, transitions=transitions,
                      rebindings=rebindings, raw_state_examples=state_examples)
    return outcome, report


def verify(output=None):
    """[designed] Four mandatory full original runs, errors retained by caller."""
    receipt = source_receipt()
    raw = (ROOT / '.cache' / IMAGE_NAME).read_bytes()
    assert sha(raw) == IMAGE_SHA, 'reference savestate SHA differs'
    assert sha((ROOT / '.cache' / 'GOAL.DAT').read_bytes()) == DAT_SHA, 'GOAL.DAT SHA differs'
    report = dict(schema=1, source=receipt,
                  inputs=dict(fixture=list(FIXTURE), kind=1, managed=7, seeds=list(SEEDS),
                              delay_byte=0, record_draws=True, answers='default at every decision',
                              image_sha256=IMAGE_SHA, goal_dat_sha256=DAT_SHA),
                  environment=dict(python=platform.python_version(), platform=platform.platform()),
                  cases=[])
    import unicorn
    report['environment']['unicorn'] = unicorn.__version__
    for seed in SEEDS:
        baseline, b_report = run_case(raw, seed, False)
        print(f'completed seed={seed:#06x} sampled=False ticks={b_report["outcome"]["ticks"]}', flush=True)
        observed, o_report = run_case(raw, seed, True)
        assert_fidelity(baseline, observed)
        report['cases'].append(dict(seed=seed, baseline=b_report, observed=o_report,
                                   exact_equal=['canonical_events', 'complete_result', 'complete_memory', 'both_rng_seeds']))
        print(f'PASS seed={seed:#06x} sampled=True {o_report["counts"]}', flush=True)
    target = Path(output) if output else ROOT / 'docs/evidence/T81' / f'runtime-{time.time_ns()}.json'
    with target.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print('PASS four completed cases; no skips; report=' + str(target), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.add_argument('--output', help='new text/hash-only report path (must not exist)')
    args = parser.parse_args()
    verify(args.output)


if __name__ == '__main__':
    main()
