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
    page=self.pages[2]
    # [designed: T101] The Pool page has two views on the fixed page: 0 the pool browser (the
    # outgoing player, the filters, the reserves, the selected detail and the exchange), 1 the two
    # complete cards (Cards: OUT, the squad player, and IN, the pool reserve, one at a time as the
    # original's pool screen toggles between squad and pool [confirmed:
    # `docs/original-game/images/m244-pool.png`]). The exchange bar stays below both; Esc returns.
    self.pool_views,(browser,cards_box)=page.add_views('poolViews',('poolBrowser','poolCardsView'))
    self.pool_views.show_view=lambda index:pool_view(self,index)
    from goal2.desktop.player_card import PlayerCardView
    from PySide6.QtWidgets import QStackedWidget,QButtonGroup
    pool_panel=QWidget();pool_layout=QVBoxLayout(pool_panel);pool_layout.setContentsMargins(0,0,0,0);pool_layout.setSpacing(8);self.pool_panel=pool_panel
    self.pool_summary=label('poolSummary','National pool membership');pool_layout.addWidget(self.pool_summary)
    outgoing_bar=QHBoxLayout();outgoing=QLabel('Outgoing squad player · selection only, confirmed XI stays unchanged');outgoing.setWordWrap(True)
    outgoing_bar.addWidget(outgoing,1)
    self.pool_outgoing=QComboBox();self.pool_outgoing.setObjectName('poolOutgoing');self.pool_outgoing.setAccessibleName('Outgoing squad player');outgoing_bar.addWidget(self.pool_outgoing,1)
    pool_layout.addLayout(outgoing_bar)
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
    self.reserves.horizontalHeader().setStretchLastSection(True)
    self.reserves.verticalHeader().setDefaultSectionSize(30);self.reserves.verticalHeader().hide()
    # [designed: T101; confirmed: `docs/original-game/images/m244-pool.png`] As the original's pool
    # list, the eighty reserves are a window of rows that follows the selection (arrows, Page
    # Up/Down, the wheel); the fixed page shows no scroll bar.
    for policy in (self.reserves.setVerticalScrollBarPolicy,self.reserves.setHorizontalScrollBarPolicy):policy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    pool_layout.addWidget(self.reserves,1)
    details=QHBoxLayout();details.setSpacing(16);pool_layout.addLayout(details)
    self.pool_detail=label('poolDetail','Selected reserve detail');details.addWidget(self.pool_detail,1)
    self.exchange_summary=label('exchangeSummary','Selected exchange identities');details.addWidget(self.exchange_summary,1)
    self.reserves.setTabKeyNavigation(False);self.reserves.setMinimumHeight(220);browser.addWidget(pool_panel,1)
    # View 1: the two complete cards, OUT and IN, one at a time.
    toggle=QHBoxLayout();cards_box.addLayout(toggle)
    self.pool_cards=QStackedWidget();self.pool_cards.setObjectName('poolCards')
    self.pool_out_card=PlayerCardView();self.pool_in_card=PlayerCardView();self.pool_card_buttons=QButtonGroup(cards_box.parentWidget())
    for number,(view,caption,name) in enumerate(((self.pool_out_card,'OUT · squad player','Outgoing player card'),(self.pool_in_card,'IN · pool reserve','Incoming player card'))):
        button=QPushButton(caption);button.setObjectName('poolCardOut' if number==0 else 'poolCardIn');button.setCheckable(True)
        button.setAccessibleName('Show the '+name.lower());self.pool_card_buttons.addButton(button,number);toggle.addWidget(button)
        button.clicked.connect(lambda checked=False,i=number:self.pool_cards.setCurrentIndex(i))
        view.setAccessibleDescription(name);self.pool_cards.addWidget(view)
    self.pool_card_buttons.button(0).setChecked(True);self.pool_cards.currentChanged.connect(lambda i:self.pool_card_buttons.button(i).setChecked(True))
    toggle.addStretch(1)
    self.pool_cards_back=QPushButton('< Pool (Esc)');self.pool_cards_back.setObjectName('poolCardsBack');self.pool_cards_back.setAccessibleName('Back to the pool')
    self.pool_cards_back.clicked.connect(lambda:pool_view(self,0));toggle.addWidget(self.pool_cards_back)
    cards_box.addWidget(self.pool_cards,0,Qt.AlignmentFlag.AlignLeft);cards_box.addStretch(1)
    footer=QWidget();footer.setObjectName('poolActionBar');bar=QHBoxLayout(footer);bar.setContentsMargins(8,8,8,8);bar.setSpacing(8)
    self.pool_policy=label('poolPolicy','Exchange policy and context');bar.addWidget(self.pool_policy,1)
    self.pool_cards_route=QPushButton('Cards >');self.pool_cards_route.setObjectName('poolCardsRoute');self.pool_cards_route.setAccessibleName('Show the outgoing and incoming cards')
    self.pool_cards_route.clicked.connect(lambda:pool_view(self,1));bar.addWidget(self.pool_cards_route)
    self.exchange=QPushButton('Exchange selected squad player and reserve');self.exchange.setObjectName('exchange');bar.addWidget(self.exchange)
    page.set_footer(footer)
    def escape():
        if self.pool_views.currentIndex()!=0:
            pool_view(self,0);return True
        return False
    page.escape=escape

    self.pool_outgoing.currentIndexChanged.connect(lambda *args:outgoing_changed(self))
    self.table.currentCellChanged.connect(lambda *args:table_changed(self))
    self.reserves.currentCellChanged.connect(lambda *args:selection(self))


