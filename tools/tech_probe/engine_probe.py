"""[designed: T158] The engine boundary's measurements (T158 point 3, T154's scope), run by the UI's CPython.

    python engine_probe.py speed   --cache DIR --pypy P [--rust-python C] --seeds 257,1 --rounds 3 --out F
    python engine_probe.py channel --cache DIR --pypy P --mode file|pipe|thread --runs 5 [--events 300] --out F

speed: whole matches, each in a fresh process (match_child.py), in interleaved rounds of three arms: the plain
port under PyPy (today's worker), the plain port under CPython, and goal2rust's hybrid under CPython. Records
each match's CPU and wall time and its outcome digests, so equality between the arms is checked per seed.

channel: one way of carrying a watched match's events from the engine to the window, measured the same way for
  file    today's channel: goal2.game.watched_jobs.WatchedJobs and the real watched worker under PyPy, polled
          every 30 ms as the window's QTimer does (goal2/desktop/window.py:34), the worker stamped by
          file_child.py; the round trip through the same command and event journals (file_child.py echo);
  pipe    option 3's prototype: one PyPy process (pipe_child.py) that stays up, fed over stdin/stdout, read by a
          thread; a cold match (spawn, open, match) and a warm one (match on the running process);
  thread  option 4: goal2rust's hybrid inside this CPython process, on a thread, events through a queue.
Each run records: process start (to the child's import of the engine), time to the first event, the one-way
latency of the first --events events (child's time.time() to the moment the window's tick or poll takes it;
for the pipe also to the reader thread's receipt, `transport_ms`), the clock-free round trip
(20 echoes), and how late a 16 ms UI tick ran while the events streamed (the window's responsiveness).

Every record carries the load (common.load). Results go to measurements/T158/ (summarize.py makes the tables).
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import random
import statistics
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

TICK = 0.016
POLL = 0.030


def stats(values, scale=1000.0):
    if not values:
        return None
    v = sorted(x * scale for x in values)
    return {"n": len(v), "p50": round(statistics.median(v), 3), "p95": round(v[min(len(v) - 1, int(len(v) * .95))], 3),
            "max": round(v[-1], 3), "mean": round(statistics.fmean(v), 3)}


# ---------------------------------------------------------------- speed

def speed(args):
    out = common.Results(args.out, "engine-speed")
    arms = {"pypy": ([args.pypy], False), "cpython": ([args.rust_python], False),
            "hybrid": ([args.rust_python], True)}
    child = str(common.PROBE / "match_child.py")
    for rnd in range(args.first_round, args.first_round + args.rounds):
        for seed in [int(s) for s in args.seeds.split(",")]:
            for arm in args.arms.split(","):
                command, rust = arms[arm]
                load = common.load()
                started = time.perf_counter()
                r = subprocess.run(command + [child, "--cache", args.cache, "--seed", str(seed)] + (["--rust"] if rust else []),
                                   capture_output=True, text=True, cwd=common.ROOT)
                record = {"round": rnd, "arm": arm, "seed": seed, "load": load,
                          "process_wall_s": round(time.perf_counter() - started, 3)}
                if r.returncode:
                    record["error"] = f"exit {r.returncode}: " + r.stderr[-2000:] + r.stdout[-500:]
                else:
                    record.update(json.loads(r.stdout.strip().splitlines()[-1]))
                out.add(record)
                print(arm, seed, record.get("match_cpu_s"), record.get("error", "")[-200:], flush=True)


# ---------------------------------------------------------------- channel

class Owner:
    def __init__(self, state, template):
        self.state = state
        self.template_bytes = template

    def view(self, state):
        return state.last_match


def ui_loop(receive, until, deadline=600):
    """The window's side: a 16 ms tick that takes what has arrived. Returns the ticks' lateness."""
    late = []
    last = time.perf_counter()
    end = time.time() + deadline
    while not until():
        if time.time() > end:
            raise TimeoutError("no end in time")
        time.sleep(TICK)
        now = time.perf_counter()
        late.append(max(0.0, now - last - TICK))
        last = now
        receive()
    return late


def file_run(args, state, raw, fixture):
    from goal2.game.watched_jobs import WatchedJobs
    stamps_file = Path(tempfile.mkdtemp(prefix="t158-stamps-")) / "stamps"
    os.environ["T158_STAMPS"] = str(stamps_file)
    jobs = WatchedJobs(Owner(state, raw), command=[args.pypy, str(common.PROBE / "file_child.py")])
    received = []
    polls = []
    last_poll = [0.0]
    asked = time.time()
    token = jobs.start(fixture, reference_seed=args.seed, delay_byte=0)

    def receive():
        if time.perf_counter() - last_poll[0] < POLL - 0.001:
            return
        last_poll[0] = time.perf_counter()
        p0 = time.perf_counter()
        events = jobs.poll(token)
        polls.append(time.perf_counter() - p0)
        now = time.time()
        received.extend(now for _ in events)
    try:
        late = ui_loop(receive, lambda: len(received) >= args.events)
    finally:
        jobs.cancel_and_reap(token) if jobs.busy else None
        jobs.close()
    lines = stamps_file.read_text().splitlines()
    head = json.loads(lines[0])
    sent = {}
    for line in lines[1:]:
        seq, kind, t = line.split()
        if kind == "event":
            sent[len(sent)] = float(t)
    latency = [received[i] - sent[i] for i in range(min(len(received), len(sent)))]
    return {"start_s": round(head["ready"] - asked, 4), "interpreter_start_s": round(head["started"] - asked, 4),
            "first_event_s": round(received[0] - asked, 4), "latency_ms": stats(latency),
            "poll_ms": stats(polls), "ui_late_ms": stats(late), "child_clock_resolution": head["clock"],
            "rtt_ms": stats(file_rtt(args))}


def file_rtt(args, echoes=20):
    """The command journal to the child and an event back, as the bench's Enter in play travels today."""
    from goal2.game.watched_jobs import READ_BUDGET
    folder = Path(tempfile.mkdtemp(prefix="t158-echo-"))
    commands = (folder / "commands").open("wb")
    events = (folder / "events").open("w+b")
    env = dict(os.environ, T158_ECHOES=str(echoes))
    child = subprocess.Popen([args.pypy, str(common.PROBE / "file_child.py"), "echo", str(folder)], env=env,
                             cwd=common.ROOT, stdin=subprocess.DEVNULL)
    buffer = bytearray()

    def poll():
        buffer.extend(events.read(READ_BUDGET))
        got = 0
        while len(buffer) >= 4:
            size = struct.unpack("!I", buffer[:4])[0]
            if len(buffer) < size + 4:
                break
            del buffer[:4 + size]
            got += 1
        return got
    rtts = []
    try:
        while not poll():                    # "ready"
            time.sleep(POLL)
        for n in range(echoes):
            time.sleep(random.uniform(0, POLL))
            packet = json.dumps(["t", n, "pause", None]).encode()
            t0 = time.perf_counter()
            commands.write(struct.pack("!I", len(packet)) + packet)
            commands.flush()
            next_poll = t0
            while True:
                if poll():
                    rtts.append(time.perf_counter() - t0)
                    break
                next_poll += POLL
                time.sleep(max(0.0, next_poll - time.perf_counter()))
        packet = json.dumps(["t", echoes, "pause", None]).encode()
        commands.write(struct.pack("!I", len(packet)) + packet)
        commands.flush()
        child.wait(30)
    finally:
        if child.poll() is None:
            child.kill()
        commands.close()
        events.close()
    return rtts


