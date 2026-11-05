"""S17 Pitch: your own friendly, watched in the main window, with the commentary always beside it.

[designed: owner, 2026-11-03, #526 decision 2; docs/design/ui-2026-11 S17 and its mockup s17-pitch.html; T166, #540]
The screen shows the engine's pitch samples and events, in order, paced by its own acknowledgements, and the match the
player watched is the match the engine published. It drives nothing: `MatchController` reads the bridge
(`goal2.game.watched_jobs.WatchedJobs`, docs/watched-jobs.md) on the window's thread and never waits on the engine.

- **Shows** [confirmed: T156-R1 steps 45-192, t156-045-kick-off.png; designed: s17-pitch.html]: the two sides, the
  score, the minute, the match's kind and the last two events above the pitch (goal2/ui/pitch.py), and the commentary
  beside it with the speed, the display and your side's colour.
- **Keys** [confirmed: E031 C39-C40, C08; T156-R1 steps 45, 267; the capture's bottom line]: **←→** the speed, the six
  `SPEEDS` of goal2/desktop/match_view.py; **↑↓** the display (the original's five marks); **Space** pauses and enlarges the
  commentary (Space/Enter resumes, owner #597); **R** quick result; **F9** sound; **Esc** / **Enter** the bench.
- **Pacing** [designed: T102, kept by the bridge]: a sample is acknowledged once the pitch has painted it, so the
  engine never runs more than `LEAD` samples ahead of what was drawn. **R** stops the pacing: every sample is
  acknowledged as it arrives and the screen says *HANG ON A TICK* where *R result* was, as the original does
  [confirmed: t156-267-quick-hang-on.png]; the pitch keeps the last sample it drew.
- **F9** [designed: T166]: goal2 has no sound; the key says so and does nothing else.
- **The stops** [designed: T167, #541; docs/design/ui-2026-11 §1, the match day]: the controller holds a stop once every
  sample before it is shown, and the match day (goal2/ui/match_day.py) shows it: half time and the menu before extra
  time on S20 then S15, a set-piece taker and the shoot-out order on S16, a substitution opportunity on S18 then
  S15, the pause Esc or Enter asks for on the bench S19 [designed: T180, #574]. Its answer is the one the engine
  receives, sent once through the bridge; no stop keeps a default answer.
- **The notices** [designed: T180; confirmed: t156-149-opponent-substitution.png]: the other side's substitution
  stops the display on S18 (the box over the pitch) until a key, as the original's notice, while the engine waits
  within its pacing; a quick result shows none. A bench answer's report (`WatchedJobs.reports`) that refuses a pair
  holds the display the same way and shows S19 with the engine's reason until a key; made and requested pairs are
  noted under the commentary.
- **Goals** [designed: T181, #575; confirmed: T156-R1 175–178]: after the goal's sample is painted, S18 asks for
  replay and saving. Playback redraws only recorded painted samples, with the live display held; automatic replay
  skips the first question. Quick result asks neither. The recording's bound and format are in `replays.py`.
- **Full time** publishes through the bridge, then the match day shows S20 and S15. Closing the window during a match
  cancels it through the bridge (`Window.closeEvent` calls `closing`): nothing is published.

The bridge is the match day's, one for the window's life (D3, #527): the controller starts its match on it and never
closes it [designed: T167, replacing T166's bridge per match].
"""
from __future__ import annotations

import copy
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QSizePolicy

from goal2.desktop.match_view import MAX_BACKLOG, PLAYBACK_RATE, Display
from goal2.desktop.pygame_viewer import MARKS
from goal2.ui import theme
from goal2.ui.kits import for_fixture
from goal2.ui.pitch import HOME, PitchWidget, side_colour
from goal2.ui.screen import Clickable, Screen, label
from goal2.ui.squad_card import box, colour

