"""[designed: T76] Readable squad draft over existing source-order controls."""
from PySide6.QtCore import Qt,QObject,QEvent
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
        if self.hasFocus():
            painter.setPen(QPen(QColor(c['focus']),3));painter.drawRect(rect.adjusted(1,1,-2,-2))
        painter.setFont(self.font());metrics=self.fontMetrics()
        flags=Qt.AlignmentFlag.AlignVCenter|Qt.AlignmentFlag.AlignLeft
        column=12+metrics.horizontalAdvance('Defence system')+metrics.horizontalAdvance('    ')
        disabled=QColor('#777777')
        painter.setPen(QColor(c['gold']) if self.isEnabled() else disabled)
        painter.drawText(rect.adjusted(12,0,0,0),flags,self.category)
        painter.setPen(QColor(c['green']) if self.isEnabled() else disabled)
        painter.drawText(rect.adjusted(column,0,-8,0),flags,self.value())
        painter.end()

    def sizeHint(self):
        from PySide6.QtCore import QSize
        metrics=self.fontMetrics()
        return QSize(32+metrics.horizontalAdvance('Defence system    Sag back to box'),max(44,metrics.height()+20))


class ViewportFit(QObject):
    """[designed: T99] Call `fit(height)` whenever `viewport` is resized."""

    def __init__(self,viewport,fit):
        super().__init__(viewport);self.fit=fit;viewport.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.Resize:self.fit(event.size().height())
        return False


