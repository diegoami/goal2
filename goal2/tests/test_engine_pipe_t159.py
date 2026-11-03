"""[designed: owner, 2026-11-03, #527 D3; T159] The engine process and its pipe protocol (goal2.game.engine_server,
goal2.game.engine_process; docs/engine-process.md).

The claim it protects: a match played over the pipe is the same match the driver plays. Its events, pitch samples,
bench decisions and outcome equal `_drive_match` on the same game, fixture and options, played through
goal2.tests.pypy_engine (#500: no match in this process). The matches run side by side in setUpClass: three
engine processes (the watched game's conversation, the competitive game's, the window's death) and their references.
The framing and the bounds are checked on byte streams and on stand-in children that play no match.
"""
from concurrent.futures import ThreadPoolExecutor
import copy
import io
import os
import queue
import struct
import sys
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from goal2.engine.original_match import Fixture
from goal2.game import engine_server
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_server import ProtocolError, encode_packet, read_packet
from goal2.tests import pypy_engine, requires

ROOT = Path(__file__).resolve().parents[2]
WAIT = 600                                   # seconds for any one reply while a match plays
FIXTURE = Fixture(7, 19, 21)                 # the reference friendly (test_pypy_worker_t152)
OPTIONS = dict(reference_seed=257, delay_byte=0, record_draws=True)
# [designed: T159] The pause case: the window holds its acknowledgements so the engine waits to write sample
# PAUSE_FRAME + 1, then presses Enter; the original takes it after that sample (as test_watched_bench_t102).
PAUSE_FRAME = 300


class Replies:
    """An engine's replies, in order, as its callback delivers them."""

    def __init__(self):
        self.queue = queue.Queue()
        self.log = []

    def __call__(self, kind, value):
        self.queue.put((kind, value))

    def next(self, timeout=WAIT):
        item = self.queue.get(timeout=timeout)
        self.log.append(item)
        return item

    def until(self, kind, timeout=WAIT):
        """The replies up to and including the first `kind`."""
        seen = []
        while True:
            item = self.next(timeout)
            seen.append(item)
            if item[0] == kind:
                return seen
            if item[0] in ("error", "death"):
                raise AssertionError(f"engine replied {item} while waiting for {kind}")


# --- the reference side, in a pypy_engine child ------------------------------------------------------------------

class Frames:
    """`drive`'s pitch observer: every sample, in order."""

    def __init__(self):
        self.frames = []

    def __call__(self, frame):
        self.frames.append(frame)


def first_pair(data):
    """The test's substitution: the second outfield starter off, the first outfield bench player on."""
    positions = dict(map(tuple, data["positions"]))
    starters = [w for w in data["eleven"] if positions[w] != 0]
    bench = [w for w in data["bench"] if positions[w] != 0]
    return [[starters[1], bench[0]]]


class Choices:
    """The choices the bench case makes, as a `_drive_match` policy: a substitution at the first decision, play on
    at the others, Enter after sample PAUSE_FRAME + 1. It records what the engine says back."""

    def __init__(self):
        self.decisions, self.reports, self.dropped = [], [], []

    def decide(self, event):
        self.decisions.append(event)
        return first_pair(event.data) if len(self.decisions) == 1 else []

    def pause_now(self, sequence):
        return sequence == PAUSE_FRAME + 1

    def pause_dropped(self, sequence):
        self.dropped.append(sequence)

    def answered(self, report):
        self.reports.append(report)


def reference(state, raw, fixture, **kwargs):
    """`_drive_match` through pypy_engine.drive, with its arguments as the call left them."""
    return pypy_engine.start("goal2.tests.pypy_engine:echo", "goal2.tests.pypy_engine:drive", state, raw, fixture,
                             **kwargs)


# --- the conversations ---------------------------------------------------------------------------------------------

