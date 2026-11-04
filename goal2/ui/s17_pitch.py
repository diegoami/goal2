"""S17 Pitch: your own friendly, watched in the main window, with the commentary always beside it.

[designed: owner, 2026-11-03, #526 decision 2; docs/design/ui-2026-11 S17 and its mockup s17-pitch.html; T166, #540]
The screen shows the engine's pitch samples and events, in order, paced by its own acknowledgements, and the match the
player watched is the match the engine published. It drives nothing: `MatchController` reads the bridge
(`goal2.game.watched_jobs.WatchedJobs`, docs/watched-jobs.md) on the window's thread and never waits on the engine.

- **Shows** [confirmed: T156-R1 steps 45-192, t156-045-kick-off.png; designed: s17-pitch.html]: the two sides, the
  score, the minute, the match's kind and the last two events above the pitch (goal2/ui/pitch.py), and the commentary
  beside it with the speed, the display and your side's colour.
- **Keys** [confirmed: E031 C39-C40, C08; T156-R1 steps 45, 267; the capture's bottom line]: **←→** the speed, the six
  `SPEEDS` of goal2/desktop/match_view.py; **↑↓** the display (the original's five marks); **Space** enlarges the
  commentary; **R** quick result; **F9** sound; **Esc** / **Enter** the bench.
- **Pacing** [designed: T102, kept by the bridge]: a sample is acknowledged once the pitch has painted it, so the
  engine never runs more than `LEAD` samples ahead of what was drawn. **R** stops the pacing: every sample is
  acknowledged as it arrives and the screen says *HANG ON A TICK* where *R result* was, as the original does
  [confirmed: t156-267-quick-hang-on.png]; the pitch keeps the last sample it drew.
- **F9** [designed: T166]: goal2 has no sound; the key says so and does nothing else.
- **The stops** [designed: T167, #541; docs/design/ui-2026-11 §1, the match day]: the controller holds a stop once every
  sample before it is shown, and the match day (goal2/ui/match_day.py) shows it: half time and the menu before extra
  time on S20 then S15, a set-piece taker and the shoot-out order on S16. Its answer is the one the engine receives,
  sent once through the bridge. A substitution opportunity and the pause Esc or Enter asks for keep T166's answer
  until T180 builds S18 and S19: no substitution, play on (goal2/desktop/bench_page.py `escape`), noted in the
  commentary.
- **Full time** publishes through the bridge, then the match day shows S20 and S15. Closing the window during a match
  cancels it through the bridge (`Window.closeEvent` calls `closing`): nothing is published.

The bridge is the match day's, one for the window's life (D3, #527): the controller starts its match on it and never
closes it [designed: T167, replacing T166's bridge per match].
"""
from __future__ import annotations

import copy
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from goal2.desktop.match_view import MAX_BACKLOG, PLAYBACK_RATE, Display
from goal2.desktop.pygame_viewer import MARKS
from goal2.ui import theme
from goal2.ui.pitch import HOME, PitchWidget, side_colour
from goal2.ui.screen import Clickable, Screen, label
from goal2.ui.squad_card import box, colour

TICK_MS = 4            # the controller's poll; the fastest speed shows 240 samples a second [designed: T166]
COMMENTARY_ROWS = 15   # the lines the commentary box shows [designed: s17-pitch.png, the box's height]
HANG_ON = "HANG ON A TICK"   # [confirmed: t156-267-quick-hang-on.png, "HANG ON"; T156-R1 step 2's full words]
NO_SOUND = "F9: goal2 has no sound, so the key does nothing."
BENCH_LATER = "The bench comes with T180: the match plays on with no substitution."
# The stops' words. [confirmed: E031 C40-C41, C44-C46b; goal2/desktop/match_view.py `Display.board`]
STOPS = {"half_time": "HALF TIME", "substitution": "SUBSTITUTION OPPORTUNITY", "pause": "PAUSE",
         "extra_time": "EXTRA TIME", "shootout_order": "PENALTY SHOOT-OUT"}