TICK_MS = 4            # the controller's poll; the fastest speed shows 240 samples a second [designed: T166]
COMMENTARY_ROWS = 15   # the lines the commentary box shows [designed: s17-pitch.png, the box's height]
HANG_ON = "HANG ON A TICK"   # [confirmed: t156-267-quick-hang-on.png, "HANG ON"; T156-R1 step 2's full words]
NO_SOUND = "F9: goal2 has no sound, so the key does nothing."
REQUESTED = "Bench requested: the bench opens when the original stops for it."
# The stops' words. [confirmed: E031 C40-C41, C44-C46b; goal2/desktop/match_view.py `Display.board`]
STOPS = {"half_time": "HALF TIME", "substitution": "SUBSTITUTION OPPORTUNITY", "pause": "PAUSE",
         "extra_time": "EXTRA TIME", "shootout_order": "PENALTY SHOOT-OUT"}
# Every decision the match day answers is held for its screens [designed: T167; T180]: S20/S15, S16, S18 and S19.
STOPS_SHOWN = ("half_time", "extra_time", "set_piece", "shootout_order", "substitution", "pause")
BENCH = ("half_time", "pause", "substitution")   # [confirmed: watched_match.BENCH_CONTEXTS]


def suggested_captain(state):
    """The original's best leader in the eleven, as T143 picks it (`best_leader`), on the Python route's records; None
    when nobody is available: the original then picks at kick-off [designed: T143]."""
    eleven = set(state.starting_eleven or state.managed_squad[:11])
    return best_leader(state.players, [w for w in state.managed_squad if w in eleven])


def best_leader(players, eleven):
    """T143's rule over player records: the eleven in squad order, the available players (positive signed energy,
    status elements 8, 6 and 3 clear), leadership the Pascal remainder of (rating - profile) / 8 as a word, halved
    below 21, the first of equals [derived: F029, archaeology 2ec0fff4; 0791:1F3C, 1771:3216; goal2/core/views.py
    `_captain_recommendation`, which reads the same records from the Core's memory and needs Unicorn to import]."""
    best_word, best = None, 0xFFFF
    for word in eleven[:11]:
        player = players[word]
        energy = player[0x0E] - 256 if player[0x0E] > 127 else player[0x0E]
        if energy <= 0 or any(player[0x10] >> (element - 1) & 1 for element in (8, 6, 3)):
            continue
        difference = player[3] - player[5]
        leadership = (difference - int(difference / 8) * 8) & 0xFFFF
        if player[1] < 21:
            leadership //= 2
        if (best - 0x10000 if best > 0x7FFF else best) < 0 or best < leadership:
            best_word, best = word, leadership
    return best_word


def engine_fixture(pending):
    """The engine's fixture of a scheduled one, as today's WatchedController makes it (its kind kept)."""
    from goal2.engine.original_match import Fixture
    return Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(":")[1]), pending.kind)


