"""[designed: T86] Fake worker commands that speak the existing child protocols.

    python3 -m goal2.scenario.worker quick|watched|competitive|viewer [--script S] [--fault F] ARGS

The controllers append ARGS exactly as for the original children. Faults that
need no input (crash, hang, wrong token, gap, ...) never read the input file, so
they run unchanged against the real backend. Every packet is written by the
real writers (`watched_jobs._write`, `watched_pitch.write_frame`, `write_json`).
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path

ROLE_FAULTS = {
    'quick': ('fail', 'garbage', 'early', 'early-garbage', 'hang', 'ignore-term', 'slow',
              'wrong-template', 'double-count', 'bad-halftime'),
    'watched': ('wrong-token', 'gap', 'repeat', 'error', 'crash', 'hang', 'truncated', 'slow',
                'early', 'duplicate', 'mismatch', 'bad-result', 'bad-stats', 'no-end', 'bad-kind',
                'bad-image', 'bad-memory', 'few-frames'),
    'viewer': ('stale-token', 'regress', 'no-ack', 'close', 'crash', 'bad-digest', 'future',
               'bad-frame-digest'),
}
ROLE_FAULTS['competitive'] = ROLE_FAULTS['watched']


def _options(args):
    script = fault = None
    while args and args[0] in ('--script', '--fault'):
        flag, value, args = args[0], args[1], args[2:]
        if flag == '--script':
            script = value
        else:
            fault = value
    return script, fault, args


def _wait_release(folder, limit=30):
    deadline = time.monotonic() + limit
    while not (folder / 'release').exists() and time.monotonic() < deadline:
        time.sleep(.005)


def quick(args):
    from goal2.desktop.worker import write_json
    from goal2.scenario import factory, scripts
    script, fault, args = _options(args)
    source, target = Path(args[0]), Path(args[1])
    halftime = args[2:] == ['--halftime']
    if fault == 'fail':
        sys.stderr.write('deliberate fictional failure');return 7
    if fault == 'ignore-term':
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    if fault in ('hang', 'ignore-term'):
        time.sleep(60);return 0
    if fault == 'early-garbage':
        target.write_bytes(b'not a continuation');_wait_release(source.parent);return 0
    if fault == 'garbage':
        target.write_bytes(b'not a continuation');return 0
    state, template = factory.load(source)
    fixture = state.campaign.next_fixture
    changes = []
    if halftime:
        packet = scripts.halftime(state, fixture, script)
        if fault == 'bad-halftime':
            packet['teams'].reverse()
        write_json(source.parent / 'halftime.json', packet)
        command = source.parent / 'continue.json'
        while not command.exists():
            time.sleep(.01)
        changes = json.loads(command.read_text())
        from goal2.game.substitutions import swap
        for outgoing, incoming in changes:
            packet = swap(packet, outgoing, incoming)
    candidate = scripts.quick_candidate(state, fixture, script, changes)
    if fault == 'double-count':
        candidate.match_count += 1
    if fault == 'slow':
        time.sleep(.4)
    out = factory.encode(candidate, b'another career template' if fault == 'wrong-template' else template)
    temporary = target.with_suffix('.tmp');temporary.write_bytes(out);temporary.replace(target)
    if fault == 'early':
        _wait_release(source.parent)
    return 0


def watched(args, competitive):
    from goal2.engine.original_match import Fixture
    from goal2.engine.original_match.match import Event
    from goal2.game.watched_jobs import _write
    from goal2.game.watched_match import WatchedOutcome
    from goal2.game.watched_pitch import write_frame
    script, fault, args = _options(args)
    source, journal = Path(args[0]), Path(args[1])
    request = json.loads((source.parent / 'request.json').read_text())
    token = request['token']
    with journal.open('ab') as stream:
        sequence = 0

        def send(kind, value, *, identity=None, number=None):
            nonlocal sequence
            _write(stream, token if identity is None else identity, sequence if number is None else number, kind, value)
            sequence += 1
        if fault == 'crash':
            return 4
        if fault == 'error':
            send('error', 'RuntimeError: deliberate fictional failure');return 1
        if fault == 'truncated':
            stream.write(b'\x00\x00');return 0
        if fault in ('wrong-token', 'gap', 'repeat', 'hang'):
            send('event', Event('minute', 1, (0, 0)), identity='0' * 48 if fault == 'wrong-token' else None)
            if fault == 'gap':
                send('event', Event('minute', 15, (0, 0)), number=2)
            if fault == 'repeat':
                send('event', Event('minute', 15, (0, 0)), number=0)
            if fault == 'hang':
                time.sleep(60)
            return 0
        from goal2.scenario import factory, scripts
        state, _ = factory.load(source)
        fixture = Fixture(**request['fixture'])
        image = hashlib.sha256(source.read_bytes()).hexdigest()
        played = scripts.match(state, fixture, image, competitive=competitive, name=script)
        events = played['events']
        if fault == 'no-end':
            events = [e for e in events if e.kind != 'end']
        poses = scripts.frames(state, fixture, played) if request.get('frames') else []
        if fault == 'few-frames':
            poses = poses[:-1]
        with open(source.parent / 'frames', 'ab') as frame_stream:
            written = 0
            for event in events:
                send('event', event)
                written += 1
                while poses and poses[0]['watermark'] <= written:
                    write_frame(frame_stream, token, poses.pop(0))
                if fault == 'slow':
                    time.sleep(.01)
        result = played['result']
        memory = played['memory']
        if fault == 'bad-result':
            result['index'] += 1
        if fault == 'bad-stats':
            result['board']['statistics']['shots'] = [-1, -1]
        if fault == 'bad-kind':
            result['kind'] = 201
        if fault == 'bad-image':
            result['image_sha256'] = '0' * 64
        if fault == 'bad-memory':
            memory = json.dumps(dict(json.loads(memory), mark='career')).encode()
        sent = list(events)
        if fault == 'mismatch':
            sent[0] = Event(sent[0].kind, sent[0].minute + 1, sent[0].score, sent[0].data)
        outcome = WatchedOutcome(result, memory, tuple(sent), played['seeds'], played['engine_year'])
        send('complete', outcome)
        if fault == 'duplicate':
            send('complete', outcome)
        if fault == 'early':
            (source.parent / 'ready').write_text('complete')
            _wait_release(source.parent)
    return 0


def viewer(args):
    """[designed: T86] Reads the display journal with the real Display; renders nothing."""
    from goal2.desktop.match_view import Display
    from goal2.desktop.pygame_viewer import frame_digest, _replace_status
    _, fault, args = _options(args)
    folder, token = Path(args[0]), args[1]
    display = Display(token)
    stream = (folder / 'display').open('rb')
    buffer, digest, last, held = b'', None, None, False
    deadline = time.monotonic() + 60

    def status(kind, sequence, value_digest, frames):
        value = {'token': '0' * 48 if fault == 'stale-token' else token, 'kind': kind,
                 'sequence': sequence, 'digest': value_digest}
        if fault == 'bad-digest':
            value['digest'] = '0' * 64
        if fault == 'future':
            value['sequence'] = sequence + 5
        if frames:
            value.update(frame_sequence=display.consumed,
                         frame_digest='0' * 64 if fault == 'bad-frame-digest' and digest else digest)
        temporary = folder / 'status.tmp'
        temporary.write_text(json.dumps(value));_replace_status(temporary, folder / 'status')
    if fault == 'crash':
        return 3
    while time.monotonic() < deadline:
        buffer += stream.read(65536)
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            display.accept(json.loads(line))
        if display.pitch_rate is not None and fault != 'no-ack':
            while display.frames:
                display.frame = display.frames.popleft();display.rendered()
                digest = frame_digest(display.frame)
        if display.sequence != last and not held:
            last = display.sequence
            pitch = display.pitch_rate is not None
            # [designed: T86] Events flow only after the parent accepted a status, so a
            # regression written at sequence >= 3 always follows an accepted sequence >= 1.
            if fault == 'regress' and display.sequence >= 3:
                status('ready', 0, Display(token).digest(), pitch);held = True
            else:
                status('ready', display.sequence, display.digest(), pitch)
            if fault == 'close' and display.sequence >= 3:
                status('closed', display.sequence, display.digest(), pitch);return 0
        time.sleep(.005)
    return 0


def main(argv=None):
    args = sys.argv[1:] if argv is None else list(argv)
    role, rest = args[0], args[1:]
    _, fault, _ = _options(rest)
    if fault is not None and fault not in ROLE_FAULTS[role]:
        raise SystemExit(f'unknown {role} fault {fault!r}')
    if role == 'quick':
        return quick(rest)
    if role in ('watched', 'competitive'):
        return watched(rest, role == 'competitive')
    if role == 'viewer':
        return viewer(rest)
    raise SystemExit(f'unknown role {role!r}')


def command(role, *, script=None, fault=None):
    """[designed: T86] The argv prefix a controller is given as its injected command."""
    out = [sys.executable, '-m', 'goal2.scenario.worker', role]
    if script is not None:
        out += ['--script', script]
    if fault is not None:
        out += ['--fault', fault]
    return out


if __name__ == '__main__':
    sys.exit(main())
