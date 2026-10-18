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
    self.squad_summary=reading_label('squadSummary');layout.addWidget(self.squad_summary)
    self.table=QTableWidget(20,7);self.table.setObjectName('squad')
    self.table.setHorizontalHeaderLabels(['XI','Player','Position','Ability','Energy','Confidence','Availability'])
    self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
    self.table.setTabKeyNavigation(False);self.table.setMinimumHeight(340)
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
    row=rows[max(0,self.table.currentRow())];availability=row['availability']
    reason=', '.join(availability['reasons']) or 'Available'
    if availability['carried_bookings']:reason+='; carried booking'
    self.player_detail.setText(f"Player detail · {row['name']}\nID {row['id']} · {row['position']}"+(' · Captain' if row['id']==captain else '')+f"\nAbility {row['ability']} · Energy {row['energy']} · Confidence {row['confidence']}\nAvailability: {reason}")