def play(engine, replies, kind, fixture, *, frames=False, bench=False, on_frame=None, on_decision=None):
    """One match over the pipe to its end: its events, samples, decisions, reports, dropped pauses and outcome."""
    seen = {"events": [], "frames": [], "decisions": [], "answered": [], "dropped": [], "pid": engine.pid}
    engine.match(kind, fixture, options=OPTIONS, frames=frames, bench=bench)
    while True:
        what, value = replies.next()
        if what == "event":
            seen["events"].append(value)
        elif what == "frame":
            seen["frames"].append(value)
            if on_frame is not None:
                on_frame(value)
        elif what == "decision":
            seen["decisions"].append(value)
            on_decision(value)
        elif what == "answered":
            seen["answered"].append(value)
        elif what == "pause_dropped":
            seen["dropped"].append(value)
        elif what == "complete":
            seen["outcome"] = value
            return seen
        elif what not in ("ready", "opened"):
            raise AssertionError(f"engine replied {what}: {value}")


def watched_conversation(state, raw):
    """One engine, one `open`: a watched match with its samples, a match cancelled at its first event, then the
    bench's match."""
    replies = Replies()
    engine = EngineProcess(replies)
    out = {"replies": replies}
    try:
        engine.open(state, raw)
        out["ready"] = replies.until("ready")[-1][1]
        replies.until("opened")
        out["frames"] = play(engine, replies, "watched", FIXTURE, frames=True)

        engine.match("watched", FIXTURE, options=OPTIONS)
        out["cancel_pid"] = engine.pid
        first = replies.until("event")
        engine.cancel()
        out["after_cancel"] = [kind for kind, _ in first[-1:] + replies.until("cancelled")]
        out["busy_after_cancel"] = engine.busy

        acked = [-1]
        paused = [False]

        def on_frame(frame):
            from goal2.game.watched_jobs import LEAD
            sequence = frame["sequence"]
            if not paused[0] and sequence == PAUSE_FRAME:
                # The engine now waits to write sample PAUSE_FRAME + 1 for an acknowledgement: Enter, then show it.
                engine.pause()
                paused[0] = True
            limit = sequence if paused[0] else min(sequence, PAUSE_FRAME - LEAD)
            if limit > acked[0]:
                engine.ack(limit)
                acked[0] = limit

        def on_decision(value):
            pairs = first_pair(value["event"].data) if value["decision"] == 0 else []
            engine.answer(value["decision"], pairs)
        out["bench"] = play(engine, replies, "watched", FIXTURE, frames=True, bench=True,
                            on_frame=on_frame, on_decision=on_decision)
        out["opens"] = engine.opens
        out["pid"] = engine.pid
    finally:
        engine.close()
    return out


def competitive_conversation(state, raw, fixture):
    """A competitive match killed at its first event, then played again: the next match starts a new process."""
    replies = Replies()
    engine = EngineProcess(replies)
    out = {}
    try:
        engine.open(state, raw)
        engine.match("competitive", fixture, options=OPTIONS)
        replies.until("event")
        out["killed_pid"] = engine.pid
        engine.process.kill()
        out["death"] = replies.until("death")
        try:
            out["after_death"] = [replies.next(timeout=2)]
        except queue.Empty:
            out["after_death"] = []
        out["pid_after_death"] = engine.pid
        out["match"] = play(engine, replies, "competitive", fixture)
        out["pid"] = engine.pid
    finally:
        engine.close()
    return out


def window_death_conversation(state, raw):
    """The bench's first decision waits for an answer; the window's end of the pipe closes."""
    replies = Replies()
    engine = EngineProcess(replies)
    out = {}
    try:
        engine.open(state, raw)
        engine.match("watched", FIXTURE, options=OPTIONS, frames=True, bench=True)
        while True:
            kind, value = replies.next()
            if kind == "frame":
                engine.ack(value["sequence"])
            elif kind == "decision":
                break
            elif kind in ("error", "death", "complete"):
                raise AssertionError(f"engine replied {kind} before a decision: {value}")
        process = engine.process
        start = time.monotonic()
        process.stdin.close()
        try:
            out["code"] = process.wait(timeout=30)
        except Exception:
            out["code"] = None
        out["seconds"] = time.monotonic() - start
        out["death"] = replies.until("death")[-1][1]
    finally:
        engine.close()
    return out


