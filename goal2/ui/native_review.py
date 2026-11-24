"""[designed: T170ai/#840] Live read-only review for the retained native pitch."""

from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from goal2.game.country_card import card as country_card
from goal2.game.player_card import card as player_card
from goal2.game.roles import role
from goal2.ui.cell_parts import GridStrip
from goal2.ui.cells import CellPara, Cells
from goal2.ui.s20_board import BoardScreen, board
from goal2.ui.screen import Screen


class NativeReviewScreen(Screen):
    GRID = True
    title = 'Post-match review'
    escape_text = None
    primary_label = 'Exit review'
    statistics_phase = 'full'

    def __init__(self, pitch, decision):
        super().__init__(pitch.window_)
        self.pitch = pitch
        self.driver = pitch.controller.driver
        self.decision = decision
        self.phase = 'loading'
        self.snapshot = None
        self.side = self.row = 0
        self.state = None
        self.players = ()
        self.names = ()
        self.data = pitch.model.goaldat

        body = self.body = Cells(90, 25, 'nativeReviewBody')
        self.body_layout.addWidget(body, 1)
        self.score = body.text('', 'h1', 0, 0, 90)
        self.team = body.text('', 'sub', 0, 3, 54)
        self.player = body.text('', 'h1', 0, 6, 54)
        self.details = CellPara('', 'value')
        body.put(self.details, 0, 8, 54, 10)
        self.status = CellPara('', 'sub')
        body.put(self.status, 0, 20, 54, 3)
        self.team_button = QPushButton('Switch team')
        self.stats_button = QPushButton('Statistics')
        for button, action, column in ((self.team_button, self.switch_team, 0),
                                       (self.stats_button, self.show_statistics, 25)):
            button.clicked.connect(action)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            body.put(button, column, 17, 23, 2)
        self.roster = GridStrip(cols=33)
        self.roster.chosen.connect(self.select_player)
        body.put(self.roster, 57, 1, 33, 22)
        self.roster.hide()
        self.set_navigation(False)
        self.bind((Qt.Key.Key_Left, Qt.Key.Key_Right), 'Switch team', self.switch_team,
                  captions=('←', '→'))
        self.bind((Qt.Key.Key_Up,), 'Previous player', lambda: self.step_player(-1))
        self.bind((Qt.Key.Key_Down,), 'Next player', lambda: self.step_player(1))
        self.bind((Qt.Key.Key_S,), 'Statistics', self.show_statistics)
        self.request_read()

    def set_navigation(self, enabled):
        self.team_button.setEnabled(enabled)
        self.stats_button.setEnabled(enabled)
        self.roster.setEnabled(enabled)

    def request_read(self):
        if not self.waiting_here():
            return
        self.driver.request_view()
        self.phase = 'loading'
        self.status.setText('Reading the current match records…')
        self.set_enter('', lambda: None)

    def waiting_here(self):
        waiting = self.driver.waiting
        return waiting is not None and waiting['decision'] == self.decision

    def update_review(self):
        if self.phase == 'exiting' and not self.driver.pending:
            if self.waiting_here():
                self.retry(self.driver.message)
            else:
                self.phase = 'finished'
        if self.phase == 'finished':
            if self.window_.current() is self:
                self.window_.pop()
                return True
            return False
        if self.phase == 'loading' and not self.driver.pending:
            view = self.driver.stopped_view
            if view is not None and self.waiting_here() and view.snapshot.decision == self.decision:
                self.show_view(view)
            elif self.waiting_here():
                self.retry(self.driver.message)
        return False

    def retry(self, message):
        self.phase = 'retry'
        self.snapshot = None
        self.set_navigation(False)
        self.status.setText(message or 'The current review could not be read.')
        self.set_enter('Retry review', self.request_read)

    def failed(self, message):
        self.phase = 'failed'
        self.snapshot = None
        self.set_navigation(False)
        self.status.setText(message)
        self.set_enter('Back to pitch', self.window_.pop)

    def show_view(self, view):
        self.snapshot = view
        self.state = view.display_state(self.pitch.model.state)
        self.names = tuple(self.data.country_names[country] for country in view.sides)
        left, right = self.score_pair(view)
        self.score.setText(f'{self.names[0]} {left}–{right} {self.names[1]}')
        self.phase = 'ready'
        self.set_navigation(True)
        self.status.clear()
        self.set_enter(self.primary_label, self.exit_review)
        self.show_team()

    def score_pair(self, view):
        return view.snapshot.data['board']['final_score']

    def available(self):
        return (self.phase == 'ready' and self.waiting_here()
                and self.driver.stopped_view is self.snapshot and self.window_.current() is self)

    def escape(self):
        # Exit uses the labelled control, including when the player presses Esc twice.
        pass

    def show_team(self):
        country = self.snapshot.sides[self.side]
        team = country_card(self.state, country, self.data, performance_context=self.snapshot.team_context)
        self.players = tuple(team['players'])
        self.team.setText(f"{team['name']}   Formation {team['formation']}")
        rows = [
            (*role(self.state, self.state.players[word][6]), self.data.player_names[word])
            if word else ('', None, 'Vacant')
            for word in self.players
        ]
        self.roster.show_rows(team['name'], rows, self.row)
        self.roster.show()
        self.show_player()

    def show_player(self):
        word = self.players[self.row]
        if not word:
            self.player.setText('Vacant')
            self.details.clear()
            return
        player = player_card(self.state, word, self.data)
        self.player.setText(player['full_name'])
        performance = str(player['performance_bar']) + '/9' if player['performance'] is not None else 'Unavailable'
        lines = [player['position'], player['readiness'].capitalize(), f'Performance {performance}']
        self.details.setText('\n'.join(lines))

    def select_player(self, row):
        if self.available() and 0 <= row < len(self.players):
            self.row = row
            for i, item in enumerate(self.roster.rows):
                item.set_on(i == row)
            self.show_player()

    def step_player(self, amount):
        self.select_player(self.row + amount)

    def switch_team(self):
        if self.available():
            self.side = 1 - self.side
            self.row = 0
            self.show_team()

    def show_statistics(self):
        if self.available():
            controller = self.pitch.controller
            state = SimpleNamespace(goaldat=self.data, state=self.state)
            phase = self.statistics_phase
            stats = BoardScreen(self.window_, state, self.names, controller.display.kind,
                                phase, board(controller.shown(), phase, False),
                                lambda _: self.window_.pop(), controller.kits)
            self.window_.push(stats)

    def exit_review(self):
        if self.available():
            self.pitch.answer_native(self.decision, {'post_match_exit': True})
            self.phase = 'exiting'
            self.set_navigation(False)
            self.status.setText('Continuing the match…')
            self.set_enter('', lambda: None)
