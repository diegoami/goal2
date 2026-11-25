"""[designed: T170al/T170ap] Request and team tactics at a verified native pause."""

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.ui.native_review import NativeReviewScreen
from goal2.ui.s10_team_tactics import TeamTacticsScreen
from goal2.ui.s19_bench import BenchAnswer


class NativePauseTacticsScreen(TeamTacticsScreen):
    GRID = True

    def __init__(self, pause):
        self.pause = pause
        model = SimpleNamespace(state=pause.state, goaldat=pause.data)
        decision = SimpleNamespace(data=pause.snapshot.snapshot.data, minute=pause.minute, score=pause._score)
        super().__init__(pause.window_, model, answer=BenchAnswer(model, decision),
                         apply=pause.apply_tactic, back='pause')

    def change(self):
        pause = self.pause
        if (pause.phase == 'ready' and pause.driver.stopped_view is pause.snapshot
                and self.window_.current() is self):
            return super().change()

    def accept_view(self, message):
        pause = self.pause
        self.model.state = pause.state
        decision = SimpleNamespace(data=pause.snapshot.snapshot.data, minute=pause.minute, score=pause._score)
        answer = BenchAnswer(self.model, decision)
        if message:
            self.answer = answer
            self.reject(message)
        else:
            self.applied(answer, {})

    def reject(self, message):
        self.pending = False
        self.changed = None
        self._requested = None
        self.message = message
        self.refresh()


class NativePauseScreen(NativeReviewScreen):
    GRID = True
    title = 'Match paused'
    primary_label = 'Play'
    statistics_phase = 'pause'

    def __init__(self, pitch, waiting):
        self._score = tuple(waiting['event']['score'])
        self.minute = waiting['event']['minute']
        self._desired = None
        self.tactics_editor = None
        self._tactic_refusal = ''
        self.request_button = QPushButton('Request substitution')
        self.request_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.request_button.clicked.connect(self.toggle_request)
        self.tactics_button = QPushButton('Team tactics')
        self.tactics_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tactics_button.clicked.connect(self.open_tactics)
        super().__init__(pitch, waiting['decision'])
        self.body.move(self.details, 0, 8, 54, 5)
        self.budget = self.body.text('', 'sub', 0, 13, 54)
        self.body.put(self.request_button, 0, 15, 25, 2)
        self.body.put(self.tactics_button, 27, 15, 21, 2)
        self.bind((Qt.Key.Key_X,), 'Request or cancel substitution', self.toggle_request)
        self.bind((Qt.Key.Key_T,), 'Team tactics', self.open_tactics)

    def score_pair(self, view):
        return self._score

    def set_navigation(self, enabled):
        super().set_navigation(enabled)
        self.request_button.setEnabled(False)
        self.tactics_button.setEnabled(False)

    def show_team(self):
        super().show_team()
        managed = self.snapshot.sides[self.side] == self.snapshot.managed_country
        self.tactics_button.setEnabled(managed)

    def show_view(self, view):
        super().show_view(view)
        data = view.snapshot.data
        requested = data.get('request_substitution')
        self.budget.setText(f"Substitutions left: {data['substitutions_left']}")
        self.request_button.setText('Cancel request' if requested else 'Request substitution')
        self.request_button.setEnabled(type(requested) is bool and data.get('substitutions_now') is False)
        if self._desired is not None and requested is not self._desired:
            self.status.setText('The substitution request state did not change.')
        self._desired = None
        if self.tactics_editor is not None and self.tactics_editor.pending:
            self.tactics_editor.accept_view(self._tactic_refusal)
            self._tactic_refusal = ''

    def open_tactics(self):
        if self.available() and self.tactics_button.isEnabled():
            self.tactics_editor = NativePauseTacticsScreen(self)
            self.window_.push(self.tactics_editor)

    def apply_tactic(self, editor, element, desired):
        try:
            if editor is not self.tactics_editor:
                raise ValueError('The team tactics editor no longer owns this pause.')
            self.submit({'edit_only': True, 'tactics': {element: desired}}, 'editing',
                        'Confirming the team tactic…')
        except ValueError as exc:
            editor.reject(str(exc))

    def toggle_request(self):
        if self.available() and self.request_button.isEnabled():
            desired = not self.snapshot.snapshot.data['request_substitution']
            self.submit({'edit_only': True, 'request_substitution': desired}, 'editing',
                        'Confirming substitution request…')
            self._desired = desired

    def submit(self, answer, phase, message):
        self.driver.answer_pause(self.decision, answer)
        self.phase = phase
        self.set_navigation(False)
        self.set_enter('', lambda: None)
        self.status.setText(message)

    def update_review(self):
        if self.tactics_editor not in self.window_.stack:
            self.tactics_editor = None
        if self.phase == 'editing' and not self.driver.pending:
            waiting = self.driver.waiting
            if waiting is not None and waiting['decision'] != self.decision:
                self.decision = waiting['decision']
                self.request_read()
            elif self.tactics_editor is not None and self.tactics_editor.pending:
                self._tactic_refusal = self.driver.message
                self.request_read()
            else:
                self._desired = None
                self.retry(self.driver.message)
        return super().update_review()

    def retry(self, message):
        super().retry(message)
        if self.tactics_editor is not None:
            self.tactics_editor.reject(self.status.text())
            self._tactic_refusal = ''

    def failed(self, message):
        super().failed(message)
        if self.tactics_editor is not None and self.tactics_editor in self.window_.stack:
            self.tactics_editor.reject(message)

    def exit_review(self):
        if self.available():
            self.submit({}, 'exiting', 'Continuing the match…')