class Pipe:
    def __init__(self, pypy):
        self.asked = time.time()
        self.process = subprocess.Popen([pypy, str(common.PROBE / "pipe_child.py")], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, cwd=common.ROOT)
        self.inbox = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        stream = self.process.stdout
        while True:
            head = stream.read(4)
            if len(head) < 4:
                self.inbox.put(None)
                return
            packet = json.loads(stream.read(struct.unpack("!I", head)[0]))
            packet["received"] = time.time()
            packet["received_perf"] = time.perf_counter()
            self.inbox.put(packet)

    def send(self, payload=b"", **request):
        data = json.dumps(request).encode()
        self.process.stdin.write(struct.pack("!I", len(data)) + data + payload)
        self.process.stdin.flush()

    def wait(self, kind, timeout=120):
        while True:
            packet = self.inbox.get(timeout=timeout)
            if packet is None:
                raise RuntimeError("the engine process ended")
            if packet["kind"] == "error":
                raise RuntimeError(packet["error"])
            if packet["kind"] == kind:
                return packet

    def close(self):
        try:
            self.send(op="quit")
            self.process.wait(10)
        finally:
            if self.process.poll() is None:
                self.process.kill()


def pipe_match(pipe, args):
    """One match over the running process: time to the first event, latencies, UI ticks."""
    latency, transport, first = [], [], []
    asked = time.time()
    pipe.send(op="match", seed=args.seed, max_events=args.events)
    done = []

    def receive():
        while True:
            try:
                packet = pipe.inbox.get_nowait()
            except queue.Empty:
                return
            if packet is None or packet["kind"] in ("stopped", "complete", "error"):
                done.append(packet)
                return
            if packet["kind"] == "event":
                if not first:
                    first.append(packet["received"] - asked)
                latency.append(time.time() - packet["t"])
                transport.append(packet["received"] - packet["t"])
    late = ui_loop(receive, lambda: bool(done))
    if done[0] is None or done[0]["kind"] == "error":
        raise RuntimeError(f"pipe match failed: {done[0]}")
    return {"first_event_s": round(first[0], 4), "latency_ms": stats(latency), "transport_ms": stats(transport),
            "ui_late_ms": stats(late)}


