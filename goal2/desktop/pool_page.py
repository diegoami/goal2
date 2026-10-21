"""[designed: T77] Focused pool presentation over the existing exchange callback."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,
 QPushButton,QComboBox,QTableWidget,QHeaderView,QLineEdit)


def label(name,accessible):
    result=QLabel();result.setObjectName(name);result.setAccessibleName(accessible)
    result.setWordWrap(True);result.setTextFormat(Qt.TextFormat.PlainText)
    result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return result


def build(self,model,TACTICS):
    page=self.pages[2];layout=page.content
    pool_panel=QWidget();pool_layout=QVBoxLayout(pool_panel);self.pool_panel=pool_panel
    self.pool_summary=label('poolSummary','National pool membership');pool_layout.addWidget(self.pool_summary)
    outgoing=QLabel('Outgoing squad player · selection only, confirmed XI stays unchanged');outgoing.setWordWrap(True);pool_layout.addWidget(outgoing)
    self.pool_outgoing=QComboBox();self.pool_outgoing.setObjectName('poolOutgoing');self.pool_outgoing.setAccessibleName('Outgoing squad player');pool_layout.addWidget(self.pool_outgoing)
    filter_bar=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search reserve name')
    self.position=QComboBox();self.position.addItem('All position codes',None)
    # [confirmed: F002 DS:69A8/69B6] The original's codes and position names.
    from goal2.game import roles
    for value,(code,name) in enumerate(zip(roles.tables(model.state)[0],roles.names(model.state))):self.position.addItem(f'{code} · {name}',value)
    filter_bar.addWidget(self.search,1);filter_bar.addWidget(self.position);pool_layout.addLayout(filter_bar)
    self.reserves=QTableWidget(0,7);self.reserves.setObjectName('reserves')
    self.reserves.setHorizontalHeaderLabels(['ID','Player','Role','Position','Energy','Confidence','Availability'])
    self.reserves.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.reserves.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
    self.reserves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    self.reserves.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
    self.reserves.verticalHeader().setDefaultSectionSize(40)
    pool_layout.addWidget(self.reserves,1)
    self.pool_detail=label('poolDetail','Selected reserve detail');pool_layout.addWidget(self.pool_detail)
    self.exchange_summary=label('exchangeSummary','Selected exchange identities');pool_layout.addWidget(self.exchange_summary)
    self.reserves.setTabKeyNavigation(False);self.reserves.setMinimumHeight(220);layout.addWidget(pool_panel)
    footer=QWidget();footer.setObjectName('poolActionBar');bar=QVBoxLayout(footer);bar.setContentsMargins(8,8,8,8)
    self.pool_policy=label('poolPolicy','Exchange policy and context');bar.addWidget(self.pool_policy)
    self.exchange=QPushButton('Exchange selected squad player and reserve');self.exchange.setObjectName('exchange');bar.addWidget(self.exchange)
    page.set_footer(footer)
    self.pool_outgoing.currentIndexChanged.connect(lambda *args:outgoing_changed(self))
    self.table.currentCellChanged.connect(lambda *args:table_changed(self))
    self.reserves.currentCellChanged.connect(lambda *args:selection(self))


def outgoing_changed(self):
    if self._refreshing:return
    word=self.pool_outgoing.currentData()
    for row in range(self.table.rowCount()):
        item=self.table.item(row,0)
        if item is not None and item.data(Qt.ItemDataRole.UserRole)==word:
            self.table.setCurrentCell(row,1);break
    selection(self)


def table_changed(self):
    if self._refreshing:return
    row=self.table.currentRow();item=self.table.item(row,0) if row>=0 else None
    word=item.data(Qt.ItemDataRole.UserRole) if item else None
    self.pool_outgoing.blockSignals(True);self.pool_outgoing.setCurrentIndex(self.pool_outgoing.findData(word));self.pool_outgoing.blockSignals(False)
    selection(self)


def refresh(self):
    """[designed: T77] Rebuilt filtered rows have no inherited incoming identity."""
    rows=self.display_model.pool_view()
    outgoing=self.table.item(self.table.currentRow(),0) if self.table.currentRow()>=0 else None
    word=outgoing.data(Qt.ItemDataRole.UserRole) if outgoing else None
    self.pool_outgoing.blockSignals(True);self.pool_outgoing.clear()
    for row in (rows['squad'] if rows else []):self.pool_outgoing.addItem(f"{row['name']} · ID {row['id']}",row['id'])
    self.pool_outgoing.setCurrentIndex(self.pool_outgoing.findData(word));self.pool_outgoing.blockSignals(False)
    self.reserves.clearSelection();self.reserves.setCurrentCell(-1,-1)
    selection(self);context(self)


def selection(self):
    if self._refreshing:return
    view=self.display_model.pool_view();rows=view['reserves'] if view else []
    index=self.reserves.currentRow();item=self.reserves.item(index,0) if index>=0 else None
    incoming=item.data(Qt.ItemDataRole.UserRole) if item else None
    row=next((r for r in rows if r['id']==incoming),None)
    if row:
        reason=', '.join(row['availability']['reasons']) or 'Available'
        self.pool_detail.setText(f"Reserve detail · {row['name']}\nID {row['id']} · Role {row['role']} (club {row['club_role']}) · {row['position_group']}\nEnergy {row['energy']} · Confidence {row['confidence']}\nAvailability: {reason}")
    else:self.pool_detail.setText('No incoming reserve selected. Select a visible reserve row.')
    outgoing=self.pool_outgoing.currentData();player=next((r for r in (view['squad'] if view else []) if r['id']==outgoing),None)
    outgoing_text='No outgoing squad player selected'
    if player:
        reason=', '.join(player['availability']['reasons']) or 'Available'
        outgoing_text=f"Outgoing · {player['name']} · ID {outgoing}\nRole {player['role']} (club {player['club_role']}) · {player['position_group']} · Energy {player['energy']} · Confidence {player['confidence']}\nAvailability: {reason}"
    self.exchange_summary.setText(outgoing_text+'\n'+(f"Incoming · {row['name']} · ID {incoming}" if row else 'No incoming reserve selected'))


def context(self,busy=False):
    """[designed: T77] Context explains existing guards without changing policy."""
    if busy or getattr(self.model,'match_pending',False):reason='Finish or cancel the match first'
    elif self.jobs.busy or self.competitive.busy or self.watched.busy:reason='Finish or cancel the match first'
    elif self.preview is not None:reason='Preview: return to the active game to exchange players'
    elif self.model.state.campaign is None:reason='Campaign required · standalone friendly has no national pool'
    else:reason=self.model.pool_view()['window']['reason']
    self.pool_policy.setText(reason)
    self.exchange.setEnabled(not busy and self.preview is None and not getattr(self.model,'match_pending',False) and not self.jobs.busy and not self.competitive.busy and not self.watched.busy and self.model.state.campaign is not None and self.model.pool_view()['window']['allowed'])
