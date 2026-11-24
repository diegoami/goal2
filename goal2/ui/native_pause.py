"""[designed: T170al/#846] Request or cancel at a verified native pause."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.ui.native_review import NativeReviewScreen


class NativePauseScreen(NativeReviewScreen):
    GRID = True
    title = 'Match paused'
    primary_label = 'Play'
    statistics_phase = 'pause'

    def __init__(self, pitch, waiting):
        self._score = tuple(waiting['event']['score'])
        self._desired = None
        self.request_button = QPushButton('Request substitution')
        self.request_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.request_button.clicked.connect(self.toggle_request)
        super().__init__(pitch, waiting['decision'])
        self.body.move(self.details, 0, 8, 54, 5)
        self.budget = self.body.text('', 'sub', 0, 13, 54)
        self.body.put(self.request_button, 0, 15, 25, 2)
        self.bind((Qt.Key.Key_X,), 'Request or cancel substitution', self.toggle_request)

    def score_pair(self, view):
        return self._score

    def set_navigation(self, enabled):
        super().set_navigation(enabled)
        self.request_button.setEnabled(False)

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
        if self.phase == 'editing' and not self.driver.pending:
            waiting = self.driver.waiting
            if waiting is not None and waiting['decision'] != self.decision:
                self.decision = waiting['decision']
                self.request_read()
            else:
                self._desired = None
                self.retry(self.driver.message)
        return super().update_review()

    def exit_review(self):
        if self.available():
            self.submit({}, 'exiting', 'Continuing the match…')
