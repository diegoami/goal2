"""[designed: owner, 2026-11-01, #500] Tests play the match engine the way goal2 does: in a child process under
`engine_python()` (PyPy 3.11, T152), never in the CPython test process (#496).

`call(target, *args, **kwargs)` runs `target` ("package.module:function") in that child and returns its value;
`start(...)` does the same without waiting (`.result()` waits), so a test can compute its reference meanwhile. The
arguments and the value cross the process boundary pickled. An exception raised in the child is raised again in the
parent as the same exception (its child traceback chained as the cause); one that does not survive pickling is
raised as ChildError with its type, message and traceback.

The guard: goal2/tests/__init__.py installs `guard()` in every test process (not in this module's children, marked
by GOAL2_ENGINE_CHILD), so a sealed port engine (PortMachine) constructed in the test process fails the test with
EngineInTestProcess. The original engine under Unicorn, the reference arm of the fidelity comparisons, is not the
port: PyPy cannot load Unicorn (its package does not build for PyPy 3.11), so those reference runs stay where they
are (#500's PR lists them).

`drive(...)` is the child side of the tests that watch the pitch or answer the bench: `_drive_match` on the prepared
image, with picklable observers that come back to the parent with what they gathered.
"""
from __future__ import annotations

import os
import pickle
import subprocess
import sys
import tempfile
import traceback
import weakref
from contextlib import nullcontext
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHILD = "GOAL2_ENGINE_CHILD"
PROTOCOL = 4


class EngineInTestProcess(AssertionError):
    """The sealed port was about to play in the CPython test process."""


class ChildError(RuntimeError):
    """An exception of the child that could not be pickled back."""


class ChildTraceback(Exception):
    """The child's traceback text, chained as the cause of a re-raised exception."""


class Enough(Exception):
    """Raised by a `drive` observer: the test has seen enough of the match; `drive` stops it there."""


# --- the guard -------------------------------------------------------------------------------------------------

def guard() -> None:
    """Make PortMachine refuse to start in this process (idempotent)."""
    from goal2.engine.original_match.port import engine
    if getattr(engine.PortMachine.__init__, "_goal2_guard", False):
        return
    original = engine.PortMachine.__init__

    def refused(self, *args, **kwargs):
        raise EngineInTestProcess(
            "the sealed port engine was started in the test process; play the match with "
            "goal2.tests.pypy_engine.call/start (under engine_python(), #500)")
    refused._goal2_guard = True
    refused._goal2_original = original
    engine.PortMachine.__init__ = refused


def guarded() -> bool:
    from goal2.engine.original_match.port import engine
    return bool(getattr(engine.PortMachine.__init__, "_goal2_guard", False))


# --- the parent side -------------------------------------------------------------------------------------------

def _interpreter():
    from goal2.game.engine_python import engine_python
    return engine_python()


def _cleanup(process, folder):
    if process.poll() is None:
        process.kill()
        process.wait()
    folder.cleanup()


class Pending:
    """A call running in its child."""

    def __init__(self, target, args, kwargs, interpreter=None):
        self.interpreter = interpreter or _interpreter()
        self._folder = tempfile.TemporaryDirectory(prefix="goal2-engine-child-")
        folder = Path(self._folder.name)
        self._request, self._reply = folder / "request.pickle", folder / "reply.pickle"
        self._request.write_bytes(pickle.dumps((target, args, kwargs), protocol=PROTOCOL))
        env = dict(os.environ, **{CHILD: "1"})
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT)] + [p for p in [env.get("PYTHONPATH")] if p])
        self.process = subprocess.Popen(
            [self.interpreter, "-B", "-m", "goal2.tests.pypy_engine", str(self._request), str(self._reply)],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL)
        self._finalizer = weakref.finalize(self, _cleanup, self.process, self._folder)
        self._done = False

    def result(self, timeout=None):
        try:
            code = self.process.wait(timeout)
            if not self._reply.exists():
                raise ChildError(f"the engine child ({self.interpreter}) exited with {code} and no reply")
            status, value, text = pickle.loads(self._reply.read_bytes())
        finally:
            if self.process.poll() is not None:
                self._finalizer()
        if status == "ok":
            return value
        if status == "error":
            raise value from ChildTraceback(text)
        raise ChildError(text)


def start(target: str, *args, interpreter: str | None = None, **kwargs) -> Pending:
    """Start `target(*args, **kwargs)` in a child under `interpreter` (default: engine_python())."""
    return Pending(target, args, kwargs, interpreter)


def call(target: str, *args, interpreter: str | None = None, **kwargs):
    """`target(*args, **kwargs)` in a child under `interpreter` (default: engine_python()); its value."""
    return start(target, *args, interpreter=interpreter, **kwargs).result()


def resolve(target: str):
    module, _, name = target.partition(":")
    value = import_module(module)
    for part in name.split("."):
        value = getattr(value, part)
    return value


# --- the child side --------------------------------------------------------------------------------------------

def probe():
    """What the child is: (implementation, guarded, child flag)."""
    import platform
    return platform.python_implementation(), guarded(), os.environ.get(CHILD)


def _drop(frame):
    pass


def drive(state, original, fixture, *, observer=None, pitch=False, snapshot=None, competitive=False, **options):
    """`_drive_match` on the prepared image (prepare_competitive when `competitive`). `observer(frame)` sees each
    pitch sample (`pitch=True` without one: samples are taken and dropped) and may raise Enough to end the match
    there; `snapshot(match, event, sequence, watermark, frame)` checks each sample against the engine as it is taken.
    Returns (the outcome, None when stopped, observer, snapshot), the observers with what they gathered."""
    from goal2.game import watched_pitch
    from goal2.game.watched_match import _drive_match, prepare_watched
    if competitive:
        from goal2.game.competitive_match import prepare_competitive
        image = prepare_competitive(state, original, fixture)
    else:
        image = prepare_watched(state, original, fixture)
    if observer is None and (pitch or snapshot is not None):
        observer = _drop
    context = nullcontext()
    if snapshot is not None:
        from unittest.mock import patch
        real = watched_pitch.snapshot

        def checked(match, event, sequence, watermark):
            frame = real(match, event, sequence, watermark)
            snapshot(match, event, sequence, watermark, frame)
            return frame
        context = patch.object(watched_pitch, "snapshot", checked)
    try:
        with context:
            outcome = _drive_match(state, image, fixture, _observe_pitch=observer, **options)
    except Enough:
        outcome = None
    return outcome, observer, snapshot


def main(argv=None) -> int:
    request, reply = (argv or sys.argv)[1:3]
    try:
        target, args, kwargs = pickle.loads(Path(request).read_bytes())
        answer = ("ok", resolve(target)(*args, **kwargs), None)
    except BaseException as exc:  # noqa: BLE001 - everything goes back to the parent
        text = traceback.format_exc()
        answer = ("error", exc, text)
    try:
        data = pickle.dumps(answer, protocol=PROTOCOL)
        pickle.loads(data)
    except Exception:  # noqa: BLE001 - an unpicklable value or exception
        if answer[0] == "ok":
            text = "the child's value could not be pickled:\n" + traceback.format_exc()
        else:
            text = f"{type(answer[1]).__name__}: {answer[1]}\n{answer[2]}"
        data = pickle.dumps(("unpicklable", None, text), protocol=PROTOCOL)
    Path(reply).write_bytes(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