def build(self,model,TACTICS):
    page=self.pages[1];layout=page.content
    # [designed: T99; accepted vision #266 screens 03/16] The Team page holds three views: 0 the
    # roster and the card with the routes, 1 Team tactics, 2 the attribute table. The window's
    # team_view(i) switches between them; Escape on 1 or 2 returns to 0.
    self.team_views=QStackedWidget();self.team_views.setObjectName('teamViews');layout.addWidget(self.team_views)
    def view(name):
        widget=QWidget();widget.setObjectName(name);box=QVBoxLayout(widget)
        box.setContentsMargins(0,0,0,0);box.setSpacing(12);self.team_views.addWidget(widget)
        return box
    roster_box,tactics_box,table_box=view('teamRosterView'),view('teamTacticsView'),view('teamTableView')
    self.team_views.currentChanged.connect(lambda index:fit_views(self))
    # A view re-arranged while the page was hidden (Columns, T91) settles when the page shows.
    self.page_stack.currentChanged.connect(lambda index:index==1 and fit_views(self))
    # [designed: T91; accepted vision #266 screen 03] View 0: the twenty beside the selected
    # player's complete card (T88), then the routes.
    from goal2.desktop.roster import Columns,RosterView
    from goal2.desktop.player_card import PlayerCardView
    from PySide6.QtWidgets import QScrollArea
    team=Columns(1096);team.setObjectName('teamDesk');roster_box.addWidget(team)
    self.team_roster=RosterView('SQUAD');self.team_roster.setFixedWidth(320);self.team_roster.setAccessibleDescription('Up/Down: select; Space: in or out of the XI')
    team.box.addWidget(self.team_roster,0,Qt.AlignmentFlag.AlignTop)
    self.team_card=PlayerCardView();card_area=QScrollArea();card_area.setObjectName('teamCard')
    card_area.setWidgetResizable(True);card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    card_area.setFrameShape(QScrollArea.Shape.NoFrame)
    card_area.setWidget(self.team_card);card_area.setMinimumHeight(644);team.box.addWidget(card_area,1)
    from PySide6.QtGui import QKeySequence,QShortcut
    actions=QGridLayout();actions.setSpacing(8);roster_box.addLayout(actions)
    self.team_pool=QPushButton('Pool / Compare >');self.team_pool.setObjectName('teamPool');self.team_pool.setAccessibleName('Pool / Compare')
    self.team_pool.clicked.connect(lambda:self.navigate(2))
    self.team_table_route=QPushButton('Attribute table >');self.team_table_route.setObjectName('teamTableRoute');self.team_table_route.setAccessibleName('Attribute table')
    self.team_table_route.clicked.connect(lambda:self.team_view(2))
    self.team_tactics_route=QPushButton('Team tactics >');self.team_tactics_route.setObjectName('teamTacticsRoute');self.team_tactics_route.setAccessibleName('Team tactics')
    self.team_tactics_route.clicked.connect(lambda:self.team_view(1))
    self.rename=QPushButton('Rename (F2)');self.rename.setObjectName('renamePlayer');self.rename.setAccessibleName('Rename the selected player')
    self.rename.clicked.connect(self.rename_selected)
    self.team_routes=(self.team_pool,self.team_table_route,self.team_tactics_route,self.rename)
    for column,button in enumerate(self.team_routes):actions.addWidget(button,0,column)
    # [confirmed: E031 C30] F2 renames the player on the card; here, on the Team page.
    self.rename_shortcut=QShortcut(QKeySequence('F2'),self)
    self.rename_shortcut.activated.connect(lambda:self.page_stack.currentIndex()==1 and self.rename_selected())
    # [designed: T99] Escape anywhere on the Team page leaves Team tactics or the attribute table.
    self.team_escape=QShortcut(QKeySequence('Escape'),page)
    self.team_escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    self.team_escape.activated.connect(lambda:self.team_views.currentIndex()!=0 and self.team_view(0))
    self.team_roster.current_changed.connect(lambda row:self.table.setCurrentCell(row,1))
    self.team_roster.toggled.connect(lambda row:toggle(self,row))
    # [designed: T99; accepted vision #266 screen 16] View 1, Team tactics: the team on the left
    # (the XI's formation, the manager, the captain, the XI and the bench), the eight tactics on
    # the right. Team skills are not shown: no aggregate is verified (G05).
    title=QLabel('TEAM TACTICS');title.setObjectName('tacticsTitle');tactics_box.addWidget(title)
    cards=Columns(900);cards.setObjectName('tacticsCards');tactics_box.addWidget(cards)
    left=QFrame();left.setObjectName('tacticsTeam');left_box=QVBoxLayout(left);left_box.setContentsMargins(16,12,16,16);left_box.setSpacing(10)
    self.tactics_heading=QLabel();self.tactics_heading.setObjectName('tacticsHeading');self.tactics_heading.setWordWrap(True);left_box.addWidget(self.tactics_heading)
    self.tactics_manager=QLabel();self.tactics_manager.setObjectName('tacticsManager');self.tactics_manager.setWordWrap(True);left_box.addWidget(self.tactics_manager)
    captain_bar=QHBoxLayout();captain_label=QLabel('Captain');captain_label.setObjectName('captainLabel');captain_bar.addWidget(captain_label)
    self.captain=QComboBox();self.captain.setObjectName('captain');captain_bar.addWidget(self.captain,1);left_box.addLayout(captain_bar)
    self.lineup_board=reading_label('lineupBoard');self.lineup_board.setAccessibleName('Starting XI grouped by position');left_box.addWidget(self.lineup_board)
    self.bench_board=reading_label('benchBoard');self.bench_board.setAccessibleName('Bench');left_box.addWidget(self.bench_board)
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
    # [designed: T76/T99] View 2, the attribute table: the summary, the twenty's raw fields and
    # the selected player's detail.
    self.squad_summary=reading_label('squadSummary');table_box.addWidget(self.squad_summary)
    self.table=QTableWidget(20,7);self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Role','Position','Energy','Confidence','Availability'])
    self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
    self.table.setTabKeyNavigation(False);self.table.setMinimumHeight(240)
    self.table.verticalHeader().setDefaultSectionSize(40);table_box.addWidget(self.table)
    # [designed: T99] The table grows with the page but never past its viewport: the whole table,
    # and so each of its rows, can always be brought into view.
    self.table_fit=ViewportFit(self.pages[1].viewport(),lambda height:self.table.setMaximumHeight(max(self.table.minimumHeight(),height-48)))
    self.player_detail=reading_label('playerDetail');self.player_detail.setAccessibleName('Selected player detail');table_box.addWidget(self.player_detail)
    back=QHBoxLayout();table_box.addLayout(back)
    self.table_back=QPushButton('< Team');self.table_back.setObjectName('tableBack');self.table_back.setAccessibleName('Back to Team')
    self.table_back.clicked.connect(lambda:self.team_view(0));back.addWidget(self.table_back);back.addStretch(1)
    footer=QWidget();footer.setObjectName('draftBar');bar=QHBoxLayout(footer);bar.setContentsMargins(8,8,8,8)
    self.draft_state=reading_label('draftState');self.draft_state.setAccessibleName('Management draft state');bar.addWidget(self.draft_state,1)
    self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm')
    self.cancel=QPushButton('Discard draft');self.cancel.setObjectName('discard')
    for action in (self.cancel,self.confirm):action.setAutoDefault(True);bar.addWidget(action)
    page.set_footer(footer)
    fit_views(self)


