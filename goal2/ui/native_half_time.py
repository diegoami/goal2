"""[designed: T170aj/T170an] Immediate guarded edits at a retained bench stop."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.game.country_card import PLAYER_DEFAULTS, TEAM_TACTICS, card
from goal2.ui.native_review import NativeReviewScreen


class NativeBenchScreen(NativeReviewScreen):
    GRID = True

    def __init__(self, pitch, waiting):
        self.controls = []
        self.outgoing = None
        self._score = tuple(waiting['event']['score'])
        self._edit_cursor = pitch.controller.driver.shown_count
        super().__init__(pitch, waiting['decision'])
        self.body.move(self.details, 0, 8, 54, 5)
        self.budget = self.body.text('', 'sub', 0, 4, 54)
        self.substitute = self.add_action('Substitute', 0, 15, 23, Qt.Key.Key_X, self.substitution)
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

    def show_team(self):
        super().show_team()
        self.refresh_controls()

    def refresh_controls(self):
        data = self.snapshot.snapshot.data
        remaining = data['substitutions_left']
        self.budget.setText(f'Substitutions left: {remaining}')
        legal = self.snapshot.sides[self.side] == self.snapshot.managed_country and data['substitutions_now'] is True
        self.substitute.setEnabled(legal and remaining > 0)
        self.substitute.setText('Choose outgoing' if self.outgoing is None else 'Make substitution')

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

    def apply_edit(self, edit):
        self._edit_cursor += len(self.driver.events_since(self._edit_cursor))
        try:
            self.submit({'edit_only': True, **edit})
        except ValueError as exc:
            self.status.setText(str(exc))
            return
        self.phase = 'editing'
        self.set_navigation(False)
        self.set_enter('', lambda: None)
        self.status.setText(self.edit_message)

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
        refusal = refusal or view.snapshot.data.get('refused')
        if refusal:
            self.status.setText(refusal)

    def exit_review(self):
        if self.available():
            self.submit({})
            self.phase = 'exiting'
            self.set_navigation(False)
            self.set_enter('', lambda: None)
            self.status.setText(self.play_message)


class NativeHalfTimeScreen(NativeBenchScreen):
    GRID = True
    title = 'Half-time'
    primary_label = 'Play second half'
    statistics_phase = 'half'
    edit_message = 'Applying half-time change…'
    play_message = 'Starting the second half…'

    def __init__(self, pitch, waiting):
        self.element = 1
        super().__init__(pitch, waiting)
        self.tactic = self.body.text('', 'sub', 0, 13, 54)
        self.next_button = self.add_action('Next tactic', 25, 15, 13, Qt.Key.Key_T, self.next_tactic)
        self.toggle_button = self.add_action('Toggle tactic', 39, 15, 15, Qt.Key.Key_G, self.toggle_tactic)
        self.set_navigation(False)

    def refresh_controls(self):
        super().refresh_controls()
        data = self.snapshot.snapshot.data
        legal = self.snapshot.sides[self.side] == self.snapshot.managed_country and data['substitutions_now'] is True
        self.next_button.setEnabled(legal)
        self.toggle_button.setEnabled(legal)
        team = card(self.state, self.snapshot.managed_country, self.data)
        names = {element: name for name, element in PLAYER_DEFAULTS + TEAM_TACTICS}
        name = names[self.element]
        values = dict(team['player_defaults'] + team['team_tactics'])
        self.tactic.setText(f'{name.capitalize()}: {values[name]}')

    def next_tactic(self):
        if self.available() and self.next_button.isEnabled():
            self.element = self.element % 8 + 1
            self.refresh_controls()

    def toggle_tactic(self):
        if self.available() and self.toggle_button.isEnabled():
            mask = 1 << (self.element - 1)
            self.apply_edit({'tactics': {self.element: not bool(self.snapshot.snapshot.data['tactics'] & mask)}})

    def submit(self, answer):
        self.driver.answer_half_time(answer)


class NativeSubstitutionScreen(NativeBenchScreen):
    GRID = True
    title = 'Substitutions'
    primary_label = 'Play'
    statistics_phase = 'stop'
    edit_message = 'Confirming the substitution…'
    play_message = 'Continuing the match…'

    def submit(self, answer):
        self.driver.answer_substitution(self.decision, answer)
