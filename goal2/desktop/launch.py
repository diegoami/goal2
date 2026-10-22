"""[designed: T86; accepted vision #266 screen 01] Launch: resume a saved career, open
another save, or browse, review and start a new one.

[confirmed: E015-r0001 state 2, E015-r0008 state 10, E031 C11-C15b] The original title asks
load or new; a failed load offers to try again; a new game browses countries with their
rankings. Nothing here writes a save or replaces a game: the validating loader
(`DesktopModel.from_save`) and `DesktopModel.new_campaign` stay authoritative, and only the
`opened(model)` callback receives a validated game.
"""
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QPushButton, QListWidget, QListWidgetItem, QComboBox, QLineEdit,
                               QStackedWidget, QFrame, QAbstractButton)
from goal2.desktop.model import DesktopModel, START_YEARS, CONTINENTS

# [designed: accepted vision #266] Black screens, large type, strong functional colours.
COLORS = dict(background='#000000', title='#4ef2f2', saved='#ff5555', country='#ffff55',
              text='#e8e8e8', list='#55ff55', hint='#ff55ff', button='#4ef2f2', focus='#ffff55')
STYLE = f"""
QMainWindow, QWidget#fixedPage, QWidget#launchRoot, QStackedWidget, QStackedWidget > QWidget {{background:{COLORS['background']};}}
QWidget {{font-family:'DejaVu Sans Mono','Consolas','Courier New',monospace;font-size:20px;color:{COLORS['text']};}}
QLabel#launchTitle {{font-size:34px;font-weight:700;color:{COLORS['title']};}}
QLabel#launchSubtitle {{font-size:28px;font-weight:700;color:{COLORS['saved']};}}
QFrame#savedPanel {{border:2px solid {COLORS['saved']};}}
QFrame#newPanel, QFrame#reviewPanel {{border:2px solid {COLORS['title']};}}
QLabel#panelHeading {{font-size:20px;font-weight:700;color:{COLORS['saved']};}}
QLabel#newHeading {{font-size:20px;font-weight:700;color:{COLORS['title']};}}
QLabel#savedCountry, QLabel#previewCountry {{font-size:48px;font-weight:700;color:{COLORS['country']};}}
QLabel#chooseHeading {{font-size:24px;font-weight:700;color:{COLORS['country']};}}
QLabel#fieldName {{color:{COLORS['text']};}}
QLabel#launchHint, QLabel#launchNote {{color:{COLORS['hint']};}}
QLabel#launchError {{color:{COLORS['saved']};font-weight:700;}}
QListWidget {{background:{COLORS['background']};color:{COLORS['list']};border:1px solid {COLORS['title']};}}
QListWidget::item:selected {{background:{COLORS['list']};color:{COLORS['background']};}}
QPushButton {{background:{COLORS['background']};color:{COLORS['button']};border:2px solid {COLORS['button']};
             padding:8px 14px;text-align:left;font-weight:700;min-height:36px;}}
QPushButton:focus {{background:#aaaaaa;color:#000000;border:3px solid {COLORS['focus']};}}
QPushButton:disabled {{color:#777777;border-color:#555555;}}
QComboBox, QLineEdit {{background:{COLORS['background']};color:{COLORS['list']};border:2px solid {COLORS['title']};padding:4px;min-height:36px;}}
QComboBox:focus, QLineEdit:focus, QListWidget:focus {{border:3px solid {COLORS['focus']};}}
"""
HINT = 'Arrows: choose / Enter: accept / Esc: back / Existing saves stay yours'
# [designed: T89] Each page names only its own keys, so the line never wraps.
HINTS = {0: HINT, 1: 'Arrows: country / Enter: review / Space: players / Esc: back',
         2: 'Enter: start / Esc: back to countries', 3: 'Arrows: player / Esc: back to countries'}