def pool_view(self,index):
    """[designed: T101] Show Pool view `index` (0 the browser, 1 the cards); presentation only."""
    self.pool_views.setCurrentIndex(index)
    if self.page_stack.currentIndex()!=2:return
    target={0:self.pool_outgoing,1:self.pool_card_buttons.button(self.pool_cards.currentIndex())}[index]
    if not target.isEnabled():target=self.pages[2].heading
    target.setFocus(Qt.FocusReason.ShortcutFocusReason)


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
    from goal2.game.player_card import card
    display=self.display_model
    self.pool_out_card.set_card(card(display.state,outgoing,display.goaldat) if player else None)
    self.pool_in_card.set_card(card(display.state,incoming,display.goaldat) if row else None)
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


# -- the core route (T107) -------------------------------------------------------------------------------------------
# [designed: owner, 2026-10-22, decisions 5 and 7; T107; confirmed: `docs/original-game/images/m244-pool.png`,
# 0791:E44F/E2E6] Over the core the Pool page copies SELECT YOUR TEAM's pool side: the card of the highlighted player
# on the left and a strip on the right that shows the squad or the pool of eighty (21 rows at a time, as the
# original's list), Left/Right toggling the two as the original's ←→ does. Enter marks a player and Enter on another
# moves him (0791:DEA6): a squad and a pool player exchange, as a driver job; the original's refusal is shown.
POOL_ROWS = 21                     # [confirmed: 0791:E2E6] the pool list shows rows top..top+20


def _strip_class():
    from PySide6.QtCore import Signal
    from goal2.desktop.core_pool_roster import PoolRoster as RosterView

    class ListStrip(RosterView):
        """A RosterView over a window of a longer list: Up/Down past an end, PgUp/PgDn, Home/End scroll it
        (`scrolled(delta)`), Left/Right switch the list (`switched()`)."""
        scrolled = Signal(int)
        switched = Signal()

        def keyPressEvent(self, event):
            key = event.key();position = self.order.index(self.current) if self.current in self.order else 0
            if key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                self.switched.emit()
            elif key == Qt.Key.Key_Down and position == len(self.order) - 1:
                self.scrolled.emit(1)
            elif key == Qt.Key.Key_Up and position == 0:
                self.scrolled.emit(-1)
            elif key in (Qt.Key.Key_PageDown, Qt.Key.Key_PageUp):
                self.scrolled.emit(POOL_ROWS if key == Qt.Key.Key_PageDown else -POOL_ROWS)
            else:
                super().keyPressEvent(event)
    return ListStrip


