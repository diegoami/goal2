"""[designed: owner, 2026-10-22, #308, #321; T105] The main window over the core.

The same shell as the Python route's window (goal2/desktop/pages.py: the top bar, the side bar with the five
destinations, one fixed page of 1440x900 scaled to the window, T101), over a `CoreModel`
(goal2/desktop/core_model.py) instead of the Python route's `DesktopModel`. The Country page shows the manager's
desk and the history, the Fixtures & match page the fixture list and the tournament (their builders are in
overview_page.py and fixtures_page.py), the Team page the squad, the card and the tactics and the Pool page the pool
(squad_page.py and pool_page.py, T107: each edit a driver action run as a background job); play next game runs the
original's round (T108: fixtures_page.CoreRound, bench_page.CoreBench) and never falls back to the Python route; the
Save page writes the core save.

`TextBoard` paints a board of coloured text in the original's own structure (its 80-column boards: the fixture
list's rows, a group table, the history's boxes), in page pixels through the page's scale, as the roster and the
cards are painted (T101).
"""
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QPushButton, QVBoxLayout,
                               QWidget)

from goal2.desktop.player_card import BLACK, CYAN, GREY, RED

# [designed: T105] The board's type: the original's text page is 80 columns; a board of 80 columns at 15 px
# DejaVu Sans Mono is about 725 page pixels wide.
BOARD_FONT, LINE_HEIGHT = 15, 19


def board_font(size=BOARD_FONT, bold=False):
    """The bundled DejaVu Sans Mono (goal2/desktop/fonts): registered first, so that a board measured before the
    window's style is applied is measured in it, not in a platform fallback ([designed: T105], found by the Windows
    workflow, #278: Windows has no DejaVu, and a fallback's wider advance made the boards wider than the page)."""
    from goal2.desktop.style import load_fonts
    load_fonts()
    font = QFont('DejaVu Sans Mono');font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPixelSize(size);font.setBold(bold)
    return font


class TextBoard(QWidget):
    """A framed board of `rows` lines of `columns` characters; `set_lines([[(text, colour), ...], ...])`.
    `title` is drawn in red on the frame. The accessible name holds the board's plain text."""
    page_painted = True

    def __init__(self, title, columns, rows, name, size=BOARD_FONT):
        super().__init__()
        self.title, self.columns, self.rows_, self.font_size = title, columns, rows, size
        self.lines = [];self.setObjectName(name);self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.char = QFontMetricsF(board_font(size)).horizontalAdvance('M')

    def scale(self):
        from goal2.desktop.fixed_page import scale_of
        return scale_of(self)

    def page_size(self):
        return QSize(round(self.columns * self.char) + 24, (self.rows_ + 1) * LINE_HEIGHT + 22)

    def sizeHint(self):
        s = self.scale();size = self.page_size()
        return QSize(round(size.width() * s), round(size.height() * s))

    def minimumSizeHint(self):
        return self.sizeHint()

    def text(self):
        return '\n'.join(''.join(t for t, _ in line) for line in self.lines)

    def set_lines(self, lines):
        self.lines = [list(line) for line in lines][:self.rows_]
        self.setAccessibleName(f'{self.title}\n{self.text()}')
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self);painter.fillRect(self.rect(), QColor(BLACK))
        s = self.scale();painter.scale(s, s)
        width, height = self.width() / s, self.height() / s
        painter.setPen(QColor(CYAN));painter.drawRect(1, 8, round(width) - 3, round(height) - 10)
        title = board_font(self.font_size + 1, True);painter.setFont(title)
        painter.fillRect(10, 0, round(QFontMetricsF(title).horizontalAdvance(self.title)) + 8, 18, QColor(BLACK))
        painter.setPen(QColor(RED));painter.drawText(14, 14, self.title)
        painter.setFont(board_font(self.font_size))
        for row, line in enumerate(self.lines):
            x, y = 12.0, 18 + (row + 1) * LINE_HEIGHT
            for text, colour in line:
                painter.setPen(QColor(colour));painter.drawText(round(x), y, text)
                x += len(text) * self.char
        painter.end()