def fit_views(self):
    """[designed: T99] The page scrolls over the shown view only: a hidden view takes no size."""
    from PySide6.QtWidgets import QSizePolicy
    current=self.team_views.currentIndex()
    for index in range(self.team_views.count()):
        policy=QSizePolicy.Policy.Preferred if index==current else QSizePolicy.Policy.Ignored
        self.team_views.widget(index).setSizePolicy(policy,policy)
    self.team_views.currentWidget().layout().invalidate();self.team_views.updateGeometry()


def show_view(self,index):
    """[designed: T99] Show Team view `index` (0 roster, 1 tactics, 2 attribute table) with its
    first control focused; presentation only, the draft is untouched."""
    self.team_views.setCurrentIndex(index)
    from PySide6.QtCore import QCoreApplication,QEvent
    for _ in range(3):QCoreApplication.sendPostedEvents(None,QEvent.Type.LayoutRequest)
    page=self.pages[1];page.verticalScrollBar().setValue(0)
    if self.page_stack.currentIndex()!=1:return
    target={0:self.team_roster,1:self.tactics[0][1],2:self.table}[index]
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
    self.squad_summary.setText(f'Squad · 20 players\nStarting XI · {len(selected)} / 11    Bench · {20-len(selected)}\nSelect a row for raw player detail. Changes take effect when you confirm.')
    groups={}
    for row in rows:
        if row['id'] in selected:
            name=row['name']+(' · Captain' if row['id']==captain else '')
            groups.setdefault(row['position'],[]).append(name)
    self.lineup_board.setText(f'Starting XI · {len(selected)}\nGrouped by position.\n'+ '\n'.join(f'{group} · {len(names)}\n'+', '.join(names) for group,names in groups.items()))
    self.bench_board.setText(f'Bench · {20-len(selected)}\n'+ '\n'.join(row['name']+' · '+row['position'] for row in rows if row['id'] not in selected))
    # [derived: goal2/game/country_card.py] The formation is counted from the drafted eleven's
    # lines (defence, midfield, attack); nothing is stored.
    eleven=[row for row in rows if row['id'] in selected]
    formation='-'.join(str(sum(1 for row in eleven if row['line']==line)) for line in ('defence','midfield','attack'))
    self.tactics_heading.setText(f"{self.display_model.goaldat.country_names[state.managed_country].upper()} / XI {len(selected)} / {formation}")
    self.tactics_manager.setText('Manager: '+self.display_model.manager.split(' (')[0])
    current=max(0,self.table.currentRow());roster=roster_rows(self,rows,selected,captain)
    self.team_roster.set_rows(roster,current);self.country_roster.set_rows(roster,current)
    from goal2.game.player_card import card
    self.team_card.set_card(card(self.display_model.state,rows[current]['id'],self.display_model.goaldat,team_tactics=self.draft()[2]))
    ready=sum(1 for r in rows if r['availability']['available'])
    self.desk_readiness.setText(f'{ready} ready / XI {len(selected)}')
    self.desk_captain.setText('Captain: '+(next((n for w,n,*_ in roster if w==captain),'chosen at kickoff') if captain else 'chosen at kickoff'))
    row=rows[current];availability=row['availability']
    reason=', '.join(availability['reasons']) or 'Available'
    if availability['carried_bookings']:reason+='; carried booking'
    self.player_detail.setText(f"Player detail · {row['name']}\nID {row['id']} · {row['position']}"+(' · Captain' if row['id']==captain else '')+f"\nRole {row['role']} · club {row['club_role']} · Energy {row['energy']} · Confidence {row['confidence']}\nAvailability: {reason}")
    if hasattr(self,'lineup_own'):
        from goal2.desktop.fixtures_page import refresh_preparation
        refresh_preparation(self)