# The bench decisions that keep T166's default answer until T180 (S18, S19) [designed: T167]; every other stop is
# held for the match day's screens (STOPS_SHOWN).
DEFAULTED = ("substitution", "pause")
STOPS_SHOWN = ("half_time", "extra_time", "set_piece", "shootout_order")


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
        if not self.running:
            return False
        try:
            return self._tick(now)
        except Exception as exc:
            self.error = str(exc)
            self.cancel()
            return False

    def _tick(self, now):
        bridge, token, display = self.bridge, self.token, self.display
        if self.drawn > self.acked and not self.quick:
            bridge.ack_frames(token, self.drawn)
            self.acked = self.drawn
        for event in bridge.poll(token):
            value = {"kind": event.kind, "minute": event.minute, "score": list(event.score),
                     "data": copy.deepcopy(event.data)}
            self._send("event", value)
            self.events.append(value)
        if not bridge.busy:
            return self._full_time()
        if len(display.frames) <= MAX_BACKLOG - 32:
            for frame in bridge.poll_frames(token):
                self._send("frame", frame)
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
            if context in DEFAULTED:
                bridge.answer(token, ())
                self.answered.append(context)
                self.choices.append((context, []))
                self.note = f"{STOPS.get(context, context)}: {BENCH_LATER}"
            elif context == "set_piece" and self.quick:
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
        return changed

    def _full_time(self):
        """The bridge has published the match (or failed it): every event is shown; the bridge stays open (D3)."""
        self.outcome = self.bridge.outcome
        if self.outcome is None:
            raise ValueError("the match ended without its publication")
        self.released = len(self.events)
        self.finished = True
        self.bridge = None
        return False

    def _answer(self, context, value):
        if context in ("set_piece", "shootout_order"):
            self.bridge.choose(self.token, value)
        else:
            self.bridge.answer(self.token, ())
        self.answered.append(context)
        self.choices.append((context, value))

    def answer_stop(self, value=None):
        """The match day's answer to the held stop, sent once: {'taker': word or None} at a set piece,
        {'shootout_order': [words]} before a shoot-out, nothing at half time and before extra time (play on; the
        bench comes with T180)."""
        stop, self.stop = self.stop, None
        if stop is None or not self.running:
            return
        self._answer(stop.data.get("context"), value if value is not None else [])

    # The player's keys.
    def painted(self, sequence):
        self.drawn = max(self.drawn, sequence)

    def step_speed(self, step):
        self.display.step_rate(step)

    def quick_result(self):
        """R: the engine plays on without pacing."""
        if self.running and not self.quick:
            self.quick = True
            self.note = HANG_ON

    def request_bench(self):
        """Esc or Enter: the original's bench request (`Match.pause` through the bridge)."""
        if not self.running:
            return False
        sent = self.bridge.pause(self.token)
        if sent:
            self.requests += 1
            self.note = "Bench requested. " + BENCH_LATER
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
    answer = "no substitution, play on (T180)" if context in DEFAULTED else "your answer"
    return f"{event['minute']}′ ── {STOPS.get(context, str(context).upper())}: {answer}"


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
        self.bind((Qt.Key.Key_Space,), "commentary", self.toggle_commentary)
        self.bind((Qt.Key.Key_F9,), "sound", self.sound)
        self.set_enter("Bench", self.request_bench)
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
        # [derived: DesktopModel.home, #562] the home side first and light red, as the original's screens
        self.home = label(names[HOME], "h1")
        colour(self.home, side_colour(HOME))
        self.away = label(names[1 - HOME], "h1")
        colour(self.away, side_colour(1 - HOME))
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
        row.addStretch(1)
        recent = QVBoxLayout()
        recent.setSpacing(4)
        self.recent = [label("", "value"), label("", "value")]
        for widget in self.recent:
            widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            recent.addWidget(widget)
        row.addLayout(recent)
        self.body_layout.addWidget(head)
        middle = QHBoxLayout()
        middle.setSpacing(18)
        self.pitch = PitchWidget(lambda: self.controller.display, self.controller.painted, self.window_.family)
        middle.addWidget(self.pitch, 0, Qt.AlignmentFlag.AlignTop)
        commentary, inner = box("Commentary")
        self.commentary = QLabel("")
        self.commentary.setObjectName("value")
        self.commentary.setTextFormat(Qt.TextFormat.PlainText)
        self.commentary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        inner.addWidget(self.commentary, 1)
        self.status = label("", "sub")
        inner.addWidget(self.status)
        side = "LIGHT RED" if managed == HOME else "WHITE"
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
    def tick(self):
        controller = self.controller
        if controller.tick(time.monotonic()):
            self.pitch.update()
        self.refresh()
        if controller.finished and not self.ended:
            self.end()
        elif controller.stop is not None and self.held is None and self.day is not None:
            self.held = controller.stop
            self.day.stop(self, controller.stop)

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
        minute, score = controller.frame_or_event()
        _set(self.minute, f"{minute}′")
        for text, goals in zip(self.goals, (score[HOME], score[1 - HOME])):
            _set(text, str(goals))
        texts = [e["data"].get("text", "") for e in shown if e["kind"] == "commentary"][-2:]
        for widget, text in zip(self.recent, [""] * (2 - len(texts)) + texts):
            _set(widget, text)
        _set(self.commentary, "\n".join(self.lines[-COMMENTARY_ROWS:]))
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
        """Space: the whole commentary over the pitch, and back. [confirmed: E031 C08, C39c]"""
        self.pitch.enlarged = not self.pitch.enlarged
        self.pitch.commentary = self.lines
        self.pitch.update()

    def quick_result(self):
        self.controller.quick_result()
        if self.controller.quick:
            self.result_binding.text = HANG_ON
            for item in self.key_bar.findChildren(Clickable, "keyItem"):
                if getattr(item, "binding", None) is self.result_binding:
                    for text in item.findChildren(QLabel, "keyLabel"):
                        text.setText(HANG_ON)
                        colour(text, theme.VALUE)
        self.refresh()

    def sound(self):
        self.controller.note = NO_SOUND
        self.refresh()

    def request_bench(self):
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