def build_core(self, model):
    from goal2.desktop.player_card import PlayerCardView
    page = self.pages[2]
    body = QHBoxLayout();body.setSpacing(16);page.content.addLayout(body, 1)
    left = QVBoxLayout();left.setSpacing(8);body.addLayout(left, 1)
    self.pool_card = PlayerCardView(compact=True);self.pool_card.setObjectName('poolCard');left.addWidget(self.pool_card)
    self.pool_marked_line = label('poolMarked', 'The marked player')
    left.addWidget(self.pool_marked_line)
    bar = QHBoxLayout();left.addLayout(bar)
    self.pool_switch = QPushButton('Squad / pool (←→)');self.pool_switch.setObjectName('poolSwitch')
    self.pool_switch.setAccessibleName('Switch between the squad and the pool')
    self.pool_switch.clicked.connect(lambda: core_switch(self))
    self.pool_move = QPushButton('Move player (Enter)');self.pool_move.setObjectName('poolMove')
    self.pool_move.setAccessibleName('Mark the highlighted player, or move the marked one to him')
    self.pool_move.clicked.connect(lambda: core_pool_enter(self))
    bar.addWidget(self.pool_switch);bar.addWidget(self.pool_move);bar.addStretch(1);left.addStretch(1)
    self.pool_strip = _strip_class()('POOL', toggles=False, capacity=POOL_ROWS, marks=False)
    self.pool_strip.setObjectName('poolStrip');self.pool_strip.setFixedWidth(314)
    self.pool_strip.setAccessibleDescription('Up/Down: select; Left/Right: squad or pool; Enter: mark, then move')
    body.addWidget(self.pool_strip, 0, Qt.AlignmentFlag.AlignTop)
    self.pool_side, self.pool_top = 'pool', 0
    self.pool_strip.current_changed.connect(lambda row: core_pool_card(self))
    self.pool_strip.activated.connect(lambda row: core_pool_enter(self))
    self.pool_strip.switched.connect(lambda: core_switch(self))
    self.pool_strip.scrolled.connect(lambda delta: core_scroll(self, delta))
    self.pool_selected = lambda: (self.pool_strip.rows[self.pool_strip.current][0]
                                  if 0 <= self.pool_strip.current < len(self.pool_strip.rows) else None)


def core_switch(self):
    self.pool_side = 'squad' if self.pool_side == 'pool' else 'pool'
    self.pool_strip.current = 0;refresh_core(self)


def core_scroll(self, delta):
    total = len(self.model.pool()['rows'])
    top = max(0, min(total - POOL_ROWS, self.pool_top + delta))
    if top != self.pool_top:
        current = self.pool_strip.current
        self.pool_top = top;refresh_core(self)
        self.pool_strip.set_current(current, notify=True);core_pool_card(self)


def core_pool_enter(self):
    from goal2.desktop.squad_page import core_mark
    if self.pool_strip.current >= 0 and self.pool_strip.rows:
        core_mark(self, self.pool_strip, self.pool_strip.current, self.pool_side)
        core_marked_line(self)


def core_marked_line(self):
    marked = self.core_marked
    if marked is None:
        self.pool_marked_line.setText('Enter marks a player; Enter on another moves him (squad ⇄ pool)')
    else:
        self.pool_marked_line.setText(f"Marked: {self.model.card(marked[1])['name']} ({marked[0]}); Enter on a "
                                      f"{'pool' if marked[0] == 'squad' else 'squad'} player to move him")


def core_pool_card(self):
    from goal2.desktop.player_card import core_card
    player = self.pool_selected()
    self.pool_card.set_card(core_card(self.model.card(player)) if player else None)


def refresh_core(self):
    from goal2.desktop.core_roles import role_code
    from goal2.desktop.core_pool_roster import caps_for
    if self.pool_side == 'squad':
        rows = [(r['player'], r['name'], role_code(r), r['line'], r['eleven'], False) for r in self.model.team()['squad']]
        self.pool_strip.capacity = 20;self.pool_strip.caption = 'YOUR SQUAD'
    else:
        pool = self.model.pool()['rows']
        rows = [(r['player'], r['name'], role_code(r), r['line'], False, False)
                for r in pool[self.pool_top:self.pool_top + POOL_ROWS]]
        self.pool_strip.capacity = POOL_ROWS
        self.pool_strip.caption = f'POOL {self.pool_top + 1}-{self.pool_top + len(rows)}/{len(pool)}'
    current = self.pool_strip.current if 0 <= self.pool_strip.current < len(rows) else 0
    self.pool_strip.caps = caps_for(self.model.state, (r[0] for r in rows))
    self.pool_strip.set_rows(rows, current)
    core_pool_card(self);core_marked_line(self)