class MatchController:
    """One watched match over the match day's bridge: what the screen shows, and the acknowledgements and answers it
    sends.

    `tick(now)` polls the bridge's events and samples, acknowledges what the pitch drew (`drawn`), holds a stop once
    every sample before it has been shown (`stop`, answered by `answer_stop`), and selects the next sample when it is
    due. It never blocks: every call is the bridge's bounded poll."""

    def __init__(self, model, pending, bridge, *, quick=False):
        self.model = model
        self.pending = pending
        self.display = Display("s17")
        self.events = []          # every event the bridge returned, in order
        self.released = 0         # how many of them the screen shows
        self.drawn = -1           # the last sample the pitch painted
        self.acked = -1           # the last sample acknowledged to the bridge
        self.quick = bool(quick)
        self.commentary_paused = False   # [designed: owner #597] reading holds polling and frame acknowledgements
        self.answered = []        # the stops answered, by context
        self.choices = []         # (context, the answer sent) of every stop answered, in order
        self.requests = 0         # the bench requests sent (Esc, Enter)
        self.note = HANG_ON if quick else ""
        self.given = bridge       # the match day's bridge: kept open after the match (D3)
        self.bridge = None
        self.token = None
        self.outcome = None
        self.error = None
        self.finished = False
        self.stop = None          # the decision the match waits on, once every sample before it is shown
        self.notice = None        # the other side's substitution shown on S18, the display held until a key
        self.refusal = None       # an answer's report that refused a pair, shown on S19 until a key
        self.reports = []         # the engine's reports of the bench answers, in order
        self._expected = None     # the report the last bench answer waits for (its index in the bridge's reports)
        self._scanned = 0         # the shown events already looked at for a notice
        self.lineup = None        # the latest pitch sample's players (the opponents' eleven for S09's mark line)
        self.lineup_at = 0        # its watermark: the events before it
        from goal2.ui.replays import GoalWindow
        self.goal_window = GoalWindow()
        self.goal = None          # [designed: T181] a goal once its sample has actually been painted
        self._goal_scanned = 0
    def _send(self, kind, value):
        self.display.accept(["s17", self.display.sequence, kind, value])

    def start(self):
        """Kick-off: the bridge plays the fixture with the pitch samples, the bench and the player prompts."""
        from goal2.desktop.watched import pitch_identity
        self._send("start", pitch_identity(self.model, self.pending))
        self._send("pitch", {"rate": PLAYBACK_RATE})
        options = dict(delay_byte=0, record_draws=True, frames=True, bench=True, prompts=True)
        if self.pending.kind == 1:
            self.token = self.given.start(engine_fixture(self.pending), **options)
        else:
            # [designed: T176] a qualifier is the competitive match on the owner's CompetitiveJobs
            self.token = self.given.start(**options)
        self.bridge = self.given

    @property
    def running(self):
        return self.bridge is not None and not self.finished

    # The poll.
    def tick(self, now):
        """One bounded step; True when the pitch has a new sample to paint."""
        if not self.running or self.commentary_paused:
            return False
        try:
            return self._tick(now)
        except Exception as exc:
            self.error = str(exc)
            self.cancel()
            return False

    def _tick(self, now):
        # [designed: T181] painted() can discover a goal on the last sample. Hold that acknowledgement as well
        # as polling until its questions finish, so publication cannot overtake the replay/save flow.
        if self.goal is not None and not self.quick:
            return False
        bridge, token, display = self.bridge, self.token, self.display
        if self.drawn > self.acked and not self.quick:
            bridge.ack_frames(token, self.drawn)
            self.acked = self.drawn
        for event in bridge.poll(token):
            value = {"kind": event.kind, "minute": event.minute, "score": list(event.score),
                     "data": copy.deepcopy(event.data)}
            self._send("event", value)
            self.events.append(value)
        self._read_report()
        if not bridge.busy:
            return self._full_time()
        if self.held:
            return False          # S18 or S19 shows a notice: the display waits, so the engine waits (LEAD)
        if len(display.frames) <= MAX_BACKLOG - 32:
            for frame in bridge.poll_frames(token):
                self._send("frame", frame)
                self.lineup, self.lineup_at = frame["players"], frame["watermark"]
            if not bridge.busy:
                return self._full_time()
        if self.quick and display.frames:
            # R: every sample is taken as it arrives; the pitch keeps the last one it drew.
            last = display.frames[-1]
            display.frames.clear()
            bridge.ack_frames(token, last["sequence"])
            self.acked = last["sequence"]
            self.released = max(self.released, last["watermark"])
        waiting = bridge.waiting
        if (waiting is not None and self.stop is None and bridge.frames_drained() and not display.frames
                and self.acked == display.frame_sequence):
            context = waiting.data.get("context")
            if self.quick:
                self.released = len(self.events)
            if context == "set_piece" and self.quick:
                # [designed: T167; docs/design S17 "R ... still stops at half time, injuries, extra time and the
                # shoot-out"] a quick result shows no taker card: no key, the current pick stands (F030)
                self._answer(context, {"taker": None})
            else:
                self.released = len(self.events)
                self.stop = waiting
        changed = False
        if not self.quick and (display.frame is None or self.drawn >= display.frame["sequence"]):
            changed = display.advance(now)
            if changed:
                self.released = max(self.released, display.frame["watermark"])
        self._look_for_notice()
        return changed

    @property
    def held(self):
        return self.notice is not None or self.refusal is not None or self.goal is not None

    def _look_for_notice(self):
        """[confirmed: t156-149] The other side's substitution, once shown, stops the display for its notice
        (not in a quick result, which shows none)."""
        managed = self.display.managed
        while self._scanned < self.released and self.notice is None:
            event = self.events[self._scanned]
            self._scanned += 1
            if (not self.quick and managed is not None and event["kind"] == "substitution"
                    and event["data"].get("team") == 1 - managed):
                self.notice = event

    def _read_report(self):
        """The engine's report of the last bench answer (made, requested, refused with the reason)."""
        if self._expected is None or len(self.bridge.reports) <= self._expected:
            return
        report = copy.deepcopy(self.bridge.reports[self._expected])
        self._expected = None
        self.reports.append(report)
        from goal2.ui.squad_card import full_name
        name = lambda w: full_name(self.model, w)
        said = []
        if report["made"]:
            said.append("Made: " + ", ".join(f"{name(b)} on for {name(a)}" for a, b in report["made"]) + ".")
        if report["requested"]:
            said.append("Requested: made at the next stoppage.")
        if report["refused"]:
            said.append("Not made: " + ", ".join(f"{name(b)} for {name(a)}" for a, b, _ in report["refused"]) + ".")
            self.refusal = report
        self.note = " ".join(said)

    def dismiss(self):
        """A key on S18's notice or on S19's refusal: the display plays on."""
        self.notice = None
        self.refusal = None

    def opponents(self):
        """The other side's eleven as the engine has it now, keeper first: the latest pitch sample's players
        (watched_pitch.snapshot: each slot's current player word, substitutions included [derived: T81]), with the
        other side's substitutions shown since. [designed: T180] The decision does not carry them."""
        managed = self.display.managed
        if self.lineup is None or managed is None:
            return []
        words = [p[3] for p in sorted((p for p in self.lineup if p[1] == 1 - managed), key=lambda p: p[2])]
        for event in self.events[self.lineup_at:]:
            if event["kind"] == "substitution" and event["data"].get("team") == 1 - managed:
                words = [event["data"]["on"] if w == event["data"]["off"] else w for w in words]
        return words

    def _full_time(self):
        """The bridge has published the match (or failed it): every event is shown; the bridge stays open (D3)."""
        self.outcome = self.bridge.outcome
        if self.outcome is None:
            raise ValueError("the match ended without its publication")
        self.released = len(self.events)
        self.finished = True
        self.bridge = None
        return False

    def _answer(self, context, value, requested=()):
        if context in ("set_piece", "shootout_order"):
            self.bridge.choose(self.token, value)
        elif context in BENCH:
            # [designed: T180] the bench's answer: the pairs, with its other changes when there are any
            if isinstance(value, dict):
                pairs = value.get("substitutions") or []
                self.bridge.answer(self.token, pairs, {k: v for k, v in value.items() if k != "substitutions"})
            else:
                pairs = list(value or [])
                self.bridge.answer(self.token, pairs)
            if pairs or (context == "substitution" and requested and not isinstance(value, dict)):
                # [confirmed: the kit's Match._on_notice; watched_match._drive_match] a report follows
                self._expected = len(self.bridge.reports)
        else:
            self.bridge.answer(self.token, ())
        self.answered.append(context)
        self.choices.append((context, value))

    def answer_stop(self, value=None):
        """The match day's answer to the held stop, sent once: {'taker': word or None} at a set piece,
        {'shootout_order': [words]} before a shoot-out, the bench's (S19, `BenchAnswer.value`) at half time, a
        substitution opportunity and a pause, nothing before extra time (play on)."""
        stop, self.stop = self.stop, None
        if stop is None or not self.running:
            return
        self._answer(stop.data.get("context"), value if value is not None else [], stop.data.get("requested"))

    # The player's keys.
    def painted(self, sequence):
        self.drawn = max(self.drawn, sequence)
        frame = self.display.frame
        if self.quick or frame is None or frame['sequence'] != sequence:
            return
        self.goal_window.painted(frame)
        # [designed: T181] Goals behind the displayed sample's watermark are visible; a future event in a poll
        # cannot open a question over a pitch that has not yet shown it. A recalled goal has player 0 (T167).
        while self._goal_scanned < min(frame['watermark'], len(self.events)) and self.goal is None:
            event = self.events[self._goal_scanned]
            self._goal_scanned += 1
            if event['kind'] == 'goal' and event['data'].get('player'):
                self.goal = event

    def dismiss_goal(self):
        self.goal = None
        self.goal_window.clear()
        self.display.next_frame = time.monotonic()

    def step_speed(self, step):
        self.display.step_rate(step)

    def quick_result(self):
        """R: the engine plays on without pacing."""
        if self.running and not self.quick:
            self.quick = True
            self.goal = None
            self.goal_window.clear()
            self.note = HANG_ON

    def request_bench(self):
        """Esc or Enter: the original's bench request (`Match.pause` through the bridge)."""
        if not self.running:
            return False
        sent = self.bridge.pause(self.token)
        if sent:
            self.requests += 1
            self.note = REQUESTED
        return sent

    def cancel(self):
        """End the match through the bridge, publishing nothing; the bridge stays the match day's."""
        bridge, self.bridge = self.bridge, None
        self.finished = True
        if bridge is not None and bridge.busy and bridge.token == self.token:
            bridge.cancel_and_reap(self.token)

    # What the screen shows.
    def shown(self):
        """The events the screen has shown, in order."""
        return self.events[:self.released]

    def frame_or_event(self):
        """(minute, score) of the sample on the pitch, else of the last event shown."""
        frame = self.display.frame
        if frame is not None and not self.finished:
            return frame["minute"], frame["score"]
        shown = self.shown()
        return (shown[-1]["minute"], shown[-1]["score"]) if shown else (0, [0, 0])