@requires.need(**requires.WATCHED)
class SameMatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.engine.original_match.assets import reference_image
        from goal2.game.state import from_savestate
        from goal2.tests.test_campaign_competitive_publication import campaign
        from goal2.tests.test_pypy_worker_t152 import pypy
        cls.pypy = pypy()
        raw = reference_image(ROOT / ".cache")
        state = from_savestate(raw)
        state.captain = 0                                  # as test_watched_adapter's state()
        cstate, craw, cfixture = campaign(42, 200)         # test_pypy_worker_t152's competitive match
        cls.state, cls.raw = copy.deepcopy(state), raw
        refs = {
            "frames": reference(state, raw, FIXTURE, observer=Frames(), **OPTIONS),
            "bench": reference(state, raw, FIXTURE, observer=Frames(), policy=Choices(), **OPTIONS),
            "competitive": reference(cstate, craw, cfixture, competitive=True, substitutions=(5, 5), **OPTIONS),
        }
        with ThreadPoolExecutor(3) as pool:
            runs = {"watched": pool.submit(watched_conversation, state, raw),
                    "competitive": pool.submit(competitive_conversation, cstate, craw, cfixture),
                    "window": pool.submit(window_death_conversation, state, raw)}
            cls.runs = {name: run.result() for name, run in runs.items()}
        cls.refs = {name: ref.result(timeout=WAIT) for name, ref in refs.items()}

    def same_match(self, seen, ref):
        (outcome, observer, _snapshot), _args, _kwargs = ref
        self.assertEqual(seen["events"], list(outcome.events))
        self.assertEqual(seen["outcome"], outcome)                 # result, memory, events, seeds, year
        if observer is not None:
            self.assertEqual(seen["frames"], observer.frames)
            self.assertEqual(len(seen["frames"]), outcome.result["ticks"])

    def test_a_watched_match_with_its_samples_is_the_driver_s_match(self):
        self.same_match(self.runs["watched"]["frames"], self.refs["frames"])

    def test_a_competitive_match_is_the_driver_s_match(self):
        self.same_match(self.runs["competitive"]["match"], self.refs["competitive"])

    def test_the_bench_asks_answers_and_pauses_as_the_driver_does(self):
        seen = self.runs["watched"]["bench"]
        self.same_match(seen, self.refs["bench"])
        choices = self.refs["bench"][2]["policy"]
        self.assertGreaterEqual(len(seen["decisions"]), 1)
        self.assertEqual([d["decision"] for d in seen["decisions"]], list(range(len(seen["decisions"]))))
        self.assertEqual([d["event"] for d in seen["decisions"]], choices.decisions)
        self.assertEqual(seen["answered"], choices.reports)
        self.assertEqual(seen["answered"][0]["asked"], first_pair(seen["decisions"][0]["event"].data))
        self.assertEqual(seen["dropped"], choices.dropped)
        # The Enter after sample PAUSE_FRAME + 1 was either taken (a pause decision) or reported dropped.
        pauses = [d for d in seen["decisions"] if d["event"].data["context"] == "pause"]
        self.assertTrue(pauses or seen["dropped"] == [PAUSE_FRAME + 1])

    def test_one_process_plays_the_matches_with_one_open(self):
        run = self.runs["watched"]
        self.assertEqual(run["opens"], 1)
        self.assertEqual({run["frames"]["pid"], run["cancel_pid"], run["bench"]["pid"], run["pid"]},
                         {run["ready"]["pid"]})

    def test_a_cancel_at_the_first_event_is_answered_and_the_process_stays(self):
        run = self.runs["watched"]
        self.assertEqual(run["after_cancel"][0], "event")
        self.assertEqual(run["after_cancel"][-1], "cancelled")
        self.assertNotIn("complete", run["after_cancel"])
        self.assertFalse(run["busy_after_cancel"])
        self.assertEqual(run["bench"]["pid"], run["cancel_pid"])     # the next match, on the same pid, completed
        self.assertIn("outcome", run["bench"])

    def test_an_engine_killed_mid_match_is_reported_once_and_replaced(self):
        run = self.runs["competitive"]
        deaths = [value for kind, value in run["death"] if kind == "death"]
        self.assertEqual(len(deaths), 1)
        self.assertEqual(run["after_death"], [])                     # reported once, nothing after
        self.assertEqual(deaths[0]["code"], 1 if sys.platform == "win32" else -9)
        self.assertIsNone(run["pid_after_death"])
        self.assertNotEqual(run["match"]["pid"], run["killed_pid"])
        self.assertIn("outcome", run["match"])

    def test_the_window_s_end_of_the_pipe_ends_an_engine_waiting_for_an_answer(self):
        run = self.runs["window"]
        self.assertEqual(run["code"], 0)
        self.assertLess(run["seconds"], 5)
        self.assertEqual(run["death"]["code"], 0)

    def test_the_engine_is_pypy_311_and_no_match_plays_here(self):
        ready = self.runs["watched"]["ready"]
        self.assertEqual((ready["implementation"], ready["version"]), ("PyPy", [3, 11]))
        self.assertTrue(pypy_engine.guarded())


