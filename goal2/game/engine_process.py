"""[designed: owner, 2026-11-03, #527 D3; T159] The window's side of the engine process (goal2.game.engine_server).

`EngineProcess(on_reply)` starts the child once under engine_python() (PyPy 3.11), sends it requests and reads its
replies on a reader thread; each reply goes to `on_reply(kind, value)` on that thread (goal2/game has no Qt: the
window turns the call into a signal). The protocol is docs/engine-process.md's.

- `open(state, template)` sends the game, encoded as a save (goal2.game.session_save), once per game, never per
  match: the engine keeps it and plays each match on a fresh copy.
- `match(kind, fixture, ...)` starts a watched or competitive match; one at a time. `ack`, `pause`, `answer` and
  `cancel` speak to the running match. No tokens: one pipe is ordered and private.
- The child's end (end of its stdout, or its exit) is reported once as `death` {code, stderr, error}, with its exit
  code and the tail of its stderr; the next `open` or `match` starts a new process, which is sent the last game
  before the match.
- A `cancel` the engine has not answered within `cancel_deadline` seconds is ended by killing the process: a death.
- `close()` sends `quit`, waits briefly, then kills; that end is not reported.

Replies and their values: `ready` {implementation, version, pid}; `opened`; `event` (an Event); `frame` (a pitch
sample, goal2.game.watched_pitch); `decision` {decision, event}; `answered` (the engine's report,
watched_match._report); `pause_dropped` (the sample); `complete` (a WatchedOutcome); `cancelled`; `error` (its text).
"""
from __future__ import annotations

import subprocess
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from goal2.game.engine_server import (KINDS, MAX_HEADER, MAX_PAYLOAD, OPTIONS, ProtocolError, encode_packet,
                                      read_packet)

ROOT = Path(__file__).resolve().parents[2]
MODULE = "goal2.game.engine_server"
# [designed: T159] How long a cancel may go unanswered before the process is killed. The engine reads it at every
# event and pitch sample, milliseconds apart in play; the longest stretch without one is a match's preparation.
CANCEL_DEADLINE = 10.0
# [designed: T159] How long close() waits for the engine to leave after `quit`.
QUIT_WAIT = 2.0
STDERR_TAIL = 4096


class _Life:
    """One child process and what is known of its end."""

    def __init__(self, process):
        self.process = process
        self.quiet = False          # close(): the end is not a death
        self.stderr = bytearray()
        self.drain = None


