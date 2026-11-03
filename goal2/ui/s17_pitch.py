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
- **The stops, until T167** [designed: T166, interim]: the match menu, the bench and the boards (S18-S20) come with
  T167. Until then every bench decision (half time, a substitution opportunity, the pause Esc or Enter asks for) is
  answered as today's window answers one left unanswered: no substitution, play on (goal2/desktop/bench_page.py
  `escape`). The engine answers the others as it always does (extra time, the shoot-out order). Each stop is noted in
  the commentary.
- **Full time** publishes through the bridge and returns to the desk, with the result in its status line. Closing the
  window during a match cancels it through the bridge (`Window.closeEvent` calls `closing`): nothing is published
  and the engine process ends.

The bridge lives for one match [designed: T166, interim]: the controller makes it at kick-off and closes it at full
time or on a cancel, so no engine process outlives the match.
"""
from __future__ import annotations

import copy
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from goal2.desktop.match_view import MAX_BACKLOG, PLAYBACK_RATE, Display
from goal2.desktop.pygame_viewer import MARKS
from goal2.ui import theme
from goal2.ui.pitch import PitchWidget, side_colour
from goal2.ui.screen import Clickable, Screen, label
from goal2.ui.squad_card import box, colour

TICK_MS = 4            # the controller's poll; the fastest speed shows 240 samples a second [designed: T166]
COMMENTARY_ROWS = 15   # the lines the commentary box shows [designed: s17-pitch.png, the box's height]
HANG_ON = "HANG ON A TICK"   # [confirmed: t156-267-quick-hang-on.png, "HANG ON"; T156-R1 step 2's full words]
NO_SOUND = "F9: goal2 has no sound, so the key does nothing."
BENCH_LATER = "The bench comes with T167: the match plays on with no substitution."
# The stops' words. [confirmed: E031 C40-C41, C44-C46b; goal2/desktop/match_view.py `Display.board`]
STOPS = {"half_time": "HALF TIME", "substitution": "SUBSTITUTION OPPORTUNITY", "pause": "PAUSE",
         "extra_time": "EXTRA TIME", "shootout_order": "PENALTY SHOOT-OUT"}
BENCH = ("half_time", "substitution", "pause")   # the decisions the watching player answers (BENCH_CONTEXTS)
QUALIFIER_LATER = ("Qualifiers in the new window come with T176 and T167; this interim route plays your friendlies "
                   "only.")


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
    """The engine's fixture of a scheduled one, as today's WatchedController makes it."""
    from goal2.engine.original_match import Fixture
    return Fixture(pending.side_a, pending.side_b, int(pending.fixture_id.split(":")[1]))


class MatchController:
    """One watched friendly over the bridge: what the screen shows, and the acknowledgements and answers it sends.

    `tick(now)` polls the bridge's events and samples, acknowledges what the pitch drew (`drawn`), answers a bench
    decision once every sample before it has been shown, and selects the next sample when it is due. It never
    blocks: every call is the bridge's bounded poll."""

    def __init__(self, model, pending, *, command=None):
        self.model = model
        self.pending = pending
        self.command = command
        self.display = Display("s17")
        self.events = []          # every event the bridge returned, in order
        self.released = 0         # how many of them the screen shows
        self.drawn = -1           # the last sample the pitch painted
        self.acked = -1           # the last sample acknowledged to the bridge
        self.quick = False
        self.answered = []        # the bench decisions answered, by context
        self.requests = 0         # the bench requests sent (Esc, Enter)
        self.note = ""
        self.bridge = None
        self.token = None
        self.outcome = None
        self.error = None
        self.finished = False

    def _send(self, kind, value):
        self.display.accept(["s17", self.display.sequence, kind, value])

    def start(self):
        """Kick-off: the bridge plays the fixture with the pitch samples and the bench (T102)."""
        from goal2.desktop.watched import pitch_identity
        from goal2.game.watched_jobs import WatchedJobs
        self._send("start", pitch_identity(self.model, self.pending))
        self._send("pitch", {"rate": PLAYBACK_RATE})
        self.bridge = WatchedJobs(self.model, command=self.command)
        try:
            self.token = self.bridge.start(engine_fixture(self.pending), delay_byte=0, record_draws=True,
                                           frames=True, bench=True)
        except Exception:
            self.bridge.close()
            self.bridge = None
            raise

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
        if (waiting is not None and bridge.frames_drained() and not display.frames
                and self.acked == display.frame_sequence):
            context = waiting.data.get("context")
            bridge.answer(token, ())
            self.answered.append(context)
            self.note = f"{STOPS.get(context, context)}: {BENCH_LATER}"
            if self.quick:
                self.released = len(self.events)
        changed = False
        if not self.quick and (display.frame is None or self.drawn >= display.frame["sequence"]):
            changed = display.advance(now)
            if changed:
                self.released = max(self.released, display.frame["watermark"])
        return changed

    def _full_time(self):
        """The bridge has published the match (or failed it): every event is shown and the bridge is closed."""
        self.outcome = self.bridge.outcome
        if self.outcome is None:
            raise ValueError("the match ended without its publication")
        self.released = len(self.events)
        self.finished = True
        bridge, self.bridge = self.bridge, None
        bridge.close()
        return False

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
        """End the match through the bridge, publishing nothing, and close the bridge (and with it the engine)."""
        bridge, self.bridge = self.bridge, None
        self.finished = True
        if bridge is not None:
            bridge.close()

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
    answer = "no substitution, play on (T167)" if context in BENCH else "the original's own answer"
    return f"{event['minute']}′ ── {STOPS.get(context, str(context).upper())}: {answer}"