def pipe_run(args, state, raw, fixture):
    from goal2.game.session_save import encode
    pipe = Pipe(args.pypy)
    try:
        ready = pipe.wait("ready")
        start = ready["received"] - pipe.asked
        payload = encode(state, raw)
        t0 = time.time()
        pipe.send(payload, op="open", size=len(payload))
        pipe.wait("opened")
        opened = time.time() - t0
        cold = pipe_match(pipe, args)
        warm = pipe_match(pipe, args)
        rtts = []
        for n in range(20):
            time.sleep(random.uniform(0, POLL))
            t0 = time.perf_counter()
            pipe.send(op="ping", n=n)
            rtts.append(pipe.wait("pong")["received_perf"] - t0)
    finally:
        pipe.close()
    return {"start_s": round(start, 4), "open_s": round(opened, 4), "open_bytes": len(payload),
            "first_event_s": round(start + opened + cold["first_event_s"], 4),
            "cold_match_first_event_s": cold["first_event_s"], "warm_first_event_s": warm["first_event_s"],
            "latency_ms": warm["latency_ms"], "transport_ms": warm["transport_ms"], "cold_latency_ms": cold["latency_ms"],
            "ui_late_ms": warm["ui_late_ms"], "child_clock_resolution": ready["clock"], "rtt_ms": stats(rtts)}


class Stop(Exception):
    pass


def thread_match(args, state, raw, fixture):
    from goal2.game.watched_match import prepare_watched, _drive_match
    from dataclasses import asdict
    inbox = queue.Queue()

    def play():
        count = [0]

        def observe(event):
            inbox.put((time.time(), asdict(event)))
            count[0] += 1
            if count[0] >= args.events:
                raise Stop
        try:
            _drive_match(state, prepare_watched(state, raw, fixture), fixture, reference_seed=args.seed,
                         delay_byte=0, _observe=observe)
        except Stop:
            pass
        inbox.put(None)
    asked = time.time()
    worker = threading.Thread(target=play, daemon=True)
    worker.start()
    latency, first, done = [], [], []

    def receive():
        while True:
            try:
                item = inbox.get_nowait()
            except queue.Empty:
                return
            if item is None:
                done.append(True)
                return
            now = time.time()
            if not first:
                first.append(now - asked)
            latency.append(now - item[0])
    late = ui_loop(receive, lambda: bool(done))
    worker.join()
    return {"first_event_s": round(first[0], 4), "latency_ms": stats(latency), "ui_late_ms": stats(late)}


def thread_run(args, state, raw, fixture):
    t0 = time.time()
    if args.rust:
        common.install_rust()
    installed = time.time() - t0
    cold = thread_match(args, state, raw, fixture)
    warm = thread_match(args, state, raw, fixture)
    inbox, outbox = queue.Queue(), queue.Queue()

    def echo():
        while (n := inbox.get()) is not None:
            outbox.put(n)
    helper = threading.Thread(target=echo, daemon=True)
    helper.start()
    rtts = []
    for n in range(20):
        t1 = time.perf_counter()
        inbox.put(n)
        outbox.get()
        rtts.append(time.perf_counter() - t1)
    inbox.put(None)
    return {"start_s": round(installed, 4), "first_event_s": cold["first_event_s"],
            "warm_first_event_s": warm["first_event_s"], "latency_ms": warm["latency_ms"],
            "cold_latency_ms": cold["latency_ms"], "ui_late_ms": warm["ui_late_ms"], "rtt_ms": stats(rtts),
            "rust": args.rust}


def channel(args):
    out = common.Results(args.out, "engine-channel")
    state, raw, fixture = common.reference(args.cache)
    run = {"file": file_run, "pipe": pipe_run, "thread": thread_run}[args.mode]
    for n in range(1, args.runs + 1):
        load = common.load()
        record = {"mode": args.mode + ("-hybrid" if args.mode == "thread" and args.rust else ""), "run": n,
                  "load": load, "events": args.events, "ui": common.interpreter(), "seed": args.seed}
        try:
            record.update(run(args, state, raw, fixture))
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"
        out.add(record)
        print(json.dumps({k: record.get(k) for k in ("mode", "run", "start_s", "first_event_s", "error")}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("speed")
    s.add_argument("--cache", required=True)
    s.add_argument("--pypy", required=True)
    s.add_argument("--rust-python", default=sys.executable)
    s.add_argument("--arms", default="pypy,cpython,hybrid")
    s.add_argument("--seeds", default="257")
    s.add_argument("--rounds", type=int, default=3)
    s.add_argument("--first-round", type=int, default=1, help="the number of the first round (a later rerun)")
    s.add_argument("--out", required=True)
    c = sub.add_parser("channel")
    c.add_argument("--cache", required=True)
    c.add_argument("--pypy", required=True)
    c.add_argument("--mode", choices=("file", "pipe", "thread"), required=True)
    c.add_argument("--rust", action="store_true", help="thread mode: goal2rust's hybrid (else the plain port)")
    c.add_argument("--runs", type=int, default=5)
    c.add_argument("--events", type=int, default=300)
    c.add_argument("--seed", type=int, default=257)
    c.add_argument("--out", required=True)
    args = parser.parse_args()
    {"speed": speed, "channel": channel}[args.command](args)


if __name__ == "__main__":
    main()