class CoreWindow(QMainWindow):
    """[designed: T105] The management window over a CoreModel."""

    def __init__(self, model):
        super().__init__();self.model = model
        from goal2.desktop.pages import DESTINATIONS, ShellPage
        from goal2.desktop.style import apply_style
        from goal2.desktop.core_model import DISABLED, DISABLED_TEXT
        self.setWindowTitle('goal2 — the original');self.resize(1440, 900)
        root = QWidget();root.setObjectName('shellRoot');layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8);layout.setSpacing(8)
        # The top bar: GOAL2, the country, the manager and the year, the next fixture.
        self.top_bar = QFrame();self.top_bar.setObjectName('topBar');top = QHBoxLayout(self.top_bar)
        top.setContentsMargins(14, 6, 14, 6);top.setSpacing(20)
        brand = QLabel('GOAL2');brand.setObjectName('brand');top.addWidget(brand, 0, Qt.AlignmentFlag.AlignVCenter)
        self.title = QLabel();self.title.setObjectName('countryTitle');top.addWidget(self.title, 2)
        self.career_line = QLabel();self.career_line.setObjectName('careerLine');self.career_line.setWordWrap(True)
        top.addWidget(self.career_line, 3)
        right = QVBoxLayout();right.setSpacing(2);top.addLayout(right, 3)
        self.next_line = QLabel();self.next_line.setObjectName('nextLine');self.next_line.setWordWrap(True)
        self.next_detail = QLabel();self.next_detail.setObjectName('nextDetail');self.next_detail.setWordWrap(True)
        right.addWidget(self.next_line);right.addWidget(self.next_detail)
        layout.addWidget(self.top_bar)
        body = QHBoxLayout();body.setSpacing(8);layout.addLayout(body, 1)
        self.side_bar = QFrame();self.side_bar.setObjectName('sideBar');side = QVBoxLayout(self.side_bar)
        side.setContentsMargins(8, 8, 8, 8);side.setSpacing(10)
        from PySide6.QtWidgets import QStackedWidget
        self.page_stack = QStackedWidget();self.page_stack.setObjectName('pageStack')
        self.pages = [ShellPage(name, i) for i, name in enumerate(DESTINATIONS)]
        self.navigation = [];self.navigation_shortcuts = []
        # [designed: T107] Team and Pool are served by the core (G12); only play next game waits (G14).
        unavailable = {}
        for i, name in enumerate(DESTINATIONS):
            label = name if i not in unavailable else f'{name} · {DISABLED[unavailable[i]]}'
            button = QPushButton(label.replace('&', '&&'));button.setObjectName(f'nav{i + 1}')
            button.setAccessibleName(label);button.setCheckable(True)
            button.clicked.connect(lambda checked=False, index=i: self.navigate(index))
            if i in unavailable:
                button.setEnabled(False);button.setToolTip(DISABLED_TEXT[unavailable[i]])
                button.setAccessibleDescription(DISABLED_TEXT[unavailable[i]])
            side.addWidget(button);self.navigation.append(button);self.page_stack.addWidget(self.pages[i])
            shortcut = QShortcut(QKeySequence(f'Ctrl+{i + 1}'), self)
            shortcut.activated.connect(lambda index=i: self.navigate(index));self.navigation_shortcuts.append(shortcut)
        side.addStretch(1)
        body.addWidget(self.side_bar)
        main = QVBoxLayout();main.setSpacing(8);body.addLayout(main, 1)
        main.addWidget(self.page_stack, 1)
        self.status = QLabel('The original game runs as the core; its screens are read from its memory.')
        self.status.setObjectName('status');self.status.setWordWrap(True);main.addWidget(self.status)
        from goal2.desktop import overview_page, fixtures_page, squad_page, pool_page
        from goal2.desktop.core_model import CoreJobs
        overview_page.build_core(self, model)
        squad_page.build_core(self, model)
        pool_page.build_core(self, model)
        fixtures_page.build_core(self, model)
        self._build_save()
        # [designed: T107, T65's pattern] Team actions run off the window's thread; a timer collects the result.
        from PySide6.QtCore import QTimer
        self.core_jobs = CoreJobs(model)
        self.core_timer = QTimer(self);self.core_timer.setInterval(30);self.core_timer.timeout.connect(self.poll_core)
        self.core_actions = [b for b in self.core_team_buttons.values()] + [self.rename, self.pool_move,
                                                                            self.pool_switch] + \
            [row for _, row in self.tactics] + self.own_tactics + [self.own_marking] + self.core_round.buttons + \
            [self.core_routes['play next game']] + self.core_pool_compare_actions
        for page in self.pages:page.content.addStretch()
        if self.model.in_round:                         # [T108] a core saved in a round resumes on its page
            from PySide6.QtCore import QTimer as _T
            _T.singleShot(0, self.resume_round)
        self.save_shortcut = QShortcut(QKeySequence('Ctrl+S'), self);self.save_shortcut.activated.connect(self.save.click)
        self.original_save_shortcut = QShortcut(QKeySequence('F7'), self)
        self.original_save_shortcut.activated.connect(self.begin_save_name)
        from goal2.desktop.fixed_page import FixedPage
        from goal2.desktop.bulletin_page import sheet as bulletin_sheet
        from goal2.desktop.style import COLORS
        sheet = apply_style(self) + bulletin_sheet(frame=COLORS['cyan'], masthead=COLORS['yellow'],
            text=COLORS['text'], hint=COLORS['magenta'], story_size=22, masthead_size=22)
        sheet += '\nQFrame#sideBar QPushButton#coreShowMatch { min-height:44px; font-weight:700; }'
        # [designed: owner #456/T139] Included before FixedPage records/scales the sheet.
        sheet += '\nQLabel#benchIntervalNotice { font-size:24px; font-weight:700; color:' + COLORS['yellow'] + '; }'
        self.setStyleSheet(sheet);self.setCentralWidget(FixedPage(root, sheet, self))
        self.refresh();self.navigate(4 if self.model.in_save_name else 0)
        self.refresh_save_controls()

    def _build_save(self):
        """[designed: T105] The Save page: the core save (F7 in the original), resumed with --resume."""
        page = self.pages[4]
        bar = QHBoxLayout();bar.addWidget(QLabel('Core save'))
        self.path = QLineEdit(str(self.model.save_path));self.path.setObjectName('savePath')
        self.path.setAccessibleName('Core save file');bar.addWidget(self.path, 1)
        self.save = QPushButton('Save (F7)');self.save.setObjectName('save');self.save.setAccessibleName('Save the core')
        self.save.clicked.connect(self.save_core);bar.addWidget(self.save)
        self.cancel_save = QPushButton('Cancel');self.cancel_save.setObjectName('cancelOriginalSave')
        self.cancel_save.clicked.connect(self.cancel_save_name);bar.addWidget(self.cancel_save)
        page.content.addLayout(bar)
        note = QLabel('Resume it with: python3 -m goal2.desktop --resume <core save> --data <GOAL.DAT>')
        note.setObjectName('deskCampaign');note.setWordWrap(True);page.content.addWidget(note)

    def save_core(self):
        if self.core_jobs.busy:
            self.status.setText('Wait for the current core action before saving');return False
        try:
            quitting = self.model.in_save_name and self.model.core.wait.view['quit']
            target = self.model.save(self.path.text().strip() or None)
        except ValueError as exc:
            self.refresh_save_controls()
            self.status.setText(str(exc));return False
        self.path.setText(str(target));self.status.setText(f'Core saved to {target}')
        if quitting:
            self.close()
        else:
            self.refresh();self.refresh_save_controls()
        return True

    def cancel_save_name(self):
        """[designed: T121] Cancel writes nothing; terminal quit closes without executing teardown."""
        if self.core_jobs.busy:
            self.status.setText('Wait for the current core action before cancelling');return False
        try:
            quitting = self.model.in_save_name and self.model.core.wait.view['quit']
            self.model.resolve_save_name(False)
        except ValueError as exc:
            self.status.setText(str(exc));return False
        if quitting:
            self.close()
        else:
            self.refresh();self.refresh_save_controls();self.navigate(0)
        return True

    def begin_save_name(self):
        if self.core_jobs.busy:
            self.status.setText('Wait for the current core action before opening Save');return False
        try:
            self.model.begin_save_name()
        except ValueError as exc:
            self.status.setText(str(exc));return False
        self.navigate(4);self.refresh_save_controls()
        return True

    def refresh_save_controls(self):
        pending = self.model.in_save_name
        self.cancel_save.setVisible(pending)
        self.cancel_save.setText('Close without saving' if pending and self.model.core.wait.view['quit'] else 'Cancel')
        self.save.setText('Save and close' if pending and self.model.core.wait.view['quit'] else 'Save (F7)')
        self.refresh_round_controls()

    def run_core(self, name, *args):
        """[designed: T107] Start the driver's team action `name` as a background job; the page shows the original
        again when it ends (poll_core)."""
        if self.core_jobs.busy:
            self.status.setText('The original is still busy with the last action');return False
        self.core_jobs.start(name, *args)
        self.save.setEnabled(False)
        for widget in self.core_actions:widget.setEnabled(False)
        self.status.setText('Asking the assistant…' if name=='suggest_pool' else 'The original is pressing its own keys…')
        from goal2.desktop.pool_page import core_suggestion_controls
        core_suggestion_controls(self)
        self.core_round.refresh_match_button()
        # [designed: T116] A pitch frame is short work: do not impose the management job's 30 ms collection delay.
        self.core_timer.setInterval(1 if name == 'live_step' else 30)
        self.core_timer.start()
        return True

    def poll_core(self):
        try:
            answer = self.core_jobs.poll()
        except Exception as exc:              # the core stopped: say so, never guess
            answer = ('stopped', str(exc).split('\n')[0])
        if answer is None:return None
        self.core_timer.stop()
        self.save.setEnabled(True)
        for widget in self.core_actions:widget.setEnabled(True)
        kind, value = answer
        self.status.setText('Done: the pages show what the original holds' if kind == 'done'
                            else f'The original refused: {value}' if kind == 'refused' else f'The core stopped: {value}')
        self.last_core = answer
        if self.model.core.stopped is not None:
            self.core_round.viewer_timer.stop()
            for widget in self.core_actions:widget.setEnabled(False)
            self.save.setEnabled(False)
            return answer
        # [designed: T116] Hidden management records do not need rebuilding for each pitch frame. Decisions
        # and all other actions still refresh, so the next management page reflects the original's current state.
        live = kind == 'done' and self.core_jobs.name == 'live_step' and value.get('stop') == 'live'
        if not live:self.refresh()
        if self.core_jobs.name=='suggest_pool' and kind=='done':
            from goal2.desktop.pool_page import core_show_suggestions
            core_show_suggestions(self,value)
        from goal2.desktop.core_model import ROUND_ACTIONS
        if self.core_jobs.name in ROUND_ACTIONS:      # [T108] a round step: the round's page shows what came of it
            self.core_round.finished(self.core_jobs.name, answer)
        self.refresh_round_controls()
        return answer

    def refresh_round_controls(self):
        """[T108] While a round waits (the match menu, half time) the manager menu's routes and the team edits wait."""
        busy = self.core_jobs.busy
        in_round = self.model.in_round
        for widget in self.core_actions:
            widget.setEnabled(not busy and not self.model.in_save_name)
        if in_round or self.model.in_save_name:
            for widget in [b for b in self.core_team_buttons.values()] + [self.rename, self.pool_move, self.pool_switch] + \
                    [row for _, row in self.tactics] + self.own_tactics + [self.own_marking, self.core_routes['play next game']]:
                widget.setEnabled(False)
        self.core_round.refresh_shootout_controls()
        self.core_round.takers.refresh_controls()
        from goal2.desktop.pool_page import core_comparison_controls
        core_comparison_controls(self)
        self.core_round.refresh_match_button()

    def closeEvent(self, event):
        """[designed: T109] Stop scheduling polls, finish the bounded owned step, then reap the pitch viewer."""
        self.core_round.viewer_timer.stop()
        try:
            self.core_jobs.wait(60)
            if self.core_round.viewer is not None:
                self.core_round.viewer.close()
            self.core_jobs.pool.shutdown(wait=True)
        except Exception as exc:
            self.status.setText(f'Cannot close yet: {exc}');event.ignore();return
        event.accept()

    def finish_core(self, timeout=60):
        """Wait for the running action and show its result (tests; closing the window)."""
        self.core_jobs.wait(timeout)
        return self.poll_core()

    def resume_round(self):
        state = self.model.round_state()
        if state['stop'] == 'full-time':          # a core saved at the full-time menu: the round's end goes on
            self.run_core('finish');return
        self.core_round.finished('resume', ('done', state))
        self.refresh_round_controls()

    def navigate(self, index):
        if not self.navigation[index].isEnabled():return
        # [designed: owner #423] Leaving the squad also leaves its position-edit selection.
        if index != 1 and getattr(self, 'core_position_edit', None) is not None:
            self.core_position_edit = None
            from goal2.desktop import squad_page
            squad_page.refresh_core(self)
        self.page_stack.setCurrentIndex(index)
        from PySide6.QtCore import QCoreApplication, QEvent
        for _ in range(3):QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
        for number, button in enumerate(self.navigation):button.setChecked(number == index)
        self.pages[index].heading.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def refresh(self):
        """Read the views from the core's memory and show them."""
        desk = self.model.desk()
        self.title.setText(desk['team']['name'])
        self.career_line.setText(f"{desk['manager']} / {desk['year']} {desk['stage_word'].lower()}")
        if desk['opponent'] is None:
            self.next_line.setText('Next: no fixture');self.next_detail.setText('')
        else:
            self.next_line.setText(f"Next: {desk['opponent']['name']}");self.next_detail.setText(desk['fixture_kind'])
        from goal2.desktop import overview_page, fixtures_page, squad_page, pool_page
        overview_page.refresh_core(self, self.model, desk)
        squad_page.refresh_core(self)
        pool_page.refresh_core(self)
        fixtures_page.refresh_core(self, self.model)
