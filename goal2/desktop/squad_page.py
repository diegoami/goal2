"""[designed: T76] Readable squad draft over existing source-order controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QFrame,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QStackedWidget)


def reading_label(name):
    label=QLabel();label.setObjectName(name);label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


# [confirmed: docs/original-game/images/m244-team-tactics.png; F010 elements] The original's category for each tactic
# element: 5..7 are the team tactics, 1..4 and 8 the player defaults (game/country_card).
CATEGORIES={5:'Defence system',6:'Protection',7:'Offside',1:'Positioning',2:'Possession',
            3:'Passing',4:'Tackling',8:'Marking'}


class TacticRow(QPushButton):
    """[designed: T99; accepted vision #266 screen 16] One tactic: its category in gold and the
    current value word in green. The row is a checkable button whose checked state is the bit, so
    the word is read from isChecked() and never kept apart from it. Space, Enter or a click
    switches it; Up/Down move between rows. `alternatives` is the TACTICS label (unchecked word /
    checked word)."""
    page_painted=True

    def __init__(self,element,alternatives):
        super().__init__();self.element=element;self.category=CATEGORIES[element]
        self.words=tuple(word.strip() for word in alternatives.split(' / '))
        self.setCheckable(True);self.setObjectName(f'tactic{element}')
        self.setProperty('alternatives',alternatives);self.setProperty('tacticRow',True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.rows=[]
        self.toggled.connect(self.follow);self.follow()

    def value(self):
        word=self.words[1 if self.isChecked() else 0]
        return word[:1].upper()+word[1:]

    def follow(self,*unused):
        text=f'{self.category}: {self.value()}'
        self.setText(text);self.setAccessibleName(text);self.update()

    def keyPressEvent(self,event):
        key=event.key()
        if key in (Qt.Key.Key_Return,Qt.Key.Key_Enter):
            self.click()
        elif key in (Qt.Key.Key_Up,Qt.Key.Key_Down) and self in self.rows:
            index=self.rows.index(self)+(1 if key==Qt.Key.Key_Down else -1)
            if 0<=index<len(self.rows):self.rows[index].setFocus(Qt.FocusReason.TabFocusReason)
        else:
            super().keyPressEvent(event)

    def paintEvent(self,event):
        from PySide6.QtGui import QColor,QPainter,QPen
        from goal2.desktop.style import COLORS as c
        painter=QPainter(self);rect=self.rect()
        painter.fillRect(rect,QColor(c['raised'] if self.underMouse() and self.isEnabled() else c['background']))
        from goal2.desktop.fixed_page import scale_of,px
        s=scale_of(self)
        if self.hasFocus():
            painter.setPen(QPen(QColor(c['focus']),px(3,s)));painter.drawRect(rect.adjusted(1,1,-2,-2))
        painter.setFont(self.font());metrics=self.fontMetrics()
        flags=Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft
        column=px(12,s)+metrics.horizontalAdvance('Defence system')+metrics.horizontalAdvance('    ')
        disabled=QColor('#777777')
        painter.setPen(QColor(c['gold']) if self.isEnabled() else disabled)
        painter.drawText(rect.adjusted(px(12,s),0,0,0),flags,self.category)
        painter.setPen(QColor(c['green']) if self.isEnabled() else disabled)
        painter.drawText(rect.adjusted(column,0,-px(8,s),0),flags,self.value())
        painter.end()

    def sizeHint(self):
        # [designed: T101] Its type comes from the scaled style sheet; its fixed lengths scale too.
        from PySide6.QtCore import QSize
        from goal2.desktop.fixed_page import scale_of,px
        metrics=self.fontMetrics();s=scale_of(self)
        return QSize(px(32,s)+metrics.horizontalAdvance('Defence system    Sag back to box'),max(px(44,s),metrics.height()+px(20,s)))

    def minimumSizeHint(self):
        return self.sizeHint()


def build(self,model,TACTICS):
    page=self.pages[1];layout=page.content
    # [designed: T99; owner, 2026-10-21 "copy the style of goal2"; confirmed:
    # `docs/original-game/images/m244-squad.png`, `m244-team-tactics.png`] As in the original, the
    # roster is a strip on the right of every Team view; the views on its left are 0 the player's
    # card with the routes and 1 Team tactics. window.team_view(i) switches them; Escape returns
    # to the card. There is no table view: window.table stays the hidden model of the XI checks.
    from goal2.desktop.roster import RosterView
    from goal2.desktop.player_card import PlayerCardView
    # [designed: T101] On the fixed page the views and the strip sit side by side at every size.
    team=QHBoxLayout();team.setSpacing(16);layout.addLayout(team,1)
    self.team_views=QStackedWidget();self.team_views.setObjectName('teamViews');team.addWidget(self.team_views,1)
    self.team_views.show_view=lambda index:self.team_view(index);page.views=self.team_views
    self.team_roster=RosterView('SQUAD',grouped=True,marks=False);self.team_roster.setFixedWidth(320)
    self.team_roster.setAccessibleDescription('Up/Down: select; Space: between the XI and the bench')
    team.addWidget(self.team_roster,0,Qt.AlignmentFlag.AlignTop)
    def view(name):
        widget=QWidget();widget.setObjectName(name);box=QVBoxLayout(widget)
        box.setContentsMargins(0,0,0,0);box.setSpacing(8);self.team_views.addWidget(widget)
        return box
    card_box,tactics_box=view('teamCardView'),view('teamTacticsView')
    # [designed: T91/T99] View 0: the selected player's complete card (T88), then the routes.
    self.team_card=PlayerCardView();card_box.addWidget(self.team_card)
    from PySide6.QtGui import QKeySequence,QShortcut
    actions=QGridLayout();actions.setSpacing(8);card_box.addLayout(actions)
    self.team_pool=QPushButton('Pool / Compare >');self.team_pool.setObjectName('teamPool');self.team_pool.setAccessibleName('Pool / Compare')
    self.team_pool.clicked.connect(lambda:self.navigate(2))
    self.team_tactics_route=QPushButton('Team tactics >');self.team_tactics_route.setObjectName('teamTacticsRoute');self.team_tactics_route.setAccessibleName('Team tactics')
    self.team_tactics_route.clicked.connect(lambda:self.team_view(1))
    self.rename=QPushButton('Rename (F2)');self.rename.setObjectName('renamePlayer');self.rename.setAccessibleName('Rename the selected player')
    self.rename.clicked.connect(self.rename_selected)
    self.team_routes=(self.team_pool,self.team_tactics_route,self.rename)
    for column,button in enumerate(self.team_routes):actions.addWidget(button,0,column)
    card_box.addStretch(1)
    # [confirmed: E031 C30] F2 renames the player on the card; here, on the Team page.
    self.rename_shortcut=QShortcut(QKeySequence('F2'),self)
    self.rename_shortcut.activated.connect(lambda:self.page_stack.currentIndex()==1 and self.rename_selected())
    # [designed: T99] Escape anywhere on the Team page leaves Team tactics for the card.
    self.team_escape=QShortcut(QKeySequence('Escape'),page)
    self.team_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    self.team_escape.activated.connect(lambda:self.team_views.currentIndex()!=0 and self.team_view(0))
    self.team_roster.current_changed.connect(lambda row:self.table.setCurrentCell(row,1))
    self.team_roster.toggled.connect(lambda row:toggle(self,row))
    # [designed: T99; accepted vision #266 screen 16] View 1, Team tactics: the team on the left
    # (the counted formation, the manager, the captain; the strip lists the players), the eight
    # tactics on the right. Team skills are not shown: no aggregate is verified (G05).
    title=QLabel('TEAM TACTICS');title.setObjectName('tacticsTitle');tactics_box.addWidget(title)
    cards=QWidget();cards.setObjectName('tacticsCards');cards.box=QHBoxLayout(cards);cards.box.setContentsMargins(0,0,0,0);cards.box.setSpacing(16);tactics_box.addWidget(cards)
    left=QFrame();left.setObjectName('tacticsTeam');left_box=QVBoxLayout(left);left_box.setContentsMargins(16,12,16,16);left_box.setSpacing(10)
    self.tactics_heading=QLabel();self.tactics_heading.setObjectName('tacticsHeading');self.tactics_heading.setWordWrap(True);left_box.addWidget(self.tactics_heading)
    self.tactics_manager=QLabel();self.tactics_manager.setObjectName('tacticsManager');self.tactics_manager.setWordWrap(True);left_box.addWidget(self.tactics_manager)
    captain_label=QLabel('Captain');captain_label.setObjectName('captainLabel');left_box.addWidget(captain_label)
    self.captain=QComboBox();self.captain.setObjectName('captain');left_box.addWidget(self.captain)
    left_box.addStretch(1);cards.box.addWidget(left,1)
    right=QFrame();right.setObjectName('tacticsDefaults');right_box=QVBoxLayout(right);right_box.setContentsMargins(16,12,16,16);right_box.setSpacing(4)
    defaults=QLabel('TEAM DEFAULTS');defaults.setObjectName('tacticsDefaultsHeading');right_box.addWidget(defaults)
    self.tactics=[]
    for element,label in TACTICS:
        row=TacticRow(element,label);self.tactics.append((element,row));right_box.addWidget(row)
    for _,row in self.tactics:row.rows=[r for _,r in self.tactics]
    right_box.addStretch(1);cards.box.addWidget(right,1)
    plan=QHBoxLayout();plan.setSpacing(8);tactics_box.addLayout(plan)
    self.confirm_plan=QPushButton('Confirm plan');self.confirm_plan.setObjectName('confirmPlan')
    self.confirm_plan.clicked.connect(lambda:self.confirm.click())
    self.discard_plan=QPushButton('Discard / Team');self.discard_plan.setObjectName('discardPlan')
    self.discard_plan.clicked.connect(lambda:discard_plan(self))
    for button in (self.confirm_plan,self.discard_plan):button.setAutoDefault(True);plan.addWidget(button)
    plan.addStretch(1)
    hint=QLabel('Enter or Space: change the selected tactic / Esc: Team');hint.setObjectName('tacticsHint');hint.setWordWrap(True);tactics_box.addWidget(hint)
    # [designed: T76/T99] The XI checks' model: never shown, the strip and the card read it.
    self.table=QTableWidget(20,7,page.widget());self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Role','Position','Energy','Confidence','Availability'])
    self.table.setTabKeyNavigation(False);self.table.hide()
    footer=QWidget();footer.setObjectName('draftBar');bar=QHBoxLayout(footer);bar.setContentsMargins(8,8,8,8)
    self.draft_state=reading_label('draftState');self.draft_state.setAccessibleName('Management draft state');bar.addWidget(self.draft_state,1)
    self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm')
    self.cancel=QPushButton('Discard draft');self.cancel.setObjectName('discard')
    for action in (self.cancel,self.confirm):action.setAutoDefault(True);bar.addWidget(action)
    page.set_footer(footer)


def show_view(self,index):
    """[designed: T99] Show Team view `index` (0 the card, 1 Team tactics) with its first
    control focused (the strip on the card view); presentation only, the draft is untouched."""
    self.team_views.setCurrentIndex(index)
    from PySide6.QtCore import QCoreApplication,QEvent
    for _ in range(3):QCoreApplication.sendPostedEvents(None,QEvent.Type.LayoutRequest)
    page=self.pages[1]
    if self.page_stack.currentIndex()!=1:return
    target={0:self.team_roster,1:self.tactics[0][1]}[index]
    if not target.isEnabled():target=page.heading
    target.setFocus(Qt.FocusReason.ShortcutFocusReason)


def discard_plan(self):
    """[designed: T99; accepted vision #266 screen 16] Discard / Team: the existing Discard draft,
    then back to the roster."""
    self.cancel.click();self.team_view(0)


def toggle(self,row):
    """[designed: T91] Space on the roster flips the same XI check box the table holds, so the
    window's existing rules decide; an unavailable or preview row says why it cannot."""
    item=self.table.item(row,0)
    if item is None:return
    # [designed: T99] The table is never shown now, so its disabled state (a running match) is
    # enforced here: the strip is the only way to change the XI.
    if not self.table.isEnabled():
        self.status.setText('Finish or cancel the match first');return
    if not item.flags() & Qt.ItemFlag.ItemIsUserCheckable:
        if self.preview is not None:self.require_active()
        else:self.status.setText('Unavailable players cannot start')
        return
    item.setCheckState(Qt.CheckState.Unchecked if item.checkState()==Qt.CheckState.Checked else Qt.CheckState.Checked)


def roster_rows(self,rows,selected,captain):
    goaldat=self.display_model.goaldat
    def name(word):
        initial=goaldat.player_initials[word] if word<len(goaldat.player_initials) else ''
        return (initial+' ' if initial else '')+goaldat.player_names[word]
    return [(r['id'],name(r['id']),r['role'],r['line'],r['id'] in selected,r['id']==captain) for r in rows]


def refresh(self,*unused):
    """[designed: T76] Read widgets for presentation; never publish draft state."""
    if self._refreshing:return
    rows=self.display_model.view()['players'];selected=self.selected_ids();captain=self.captain.currentData()
    state=self.display_model.state;dirty=self.draft()!=(state.starting_eleven,state.captain,state.country_tactics)
    self.draft_state.setText(('Unconfirmed draft' if dirty else 'Confirmed management')+f' · XI {len(selected)}/11')
    # [derived: goal2/game/country_card.py] The formation is counted from the drafted eleven's
    # lines (defence, midfield, attack); nothing is stored.
    eleven=[row for row in rows if row['id'] in selected]
    formation='-'.join(str(sum(1 for row in eleven if row['line']==line)) for line in ('defence','midfield','attack'))
    self.tactics_heading.setText(f"{self.display_model.goaldat.country_names[state.managed_country].upper()} / XI {len(selected)} / {formation}")
    self.tactics_manager.setText('Manager: '+self.display_model.manager.split(' (')[0])
    current=max(0,self.table.currentRow());roster=roster_rows(self,rows,selected,captain)
    # [designed: T99] The strip: the eleven in the draft's order, then the bench in squad order.
    index={r['id']:i for i,r in enumerate(rows)}
    order=[index[w] for w in self.drafted_eleven() if w in index]+[i for i,r in enumerate(rows) if r['id'] not in selected]
    self.team_roster.caption=self.display_model.goaldat.country_names[state.managed_country].upper()
    self.team_roster.set_rows(roster,current,order=order,unavailable={r['id'] for r in rows if not r['availability']['available']})
    self.country_roster.set_rows(roster,current)
    from goal2.game.player_card import card
    self.team_card.set_card(card(self.display_model.state,rows[current]['id'],self.display_model.goaldat,team_tactics=self.draft()[2]))
    ready=sum(1 for r in rows if r['availability']['available'])
    self.desk_readiness.setText(f'{ready} ready / XI {len(selected)}')
    self.desk_captain.setText('Captain: '+(next((n for w,n,*_ in roster if w==captain),'chosen at kickoff') if captain else 'chosen at kickoff'))
    if hasattr(self,'lineup_own'):
        from goal2.desktop.fixtures_page import refresh_preparation
        refresh_preparation(self)


# -- the core route (T107) -------------------------------------------------------------------------------------------
# [designed: owner, 2026-10-22, decisions 5 and 7; T107] Over the core the Team page is T99's page filled from the
# original's memory: the roster strip (SELECT YOUR TEAM's squad, the eleven, a rule, the bench), the player card
# (1771:42BC) and the tactic rows (1771:1981). Every edit is a driver action run as a background job (CoreJobs); the
# page reads the original again when the job ends. There is no draft, no Confirm and no captain: the original
# holds none outside a match.
class CoreTacticRow(TacticRow):
    """A tactic row whose word is the original's (set by refresh), never a checked state of its own."""

    def __init__(self, element, name):
        self.word = '';self.label = name
        super().__init__(element, 'x / x')
        self.setCheckable(False);self.category = name

    def value(self):
        return self.word[:1].upper() + self.word[1:]

    def set_word(self, word):
        self.word = word;self.follow()


def core_roster_rows(team):
    return [(r['player'], r['name'], r['code'], r['line'], r['eleven'], False) for r in team['squad']]


def build_core(self, model):
    from PySide6.QtWidgets import QLineEdit
    from goal2.desktop.roster import RosterView
    from goal2.desktop.player_card import PlayerCardView
    page = self.pages[1]
    team = QHBoxLayout();team.setSpacing(16);page.content.addLayout(team, 1)
    self.team_views = QStackedWidget();self.team_views.setObjectName('teamViews');team.addWidget(self.team_views, 1)
    self.team_views.show_view = lambda index: core_team_view(self, index);page.views = self.team_views
    self.team_roster = RosterView('SQUAD', toggles=False, grouped=True, marks=False);self.team_roster.setFixedWidth(300)
    self.team_roster.setAccessibleDescription('Up/Down: select; Enter: mark, then Enter on another to swap')
    team.addWidget(self.team_roster, 0, Qt.AlignmentFlag.AlignTop)

    def view(name):
        widget = QWidget();widget.setObjectName(name);box = QVBoxLayout(widget)
        box.setContentsMargins(0, 0, 0, 0);box.setSpacing(8);self.team_views.addWidget(widget)
        return box
    card_box, tactics_box, own_box = view('teamCardView'), view('teamTacticsView'), view('teamOwnView')
    self.team_card = PlayerCardView(compact=True);card_box.addWidget(self.team_card)
    actions = QGridLayout();actions.setSpacing(8);card_box.addLayout(actions)
    buttons = (('Team tactics >', 'teamTacticsRoute', lambda: core_team_view(self, 1)),
               ('Own tactics (T) >', 'teamOwnRoute', lambda: core_team_view(self, 2)),
               ('Reposition (R)', 'reposition', lambda: core_reposition(self, False)),
               ('Club position (C)', 'clubPosition', lambda: core_reposition(self, True)))
    self.core_team_buttons = {}
    for i, (text, name, action) in enumerate(buttons):
        button = QPushButton(text);button.setObjectName(name);button.setAccessibleName(text.rstrip(' >'))
        button.clicked.connect(action);self.core_team_buttons[name] = button
        if name == 'reposition':
            button.setToolTip('R: next position; Shift+R: previous position; Enter: confirm')
            button.setAccessibleDescription(button.toolTip())
        if i < 3:actions.addWidget(button, 0, i)
    rename = QHBoxLayout();card_box.addLayout(rename);rename.addWidget(self.core_team_buttons['clubPosition'])
    self.rename_text = QLineEdit();self.rename_text.setObjectName('renameText');self.rename_text.setMaxLength(12)
    self.rename_text.setAccessibleName('New name, 12 characters at most')
    self.rename_text.setPlaceholderText('New name (12 characters)')
    self.rename = QPushButton('Rename (F2)');self.rename.setObjectName('renamePlayer')
    self.rename.setAccessibleName('Rename the selected player');self.rename.clicked.connect(lambda: core_rename(self))
    self.rename_text.returnPressed.connect(self.rename.click)
    rename.addWidget(self.rename_text, 1);rename.addWidget(self.rename);card_box.addStretch(1)
    from PySide6.QtGui import QKeySequence, QShortcut
    for key, action in (('F2', lambda: self.rename_text.setFocus(Qt.FocusReason.ShortcutFocusReason)),
                        ('R', lambda: core_reposition(self, False)), ('C', lambda: core_reposition(self, True)),
                        ('Shift+R', lambda: core_reposition(self, False, -1)),
                        ('T', lambda: core_team_view(self, 2))):
        shortcut = QShortcut(QKeySequence(key), page);shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(lambda a=action: self.rename_text.hasFocus() or a())
    # View 1: the team tactics, as 1771:1981 lists them (DS:6BBF's row order).
    title = QLabel('TEAM TACTICS');title.setObjectName('tacticsTitle');tactics_box.addWidget(title)
    cards = QHBoxLayout();cards.setSpacing(16);tactics_box.addLayout(cards)
    left = QFrame();left.setObjectName('tacticsTeam');left_box = QVBoxLayout(left);left_box.setContentsMargins(16, 12, 16, 16)
    self.tactics_heading = QLabel();self.tactics_heading.setObjectName('tacticsHeading');self.tactics_heading.setWordWrap(True)
    self.tactics_manager = QLabel();self.tactics_manager.setObjectName('tacticsManager');self.tactics_manager.setWordWrap(True)
    left_box.addWidget(self.tactics_heading);left_box.addWidget(self.tactics_manager);left_box.addStretch(1)
    cards.addWidget(left, 1)
    right = QFrame();right.setObjectName('tacticsDefaults');right_box = QVBoxLayout(right)
    right_box.setContentsMargins(16, 12, 16, 16);right_box.setSpacing(4)
    heading = QLabel('TEAM TACTICS / PLAYER DEFAULTS');heading.setObjectName('tacticsDefaultsHeading');right_box.addWidget(heading)
    self.tactics = []
    for element in (5, 6, 7, 1, 2, 3, 4, 8):
        row = CoreTacticRow(element, CATEGORIES[element]);self.tactics.append((element, row));right_box.addWidget(row)
        row.clicked.connect(lambda checked=False, e=element: core_toggle_tactic(self, e))
    for _, row in self.tactics:row.rows = [r for _, r in self.tactics]
    right_box.addStretch(1);cards.addWidget(right, 1)
    hint = QLabel('Enter or Space: change the selected tactic (the original toggles it) / Esc: the card')
    hint.setObjectName('tacticsHint');hint.setWordWrap(True);tactics_box.addWidget(hint);tactics_box.addStretch(1)
    # View 2: the selected player's own tactics (1771:4B61): each row cycles the team's, his own off, his own on.
    own_title = QLabel();own_title.setObjectName('ownTacticsTitle');own_box.addWidget(own_title);self.own_title = own_title
    self.own_tactics = []
    for element, name in enumerate(('Positioning', 'Possession', 'Passing', 'Tackling'), 1):
        row = CoreTacticRow(element, name);row.setObjectName(f'ownTactic{element}');self.own_tactics.append(row)
        row.clicked.connect(lambda checked=False, e=element: core_own_tactic(self, e));own_box.addWidget(row)
    self.own_marking = CoreTacticRow(8, 'Marking');self.own_marking.setObjectName('ownMarking')
    self.own_marking.clicked.connect(lambda: core_marking(self));own_box.addWidget(self.own_marking)
    for row in self.own_tactics + [self.own_marking]:row.rows = self.own_tactics + [self.own_marking]
    own_hint = QLabel('Enter: the team\'s tactic, his own (P) one way, his own the other way / Esc: the card')
    own_hint.setObjectName('ownTacticsHint');own_hint.setWordWrap(True);own_box.addWidget(own_hint);own_box.addStretch(1)
    self.team_roster.current_changed.connect(lambda row: core_selection_changed(self))
    self.team_roster.activated.connect(lambda row: core_mark(self, self.team_roster, row, 'squad'))

    def escape():
        if self.team_views.currentIndex() != 0:
            core_team_view(self, 0);return True
        if self.team_roster.marked:
            self.team_roster.marked = set();self.core_marked = None;self.team_roster.update();return True
        return False
    page.escape = escape
    self.core_marked = None


def core_team_view(self, index):
    self.team_views.setCurrentIndex(index)
    from PySide6.QtCore import QCoreApplication, QEvent
    for _ in range(3):QCoreApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
    if self.page_stack.currentIndex() != 1:return
    target = {0: self.team_roster, 1: self.tactics[0][1], 2: self.own_tactics[0]}[index]
    target.setFocus(Qt.FocusReason.ShortcutFocusReason)


def selected_player(self):
    rows = self.team_roster.rows
    return rows[self.team_roster.current][0] if rows and 0 <= self.team_roster.current < len(rows) else None


def core_selection_changed(self):
    """[designed: owner #423] Leaving the editing player releases visual order, following the new full ID."""
    pending = getattr(self, 'core_position_edit', None)
    if pending is not None and selected_player(self) != pending[0]:
        self.core_position_edit = None
        refresh_core(self)
    else:
        core_refresh_card(self)


def core_mark(self, strip, row, side):
    """[designed: T107; confirmed: 0791:DEA6] Enter marks a player, Enter on another moves him: two squad players
    swap, a squad and a pool player exchange (the original's own Enter, Enter)."""
    # [designed: owner #423] The first Enter confirms a position edit; it must not mark or swap anyone.
    if strip is self.team_roster and getattr(self, 'core_position_edit', None) is not None:
        self.core_position_edit = None
        refresh_core(self)
        return
    player = strip.rows[row][0]
    marked = self.core_marked
    if marked is None or marked[1] == player:
        self.core_marked = None if marked else (side, player)
    else:
        sides = {marked[0]: marked[1], side: player}
        self.core_marked = None
        if len(sides) == 1:
            if side == 'squad':
                self.run_core('swap', marked[1], player)
            else:
                self.status.setText('Mark a squad player, then a pool player, to move them')
        else:
            self.run_core('exchange', sides['squad'], sides['pool'])
    for s in (self.team_roster, getattr(self, 'pool_strip', None)):
        if s is not None:
            s.marked = {self.core_marked[1]} if self.core_marked else set();s.update()


def core_reposition(self, club, direction=1):
    player = selected_player(self) if self.page_stack.currentIndex() == 1 else self.pool_selected()
    if player is None:return
    card = self.model.card(player)
    # [designed: owner #423] Guest edits remain immediate; only the displayed row order is held.
    pending = (player, [r[0] for r in self.team_roster.rows]) if self.page_stack.currentIndex() == 1 else None
    if self.run_core('set_position', player, card['club_position'] if club else (card['position'] + direction) % 14):
        if pending is not None and getattr(self, 'core_position_edit', None) is None:
            self.core_position_edit = pending


def core_rename(self):
    player = selected_player(self)
    text = self.rename_text.text()
    if player is None or not text.strip():
        self.status.setText('Type the new name (12 characters at most), then Rename');return
    self.run_core('rename', player, text)


def core_toggle_tactic(self, element):
    self.run_core('set_tactic', element, not self.model.team_tactics()['byte'] >> (element - 1) & 1)


def core_own_tactic(self, element):
    player = selected_player(self)
    if player is None:return
    r = self.model.card(player)['own_tactics']
    state = None if not r >> (element + 3) & 1 else bool(r >> (element - 1) & 1)
    following = {None: False, False: True, True: None}[state]         # 1771:4B61's cycle
    self.run_core('set_own_tactic', player, element, following)


def core_marking(self):
    player = selected_player(self)
    if player is not None:self.run_core('set_marking', player, 0)


def core_refresh_card(self):
    from goal2.desktop.player_card import core_card
    player = selected_player(self)
    card = self.model.card(player) if player is not None else None
    self.team_card.set_card(core_card(card) if card else None)
    if card:
        self.own_title.setText(f"{card['name'].upper()} / OWN TACTICS (P = his own)")
        for row, (_, word, own) in zip(self.own_tactics, card['tactics']):row.set_word(word + (' P' if own else ''))
        self.own_marking.set_word(card['mark'] or '—')


def refresh_core(self):
    selected = selected_player(self)
    team = self.model.team()
    tactics = self.model.team_tactics()
    rows = core_roster_rows(team)
    pending = getattr(self, 'core_position_edit', None)
    if pending is not None:
        by_id = {r[0]: r for r in rows}
        if set(by_id) == set(pending[1]):
            rows = [by_id[player] for player in pending[1]]
        else:
            self.core_position_edit = None
    self.team_roster.caption = team['name'].upper()
    current = next((i for i, r in enumerate(rows) if r[0] == selected), 0)
    self.team_roster.set_rows(rows, current)
    words = {r['element']: r['word'] for r in tactics['rows']}
    for element, row in self.tactics:row.set_word(words[element])
    eleven = [r for r in team['squad'] if r['eleven']]
    # [derived: goal2/game/country_card.py] the formation is counted from the eleven's lines; nothing is stored.
    formation = '-'.join(str(sum(1 for r in eleven if r['line'] == line)) for line in ('defence', 'midfield', 'attack'))
    self.tactics_heading.setText(f"{team['name'].upper()} / {formation}")
    self.tactics_manager.setText('Manager: ' + self.model.desk()['manager'])
    core_refresh_card(self)
