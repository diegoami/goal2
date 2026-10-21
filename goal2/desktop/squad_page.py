"""[designed: T76] Readable squad draft over existing source-order controls."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QCheckBox)


def reading_label(name):
    label=QLabel();label.setObjectName(name);label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def build(self,model,TACTICS):
    page=self.pages[1];layout=page.content
    # [designed: T91; accepted vision #266 screen 03] The twenty beside the selected player's
    # complete card (T88). The table, boards and controls below are the attribute table.
    from goal2.desktop.roster import Columns,RosterView
    from goal2.desktop.player_card import PlayerCardView
    from PySide6.QtWidgets import QScrollArea
    team=Columns(1096);team.setObjectName('teamDesk');layout.addWidget(team)
    self.team_roster=RosterView('SQUAD');self.team_roster.setFixedWidth(320);self.team_roster.setAccessibleDescription('Up/Down: select; Space: in or out of the XI')
    team.box.addWidget(self.team_roster,0,Qt.AlignmentFlag.AlignTop)
    self.team_card=PlayerCardView();card_area=QScrollArea();card_area.setObjectName('teamCard')
    card_area.setWidgetResizable(True);card_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    card_area.setFrameShape(QScrollArea.Shape.NoFrame)
    card_area.setWidget(self.team_card);card_area.setMinimumHeight(644);team.box.addWidget(card_area,1)
    from PySide6.QtGui import QKeySequence,QShortcut
    actions=QHBoxLayout();layout.addLayout(actions)
    self.rename=QPushButton('Rename (F2)');self.rename.setObjectName('renamePlayer');self.rename.setAccessibleName('Rename the selected player')
    self.rename.clicked.connect(self.rename_selected);actions.addWidget(self.rename);actions.addStretch(1)
    # [confirmed: E031 C30] F2 renames the player on the card; here, on the Team page.
    self.rename_shortcut=QShortcut(QKeySequence('F2'),self)
    self.rename_shortcut.activated.connect(lambda:self.page_stack.currentIndex()==1 and self.rename_selected())
    self.team_roster.current_changed.connect(lambda row:self.table.setCurrentCell(row,1))
    self.team_roster.toggled.connect(lambda row:toggle(self,row))
    self.squad_summary=reading_label('squadSummary');layout.addWidget(self.squad_summary)
    self.table=QTableWidget(20,7);self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Role','Position','Energy','Confidence','Availability'])
    self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
    self.table.setTabKeyNavigation(False);self.table.setMinimumHeight(240)
    self.table.verticalHeader().setDefaultSectionSize(40);layout.addWidget(self.table)
    self.player_detail=reading_label('playerDetail');self.player_detail.setAccessibleName('Selected player detail');layout.addWidget(self.player_detail)
    self.lineup_board=reading_label('lineupBoard');self.lineup_board.setAccessibleName('Starting XI grouped by position');layout.addWidget(self.lineup_board)
    self.bench_board=reading_label('benchBoard');self.bench_board.setAccessibleName('Bench');layout.addWidget(self.bench_board)
    captain_bar=QHBoxLayout();captain_bar.addWidget(QLabel('Captain'));self.captain=QComboBox();self.captain.setObjectName('captain');captain_bar.addWidget(self.captain,1);layout.addLayout(captain_bar)
    heading=QLabel('Team tactics · unchecked / checked alternatives');heading.setWordWrap(True);layout.addWidget(heading)
    self.tactics=[];tactics=QVBoxLayout()
    for element,label in TACTICS:
        box=QCheckBox(label);box.setObjectName(f'tactic{element}')
        self.tactics.append((element,box));tactics.addWidget(box,0,Qt.AlignmentFlag.AlignLeft)
    layout.addLayout(tactics)
    footer=QWidget();footer.setObjectName('draftBar');bar=QHBoxLayout(footer);bar.setContentsMargins(8,8,8,8)
    self.draft_state=reading_label('draftState');self.draft_state.setAccessibleName('Management draft state');bar.addWidget(self.draft_state,1)
    self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm')
    self.cancel=QPushButton('Discard draft');self.cancel.setObjectName('discard')
    for action in (self.cancel,self.confirm):action.setAutoDefault(True);bar.addWidget(action)
    page.set_footer(footer)


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