def commentary_line(event):
    """A line of the commentary: the minute and the text, or a stop and how it was answered."""
    if event["kind"] == "commentary":
        return f"{event['minute']}′ {event['data'].get('text', '')}"
    context = event["data"].get("context")
    return f"{event['minute']}′ ── {STOPS.get(context, str(context).upper())}: your answer"


class PitchScreen(Screen):
    title = "watching"
    escape_text = "bench"

    def __init__(self, window, model, controller, day=None):
        super().__init__(window)
        self.model = model
        self.controller = controller
        self.day = day            # the match day that shows the stops and full time (goal2/ui/match_day.py)
        self.lines = []           # the commentary's lines, oldest first
        self._seen = 0            # the shown events already made into lines
        self.ended = False
        self.held = None          # the stop the match day is showing
        self.replay = None        # [designed: T181] a presentation-only Playback, no bridge acknowledgements
        self.replay_done = None
        self.replay_display = None
        self.goal_record = None
        names = controller.display.countries
        self.name_label.setText(f"watching · {names[HOME]} v {names[1 - HOME]}")
        self._build(names)
        self.bind((Qt.Key.Key_Up,), "", lambda: self.step_marks(-1), shown=False)
        self.bind((Qt.Key.Key_Down,), "", lambda: self.step_marks(1), shown=False)
        self.bind((), "display", lambda: self.step_marks(1), captions=("↑", "↓"))
        self.bind((Qt.Key.Key_Left,), "", lambda: self.step_speed(-1), captions=("←",), shown=False)
        self.bind((Qt.Key.Key_Right,), "", lambda: self.step_speed(1), captions=("→",), shown=False)
        self.bind((), "speed", lambda: self.step_speed(1), captions=("←", "→"))
        self.result_binding = self.bind((Qt.Key.Key_R,), "result", self.quick_result)
        self.commentary_binding = self.bind((Qt.Key.Key_Space,), "commentary", self.toggle_commentary)
        self.bind((Qt.Key.Key_F9,), "sound", self.sound)
        self.set_enter("Bench", self.request_bench)
        from goal2.ui.s18_stop import StopBox
        self.stop_box = StopBox(self)   # S18, over the pitch [designed: T180]
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.tick)
        self.refresh()
        self.timer.start()
        if controller.quick:
            self.quick_result()

    # Building. [designed: s17-pitch.html]
    def _build(self, names):
        managed = self.controller.display.managed
        head = QFrame()
        head.setObjectName("box")
        row = QHBoxLayout(head)
        row.setContentsMargins(18, 10, 18, 10)
        row.setSpacing(30)
        score = QHBoxLayout()
        score.setSpacing(18)
        # [confirmed: t156-045-kick-off.png; #562, #583] the home side first, each name in its side's kit
        self.kits = getattr(self.controller, 'kits', None) or for_fixture(self.model, self.controller.pending)
        self.home = label(names[HOME], "h1")
        colour(self.home, side_colour(HOME, self.kits))
        self.away = label(names[1 - HOME], "h1")
        colour(self.away, side_colour(1 - HOME, self.kits))
        self.goals = []
        score.addWidget(self.home)
        for _ in (0, 1):
            digit = QFrame()
            digit.setObjectName("digit")
            digit.setFixedSize(46, 46)
            inner = QHBoxLayout(digit)
            inner.setContentsMargins(0, 0, 0, 0)
            text = label("0", "digitText")
            text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inner.addWidget(text)
            self.goals.append(text)
            score.addWidget(digit)
        score.addWidget(self.away)
        row.addLayout(score)
        self.minute = label("0′", "h1")
        row.addWidget(self.minute)
        self.kind = label(self.controller.display.kind.upper(), "sub")
        row.addWidget(self.kind)
        from goal2.ui.readable_text import Excerpt
        recent = QVBoxLayout()
        recent.setSpacing(4)
        self.recent = [Excerpt(),Excerpt()]
        for widget in self.recent:
            widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            recent.addWidget(widget)
        row.addLayout(recent,1)
        self.score_head = head
        self.body_layout.addWidget(head)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.pitch = PitchWidget(self.display, self.painted, self.window_.family)
        self.pitch.kits = self.kits
        middle.addWidget(self.pitch, 0, Qt.AlignmentFlag.AlignTop)
        commentary, inner = box("Commentary")
        self.commentary = QLabel("")
        self.commentary.setObjectName("value")
        self.commentary.setTextFormat(Qt.TextFormat.PlainText)
        self.commentary.setWordWrap(True)
        self.commentary.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Expanding)
        self.commentary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        inner.addWidget(self.commentary, 1)
        self.status = label("", "sub")
        self.status.setWordWrap(True)
        inner.addWidget(self.status)
        side = self.kits.name(managed) if managed is not None else "none"
        tag_row = QHBoxLayout()
        self.side_tag = label(f"YOUR SIDE: {side}", "tag")
        tag_row.addWidget(self.side_tag)
        tag_row.addStretch(1)
        inner.addLayout(tag_row)
        self.note = QLabel("")
        self.note.setObjectName("note")
        self.note.setWordWrap(True)
        colour(self.note, theme.VALUE)
        inner.addWidget(self.note)
        middle.addWidget(commentary, 1)
        self.body_layout.addLayout(middle, 1)

    # The poll and what is shown.
    def display(self):
        return self.replay_display if self.replay is not None else self.controller.display

    def painted(self, sequence):
        if self.replay is not None:
            self.replay.painted(sequence)
        else:
            self.controller.painted(sequence)

    def start_replay(self, frames, done):
        from goal2.ui.replays import Playback
        self.replay = Playback(frames)
        self.replay_display = copy.copy(self.controller.display)
        self.replay_done = done
        self._replay_enter_before = self.enter_action
        self.set_enter('Replay playing', lambda: None)
        self._result_text('REPLAY')
        self.replay_tick(time.monotonic())

    def replay_tick(self, now):
        if getattr(self.controller, 'commentary_paused', False):
            return
        replay = self.replay
        if replay.advance(now, self.controller.display.pitch_rate):
            self.replay_display.frame = replay.frame
            self.pitch.update()
        self.refresh()
        if replay.finished:
            done = self.replay_done
            self.replay = self.replay_display = self.replay_done = None
            self.set_enter(*self._replay_enter_before)
            self._result_text(HANG_ON if self.controller.quick else 'result')
            self.pitch.update()
            self.refresh()
            done()

    def tick(self):
        if getattr(self.controller, 'commentary_paused', False):
            return
        if self.replay is not None:
            self.replay_tick(time.monotonic())
            return
        controller = self.controller
        if controller.tick(time.monotonic()):
            self.pitch.update()
        self.refresh()
        if controller.finished and not self.ended:
            self.end()
        elif self.stop_box.open or self.window_.current() is not self or self.day is None:
            return
        elif controller.goal is not None:
            self.day.goal(self, controller.goal)
        elif controller.notice is not None:
            self.show_notice(controller.notice)
        elif controller.refusal is not None:
            self.day.refused(self, controller.refusal)
        elif controller.stop is not None and self.held is None:
            self.held = controller.stop
            self.day.stop(self, controller.stop)

    def show_notice(self, event):
        """[confirmed: t156-149] S18: the other side's substitution; any key plays on."""
        from goal2.ui.s18_stop import NOTICE_OPPONENT, opponent_text, score_line
        names = self.controller.display.countries
        country = names[event["data"]["team"]]
        self.show_stop(NOTICE_OPPONENT, opponent_text(self.model, event),
                       f"{country}: {score_line(names, event['score'], event['minute'])}. Press any key: play on.",
                       lambda key: self.dismiss())

    def show_stop(self, kind, headline, detail, handler, answers=None):
        """S18 over the pitch, answered by any key."""
        self.stop_box.show_stop(kind, headline, detail, handler, answers)
        self._enter_before = self.enter_action
        self.set_enter('Answer Y or N' if answers else 'Continue',
                       lambda: self.answer_stop_box(Qt.Key.Key_Return))
        self.refresh()

    def answer_stop_box(self, key):
        if self.stop_box.answers and key not in self.stop_box.answers:
            return False
        self.set_enter(*self._enter_before)
        return self.stop_box.answer(key)

    def handle_key(self, key):
        if self.stop_box.open and key != Qt.Key.Key_F1:
            self.answer_stop_box(key)
            return True
        if self.replay is not None and key in (Qt.Key.Key_R, Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            return True
        return super().handle_key(key)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.stop_box.open:
            self.stop_box.place()

    def dismiss(self):
        """A key on a notice or a refusal: the display plays on."""
        self.controller.dismiss()
        self.refresh()

    def resume(self, value=None):
        """The match day's answer to the stop it showed: sent once, and the match plays on."""
        self.held = None
        self.controller.answer_stop(value)
        self.refresh()

    def refresh(self):
        controller = self.controller
        shown = controller.shown()
        for event in shown[self._seen:]:
            if event["kind"] == "commentary" or event["kind"] == "decision":
                self.lines.append(commentary_line(event))
        self._seen = len(shown)
        minute, score = ((self.replay.frame['minute'], self.replay.frame['score'])
                         if self.replay is not None and self.replay.frame is not None else controller.frame_or_event())
        _set(self.minute, f"{minute}′")
        for text, goals in zip(self.goals, (score[HOME], score[1 - HOME])):
            _set(text, str(goals))
        texts = [e["data"].get("text", "") for e in shown if e["kind"] == "commentary"][-2:]
        for widget, text in zip(self.recent, [""] * (2 - len(texts)) + texts):
            _set(widget, text)
        from goal2.ui.readable_text import recent_text
        _set(self.commentary,recent_text(self.lines,self.commentary.fontMetrics(),
                                         self.commentary.width(),self.commentary.height(),COMMENTARY_ROWS))
        _set(self.status, f"Speed {controller.display.speed_markers()} · {controller.display.speed_name().lower()}"
                          f" · marks: {MARKS[self.pitch.marks].lower()}")
        _set(self.note, controller.note)
        if self.pitch.enlarged:
            self.pitch.commentary = self.lines

    # The keys.
    def step_marks(self, step):
        """↑↓: the original's display styles. [confirmed: 0791:9372 Up/Down step DS:066A over 0..4]"""
        self.pitch.marks = (self.pitch.marks + step) % len(MARKS)
        self.pitch.update()
        self.refresh()

    def step_speed(self, step):
        """←→: the next slower or faster of the six speeds. [confirmed: E031 C39; match_view.py SPEEDS]"""
        self.controller.step_speed(step)
        self.refresh()

    def speed(self):
        return self.controller.display.speed_name()

    def toggle_commentary(self):
        """Space: pause for the whole commentary; Space/Enter resumes [designed: owner #597]."""
        if self.stop_box.open:
            # Mouse key-bar actions must obey the same question/notice gate as keyboard Space.
            self.answer_stop_box(Qt.Key.Key_Space)
            return
        paused = not getattr(self.controller, 'commentary_paused', False)
        self.controller.commentary_paused = paused
        self.pitch.enlarged = paused
        self.pitch.commentary = self.lines
        if paused:
            self.score_head.hide()
            self._commentary_enter_before = self.enter_action
            self.set_enter('Resume match', self.toggle_commentary)
            self.wait_for('PAUSED', 'Reading commentary. Space or Enter resumes the same match.')
        else:
            self.score_head.show()
            self.set_enter(*self._commentary_enter_before)
            self.wait_for(None)
            # No catch-up burst after time spent reading; the next sample gets a normal interval.
            now = time.monotonic()
            self.controller.display.next_frame = now + 1 / self.controller.display.pitch_rate
            if self.replay is not None:
                self.replay.next_frame = now + 1 / self.controller.display.pitch_rate
        self.commentary_binding.text = 'resume' if paused else 'commentary'
        for item in self.key_bar.findChildren(Clickable, 'keyItem'):
            if getattr(item, 'binding', None) is self.commentary_binding:
                for widget in item.findChildren(QLabel, 'keyLabel'):
                    widget.setText(self.commentary_binding.text)
        self.pitch.update()
        self.refresh()

    def _result_text(self, text):
        self.result_binding.text = text
        for item in self.key_bar.findChildren(Clickable, 'keyItem'):
            if getattr(item, 'binding', None) is self.result_binding:
                for label_ in item.findChildren(QLabel, 'keyLabel'):
                    label_.setText(text)
                    colour(label_, theme.VALUE)

    def quick_result(self):
        # [designed: T181] Mouse key-bar callbacks do not pass through handle_key. They must hold the same live
        # controls during replay and the goal questions; a click cannot clear a goal or bypass its pacing.
        if (getattr(self.controller, 'commentary_paused', False) or self.replay is not None
                or self.stop_box.kind in ('replay', 'save-goal')):
            return
        self.controller.quick_result()
        if self.controller.quick:
            self._result_text(HANG_ON)
        self.refresh()

    def sound(self):
        self.controller.note = NO_SOUND
        self.refresh()

    def request_bench(self):
        if (getattr(self.controller, 'commentary_paused', False) or self.replay is not None
                or self.stop_box.kind in ('replay', 'save-goal')):
            return
        self.controller.request_bench()
        self.refresh()

    def escape(self):
        self.request_bench()

    # The end.
    def end(self):
        """Full time: the match day shows the board (S20) and the menu (S15). A failure or a cancel: back to the desk
        with what happened in its status line."""
        self.ended = True
        self.timer.stop()
        controller = self.controller
        if controller.outcome is not None and self.day is not None:
            self.day.full_time(self)
            return
        if controller.error is not None:
            text = f"The match stopped: {controller.error}"
        else:
            text = "The match was cancelled; nothing was published."
        window = self.window_
        while len(window.stack) > 1:
            window.pop()
        say = getattr(window.current(), "say", None)
        if say is not None:
            say(text)

    def closing(self):
        """The window closes during the match: cancel it through the bridge; nothing is published."""
        self.timer.stop()
        self.ended = True
        self.controller.cancel()


def _set(widget, text):
    if widget.text() != text:
        widget.setText(text)
