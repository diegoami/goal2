"""[designed: T65] Private local child; default decisions use the shared driver.

[designed: T102] A job with the bench (`bench` in its request) is played by a watching player: the
child reports each bench decision and waits for the parent's answer, takes the player's Enter in
play, and never writes a pitch sample more than LEAD past the one the viewer acknowledged
(goal2.game.watched_jobs)."""
import json
from pathlib import Path
from types import SimpleNamespace
from goal2.engine.original_match import Fixture
from goal2.game.session_save import load
import sys
from goal2.game.watched_jobs import _write, CommandReader, LEAD
from goal2.game.watched_pitch import write_frame
from goal2.game.watched_match import prepare_watched, _drive_match


class BenchPolicy:
    """[designed: T102] The parent's answers, read from the command journal."""
    def __init__(self, commands, send):
        self.commands = commands
        self.send = send
        self.asked = 0
        self.paused = 0

    def decide(self, event):
        number = self.asked
        self.asked += 1
        self.commands.wait(lambda: bool(self.commands.answers))
        decision, pairs = self.commands.answers.pop(0)
        if decision != number:
            raise ValueError('watched answer is for another decision')
        return pairs

    def pace(self, sequence):
        """Write sample `sequence` only within LEAD of the acknowledged one. The wait reads the
        journal at least once, so an Enter read here is applied after this sample."""
        self.commands.wait(lambda: sequence <= self.commands.ack + LEAD)

    def pause_now(self, sequence):
        # [designed: T102] Only Enters read before this sample was written count, so a pause
        # lands after a definite sample (the one after the read).
        if self.commands.pauses > self.paused:
            self.paused = self.commands.pauses
            return True
        return False

    def answered(self, report):
        self.send('answered', report)


def main():
    state, original = load(sys.argv[1])
    folder = Path(sys.argv[1]).parent
    request = json.loads((folder / 'request.json').read_text())
    job = SimpleNamespace(state=state,token=request['token'],fixture=Fixture(**request['fixture']))
    options = request['options']
    with open(sys.argv[2], 'ab') as stream, open(folder / 'frames', 'ab') as frames:
        sequence = 0
        def send(kind, value):
            nonlocal sequence
            _write(stream, job.token, sequence, kind, value)
            sequence += 1
        try:
            policy = BenchPolicy(CommandReader(folder / 'commands', job.token), send) if request.get('bench') else None
            def pitch(frame):
                if policy is not None:
                    policy.pace(frame['sequence'])
                write_frame(frames, job.token, frame)
            image = prepare_watched(job.state, original, job.fixture)
            outcome = _drive_match(job.state, image, job.fixture,
                _observe=lambda event: send('event', event),
                _observe_pitch=pitch if request.get('frames',False) else None, policy=policy, **options)
            send('complete', outcome)
        except Exception as exc:
            send('error', f'{type(exc).__name__}: {exc}')
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
