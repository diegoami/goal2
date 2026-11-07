"""[designed: owner, 2026-11-03, #527 D3; T159] The engine process: one long-lived child that plays matches for the
window over one pipe, `python -m goal2.game.engine_server` under engine_python() (PyPy 3.11).

The protocol is docs/engine-process.md's; it is the one docs/design/technology-2026-11/README.md §3.4 proposes,
from T158's prototype (`pipe_child.py`, deleted with tools/tech_probe/ by T161). Both directions are packets: a 4-byte big-endian length, that
many bytes of UTF-8 JSON (an object, the header), then, when the header has `size`, that many bytes of binary
payload. Requests carry `op`, replies `kind` and `value`.

The match is the file workers' match, never a second driver [designed: T159, the task's hazard; T161 deleted the
workers]: preparation by prepare_watched, or prepare_competitive with `substitutions=(5, 5)`; a friendly has
BM-7's unlimited budget (watched_match.FRIENDLY_SUBSTITUTIONS, T180). The shared `_drive_match` and the bench's
answers, pauses and LEAD pacing use BenchPolicy (the workers', moved here by T161), fed from the pipe.

Commands arrive on a reader thread and wait in a queue; the match reads them at each paced sample and each decision
wait and, for `cancel`, also at each event and sample, so a match without the bench can be cancelled too. End of stdin (the window gone) ends the process wherever it waits (#417).

Nothing else of this process writes to the protocol's stream: file descriptor 1 is moved to a private descriptor at
start, and fd 1 and sys.stdout then point at stderr, so a stray print or warning lands in the diagnostics.
"""
from __future__ import annotations

import json
import os
import queue
import struct
import sys
import threading

# [designed: T159] The bounds of one packet. A header holds at most a completed match's result and events (the file
# journal bounded its whole completion record at 8 MiB, with the memory in it); a payload holds
# the encoded game (26.7 MB today, measurements/T158 `open_bytes`) or a completed match's memory.
MAX_HEADER = 16 * 1024 * 1024
MAX_PAYLOAD = 64 * 1024 * 1024
# The options a match request may carry: the bridges pass exactly these to _drive_match (watched_jobs._start).
OPTIONS = ("reference_seed", "delay_byte", "record_draws")
KINDS = ("watched", "competitive")


class ProtocolError(ValueError):
    """A packet that cannot be read: oversized, truncated or malformed. The stream cannot be resynchronised."""


def encode_packet(header: dict, payload: bytes = b"") -> bytes:
    """One packet: the header with `size` set when there is a payload."""
    if payload:
        header = dict(header, size=len(payload))
    data = json.dumps(header, allow_nan=False, separators=(",", ":")).encode("utf8")
    if len(data) > MAX_HEADER:
        raise ProtocolError(f"engine packet header of {len(data)} bytes exceeds {MAX_HEADER}")
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError(f"engine packet payload of {len(payload)} bytes exceeds {MAX_PAYLOAD}")
    return struct.pack("!I", len(data)) + data + bytes(payload)


def write_packet(stream, header: dict, payload: bytes = b"") -> None:
    stream.write(encode_packet(header, payload))
    stream.flush()


def _read_exact(stream, size: int, what: str) -> bytes:
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            raise ProtocolError(f"truncated engine packet: the stream ended {len(data)} of {size} bytes into its {what}")
        data += chunk
    return bytes(data)