class PitchScreen(Screen):
    title = "watching"
    escape_text = "bench"

    def __init__(self, window, model, controller):
        super().__init__(window)
        self.model = model
        self.controller = controller
        self.lines = []           # the commentary's lines, oldest first
        self._seen = 0            # the shown events already made into lines
        self.ended = False
        names = controller.display.countries
        self.name_label.setText(f"watching · {names[0]} v {names[1]}")
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
        self.home = label(names[0], "h1")
        colour(self.home, side_colour(0))
        self.away = label(names[1], "h1")
        colour(self.away, side_colour(1))
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
        side = "LIGHT RED" if managed == 0 else "WHITE"
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

    def refresh(self):
        controller = self.controller
        shown = controller.shown()
        for event in shown[self._seen:]:
            if event["kind"] == "commentary" or event["kind"] == "decision":
                self.lines.append(commentary_line(event))
        self._seen = len(shown)
        minute, score = controller.frame_or_event()
        _set(self.minute, f"{minute}′")
        for text, goals in zip(self.goals, score):
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
        """Full time, a failure or a cancel: back to the desk with what happened in its status line."""
        self.ended = True
        self.timer.stop()
        controller = self.controller
        if controller.outcome is not None:
            result = self.model.result_text().split("\n", 1)[0]
            text = f"Full time: {result}. The match board and the round come with T167."
        elif controller.error is not None:
            text = f"The match stopped: {controller.error}"
        else:
            text = "The match was cancelled; nothing was published."
        window = self.window_
        while window.current() is not self and len(window.stack) > 1:
            window.pop()
        desk = window.pop()
        say = getattr(desk, "say", None)
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


def play_next_game(window, model):
    """The desk's *play next game*, until T167 brings the round, the match menu and the captain: the next friendly
    on S17, with the original's suggested captain. Returns the screen, or the reason it cannot start.
    [designed: T166, the interim route]"""
    campaign = model.state.campaign
    pending = campaign.next_fixture if campaign is not None else None
    if pending is None:
        return "There is no match to play: the stage is complete."
    if pending.kind != 1:
        return QUALIFIER_LATER
    state = model.state
    captain = suggested_captain(state)
    if captain is not None:
        eleven = list(state.starting_eleven or state.managed_squad[:11])
        try:
            model.confirm(eleven, captain, state.country_tactics)
        except ValueError as exc:
            return f"The match cannot start: {exc}"
    controller = MatchController(model, pending)
    try:
        controller.start()
    except (OSError, ValueError) as exc:
        return f"The match cannot start: {exc}"
    try:
        screen = PitchScreen(window, model, controller)
    except BaseException:
        controller.cancel()
        raise
    return window.push(screen)