def fields(layout, rows):
    """Two-column name/value labels; returns the value labels by key."""
    grid = QGridLayout();grid.setHorizontalSpacing(28);grid.setVerticalSpacing(12);layout.addLayout(grid)
    values = {}
    for row, (key, name) in enumerate(rows):
        label = QLabel(name);label.setObjectName('fieldName');grid.addWidget(label, row, 0)
        value = QLabel();value.setObjectName(key);value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(value, row, 1, 1, 1);values[key] = value
    grid.setColumnStretch(1, 1)
    return values


class LaunchWindow(QMainWindow):
    """[designed: T86] Pages: 0 launch, 1 country browsing, 2 review. Owns no game until opened."""

    def __init__(self, data_path, template_path, save_path, opened):
        super().__init__()
        self.data_path = Path(data_path);self.template_path = None if template_path is None else Path(template_path)
        self.save_path = Path(save_path);self.opened = opened
        self.browser = None  # a private DesktopModel for previews; never published until Start
        self.candidate = None
        self.setWindowTitle('goal2 — Start or resume');self.resize(1440, 900)
        # [designed: T101] One fixed page of 1440x900, scaled to the window (fixed_page.py).
        root = QWidget();root.setObjectName('launchRoot')
        outer = QVBoxLayout(root);outer.setContentsMargins(20, 16, 20, 16);outer.setSpacing(14)
        title = QLabel('GOAL2 / START OR RESUME');title.setObjectName('launchTitle');outer.addWidget(title)
        self.pages = QStackedWidget();outer.addWidget(self.pages, 1)
        self.hint = QLabel(HINT);self.hint.setObjectName('launchHint');self.hint.setWordWrap(True);outer.addWidget(self.hint)
        self._build_launch();self._build_browse();self._build_review();self._build_players()
        from goal2.desktop.style import load_fonts
        from goal2.desktop.fixed_page import FixedPage
        load_fonts();self.setStyleSheet(STYLE);self.setCentralWidget(FixedPage(root, STYLE, self))
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.back)
        self.preview_timer = QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(120)
        self.preview_timer.timeout.connect(self.preview)
        self.read_saved(self.save_path)
        self.show_page(0)

    # Launch page -----------------------------------------------------------------------
    def _build_launch(self):
        page = QWidget();layout = QVBoxLayout(page);layout.setSpacing(14)
        subtitle = QLabel('RETURN TO YOUR COUNTRY');subtitle.setObjectName('launchSubtitle');layout.addWidget(subtitle)
        panels = QHBoxLayout();panels.setSpacing(20);layout.addLayout(panels, 1)
        saved = QFrame();saved.setObjectName('savedPanel');body = QVBoxLayout(saved);body.setSpacing(10)
        heading = QLabel('SAVED CAREER');heading.setObjectName('panelHeading');body.addWidget(heading)
        self.saved_country = QLabel();self.saved_country.setObjectName('savedCountry');self.saved_country.setWordWrap(True)
        body.addWidget(self.saved_country)
        self.saved_fields = fields(body, (('manager', 'MANAGER'), ('campaign', 'CAMPAIGN'), ('next', 'NEXT'),
                                          ('then', 'THEN'), ('checkpoint', 'SAVE'), ('team', 'TEAM')))
        self.error = QLabel();self.error.setObjectName('launchError');self.error.setWordWrap(True);body.addWidget(self.error)
        self.resume = QPushButton();self.resume.setObjectName('launchResume');self.resume.clicked.connect(self.do_resume)
        self.retry = QPushButton('Retry');self.retry.setObjectName('launchRetry');self.retry.clicked.connect(self.do_retry)
        body.addStretch(1)
        for button in (self.resume, self.retry):body.addWidget(button)
        panels.addWidget(saved, 3)
        new = QFrame();new.setObjectName('newPanel');side = QVBoxLayout(new);side.setSpacing(10)
        heading = QLabel('NEW GAME');heading.setObjectName('newHeading');side.addWidget(heading)
        self.new_career = QPushButton('New career >');self.new_career.setObjectName('launchNew')
        self.new_career.clicked.connect(lambda: self.show_page(1));side.addWidget(self.new_career)
        if self.template_path is None:
            self.new_career.setEnabled(False)
            reason = QLabel('New career needs the local engine template (--template).');reason.setObjectName('launchNote')
            reason.setWordWrap(True);side.addWidget(reason)
        load = QLabel('Open another save');load.setObjectName('newHeading');side.addWidget(load)
        self.other_path = QLineEdit(str(self.save_path));self.other_path.setObjectName('launchPath')
        self.other_path.setAccessibleName('Save file to open');side.addWidget(self.other_path)
        self.load_other = QPushButton('Open another save');self.load_other.setObjectName('launchLoad')
        self.load_other.clicked.connect(self.do_load_other);side.addWidget(self.load_other)
        side.addStretch(1)
        note = QLabel('One manager first.\nReview before starting.');note.setObjectName('launchNote');side.addWidget(note)
        panels.addWidget(new, 2)
        self.pages.addWidget(page)

    def read_saved(self, path):
        """[designed] Summarise only what the validating loader accepts; otherwise name the reason."""
        self.saved_path = Path(path)
        try:
            model = DesktopModel.from_save(self.saved_path, self.data_path)
        except ValueError as exc:
            self.saved_model = None
            missing = not self.saved_path.exists()
            self.saved_country.setText('NO SAVED CAREER' if missing else 'SAVE NOT USABLE')
            for value in self.saved_fields.values():value.setText('')
            self.error.setText(f'{self.saved_path}: ' + ('no save here yet.' if missing else str(exc)))
            self.resume.setText('Resume unavailable');self.resume.setEnabled(False)
            self.retry.setVisible(True)
            return False
        self.saved_model = model
        summary = model.summary()
        self.saved_country.setText(summary['country'].upper())
        for key, value in self.saved_fields.items():value.setText(summary[key])
        self.error.setText('');self.retry.setVisible(False)
        self.resume.setText('RESUME ' + summary['country'].upper());self.resume.setEnabled(True)
        return True

    def do_resume(self):
        # Validate the file again at the moment of opening: it may have changed since the summary.
        if self.read_saved(self.saved_path):
            self.finish(DesktopModel.from_save(self.saved_path, self.data_path))

    def do_retry(self):
        self.read_saved(self.saved_path)
        (self.resume if self.resume.isEnabled() else self.other_path).setFocus()

    def do_load_other(self):
        if self.read_saved(Path(self.other_path.text().strip())):self.resume.setFocus()
        else:self.other_path.setFocus()

    # Country browsing ------------------------------------------------------------------
    def _build_browse(self):
        page = QWidget();layout = QHBoxLayout(page);layout.setSpacing(20)
        left = QFrame();left.setObjectName('newPanel');body = QVBoxLayout(left)
        heading = QLabel('CHOOSE YOUR COUNTRY');heading.setObjectName('chooseHeading');body.addWidget(heading)
        columns = QLabel(f"{'COUNTRY':<13}{'WORLD':>5}  CONTINENT");columns.setObjectName('fieldName');body.addWidget(columns)
        self.country_list = QListWidget();self.country_list.setObjectName('countryList')
        self.country_list.setAccessibleName('Countries with world rank and continent rank')
        # [designed: T101; confirmed: `docs/original-game/images/country-select.png`] As the
        # original's country list, the 128 countries are a window of rows that follows the
        # selection (arrows, Page Up/Down, the wheel); the fixed page shows no scroll bar.
        for policy in (self.country_list.setVerticalScrollBarPolicy, self.country_list.setHorizontalScrollBarPolicy):
            policy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.addWidget(self.country_list, 1)
        year = QHBoxLayout();year.addWidget(QLabel('Start year'))
        self.start_year = QComboBox();self.start_year.setObjectName('launchStartYear');self.start_year.setAccessibleName('Start year')
        for value, label in START_YEARS:self.start_year.addItem(label, value)
        # A long year label must not widen this pane at the preview's expense.
        self.start_year.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.start_year.setMinimumContentsLength(24);self.country_list.setMinimumWidth(320)
        year.addWidget(self.start_year, 1);body.addLayout(year)
        self.to_review = QPushButton('Review >');self.to_review.setObjectName('launchToReview')
        self.to_review.clicked.connect(self.review);body.addWidget(self.to_review)
        # [designed: owner, 2026-10-21] As the original's country selection: Space shows the players.
        self.to_players = QPushButton('Players (Space) >');self.to_players.setObjectName('launchPlayers')
        self.to_players.clicked.connect(self.show_players);body.addWidget(self.to_players)
        self.country_list.installEventFilter(self)
        layout.addWidget(left, 2)
        # [designed: T89] The original's country card. [designed: T101] The fixed page gives it its
        # whole composition at every window size (superseding screen 11's stacking and scrolling).
        from goal2.desktop.country_card import CountryCardView
        self.country_card = CountryCardView()
        layout.addWidget(self.country_card, 3, Qt.AlignmentFlag.AlignTop)
        self.pages.addWidget(page)
        self.country_list.currentRowChanged.connect(lambda _: self.preview_timer.start())
        self.start_year.currentIndexChanged.connect(lambda _: self.preview_timer.start())
        # Enter is handled by keyPressEvent: itemActivated would let the same key event go on to click Start.
        self.country_list.itemDoubleClicked.connect(lambda _: self.review())

    def fill_countries(self):
        if self.country_list.count():return
        self.browser = DesktopModel.open(self.template_path, self.data_path, self.save_path, country=1)
        for number, name, world, continent, within in self.browser.countries():
            item = QListWidgetItem(f'{name:<13}{world:>4}   {CONTINENTS[continent][:2].upper()}{within:>3}')
            item.setData(Qt.ItemDataRole.UserRole, number);self.country_list.addItem(item)
        self.country_list.setCurrentRow(0)

    def selection(self):
        item = self.country_list.currentItem()
        return (None if item is None else item.data(Qt.ItemDataRole.UserRole)), self.start_year.currentData()

    def preview(self):
        """[designed] A private candidate per choice; the published game and save are untouched."""
        country, year = self.selection()
        if country is None:return
        self.browser.new_campaign(country, year)
        # Every value below reads the private candidate only.
        from goal2.game.country_card import card
        summary = self.browser.summary()
        self.country_card.set_card(card(self.browser.state, country, self.browser.goaldat),
                                   f"{summary['campaign']}: {summary['next']}")
        self.previewed = (country, year)

    # Players -----------------------------------------------------------------------------
    def _build_players(self):
        """[designed: T88] The previewed country's twenty, each with its complete card."""
        from goal2.desktop.player_card import PlayerCardView
        page = QWidget();layout = QHBoxLayout(page);layout.setSpacing(20)
        left = QFrame();left.setObjectName('newPanel');body = QVBoxLayout(left)
        self.players_heading = QLabel();self.players_heading.setObjectName('chooseHeading');body.addWidget(self.players_heading)
        self.player_list = QListWidget();self.player_list.setObjectName('playerList')
        self.player_list.setAccessibleName('Players with role codes');self.player_list.setMinimumWidth(240)
        for policy in (self.player_list.setVerticalScrollBarPolicy, self.player_list.setHorizontalScrollBarPolicy):
            policy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body.addWidget(self.player_list, 1)
        layout.addWidget(left, 1)
        self.player_card = PlayerCardView()
        layout.addWidget(self.player_card, 3, Qt.AlignmentFlag.AlignTop)
        self.pages.addWidget(page)
        self.player_list.currentRowChanged.connect(self.show_card)

    def show_players(self):
        from PySide6.QtGui import QColor
        from goal2.desktop.player_card import LINE
        from goal2.game.player_card import card
        country, year = self.selection()
        if country is None:return
        if getattr(self, 'previewed', None) != (country, year):self.preview()
        state = self.browser.state
        self.cards = [card(state, word, self.browser.goaldat) for word in state.managed_squad]
        self.players_heading.setText(self.browser.goaldat.country_names[country].upper() + ' / PLAYERS')
        self.player_list.clear()
        for i, c in enumerate(self.cards):
            if i == 11:
                rule = QListWidgetItem('─' * 18);rule.setFlags(Qt.ItemFlag.NoItemFlags);self.player_list.addItem(rule)
            item = QListWidgetItem(f"{c['role']}  {c['full_name']}");item.setData(Qt.ItemDataRole.UserRole, i)
            item.setForeground(QColor(LINE[c['line']]));self.player_list.addItem(item)
        self.show_page(3);self.player_list.setCurrentRow(0)

    def show_card(self, row):
        item = self.player_list.item(row)
        index = None if item is None else item.data(Qt.ItemDataRole.UserRole)
        self.player_card.set_card(None if index is None else self.cards[index])

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent
        if watched is self.country_list and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Space:
            self.show_players();return True
        return super().eventFilter(watched, event)

    # Review ----------------------------------------------------------------------------
    def _build_review(self):
        page = QWidget();layout = QVBoxLayout(page)
        panel = QFrame();panel.setObjectName('reviewPanel');body = QVBoxLayout(panel);body.setSpacing(12)
        heading = QLabel('REVIEW BEFORE STARTING');heading.setObjectName('chooseHeading');body.addWidget(heading)
        self.review_fields = fields(body, (('country', 'COUNTRY'), ('manager', 'MANAGER'), ('campaign', 'CAMPAIGN'),
                                           ('next', 'FIRST'), ('then', 'THEN'), ('save', 'SAVE')))
        body.addStretch(1)
        self.start = QPushButton('Start career');self.start.setObjectName('launchStart');self.start.clicked.connect(self.do_start)
        self.back_to_browse = QPushButton('< Back to countries');self.back_to_browse.setObjectName('launchBack')
        self.back_to_browse.clicked.connect(lambda: self.show_page(1))
        body.addWidget(self.start);body.addWidget(self.back_to_browse)
        layout.addWidget(panel)
        self.pages.addWidget(page)

    def review(self):
        country, year = self.selection()
        if country is None:return
        if getattr(self, 'previewed', None) != (country, year):self.preview()
        summary = self.browser.summary()
        values = dict(summary, save=f'Nothing is saved until you save; {self.save_path.name} is not touched by starting')
        for key, label in self.review_fields.items():label.setText(values[key])
        self.show_page(2)

    def do_start(self):
        country, year = self.selection()
        model = DesktopModel(self.browser.goaldat, self.browser.template_bytes, self.save_path)
        model.new_campaign(country, year)
        self.finish(model)

    # Navigation ------------------------------------------------------------------------
    def show_page(self, index):
        if index == 1:
            self.fill_countries()
        self.pages.setCurrentIndex(index);self.hint.setText(HINTS[index])
        first = {0: self.resume if self.resume.isEnabled() else self.new_career if self.new_career.isEnabled() else self.other_path,
                 1: self.country_list, 2: self.start, 3: self.player_list}[index]
        first.setFocus(Qt.FocusReason.OtherFocusReason)

    def back(self):
        index = self.pages.currentIndex()
        if index:self.show_page(1 if index == 3 else index - 1)

    def focusables(self):
        page = self.pages.currentWidget()
        return [w for w in page.findChildren(QWidget)
                if isinstance(w, (QAbstractButton, QLineEdit, QComboBox, QListWidget)) and w.isVisible() and w.isEnabled()]

    def keyPressEvent(self, event):
        """[designed: T86] The hint line's keys: arrows choose, Enter accepts."""
        focus = self.focusWidget();key = event.key()
        if key == Qt.Key.Key_Escape:
            self.back();return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and isinstance(focus, QAbstractButton):
            focus.click();return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and focus is self.country_list:
            self.review();return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and focus is self.other_path:
            self.do_load_other();return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and isinstance(focus, QAbstractButton):
            order = self.focusables()
            if focus in order:
                step = 1 if key == Qt.Key.Key_Down else -1
                order[(order.index(focus) + step) % len(order)].setFocus(Qt.FocusReason.TabFocusReason);return
        super().keyPressEvent(event)

    def finish(self, model):
        self.opened(model);self.close()
