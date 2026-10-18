"""[designed: T80] Owned original competitive child; no UI or active-state writes.
[confirmed: T51/E034 at424d599] Shared original driver, five substitutions each,
default play-on answers and full original post-match tail; no Python simulation.
"""
import json
from pathlib import Path
import sys
from goal2.engine.original_match import Fixture
from goal2.game.competitive_match import prepare_competitive
from goal2.game.session_save import load
from goal2.game.watched_jobs import _write
from goal2.game.watched_match import _drive_match


def main():
    source = Path(sys.argv[1])
    state, original = load(source)
    request = json.loads((source.parent / 'request.json').read_text())
    fixture = Fixture(**request['fixture'])
    with open(sys.argv[2], 'ab') as stream:
        sequence = 0
        def send(kind, value):
            nonlocal sequence
            _write(stream, request['token'], sequence, kind, value)
            sequence += 1
        try:
            image = prepare_competitive(state, original, fixture)
            outcome = _drive_match(state, image, fixture, substitutions=(5, 5),
                                   _observe=lambda event: send('event', event), **request['options'])
            send('complete', outcome)
        except Exception as exc:
            send('error', f'{type(exc).__name__}: {exc}')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