def read_packet(stream, *, max_header: int = MAX_HEADER, max_payload: int = MAX_PAYLOAD):
    """The next packet as (header, payload), or None at the stream's end between packets. A packet over the bounds
    is refused from its declared size, before any of it is read."""
    first = stream.read(4)
    if not first:
        return None
    if len(first) < 4:
        first += _read_exact(stream, 4 - len(first), "length")
    size = struct.unpack("!I", first)[0]
    if size > max_header:
        raise ProtocolError(f"engine packet header of {size} bytes exceeds {max_header}")
    try:
        header = json.loads(_read_exact(stream, size, "header").decode("utf8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"malformed engine packet header: {exc}") from exc
    if not isinstance(header, dict):
        raise ProtocolError("malformed engine packet header: not an object")
    payload = b""
    if "size" in header:
        length = header["size"]
        if type(length) is not int or length < 0:
            raise ProtocolError("malformed engine packet header: invalid payload size")
        if length > max_payload:
            raise ProtocolError(f"engine packet payload of {length} bytes exceeds {max_payload}")
        payload = _read_exact(stream, length, "payload")
    return header, payload


# --- the child -------------------------------------------------------------------------------------------------

class WindowGone(Exception):
    """End of stdin, or `quit`, while a match runs: the process ends."""


class Cancelled(Exception):
    """The window's `cancel`: the match ends and the process waits for the next."""


_EOF = object()


class Commands:
    """[designed: T159] The match's view of the pipe, the interface BenchPolicy reads: the latest acknowledged
    sample, the Enter presses counted, the answers in order, and `wait(ready)`."""

    def __init__(self, inbox: queue.Queue):
        self.inbox = inbox
        self.ack = -1
        self.pauses = 0
        self.answers = []

    def _apply(self, item):
        if item is _EOF:
            raise WindowGone
        header, _payload = item
        op = header.get("op")
        if op == "cancel":
            raise Cancelled
        if op == "quit":
            raise WindowGone
        if op == "ack" and type(header.get("sample")) is int:
            self.ack = max(self.ack, header["sample"])
        elif op == "pause":
            self.pauses += 1
        elif op == "answer" and type(header.get("decision")) is int:
            from goal2.game.watched_jobs import _changes, _choice, _pairs
            if "taker" in header or "shootout_order" in header:
                # [designed: T167, #541] the answer to a player prompt (watched_match.PROMPT_CONTEXTS)
                self.answers.append((header["decision"], _choice(header)))
            elif header.get("changes"):
                # [designed: T180] the bench's pairs with its positions, marks and own tactics, in one answer
                self.answers.append((header["decision"], dict(_changes(header["changes"]),
                                                              substitutions=_pairs(header.get("substitutions", [])))))
            else:
                self.answers.append((header["decision"], _pairs(header.get("substitutions", []))))
        else:
            raise ValueError(f"invalid engine request during a match: {op!r}")

    def poll(self):
        """Apply every command already received, without waiting."""
        while True:
            try:
                item = self.inbox.get_nowait()
            except queue.Empty:
                return
            self._apply(item)

    def wait(self, ready):
        """Read until `ready()`; the commands are read at least once."""
        self.poll()
        while not ready():
            self._apply(self.inbox.get())


class BenchPolicy:
    """[designed: T102; T159] The window's answers, pauses and acknowledgements, read from the pipe (Commands). A
    decision is announced as `decision` before the wait. [designed: T161] The deleted file worker's BenchPolicy, moved
    here with T159's PipeBench folded in."""

    def __init__(self, commands, send):
        self.commands = commands
        self.send = send
        self.asked = 0
        self.paused = 0

    def decide(self, event):
        number = self.asked
        self.send("decision", {"decision": number, "event": _event_value(event)})
        self.asked += 1
        self.commands.wait(lambda: bool(self.commands.answers))
        decision, pairs = self.commands.answers.pop(0)
        if decision != number:
            raise ValueError("watched answer is for another decision")
        return pairs

    def pace(self, sequence):
        """Send sample `sequence` only within LEAD of the acknowledged one. The wait reads the commands at least
        once, so an Enter read here is applied after this sample."""
        from goal2.game.watched_jobs import LEAD
        self.commands.wait(lambda: sequence <= self.commands.ack + LEAD)

    def pause_now(self, sequence):
        # [designed: T102] Only Enters read before this sample was sent count, so a pause lands after a definite
        # sample (the one after the read).
        if self.commands.pauses > self.paused:
            self.paused = self.commands.pauses
            return True
        return False

    def pause_dropped(self, sequence):
        # [designed: #316] The window clears its pending pause, so the player's next Enter is sent.
        self.send("pause_dropped", sequence)

    def answered(self, report):
        self.send("answered", report)


def _event_value(event):
    """An Event as plain data; `send` encodes it (its tuples kept, session_save._json_value)."""
    from dataclasses import asdict
    return asdict(event)


class Server:
    def __init__(self, stdin, out):
        self.out = out
        self.inbox: queue.Queue = queue.Queue()
        self.game = None
        self.lock = threading.Lock()   # the reader thread reports a malformed request too
        self.reader = threading.Thread(target=self._read, args=(stdin,), name="goal2-engine-requests", daemon=True)

    def _read(self, stdin):
        try:
            while True:
                packet = read_packet(stdin)
                if packet is None:
                    break
                self.inbox.put(packet)
        except ProtocolError as exc:
            # The stream cannot be resynchronised: say why, then behave as at its end.
            self.send("error", f"{type(exc).__name__}: {exc}")
        except OSError as exc:
            print(f"engine_server: stdin failed: {exc}", file=sys.stderr, flush=True)
        self.inbox.put(_EOF)

    def send(self, kind, value=None, payload=b""):
        from goal2.game.session_save import _json_value
        packet = encode_packet({"kind": kind, "value": _json_value(value)}, payload)
        with self.lock:
            self.out.write(packet)
            self.out.flush()

    def serve(self) -> int:
        import platform
        self.reader.start()
        self.send("ready", {"implementation": platform.python_implementation(),
                            "version": list(sys.version_info[:2]), "pid": os.getpid()})
        while True:
            item = self.inbox.get()
            if item is _EOF:
                return 0
            header, payload = item
            op = header.get("op")
            try:
                if op == "open":
                    self._open(payload)
                    self.send("opened")
                elif op == "match":
                    self._match(header)
                elif op == "quit":
                    return 0
                elif op in ("ack", "pause", "answer", "cancel"):
                    # [designed: T159] A command sent before the window read the end of the match it was for.
                    continue
                else:
                    self.send("error", f"unknown engine request: {op!r}")
            except WindowGone:
                return 0
            except Exception as exc:  # noqa: BLE001 - reported to the window; the process stays up
                import traceback
                traceback.print_exc(file=sys.stderr)
                self.send("error", f"{type(exc).__name__}: {exc}")

    def _open(self, payload):
        from goal2.game.session_save import decode
        self.game = decode(payload)

    def _match(self, header):
        import copy
        from goal2.engine.original_match import Fixture
        from goal2.game.watched_match import _drive_match
        if self.game is None:
            raise ValueError("no game is open")
        kind, frames, bench = header.get("kind"), header.get("frames", False), header.get("bench", False)
        prompts = header.get("prompts", False)
        live_players = header.get("live_players",False)
        options = header.get("options") or {}
        if (kind not in KINDS or type(frames) is not bool or type(bench) is not bool or (bench and not frames)
                or type(prompts) is not bool or (prompts and not bench) or type(live_players) is not bool):
            raise ValueError("invalid engine match request")
        if not isinstance(options, dict) or set(options) - set(OPTIONS):
            raise ValueError("invalid engine match options")
        fixture = Fixture(**header["fixture"])
        # [designed: T159] Each match plays the game as opened, a fresh copy, as the file workers loaded it afresh.
        state, original = copy.deepcopy(self.game[0]), self.game[1]
        commands = Commands(self.inbox)
        policy = BenchPolicy(commands, self.send) if bench else None

        def observe(event):
            commands.poll()
            self.send("event", _event_value(event))

        def pitch(frame):
            commands.poll()
            if policy is not None:
                policy.pace(frame["sequence"])
            self.send("frame", frame)
        try:
            if kind == "competitive":
                from goal2.game.competitive_match import prepare_competitive
                image = prepare_competitive(state, original, fixture)
                extra = {"substitutions": (5, 5)}
            else:
                from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS, prepare_watched
                image = prepare_watched(state, original, fixture)
                # [designed: owner BM-7, #73; T180] a watched friendly plays with the rebuild's unlimited budget
                extra = {"substitutions": FRIENDLY_SUBSTITUTIONS} if fixture.kind == 1 else {}
            commands.poll()
            outcome = _drive_match(state, image, fixture, _observe=observe, _observe_pitch=pitch if frames else None,
                                   policy=policy, prompts=prompts, **extra, **options,
                                   **({'live_players':True} if live_players else {}))
        except Cancelled:
            self.send("cancelled")
            return
        self.send("complete", {"result": outcome.result, "events": [_event_value(e) for e in outcome.events],
                               "seeds": list(outcome.seeds), "engine_year": outcome.engine_year},
                  bytes(outcome.memory))
        # [designed: T199, #627] The private transaction ends after the completed result.
        self.send("settled")


def main() -> int:
    # [designed: T159] The protocol's stream is a private copy of fd 1; fd 1 and sys.stdout become stderr.
    out = os.fdopen(os.dup(sys.stdout.fileno()), "wb")
    if sys.platform == "win32":
        # [designed: T159, the task's Windows hazard] binary on both ends: no newline translation
        import msvcrt
        msvcrt.setmode(out.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    sys.stdout.flush()
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    code = Server(sys.stdin.buffer, out).serve()
    # [designed: T160] Leave without the interpreter's shutdown: the request reader is a daemon thread that may be
    # blocked in a read of stdin (after `quit`), and CPython's shutdown then aborts on that stream's lock ("could not
    # acquire lock for <_io.BufferedReader name='<stdin>'>", exit -6). Every reply was flushed when it was sent.
    for stream in (out, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
