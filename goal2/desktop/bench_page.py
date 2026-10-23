"""[designed: T102] The bench of a watched match: the original's in-match players screen.

[confirmed: goal2-archaeology E031 C39-C41k, 53d7ef5; `docs/original-game/squad-and-tactics.md`
"Captain and in-match bench"; `images/squad-substitution-take-off.png`, `-put-on.png`] The
original's players screen in a match: the eleven and the bench in the strip on the right, the
selected player's card, a **substitutions left** counter, and the prompt "take off this player" on
a starter or "put on this player" on a bench player. Enter on one and Enter on one of the other
group makes a pair (either order, E031 C41e-C41i). Esc returns to the menu and **play** plays on.

[designed: T102] It is a view of the Fixtures & match page on the fixed page (T101), raised in
front when the original stops on a bench decision once the pitch view reached it. The pairs are
passed to the original as they are; the view never decides whether one is legal. The counter is the
decision's `substitutions_left`, and after **Play** the engine's own report: what it made, what it
requested for the next stoppage (at a pause) and what it refused, with the reason. With no
substitutions left the original shows "no more substitutes" [confirmed: F027 E544; E015-r0013
state 790].
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton

VIEW = 4
TITLES = {'half_time': 'HALF TIME', 'pause': 'PAUSE', 'substitution': 'SUBSTITUTION OPPORTUNITY'}
# [confirmed: the kit's Match._on_notice] At the stoppage after a pause an empty answer makes what was
# asked for; Esc there cannot cancel the request, and the bench says so (#316).
ESC_KEEPS_REQUESTED = 'Esc: the requested substitutions are still made'


def sheet():
    from goal2.desktop.style import COLORS as c
    return f"""
    QLabel#benchTitle {{font-size:30px;font-weight:700;color:{c['cyan']};}}
    QLabel#benchContext {{font-size:20px;color:{c['green']};border:2px solid {c['text']};padding:4px 10px;}}
    QLabel#benchCounter {{font-size:22px;font-weight:700;color:{c['yellow']};border:2px solid {c['text']};padding:4px 10px;}}
    QLabel#benchPrompt {{font-size:20px;color:{c['magenta']};}}
    QLabel#benchChosen {{font-size:18px;color:{c['green']};}}
    QLabel#benchMessage {{font-size:18px;font-weight:700;color:{c['green']};}}
    QLabel#benchHint {{font-size:18px;color:{c['magenta']};}}
    """


def label(name, text=''):
    widget = QLabel(text);widget.setObjectName(name);widget.setWordWrap(True)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


class Bench:
    """[designed: T102] The bench view and its state; the window owns the match."""

    def __init__(self, window):
        from goal2.desktop.roster import RosterView
        from goal2.desktop.player_card import PlayerCardView
        # decision: the waiting decision to answer; data: the one shown (kept for its report).
        self.window = window;self.decision = None;self.data = {};self.chosen = [];self.mark = None
        self.expected = None;self.report = None;self.message = ''
        view = QWidget();view.setObjectName('benchView');box = QVBoxLayout(view)
        box.setContentsMargins(0, 0, 0, 0);box.setSpacing(8)
        head = QHBoxLayout();head.setSpacing(16);box.addLayout(head)
        self.title = label('benchTitle', 'PLAYERS');self.title.setWordWrap(False)
        head.addWidget(self.title, 0, Qt.AlignmentFlag.AlignVCenter)
        self.context = label('benchContext');head.addWidget(self.context, 1, Qt.AlignmentFlag.AlignVCenter)
        self.counter = label('benchCounter');self.counter.setWordWrap(False)
        head.addWidget(self.counter, 0, Qt.AlignmentFlag.AlignVCenter)
        body = QHBoxLayout();body.setSpacing(16);box.addLayout(body, 1)
        left = QVBoxLayout();left.setSpacing(6);body.addLayout(left, 1)
        self.card = PlayerCardView();left.addWidget(self.card)
        lines = QHBoxLayout();lines.setSpacing(16);left.addLayout(lines)
        self.prompt = label('benchPrompt');self.prompt.setWordWrap(False);lines.addWidget(self.prompt, 0, Qt.AlignmentFlag.AlignTop)
        self.chosen_label = label('benchChosen');self.chosen_label.setWordWrap(False);lines.addWidget(self.chosen_label, 1)
        actions = QHBoxLayout();actions.setSpacing(12);left.addLayout(actions)
        self.play = QPushButton('Play');self.play.setObjectName('benchPlay');self.play.setAutoDefault(True)
        self.play.setAccessibleName('Play: make the chosen substitutions and play on')
        self.play.clicked.connect(self.play_on);actions.addWidget(self.play)
        self.message_label = label('benchMessage');actions.addWidget(self.message_label, 1)
        left.addStretch(1)
        self.hint = label('benchHint', 'Up/Down select  Enter take off / put on  Esc play on')
        left.addWidget(self.hint)
        self.roster = RosterView('BENCH', toggles=False, grouped=True, marks=False)
        self.roster.setObjectName('benchRoster');self.roster.setFixedWidth(320)
        self.roster.setAccessibleDescription('Up/Down: select; Enter: take off or put on this player')
        body.addWidget(self.roster, 0, Qt.AlignmentFlag.AlignTop)
        self.roster.current_changed.connect(lambda row: self.show_card())
        self.roster.activated.connect(self.enter)
        self.view = view
        stack = window.fixture_views;stack.addWidget(view)
        QWidget.setTabOrder(self.roster, self.play)
        assert stack.indexOf(view) == VIEW
        shown = stack.show_view
        stack.show_view = lambda index: self.show() if index == VIEW else shown(index)
        page = window.pages[3];escape = page.escape
        page.escape = lambda: self.escape() if stack.currentIndex() == VIEW else escape()
        from goal2.desktop.fixed_page import host, record
        frame = host(window)
        if frame is not None:
            record(frame.page);frame.restyle(frame.sheet + sheet())

    # -- what is shown --------------------------------------------------------------------------------
    @property
    def open(self):
        return self.decision is not None or self.report is not None

    def words(self):
        return list(self.data.get('eleven', [])), list(self.data.get('bench', []))

    def name(self, word):
        goaldat = self.window.model.goaldat
        initial = goaldat.player_initials[word] if word < len(goaldat.player_initials) else ''
        return (initial + ' ' if initial else '') + goaldat.player_names[word]

    def refresh(self):
        eleven, bench = self.words()
        data = self.data
        roles = {p['id']: p for p in self.window.model.view()['players']}
        off = {a for a, _ in self.chosen};on = {b for _, b in self.chosen}
        rows = []
        for word in eleven + bench:
            player = roles.get(word, {'role': '?', 'line': 'unknown'})
            # The chosen pairs: v beside a player to take off, ^ beside one to put on.
            mark = ' v' if word in off else ' ^' if word in on else ' *' if word == self.mark else ''
            rows.append((word, self.name(word) + mark, player['role'], player['line'], word in eleven, False))
        current = self.roster.current if 0 <= self.roster.current < len(rows) else 0
        self.roster.caption = self.window.model.goaldat.country_names[self.window.model.state.managed_country].upper()
        self.roster.set_rows(rows, current, unavailable=set(data.get('injured', ())))
        left = self.report['substitutions_left'] if self.report is not None else data.get('substitutions_left', 0)
        self.counter.setText('no more substitutes' if left == 0 else f'substitutions left {left}')
        self.counter.setAccessibleName(self.counter.text())
        context = data.get('context')
        self.title.setText('PLAYERS / ' + TITLES.get(context, 'BENCH'))
        self.context.setText('make substitutions now' if data.get('substitutions_now', True)
                             else 'substitutions are made at the next stoppage')
        # The strip marks each chosen pair (v off, ^ on); the line names them while they fit one line.
        names = ', '.join(f'{self.window.model.goaldat.player_names[a]} > {self.window.model.goaldat.player_names[b]}'
                          for a, b in self.chosen)
        self.chosen_label.setText(('Chosen: ' + names if len(names) <= 40 else f'Chosen: {len(self.chosen)} (v off, ^ on)')
                                  if self.chosen else 'Chosen: none')
        self.chosen_label.setAccessibleName('Chosen: ' + (names or 'none'))
        self.message_label.setText(self.message)
        self.show_card()

    def show_card(self):
        eleven, bench = self.words()
        rows = eleven + bench
        row = self.roster.current
        if not 0 <= row < len(rows):
            self.card.set_card(None);self.prompt.setText('');return
        word = rows[row]
        from goal2.game.player_card import card
        state = self.window.model.state
        try:self.card.set_card(card(state, word, self.window.model.goaldat, team_tactics=state.country_tactics))
        except (ValueError, IndexError, KeyError):self.card.set_card(None)
        # [confirmed: images/squad-substitution-take-off.png, -put-on.png] The original's prompt.
        self.prompt.setText('Enter - take off this player' if word in eleven else 'Enter - put on this player')

    # -- the route ------------------------------------------------------------------------------------
    def show(self):
        w = self.window
        w.fixture_views.setCurrentIndex(VIEW)
        if w.page_stack.currentIndex() != 3:w.navigate(3)
        w.fixture_views.setCurrentIndex(VIEW)
        self.roster.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def offer(self, decision):
        """The original stops on `decision`: raise the bench in front with its eleven and bench."""
        self.decision = decision;self.report = None;self.expected = None;self.mark = None
        self.data = data = decision.data
        # [confirmed: the kit's Match.answer] At the stoppage after a pause the default answer is
        # what was asked; the view offers it again.
        self.chosen = [list(pair) for pair in data.get('requested') or []] if data.get('context') == 'substitution' else []
        self.message = data.get('refused') or ''
        if data.get('context') == 'pause':
            self.message = self.message or 'Substitutions chosen now are made at the next stoppage.'
        if self.requested():
            self.message = (self.message + ' ' if self.message else '') + ESC_KEEPS_REQUESTED
        self.roster.current = 0
        self.refresh();self.show()
        w = self.window;w.raise_();w.activateWindow()

    def enter(self, row):
        """Enter on a player: mark him, or pair him with the marked player of the other group."""
        if self.decision is None:
            self.close();return
        eleven, bench = self.words();rows = eleven + bench
        if not 0 <= row < len(rows):return
        word = rows[row]
        if self.mark is not None and (self.mark in eleven) != (word in eleven):
            off, on = (self.mark, word) if self.mark in eleven else (word, self.mark)
            self.chosen = [p for p in self.chosen if p[0] != off and p[1] != on] + [[off, on]];self.mark = None
        else:
            self.mark = word
        self.refresh()

    def requested(self):
        """The pairs the original still makes on an empty answer: those requested at a pause, at
        the stoppage that offers them."""
        return self.data.get('requested') or [] if self.data.get('context') == 'substitution' else []

    def play_on(self):
        """Play: pass the chosen pairs to the original (none plays on, or at a stoppage with
        requested pairs makes those)."""
        if self.decision is None:
            self.close();return
        pairs = list(self.chosen)
        self.window.watched.answer(pairs)
        self.decision = None;self.chosen = [];self.mark = None
        if pairs or self.requested():
            # The original's report decides what the view says next.
            self.expected = len(self.window.watched.reports) + 1
            self.message = 'Waiting for the original…';self.refresh()
        else:
            self.close()

    def escape(self):
        """Esc: drop the choice; with nothing chosen, play on (at a stoppage with requested pairs
        the original still makes them); after a report, back to the match."""
        if self.decision is None:
            self.close();return True
        if self.chosen or self.mark is not None:
            self.chosen = [];self.mark = None;self.refresh();return True
        self.play_on();return True

    def poll(self):
        """Called with the window's watched poll: the engine's report, a new decision, the end."""
        watched = self.window.watched
        if self.expected is not None and len(watched.reports) >= self.expected:
            report = watched.reports[self.expected - 1];self.expected = None
            if report['refused']:
                self.report = report
                self.message = 'Not made: ' + '; '.join(f'{self.name(a)} for {self.name(b)}: {why}'
                                                        for a, b, why in report['refused']) + '. Press Enter.'
                self.refresh();self.show()
            elif report['requested']:
                self.close('Requested: made at the next stoppage')
            else:
                self.close()
        decision = watched.decision if watched.busy else None
        if decision is not None and decision is not self.decision:
            self.offer(decision)
        elif not watched.busy and self.open:
            self.close()

    def close(self, note=None):
        was = self.window.fixture_views.currentIndex() == VIEW
        self.decision = None;self.report = None;self.expected = None;self.chosen = [];self.mark = None;self.message = ''
        self.data = {}
        if was:
            self.window.fixture_views.setCurrentIndex(0)
        if note:self.window.status.setText(note)


# -- the core route (T108) ------------------------------------------------------------------------------------
# [designed: owner, 2026-10-22, #308, #331; decision 4] Over the core the bench is the original's SELECT TEAM at half
# time (0791:E44F in a match) with T102's look: the strip of the eleven and the bench, the selected player's card, the
# original's counter (DS:9B3A + side) or, with none left, its own line ("no more substitutes", DS:2538), and the
# prompt E2A0 draws on the selected player. Enter on one and Enter on one of the other group passes the pair to the
# original as a background job (the driver's `substitute`, its own keys); the strip and the counter are then read
# from the original again, and a refusal shows the original's message. Before the kick-off, when the original
# refused the eleven (0791:EA09), the same view is SELECT YOUR TEAM before the match: Enter, Enter swaps two players
# (`prematch_swap`). The view never decides whether a pair is legal.
class CoreBench:
    """[designed: T108] The bench view over the core; the window's CoreRound owns the round."""

    def __init__(self, window, stack):
        from goal2.desktop.roster import RosterView
        from goal2.desktop.player_card import PlayerCardView
        self.window = window;self.state = None;self.mark = None;self.mode = 'half_time';self.message = ''
        # [designed: T108] T102's parts, the head in the left column so that the strip of twenty takes the height
        view = QWidget();view.setObjectName('benchView');body = QHBoxLayout(view)
        body.setContentsMargins(0, 0, 0, 0);body.setSpacing(12)
        left = QVBoxLayout();left.setSpacing(6);body.addLayout(left, 1)
        head = QHBoxLayout();head.setSpacing(16);left.addLayout(head)
        self.title = label('benchTitle', 'PLAYERS / HALF TIME');self.title.setWordWrap(False)
        head.addWidget(self.title, 0, Qt.AlignmentFlag.AlignVCenter)
        self.context = label('benchContext');head.addWidget(self.context, 1, Qt.AlignmentFlag.AlignVCenter)
        self.counter = label('benchCounter');self.counter.setWordWrap(False)
        head.addWidget(self.counter, 0, Qt.AlignmentFlag.AlignVCenter)
        self.card = PlayerCardView(compact=True);left.addWidget(self.card)
        lines = QHBoxLayout();lines.setSpacing(12);left.addLayout(lines)
        self.prompt = label('benchPrompt');self.prompt.setWordWrap(False);lines.addWidget(self.prompt, 0, Qt.AlignmentFlag.AlignVCenter)
        self.chosen_label = label('benchChosen');self.chosen_label.setWordWrap(False);lines.addWidget(self.chosen_label, 1)
        self.play = QPushButton('Play on');self.play.setObjectName('benchPlay');self.play.setAutoDefault(True)
        self.play.setAccessibleName('Play on: the second half')
        self.play.clicked.connect(self.play_on);lines.addWidget(self.play)
        self.message_label = label('benchMessage');self.message_label.setWordWrap(False);left.addWidget(self.message_label)
        self.hint = self.message_label     # the hint goes to the strip's description (no room for a line of its own)
        left.addStretch(1)
        self.roster = RosterView('BENCH', toggles=False, grouped=True, marks=False)
        self.roster.setObjectName('benchRoster');self.roster.setFixedWidth(300)
        self.roster.setAccessibleDescription('Up/Down: select; Enter: take off or put on this player')
        body.addWidget(self.roster, 0, Qt.AlignmentFlag.AlignTop)
        self.roster.current_changed.connect(lambda row: self.show_card())
        self.roster.activated.connect(self.enter)
        self.view = view;stack.addWidget(view)
        from goal2.desktop.fixed_page import host, record
        frame = host(window)
        if frame is not None:
            record(frame.page);frame.restyle(frame.sheet + sheet())

    def words(self):
        bench = self.state['bench'] if self.state else None
        return (list(bench['eleven']), list(bench['bench'])) if bench else ([], [])

    def offer(self, state, mode):
        """Show the bench of the round's `state` (CoreModel.round_state): mode 'half_time', 'stoppage' or
        'pre_match'."""
        self.state, self.mode, self.mark = state, mode, None
        self.refresh()

    def refresh(self):
        eleven, bench = self.words()
        data = self.state['bench'] if self.state else None
        rows = []
        if data:
            by_word = {r['player']: r for r in data['squad']}
            for word in eleven + bench:
                r = by_word.get(word, {'name': '?', 'code': '?', 'line': 'unknown'})
                rows.append((word, r['name'] + (' *' if word == self.mark else ''), r['code'], r['line'], word in eleven, False))
            self.roster.caption = data['name'].upper()
        current = self.roster.current if 0 <= self.roster.current < len(rows) else 0
        self.roster.set_rows(rows, current)
        self.roster.marked = {self.mark} if self.mark else set();self.roster.update()
        if self.mode in ('half_time', 'stoppage') and data:
            # [confirmed: named/seg_0791_11.c E44F] the original's counter, or its own line when none is left
            self.counter.setText(data['message'] if data['left'] == 0 and data['message']
                                 else f"substitutions left {data['left']}")
            board = self.state.get('board') or {}
            names = board.get('names', ['', '']);score = board.get('score', [0, 0])
            self.title.setText('PLAYERS / HALF TIME' if self.mode == 'half_time' else 'PLAYERS / SUBSTITUTION')
            self.context.setText(f'{names[0].upper()} {score[0]} - {score[1]} {names[1].upper()}')
            self.play.setText('Play on');self.play.setAccessibleName('Play on: the second half')
            self.roster.setAccessibleDescription('Up/Down select; Enter take off / put on; Play on: the second half')
        else:
            self.counter.setText('before the kick-off')
            self.title.setText('PLAYERS / SELECT YOUR TEAM')
            self.context.setText(self.state.get('refused') or '' if self.state else '')
            self.play.setText('< Captain and kick-off');self.play.setAccessibleName('Back to the captain and the kick-off')
            self.roster.setAccessibleDescription('Up/Down select; Enter, Enter swaps two players (the original\'s keys)')
        self.counter.setAccessibleName(self.counter.text())
        self.message_label.setText(self.message)
        self.show_card()

    def show_card(self):
        from goal2.desktop.player_card import core_card
        eleven, bench = self.words();rows = eleven + bench
        row = self.roster.current
        if not 0 <= row < len(rows):
            self.card.set_card(None);self.prompt.setText('');return
        word = rows[row]
        try:self.card.set_card(core_card(self.window.model.card(word)))
        except (ValueError, IndexError, KeyError):self.card.set_card(None)
        if self.mode in ('half_time', 'stoppage'):
            # [confirmed: named/seg_0791_11.c E2A0; images/squad-substitution-take-off.png, -put-on.png]
            self.prompt.setText('Enter - take off this player' if word in eleven else 'Enter - put on this player')
        else:
            self.prompt.setText('Enter - move player')
        self.chosen_label.setText(f'Marked: {self.window.model.card(self.mark)["name"]}' if self.mark else 'Marked: none')

    def enter(self, row):
        """Enter on a player: mark him; Enter on another passes the pair to the original."""
        eleven, bench = self.words();rows = eleven + bench
        if not 0 <= row < len(rows) or self.window.core_jobs.busy:return
        word = rows[row]
        if self.mark is None or self.mark == word:
            self.mark = None if self.mark == word else word;self.refresh();return
        first, self.mark = self.mark, None
        if self.mode in ('half_time', 'stoppage'):
            off, on = (first, word) if first in eleven else (word, first)
            self.message = 'The original is making it…'
            self.window.run_core('substitute', off, on)
        else:
            self.message = 'The original is moving them…'
            self.window.run_core('prematch_swap', first, word)
        self.refresh()

    def play_on(self):
        if self.window.core_jobs.busy:return
        if self.mode in ('half_time', 'stoppage'):
            self.window.core_round.start_play_on()
        else:
            self.window.core_round.show_captain()

    def escape(self):
        if self.mark is not None:
            self.mark = None;self.refresh();return True
        if self.mode == 'pre_match':
            self.window.core_round.show_captain();return True
        return False