# --- framing and bounds, without a match ---------------------------------------------------------------------------

class Framing(unittest.TestCase):
    def test_a_packet_round_trips_with_its_payload(self):
        payload = bytes(range(256)) * 1000 + b"\r\n\n\r\x1a"
        stream = io.BytesIO(encode_packet({"op": "open"}, payload) + encode_packet({"kind": "event", "value": [1]}))
        self.assertEqual(read_packet(stream), ({"op": "open", "size": len(payload)}, payload))
        self.assertEqual(read_packet(stream), ({"kind": "event", "value": [1]}, b""))
        self.assertIsNone(read_packet(stream))

    def test_an_oversized_packet_is_refused_before_it_is_read(self):
        for data, why in [(struct.pack("!I", engine_server.MAX_HEADER + 1), "header"),
                          (encode_packet({"op": "open", "size": engine_server.MAX_PAYLOAD + 1}), "payload")]:
            with self.subTest(why), self.assertRaisesRegex(ProtocolError, f"{why} of .* exceeds"):
                read_packet(io.BytesIO(data))
        with patch.object(engine_server, "MAX_PAYLOAD", 10), self.assertRaisesRegex(ProtocolError, "exceeds"):
            encode_packet({"op": "open"}, b"x" * 11)

    def test_a_truncated_or_malformed_packet_is_refused(self):
        whole = encode_packet({"op": "open"}, b"0123456789")
        for cut, part in [(2, "length"), (8, "header"), (len(whole) - 3, "payload")]:
            with self.subTest(part), self.assertRaisesRegex(ProtocolError, f"truncated .* its {part}"):
                read_packet(io.BytesIO(whole[:cut]))
        for body in (b"not json", b"[1, 2]", b'{"size": -1}'):
            with self.subTest(body=body), self.assertRaisesRegex(ProtocolError, "malformed"):
                read_packet(io.BytesIO(struct.pack("!I", len(body)) + body))


# A stand-in child: the protocol's framing, no engine. Its behaviour is chosen by argv[1].
STAND_IN = textwrap.dedent("""
    import os, struct, sys, time
    from goal2.game.engine_server import read_packet, encode_packet
    mode, out = sys.argv[1], sys.stdout.buffer
    def send(kind, value=None):
        out.write(encode_packet({"kind": kind, "value": value})); out.flush()
    send("ready", {"implementation": "stand-in", "version": [0, 0], "pid": os.getpid()})
    if mode == "oversized":
        out.write(struct.pack("!I", 2 ** 31)); out.flush(); time.sleep(60)
    if mode == "truncated":
        out.write(struct.pack("!I", 100) + b'{"kind"'); out.flush(); sys.exit(3)
    while True:
        packet = read_packet(sys.stdin.buffer)
        if packet is None:
            sys.exit(0)
        if packet[0]["op"] == "open":
            send("opened")
        elif packet[0]["op"] == "match":
            send("event", {"kind": "kickoff", "minute": 0, "score": {"__goal2_session_tuple__": [0, 0]}, "data": {}})
        elif packet[0]["op"] == "quit":
            sys.exit(0)
        # "deaf": a cancel is never answered
""")


