"""[designed: T158] A minimal prototype of #516's option 3: one long-lived engine process over one pipe.

Started once (under PyPy, as the match workers are), it answers requests on stdin and replies on stdout, both
length-prefixed (4 bytes, big-endian) JSON packets. It plays real matches through goal2's own driver
(goal2.game.watched_match._drive_match on the sealed port), so its timings are a real engine's.

Requests:
    {"op": "open", "size": N} + N bytes      the encoded game (goal2.game.session_save.encode)
    {"op": "match", "seed": S, "max_events": E}
    {"op": "ping", "n": K}                   answered at once with pong K (the clock-free round trip)
    {"op": "quit"}
Replies: {"kind": "ready" | "opened" | "event" | "stopped" | "complete" | "pong" | "error", "t": time.time(), ...}

End of stdin (the window gone) ends the process: the parent-liveness signal file journals lack (#417).
A throwaway prototype; nothing of goal2 uses it.
"""
import json
import struct
import sys
import time
from dataclasses import asdict
from pathlib import Path

T0 = time.time()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

IN = sys.stdin.buffer
OUT = sys.stdout.buffer


class Stop(Exception):
    pass


def send(**packet):
    packet["t"] = time.time()
    data = json.dumps(packet, separators=(",", ":")).encode()
    OUT.write(struct.pack("!I", len(data)) + data)
    OUT.flush()


def read_exact(n):
    data = b""
    while len(data) < n:
        chunk = IN.read(n - len(data))
        if not chunk:
            raise EOFError
        data += chunk
    return data


def main():
    from goal2.game.session_save import decode, _json_value
    from goal2.game.watched_match import prepare_watched, _drive_match
    from goal2.engine.original_match import Fixture
    send(kind="ready", started=T0, clock=time.get_clock_info("time").resolution, interpreter=common.interpreter())
    state = original = None
    while True:
        try:
            request = json.loads(read_exact(struct.unpack("!I", read_exact(4))[0]))
        except EOFError:
            return
        op = request["op"]
        try:
            if op == "open":
                state, original = decode(read_exact(request["size"]))
                state.captain = 0
                send(kind="opened")
            elif op == "ping":
                send(kind="pong", n=request["n"])
            elif op == "quit":
                return
            elif op == "match":
                count = 0

                def observe(event):
                    nonlocal count
                    send(kind="event", seq=count, event=_json_value(asdict(event)))
                    count += 1
                    if count >= request["max_events"]:
                        raise Stop
                fixture = Fixture(7, 19, 21)
                try:
                    _drive_match(state, prepare_watched(state, original, fixture), fixture,
                                 reference_seed=request["seed"], delay_byte=0, _observe=observe)
                    send(kind="complete", events=count)
                except Stop:
                    send(kind="stopped", events=count)
        except Exception as exc:  # the prototype reports, the parent decides
            send(kind="error", error=f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
