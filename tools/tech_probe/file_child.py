"""[designed: T158] Today's watched worker (goal2.game.watched_worker), unchanged, with a clock beside it.

As WatchedJobs' command (engine_probe.py channel --mode file) it is started exactly as the real worker is,
with the job's `input` and `events` paths. Before running watched_worker.main() it wraps the module's `_write`
so that every record it sends is also stamped (sequence, kind, time.time()) into the file named by
T158_STAMPS; the journal itself is untouched. The first stamp line says when the interpreter had imported the
worker ("ready").

    <pypy> file_child.py echo FOLDER

is the clock-free round trip of the same journals: it reads the command journal with the real CommandReader
(polling every 2 ms as the worker does) and answers each `pause` with one `event` record written by the real
`_write`, and exits after T158_ECHOES answers (engine_probe.py channel --mode file).
"""
import json
import os
import sys
import time
from pathlib import Path

T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402,F401


def echo(folder):
    from goal2.game.watched_jobs import CommandReader, _write
    folder = Path(folder)
    reader = CommandReader(folder / "commands", "t")
    with open(folder / "events", "ab") as stream:
        _write(stream, "t", 0, "ready", None)
        sent = 1
        answered = 0
        while True:
            reader.wait(lambda: reader.pauses > answered)
            answered += 1
            if answered > int(os.environ.get("T158_ECHOES", "20")):
                return
            _write(stream, "t", sent, "event", {"echo": answered})
            sent += 1


def main():
    if sys.argv[1] == "echo":
        return echo(sys.argv[2])
    import goal2.game.watched_worker as worker
    stamps = open(os.environ["T158_STAMPS"], "a", encoding="utf-8")
    stamps.write(json.dumps({"ready": time.time(), "started": T0,
                             "clock": time.get_clock_info("time").resolution}) + "\n")
    stamps.flush()
    original = worker._write

    def stamped(stream, token, sequence, kind, value):
        original(stream, token, sequence, kind, value)
        stamps.write(f"{sequence} {kind} {time.time()!r}\n")
        stamps.flush()

    worker._write = stamped
    worker.main()


if __name__ == "__main__":
    main()