class StandIn(unittest.TestCase):
    def engine(self, mode, **kwargs):
        replies = Replies()
        engine = EngineProcess(replies, command=[sys.executable, "-c", STAND_IN, mode], **kwargs)
        self.addCleanup(engine.close)
        engine.open_encoded(b"game")
        return engine, replies

    def test_an_oversized_or_truncated_reply_is_an_error_never_a_hang(self):
        for mode, text in [("oversized", "header of 2147483648 bytes exceeds"), ("truncated", "truncated")]:
            with self.subTest(mode):
                engine, replies = self.engine(mode)
                death = replies.until("death", timeout=30)[-1][1]
                self.assertIn(text, death["error"])
                self.assertIsNone(engine.pid)

    def test_a_cancel_left_unanswered_kills_the_process_and_the_next_match_starts_another(self):
        engine, replies = self.engine("deaf", cancel_deadline=0.5)
        engine.match("watched", FIXTURE)
        replies.until("event", timeout=30)
        first = engine.pid
        start = time.monotonic()
        self.assertTrue(engine.cancel())
        death = replies.until("death", timeout=30)
        self.assertGreaterEqual(time.monotonic() - start, 0.5)
        self.assertEqual([kind for kind, _ in death].count("death"), 1)
        self.assertNotIn("cancelled", [kind for kind, _ in death])
        engine.match("watched", FIXTURE)
        replies.until("event", timeout=30)
        self.assertNotIn(engine.pid, (None, first))
        self.assertEqual(engine.opens, 2)                       # the new process was sent the game first

    def test_one_match_at_a_time_and_close_is_not_a_death(self):
        engine, replies = self.engine("deaf")
        engine.match("watched", FIXTURE)
        with self.assertRaisesRegex(ValueError, "already playing"):
            engine.match("watched", FIXTURE)
        with self.assertRaisesRegex(ValueError, "playing a match"):
            engine.open_encoded(b"other")
        process = engine.process
        engine.close()
        self.assertIsNotNone(process.poll())
        time.sleep(0.5)
        self.assertNotIn("death", [kind for kind, _ in list(replies.queue.queue)])
        with self.assertRaisesRegex(ValueError, "closed"):
            engine.match("watched", FIXTURE)


class TheChild(unittest.TestCase):
    """The real child under engine_python(), with stray output during a request (its `open` patched to print)."""

    @classmethod
    def setUpClass(cls):
        from goal2.tests.test_pypy_worker_t152 import pypy
        cls.pypy = pypy()

    def test_stray_output_goes_to_stderr_and_the_protocol_holds(self):
        script = textwrap.dedent("""
            import os, sys, warnings
            from goal2.game import engine_server
            def noisy(self, payload):
                print("stray print"); os.write(1, b"stray bytes on fd 1\\n"); warnings.warn("stray warning")
                print("stray diagnostic", file=sys.stderr)
                self.game = None
            engine_server.Server._open = noisy
            sys.exit(engine_server.main())
        """)
        replies = Replies()
        engine = EngineProcess(replies, command=[self.pypy, "-c", script])
        self.addCleanup(engine.close)
        engine.open_encoded(b"not a game")
        ready = replies.until("ready", timeout=60)[-1][1]
        self.assertEqual((ready["implementation"], ready["version"]), ("PyPy", [3, 11]))
        replies.until("opened", timeout=60)
        engine.open_encoded(b"again")
        replies.until("opened", timeout=60)
        deadline = time.monotonic() + 30
        while engine.stderr.count("stray diagnostic") < 2 and time.monotonic() < deadline:
            time.sleep(0.05)
        for text in ("stray print", "stray bytes on fd 1", "stray warning", "stray diagnostic"):
            self.assertIn(text, engine.stderr)
        process = engine.process
        engine.close()
        self.assertEqual(process.returncode, 0)

    def test_the_child_alone_reports_pypy_311_and_ends_with_its_stdin(self):
        import subprocess
        process = subprocess.Popen([self.pypy, "-m", "goal2.game.engine_server"], cwd=ROOT, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        header, _ = read_packet(process.stdout)
        self.assertEqual(header["kind"], "ready")
        self.assertEqual((header["value"]["implementation"], header["value"]["version"]), ("PyPy", [3, 11]))
        self.assertEqual(header["value"]["pid"], process.pid)
        process.stdin.close()
        self.assertEqual(process.wait(timeout=5), 0)
        self.assertIsNone(read_packet(process.stdout))          # nothing else on its stdout
        process.stderr.close()
        process.stdout.close()


if __name__ == "__main__":
    unittest.main()
