"""[designed: T170aj/T170an] Immediate guarded edits at a retained bench stop."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.game.country_card import PLAYER_DEFAULTS, TEAM_TACTICS, card
from goal2.ui.native_review import NativeReviewScreen


class NativeEditableStopScreen(NativeReviewScreen):
    GRID = True
    uses_substitutions = False

    def __init__(self, pitch, waiting):
        self.controls = []
        self.outgoing = None
        self._edited_player = None
        self.own_editor = None
        self._own_refusal = ''
        self._score = tuple(waiting['event']['score'])
        self._edit_cursor = pitch.controller.driver.shown_count
        super().__init__(pitch, waiting['decision'])
        self.body.move(self.details, 0, 8, 54, 5)
        if self.uses_substitutions:
            self.budget = self.body.text('', 'sub', 0, 4, 54)
            self.substitute = self.add_action('Substitute', 0, 15, 23, Qt.Key.Key_X, self.substitution)
            self.body.move(self.status, 0, 21, 54, 3)
            self.next_position = self.add_action('Next position', 0, 19, 17, Qt.Key.Key_R,
                                                 lambda: self.change_position(club=False))
            self.club_position = self.add_action('Club position', 18, 19, 17, Qt.Key.Key_C,
                                                 lambda: self.change_position(club=True))
            self.own_tactics = self.add_action('Own tactics', 36, 19, 17, Qt.Key.Key_T, self.open_own_tactics)
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
        if self._edited_player in self.snapshot.squad:
            self.row = self.snapshot.squad.index(self._edited_player)
        super().show_team()
        self.refresh_controls()

    def player_details(self, player):
        details = super().player_details(player)
        if self.uses_substitutions:
            details.append(f"Club position: {player['club_position']}")
        return details

    def select_player(self, row):
        super().select_player(row)
        if self.uses_substitutions and self.available():
            self.refresh_controls()

    def refresh_controls(self):
        if not self.uses_substitutions:
            return
        data = self.snapshot.snapshot.data
        remaining = data['substitutions_left']
        self.budget.setText(f'Substitutions left: {remaining}')
        legal = self.snapshot.sides[self.side] == self.snapshot.managed_country and data['substitutions_now'] is True
        self.substitute.setEnabled(legal and remaining > 0)
        self.substitute.setText('Choose outgoing' if self.outgoing is None else 'Make substitution')
        word = self.players[self.row]
        record = self.snapshot.record(word)
        self.next_position.setEnabled(legal and word != 0 and record[6] < 14)
        self.club_position.setEnabled(legal and word != 0 and record[7] < 14)
        self.own_tactics.setEnabled(legal and word != 0)

    def open_own_tactics(self):
        if self.available() and self.own_tactics.isEnabled():
            from goal2.ui.native_player_tactics import NativePlayerTacticsScreen
            self.own_editor = NativePlayerTacticsScreen(self, self.players[self.row])
            self.window_.push(self.own_editor)

    def change_position(self, *, club):
        control = self.club_position if club else self.next_position
        if not self.available() or not control.isEnabled():
            return
        word = self.players[self.row]
        record = self.snapshot.record(word)
        target = record[7] if club else (record[6] + 1) % 14
        if self.apply_edit({'positions': {word: target}}):
            self._edited_player = word

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
            return False
        self.phase = 'editing'
        self.set_navigation(False)
        self.set_enter('', lambda: None)
        self.status.setText(self.edit_message)
        return True

    def update_review(self):
        if self.own_editor not in self.window_.stack:
            self.own_editor = None
        if self.phase == 'editing' and not self.driver.pending:
            waiting = self.driver.waiting
            if waiting is not None and waiting['decision'] != self.decision:
                self.decision = waiting['decision']
                self.outgoing = None
                self.request_read()
            elif self.own_editor is not None and self.own_editor.pending:
                self._own_refusal = self.driver.message or 'The player tactic was refused.'
                self.request_read()
            else:
                self.retry(self.driver.message)
        return super().update_review()

    def show_view(self, view):
        super().show_view(view)
        self._edited_player = None
        events = self.driver.events_since(self._edit_cursor)
        refusal = next((event['data']['reason'] for event in reversed(events) if event['kind'] == 'refused'), None)
        refusal = refusal or view.snapshot.data.get('refused')
        if refusal:
            self.status.setText(refusal)
        if self.own_editor is not None and self.own_editor.pending:
            self.own_editor.acknowledge(self._own_refusal or refusal)
            self._own_refusal = ''

    def retry(self, message):
        super().retry(message)
        if self.own_editor is not None:
            self.own_editor.rejected(self.status.text())
            self._own_refusal = ''

    def failed(self, message):
        super().failed(message)
        if self.own_editor is not None and self.own_editor in self.window_.stack:
            self.own_editor.rejected(message)

    def exit_review(self):
        if self.available():
            self.submit({})
            self.phase = 'exiting'
            self.set_navigation(False)
            self.set_enter('', lambda: None)
            self.status.setText(self.play_message)


class NativeTacticStopScreen(NativeEditableStopScreen):
    GRID = True
    next_tactic_key = Qt.Key.Key_T

    def __init__(self, pitch, waiting):
        self.element = 1
        super().__init__(pitch, waiting)
        self.tactic = self.body.text('', 'sub', 0, 13, 54)
        self.next_button = self.add_action('Next tactic', 25, 15, 13, self.next_tactic_key, self.next_tactic)
        self.toggle_button = self.add_action('Toggle tactic', 39, 15, 15, Qt.Key.Key_G, self.toggle_tactic)
        self.set_navigation(False)

    def refresh_controls(self):
        super().refresh_controls()
        data = self.snapshot.snapshot.data
        legal = (self.snapshot.sides[self.side] == self.snapshot.managed_country
                 and self.tactics_available(data))
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


class NativeHalfTimeScreen(NativeTacticStopScreen):
    GRID = True
    uses_substitutions = True
    next_tactic_key = Qt.Key.Key_Y
    title = 'Half-time'
    primary_label = 'Play second half'
    statistics_phase = 'half'
    edit_message = 'Applying half-time change…'
    play_message = 'Starting the second half…'

    def tactics_available(self, data):
        return data['substitutions_now'] is True

    def submit(self, answer):
        self.driver.answer_half_time(answer)


class NativeSubstitutionScreen(NativeEditableStopScreen):
    GRID = True
    uses_substitutions = True
    title = 'Substitutions'
    primary_label = 'Play'
    statistics_phase = 'stop'
    edit_message = 'Confirming the substitution…'
    play_message = 'Continuing the match…'

    def submit(self, answer):
        self.driver.answer_substitution(self.decision, answer)


class NativeExtraTimeScreen(NativeTacticStopScreen):
    GRID = True
    statistics_phase = 'extra'
    edit_message = 'Confirming the extra-time tactic…'
    play_message = 'Continuing to the next period…'

    def __init__(self, pitch, waiting):
        from goal2.game.half_time_edit import extra_time_half
        half = extra_time_half(waiting['event']['data'])
        self.title, self.primary_label = (
            ('Extra time', 'Play extra time') if half == 1
            else ('Extra-time half-time', 'Play second half of extra time')
        )
        super().__init__(pitch, waiting)

    def tactics_available(self, data):
        return True  # [confirmed: #679/#680] Neither half needs a legal substitution.

    def submit(self, answer):
        self.driver.answer_extra_time(self.decision, answer)
