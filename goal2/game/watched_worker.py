"""[designed: T65] Private local child; default decisions use the shared driver."""
import json
from pathlib import Path
from types import SimpleNamespace
from goal2.engine.original_match import Fixture
from goal2.game.session_save import load
import sys
from goal2.game.watched_jobs import _write
from goal2.game.watched_pitch import write_frame
from goal2.game.watched_match import prepare_watched, _drive_match


def main():
    state, original = load(sys.argv[1])
    request = json.loads((Path(sys.argv[1]).parent / 'request.json').read_text())
    job = SimpleNamespace(state=state,token=request['token'],fixture=Fixture(**request['fixture']))
    options = request['options']
    with open(sys.argv[2], 'ab') as stream, open(Path(sys.argv[1]).parent / 'frames', 'ab') as frames:
        sequence = 0
        def send(kind, value):
            nonlocal sequence
            _write(stream, job.token, sequence, kind, value)
            sequence += 1
        try:
            image = prepare_watched(job.state, original, job.fixture)
            outcome = _drive_match(job.state, image, job.fixture,
                _observe=lambda event: send('event', event),
                _observe_pitch=(lambda frame: write_frame(frames,job.token,frame)) if request.get('frames',False) else None, **options)
            send('complete', outcome)
        except Exception as exc:
            send('error', f'{type(exc).__name__}: {exc}')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