class EngineProcess:
    def __init__(self, on_reply, *, command=None, cancel_deadline=CANCEL_DEADLINE):
        self.on_reply = on_reply
        self.command = None if command is None else list(command)
        self.cancel_deadline = cancel_deadline
        self._life = None
        self._game = None
        self._lock = threading.RLock()
        self._write = threading.Lock()
        self._match = None           # the running match's number
        self._completion = None      # [designed: T199] private until the reply transaction ends
        self._cancelled_completion = False
        self._completion_timer = None
        self._matches = 0
        self.opens = 0               # `open` requests sent, over every process
        self.ready = None            # the current process's `ready` value
        self.closed = False

    # --- state ---------------------------------------------------------------------------------------------------

    @property
    def process(self):
        life = self._life
        return life.process if life is not None else None

    @property
    def pid(self):
        process = self.process
        return process.pid if process is not None else None

    @property
    def stderr(self) -> str:
        """The tail of the current process's stderr: its diagnostics."""
        life = self._life
        return bytes(life.stderr).decode("utf8", "replace") if life is not None else ""

    @property
    def busy(self) -> bool:
        return self._match is not None or self._completion is not None

    # --- requests ------------------------------------------------------------------------------------------------

    def open(self, state, template) -> None:
        from goal2.game.session_save import encode
        self.open_encoded(encode(state, template))

    def open_encoded(self, raw: bytes) -> None:
        """Send an encoded game (session_save.encode); a new process is started when there is none."""
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError("the engine is playing a match; cancel it before opening another game")
            self._game = bytes(raw)
            if self._life is None:
                self._start()
            else:
                self._send_open()

    def match(self, kind, fixture, *, options=None, frames=False, bench=False, prompts=False) -> None:
        """Start a match on the open game: `kind` watched or competitive; `options` among reference_seed,
        delay_byte and record_draws; `frames` streams the pitch samples; `bench` (with frames) asks the bench's
        decisions and paces the samples on `ack`; `prompts` (with the bench) also asks the player prompts
        (watched_match.PROMPT_CONTEXTS: the set-piece taker, the shoot-out order, the menu before extra time) [designed:
        T167, #541]."""
        options = dict(options or {})
        if (kind not in KINDS or type(frames) is not bool or type(bench) is not bool or type(prompts) is not bool
                or (prompts and not bench)):
            raise ValueError("invalid engine match request")
        if bench and not frames:
            # [designed: #316] the original takes the player's Enter in play at a pitch sample
            raise ValueError("the bench needs the pitch samples (frames=True)")
        if set(options) - set(OPTIONS):
            raise ValueError(f"engine match options are {', '.join(OPTIONS)}")
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError("the engine is already playing a match")
            if self._game is None:
                raise ValueError("no game is open")
            if self._life is None:
                self._start()
            self._matches += 1
            self._match = self._matches
            self._events = []
            self._frame_sequence, self._frame_watermark = 0, 0
            request = {"op": "match", "kind": kind, "fixture": asdict(fixture), "options": options,
                       "frames": frames, "bench": bench}
            if prompts:
                request["prompts"] = True
            self._send(request)

    def ack(self, sample: int) -> bool:
        """The window has shown pitch sample `sample`: the engine may run LEAD samples past it."""
        if type(sample) is not int or sample < 0:
            raise ValueError("invalid pitch sample acknowledgement")
        return self._command({"op": "ack", "sample": sample})

    def pause(self) -> bool:
        """The player's Enter in play."""
        return self._command({"op": "pause"})

    def answer(self, decision: int, substitutions=(), *, choice=None, changes=None) -> bool:
        """Answer bench decision `decision` with (off, on) pairs; none plays on. `choice` answers a player prompt
        instead: {'taker': word or None} or {'shootout_order': [words]} [designed: T167, #541]. `changes` adds the
        bench's positions, marks and own tactics to the same answer (watched_jobs.CHANGES) [designed: T180]."""
        from goal2.game.watched_jobs import _changes, _choice, _pairs
        if type(decision) is not int or decision < 0:
            raise ValueError("invalid bench decision number")
        if choice is not None:
            return self._command(dict({"op": "answer", "decision": decision}, **_choice(choice)))
        command = {"op": "answer", "decision": decision, "substitutions": _pairs(list(substitutions))}
        changes = _changes(changes or {})
        if changes:
            command["changes"] = changes
        return self._command(command)

    def cancel(self) -> bool:
        """End the running match; the engine replies `cancelled` and stays up. Unanswered within the deadline, the
        process is killed."""
        with self._lock:
            number = self._match
            if self._completion is not None:
                self._cancelled_completion = True
                return True
            elif not self._command({"op": "cancel"}):
                return False
            timer = threading.Timer(self.cancel_deadline, self._overdue, args=(number,))
            timer.daemon = True
            timer.start()
            return True

    def close(self) -> None:
        with self._lock:
            self.closed = True
            if self._completion is not None:
                self._cancelled_completion = True
            life = self._life
            if life is None:
                return
            life.quiet = True
            try:
                self._send({"op": "quit"})
            except OSError:
                pass
        try:
            life.process.wait(timeout=QUIT_WAIT)
        except subprocess.TimeoutExpired:
            life.process.kill()
            life.process.wait()
        self._ended(life)

    # --- internals -----------------------------------------------------------------------------------------------

    def _usable(self):
        if self.closed:
            raise ValueError("the engine process is closed")

    def _command(self, header) -> bool:
        with self._lock:
            if self._match is None:
                return False
            self._send(header)
            return True

    def _send(self, header, payload=b""):
        packet = encode_packet(header, payload)
        with self._write:
            stream = self._life.process.stdin
            stream.write(packet)
            stream.flush()

    def _send_open(self):
        self._send({"op": "open"}, self._game)
        self.opens += 1

    def _start(self):
        from goal2.game.engine_python import worker_command
        command = worker_command(MODULE) if self.command is None else self.command
        # [designed: T159, the task's Windows hazard] binary pipes on every stream; stderr drained on its own thread
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        life = _Life(process)
        life.drain = threading.Thread(target=self._drain, args=(life,), name="goal2-engine-stderr", daemon=True)
        life.drain.start()
        self._life = life
        self.ready = None
        threading.Thread(target=self._read, args=(life,), name="goal2-engine-replies", daemon=True).start()
        if self._game is not None:
            self._send_open()

    def _drain(self, life):
        stream = life.process.stderr
        while True:
            chunk = stream.read(4096)
            if not chunk:
                stream.close()
                return
            life.stderr += chunk
            del life.stderr[:-STDERR_TAIL]

    def _overdue(self, number):
        with self._lock:
            pending = self._completion is not None and self._matches == number
            if (self._match == number or pending) and self._life is not None:
                self._life.process.kill()

    def _read(self, life):
        error = None
        try:
            while True:
                packet = read_packet(life.process.stdout, max_header=MAX_HEADER, max_payload=MAX_PAYLOAD)
                if packet is None:
                    break
                reply = self._decode(life, *packet)
                if reply is not None:
                    self._deliver(*reply)
        except (ProtocolError, ValueError, TypeError, KeyError) as exc:
            # [designed: T159] A reply that cannot be read ends the engine: the stream cannot be resynchronised.
            error = f"{type(exc).__name__}: {exc}"
            life.process.kill()
        except OSError as exc:
            error = f"{type(exc).__name__}: {exc}"
        life.process.wait()
        with self._lock:
            unfinished = self._life is life and self._completion is not None
        if unfinished and error is None:
            error = (f"engine exited ({life.process.returncode}) after its completion" if life.process.returncode
                     else "engine ended before confirming its completion")
        life.process.stdout.close()
        if life.drain is not None:
            life.drain.join(2)
        if self._ended(life) and not life.quiet:
            self._deliver("death", {"code": life.process.returncode,
                                    "stderr": bytes(life.stderr).decode("utf8", "replace"), "error": error})

    def _ended(self, life) -> bool:
        """Forget `life` if it is still the current process; whether it was."""
        with self._lock:
            if self._life is not life:
                return False
            self._life = None
            self._match = None
            self._take_completion()
            self.ready = None
        for stream in (life.process.stdin,):
            try:
                stream.close()
            except OSError:
                pass
        return True

    def _decode(self, life, header, payload):
        from goal2.game.session_save import _restore_json_value
        from goal2.game.watched_jobs import _event, _report
        kind = header.get("kind")
        value = _restore_json_value(header.get("value"), "engine reply")
        with self._lock:
            if self._life is not life:
                return kind, value
            if kind == "ready":
                if not isinstance(value, dict):
                    raise ProtocolError("invalid ready reply")
                self.ready = value
            elif kind in ("opened",):
                value = None
            elif kind == "event":
                value = _event(value)
                self._running(kind)
                self._events.append(value)
            elif kind == "frame":
                from goal2.game.watched_pitch import validate
                self._running(kind)
                validate(value, self._frame_sequence, self._frame_watermark)
                self._frame_sequence += 1
                self._frame_watermark = value["watermark"]
            elif kind == "decision":
                self._running(kind)
                if set(value) != {"decision", "event"} or type(value["decision"]) is not int:
                    raise ProtocolError("invalid decision reply")
                value = {"decision": value["decision"], "event": _event(value["event"])}
            elif kind == "answered":
                self._running(kind)
                value = _report(value)
            elif kind == "pause_dropped":
                self._running(kind)
                if type(value) is not int:
                    raise ProtocolError("invalid pause_dropped reply")
            elif kind == "complete":
                from goal2.game.watched_match import WatchedOutcome
                self._running(kind)
                if set(value) != {"result", "events", "seeds", "engine_year"}:
                    raise ProtocolError("invalid complete reply")
                value = WatchedOutcome(value["result"], payload, tuple(_event(e) for e in value["events"]),
                                       tuple(value["seeds"]), value["engine_year"])
                if list(value.events) != self._events:
                    raise ProtocolError("the completed match differs from the events streamed")
                # [designed: T199, #627] Do not publish before the transcript is confirmed.
                self._completion = value
                self._match = None
                self._completion_timer = threading.Timer(self.cancel_deadline, self._overdue, args=(self._matches,))
                self._completion_timer.daemon = True
                self._completion_timer.start()
                return None
            elif kind == "settled":
                if self._completion is None or value is not None or payload:
                    raise ProtocolError("invalid completion confirmation")
                cancelled = self._cancelled_completion
                value = self._take_completion()
                if cancelled:
                    kind, value = "cancelled", None
                else:
                    kind = "complete"
            elif kind == "cancelled":
                self._running(kind)
                value = None
                self._match = None
            elif kind == "error":
                if not isinstance(value, str):
                    raise ProtocolError("invalid error reply")
                self._match = None
                self._take_completion()
            else:
                raise ProtocolError(f"unknown engine reply: {kind!r}")
        return kind, value

    def _take_completion(self):
        """Called under the lifecycle lock: consume or discard the held result."""
        value, self._completion = self._completion, None
        self._cancelled_completion = False
        timer, self._completion_timer = self._completion_timer, None
        if timer is not None:
            timer.cancel()
        return value

    def _running(self, kind):
        if self._match is None:
            raise ProtocolError(f"engine reply {kind!r} with no match running")

    def _deliver(self, kind, value):
        try:
            self.on_reply(kind, value)
        except Exception:  # noqa: BLE001 - the window's callback must not end the reader
            import traceback
            traceback.print_exc(file=sys.stderr)
