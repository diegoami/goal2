"""[designed: T170aj/#842] Immediate guarded edits at a retained half-time stop."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.game.country_card import PLAYER_DEFAULTS, TEAM_TACTICS, card
from goal2.ui.native_review import NativeReviewScreen


class NativeHalfTimeScreen(NativeReviewScreen):
    GRID = True
    title = 'Half-time'
    primary_label = 'Play second half'
    statistics_phase = 'half'

    def __init__(self, pitch, waiting):
        self.controls = []
        self.outgoing = None
        self.element = 1
        self._score = tuple(waiting['event']['score'])
        self._edit_cursor = pitch.controller.driver.shown_count
        super().__init__(pitch, waiting['decision'])
        self.body.move(self.details, 0, 8, 54, 5)
        self.budget = self.body.text('', 'sub', 0, 4, 54)
        self.tactic = self.body.text('', 'sub', 0, 13, 54)
        self.substitute = self.add_action('Substitute', 0, 15, 23, Qt.Key.Key_X, self.substitution)
        self.add_action('Next tactic', 25, 15, 13, Qt.Key.Key_T, self.next_tactic)
        self.add_action('Toggle tactic', 39, 15, 15, Qt.Key.Key_G, self.toggle_tactic)
        self.set_navigation(False)

    def add_action(self, label, col, row, width, key, action):
        button = QPushButton(label)
        button.clicked.connect(action)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.body.put(button, col, row, width, 2)
        self.bind((key,), label, action)
        self.controls.append(button)
        return button

    def score_pair(self, view):
        return self._score

    def set_navigation(self, enabled):
        super().set_navigation(enabled)
        for button in self.controls:
            button.setEnabled(False)
        if enabled and self.controls:
            self.refresh_controls()

    def show_team(self):
        super().show_team()
        self.refresh_controls()

    def refresh_controls(self):
        data = self.snapshot.snapshot.data
        remaining = data['substitutions_left']
        self.budget.setText(f'Substitutions left: {remaining}')
        legal = self.snapshot.sides[self.side] == self.snapshot.managed_country and data['substitutions_now'] is True
        self.substitute.setEnabled(legal and remaining > 0)
        self.controls[1].setEnabled(legal)
        self.controls[2].setEnabled(legal)
        self.substitute.setText('Choose outgoing' if self.outgoing is None else 'Make substitution')
        team = card(self.state, self.snapshot.managed_country, self.data)
        names = {element: name for name, element in PLAYER_DEFAULTS + TEAM_TACTICS}
        name = names[self.element]
        values = dict(team['player_defaults'] + team['team_tactics'])
        self.tactic.setText(f'{name.capitalize()}: {values[name]}')

    def switch_team(self):
        if self.available():
            self.outgoing = None
        super().switch_team()

    def substitution(self):
        if not self.available() or not self.substitute.isEnabled():
            return
        word = self.players[self.row]
        if 0 <= self.row < 11 and word:
            self.outgoing = word
            self.status.setText('Select an available bench player and make the substitution.')
            self.refresh_controls()
        elif self.outgoing is not None and word:
            self.apply_edit({'substitutions': [[self.outgoing, word]]})

    def next_tactic(self):
        if self.available() and self.controls[1].isEnabled():
            self.element = self.element % 8 + 1
            self.refresh_controls()

    def toggle_tactic(self):
        if self.available() and self.controls[2].isEnabled():
            mask = 1 << (self.element - 1)
            self.apply_edit({'tactics': {self.element: not bool(self.snapshot.snapshot.data['tactics'] & mask)}})

    def apply_edit(self, edit):
        self._edit_cursor += len(self.driver.events_since(self._edit_cursor))
        try:
            self.driver.answer_half_time({'edit_only': True, **edit})
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.phase = 'editing'
        self.set_navigation(False)
        self.set_enter('', lambda: None)
        self.status.setText('Applying half-time change…')

    def update_review(self):
        if self.phase == 'editing' and not self.driver.pending:
            waiting = self.driver.waiting
            if waiting is not None and waiting['decision'] != self.decision:
                self.decision = waiting['decision']
                self.outgoing = None
                self.request_read()
            else:
                self.retry(self.driver.message)
        return super().update_review()

    def show_view(self, view):
        super().show_view(view)
        events = self.driver.events_since(self._edit_cursor)
        refusal = next((event['data']['reason'] for event in reversed(events) if event['kind'] == 'refused'), None)
        if refusal:
            self.status.setText(refusal)

    def exit_review(self):
        if self.available():
            self.driver.answer_half_time({})
            self.phase = 'exiting'
            self.set_navigation(False)
            self.set_enter('', lambda: None)
            self.status.setText('Starting the second half…')
