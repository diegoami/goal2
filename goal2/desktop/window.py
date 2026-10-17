"""[designed: T69] Native Qt management widgets; drafts never mutate the game.
[derived: F010] Tactics elements1..4; remaining labels retain rebuild policy.
"""
from PySide6.QtCore import Qt,QTimer
from goal2.desktop.jobs import QuickJobs
from PySide6.QtWidgets import (QCheckBox,QComboBox,QHeaderView,QHBoxLayout,QLabel,
 QLineEdit,QMainWindow,QPushButton,QSplitter,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)

# [confirmed: F010] Display order5,6,7,1,2,3,4,8. [designed] Labels5..8.
TACTICS=((5,'Half pitch / full pitch'),(6,'Short kicks / long kicks'),(7,'Stay back / push forward'),
         (1,'Stay back / push forward'),(2,'Keep ball / quick pass'),(3,'Short passes / long passes'),
         (4,'Avoid injury / go in hard'),(8,'Zone / man to man'))


class ManagementWindow(QMainWindow):
    """[designed] All widget access and active-state publication stay on the Qt thread."""
    def __init__(self,model):
        super().__init__();self.model=model;self._refreshing=False;self.preview=None;self.active_draft=None
        self.jobs=QuickJobs(model);self.timer=QTimer(self);self.timer.setInterval(30);self.timer.timeout.connect(self.poll_match)
        self.setWindowTitle('goal2 — Country management');self.resize(1050,780)
        root=QWidget();self.setCentralWidget(root);layout=QVBoxLayout(root)
        self.title=QLabel();self.title.setStyleSheet('font-size:22px;font-weight:600')
        layout.addWidget(self.title)
        country_bar=QHBoxLayout();self.country=QComboBox();self.country.setObjectName('country')
        for number,name in model.view()['countries']:self.country.addItem(name,number)
        self.new=QPushButton('New campaign');self.new.setObjectName('newCampaign')
        self.friendly=QPushButton('New standalone friendly');country_bar.addWidget(self.friendly)
        country_bar.addWidget(QLabel('Country'));country_bar.addWidget(self.country,1);country_bar.addWidget(self.new);layout.addLayout(country_bar)
        self.summary=QLabel();layout.addWidget(self.summary)
        self.standings_dialog=None
        self.standings=QPushButton('Competition table');self.standings.setObjectName('showStandings')
        self.standings.clicked.connect(self.show_standings);layout.addWidget(self.standings)
        self.table=QTableWidget(20,7);self.table.setObjectName('squad')
        self.table.setHorizontalHeaderLabels(['XI','Player','Position','Ability','Energy','Confidence','Availability'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        # [designed: T71] Show the existing squad beside its source reserve pool.
        split=QSplitter();split.addWidget(self.table)
        pool_panel=QWidget();pool_layout=QVBoxLayout(pool_panel);self.pool_panel=pool_panel
        self.pool_summary=QLabel();self.pool_summary.setWordWrap(True);pool_layout.addWidget(self.pool_summary)
        filter_bar=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Search reserve name')
        self.position=QComboBox();self.position.addItem('All position codes',None)
        for code in range(14):self.position.addItem(f'Position code {code}',code)
        filter_bar.addWidget(self.search,1);filter_bar.addWidget(self.position);pool_layout.addLayout(filter_bar)
        self.reserves=QTableWidget(0,7);self.reserves.setObjectName('reserves')
        self.reserves.setHorizontalHeaderLabels(['ID','Player','Position','Ability','Energy','Confidence','Availability'])
        self.reserves.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.reserves.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.reserves.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.reserves.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        pool_layout.addWidget(self.reserves,1)
        self.exchange=QPushButton('Exchange selected squad player and reserve');pool_layout.addWidget(self.exchange)
        split.addWidget(pool_panel);split.setSizes([620,620]);layout.addWidget(split,1)
        captain_bar=QHBoxLayout();captain_bar.addWidget(QLabel('Captain'));self.captain=QComboBox();self.captain.setObjectName('captain');captain_bar.addWidget(self.captain,1)
        self.confirm=QPushButton('Confirm management');self.confirm.setObjectName('confirm');self.cancel=QPushButton('Discard draft')
        captain_bar.addWidget(self.cancel);captain_bar.addWidget(self.confirm);layout.addLayout(captain_bar)
        self.tactics=[]
        for start in (0,4):
            bar=QHBoxLayout()
            for element,label in TACTICS[start:start+4]:
                box=QCheckBox(label);box.setObjectName(f'tactic{element}');self.tactics.append((element,box));bar.addWidget(box)
            layout.addLayout(bar)
        save_bar=QHBoxLayout();save_bar.addWidget(QLabel('Save file'));self.path=QLineEdit(str(model.save_path));self.path.setObjectName('savePath');save_bar.addWidget(self.path,1)
        self.save=QPushButton('Save');self.save.setObjectName('save');self.resume=QPushButton('Resume');self.resume.setObjectName('resume');save_bar.addWidget(self.save);save_bar.addWidget(self.resume);layout.addLayout(save_bar)
        play_bar=QHBoxLayout();self.play=QPushButton('Play quick friendly');self.stop=QPushButton('Cancel match');self.stop.setEnabled(False)
        play_bar.addWidget(self.play);play_bar.addWidget(self.stop);layout.addLayout(play_bar)
        half_bar=QHBoxLayout();self.half_out=QComboBox();self.half_in=QComboBox()
        self.substitute=QPushButton('Substitute');self.continue_match=QPushButton('Continue second half')
        half_bar.addWidget(QLabel('Off'));half_bar.addWidget(self.half_out);half_bar.addWidget(QLabel('On'));half_bar.addWidget(self.half_in)
        half_bar.addWidget(self.substitute);half_bar.addWidget(self.continue_match)
        for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(False)
        layout.addLayout(half_bar);self.half_preview=None
        self.substitute.clicked.connect(self.substitute_halftime);self.continue_match.clicked.connect(self.continue_halftime)
        self.result=QLabel();self.result.setWordWrap(True);self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.result)
        self.status=QLabel('Confirm management, then play a quick friendly or save.');self.status.setWordWrap(True);self.status.setObjectName('status');layout.addWidget(self.status)
        self.new.clicked.connect(lambda:self.action(lambda:model.new_campaign(self.country.currentData()),'New campaign created',replace=True))
        self.friendly.clicked.connect(lambda:self.action(lambda:model.new_friendly(self.country.currentData()),'New standalone friendly created',replace=True))
        self.play.clicked.connect(self.start_match);self.stop.clicked.connect(self.cancel_match)
        self.confirm.clicked.connect(self.confirm_draft);self.cancel.clicked.connect(lambda:self.refresh('Draft discarded'))
        self.save.clicked.connect(lambda:self.action(lambda:model.save(self.path.text()),'Game saved; unconfirmed edits are excluded'))
        self.resume.clicked.connect(lambda:self.action(lambda:model.resume(self.path.text()),'Game resumed',replace=True))
        self.search.textChanged.connect(self.refresh_pool);self.position.currentIndexChanged.connect(self.refresh_pool)
        self.exchange.clicked.connect(self.exchange_selected)
        self.table.itemChanged.connect(self.selection_changed)
        self.refresh()
        self.country.currentIndexChanged.connect(self.country_changed)

    @property
    def display_model(self):
        # [designed: #181] A preview owns generated records, never the active game.
        return self.preview if self.preview is not None else self.model

    def draft(self):
        return (self.selected_ids(),self.captain.currentData(),
                sum(1<<(element-1) for element,box in self.tactics if box.isChecked()))

    def apply_draft(self,draft):
        eleven,captain,bits=draft;self._refreshing=True
        for row in range(20):
            item=self.table.item(row,0)
            item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in eleven else Qt.CheckState.Unchecked)
        self.update_captain();self.captain.setCurrentIndex(max(0,self.captain.findData(captain)))
        for element,box in self.tactics:box.setChecked(bool(bits & (1<<(element-1))))
        self._refreshing=False

    def country_changed(self):
        if self._refreshing:return
        country=self.country.currentData()
        if self.jobs.busy:
            self._refreshing=True;self.country.setCurrentIndex(self.country.findData(self.model.state.managed_country));self._refreshing=False
            return
        try:
            if country==self.model.state.managed_country:
                self.preview=None;self.refresh('Active game; previous management draft restored')
                if self.active_draft is not None:self.apply_draft(self.active_draft)
                self.active_draft=None
            else:
                from goal2.desktop.model import DesktopModel
                candidate=DesktopModel(self.model.goaldat,self.model.template_bytes,self.model.save_path)
                candidate.new_campaign(country)
                if self.preview is None:self.active_draft=self.draft()
                self.preview=candidate;self.refresh()
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self._refreshing=True;self.country.setCurrentIndex(self.country.findData(self.display_model.state.managed_country));self._refreshing=False
            self.status.setText(str(exc))

    def require_active(self):
        if self.jobs.busy:
            self.status.setText('Finish or cancel the match first');return False
        if self.preview is not None:
            self.status.setText('Fresh campaign preview: choose New campaign or New standalone friendly to manage this team, or return to the active country.');return False
        return True

    def selected_ids(self):
        return [self.table.item(row,0).data(Qt.ItemDataRole.UserRole) for row in range(20)
                if self.table.item(row,0).checkState()==Qt.CheckState.Checked]

    def selection_changed(self,item):
        if self._refreshing or item.column()!=0:return
        if not item.data(Qt.ItemDataRole.UserRole+1) and item.checkState()==Qt.CheckState.Checked:
            self._refreshing=True;item.setCheckState(Qt.CheckState.Unchecked);self._refreshing=False
            self.status.setText('Unavailable players cannot start')
        if not item.data(Qt.ItemDataRole.UserRole+1):
            self._refreshing=True
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            self._refreshing=False
        self.update_captain()

    def update_captain(self):
        previous=self.captain.currentData();selected=self.selected_ids()
        self.captain.clear()
        for word in selected:self.captain.addItem(self.model.goaldat.player_names[word],word)
        self.captain.setCurrentIndex(max(0,self.captain.findData(previous)))

    def refresh(self,message=None):
        if self.standings_dialog is not None:
            self.standings_dialog.close();self.standings_dialog=None
        display=self.display_model;view=display.view();state=display.state;self._refreshing=True
        self.title.setText(view['country_name']);self.country.setCurrentIndex(self.country.findData(view['country']))
        self.result.setText('Quick simulation (rebuild setup)\n'+display.result_text())
        self.summary.setText(f"Team morale: {view['morale']}     Next fixture: {view['fixture'] or ('Standalone friendly' if state.campaign is None else 'No supported fixture')}")
        for row,p in enumerate(view['players']):
            available=p['availability']['available'];selected=p['id'] in state.starting_eleven
            item=QTableWidgetItem();item.setData(Qt.ItemDataRole.UserRole,p['id']);item.setData(Qt.ItemDataRole.UserRole+1,available)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable| (Qt.ItemFlag.ItemIsUserCheckable if available or selected else Qt.ItemFlag.NoItemFlags))
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked);self.table.setItem(row,0,item)
            reason=', '.join(p['availability']['reasons']) or 'Available'
            if p['availability']['carried_bookings']:reason+='; carried booking'
            for col,value in enumerate((p['name'],p['position'],p['ability'],p['energy'],p['confidence'],reason),1):
                cell=QTableWidgetItem(str(value));cell.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);self.table.setItem(row,col,cell)
        self.update_captain();self.captain.setCurrentIndex(max(0,self.captain.findData(state.captain)))
        for element,box in self.tactics:box.setChecked(bool(state.country_tactics & (1<<(element-1))))
        self.path.setText(str(self.model.save_path));self._refreshing=False
        self.refresh_pool()
        self.set_busy(self.jobs.busy)
        if self.preview is not None:self.require_active()
        elif message:self.status.setText(message)

    def show_standings(self):
        """[designed: T49] Render a pure snapshot, closing it when the active game refreshes."""
        if not self.require_active():return
        from goal2.desktop.standings import CompetitionTable
        try:
            view=self.model.competition_table()
            if view is None:
                self.status.setText('Competition table unavailable: this session has no complete opening group schedule')
                return
            if self.standings_dialog is not None:self.standings_dialog.close()
            self.standings_dialog=CompetitionTable(view,self);self.standings_dialog.show()
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def action(self,operation,message,*,replace=False):
        if self.jobs.busy or (not replace and not self.require_active()):return
        try:
            operation()
            if replace:self.preview=None;self.active_draft=None
            self.refresh(message)
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def confirm_draft(self):
        if not self.require_active():return
        bits=sum(1<<(element-1) for element,box in self.tactics if box.isChecked())
        self.action(lambda:self.model.confirm(self.selected_ids(),self.captain.currentData(),bits),'Management confirmed')

    def set_busy(self,busy):
        # [designed: T70] Prevent conflicting edits while keeping the UI responsive.
        for widget in (self.country,self.new,self.friendly,self.resume,self.path):widget.setEnabled(not busy)
        active=not busy and self.preview is None
        for widget in (self.table,self.captain,self.confirm,self.cancel,self.save,self.pool_panel,self.play,self.standings):widget.setEnabled(active)
        for _,box in self.tactics:box.setEnabled(active)
        self.stop.setEnabled(busy)

    def start_match(self):
        if not self.require_active():return
        try:
            bits=sum(1<<(element-1) for element,box in self.tactics if box.isChecked())
            state=self.model.state
            if (self.selected_ids()!=state.starting_eleven or self.captain.currentData()!=state.captain or bits!=state.country_tactics):
                raise ValueError('Confirm or discard management edits before playing')
            self.jobs.start(halftime=self.model.state.campaign is not None);self.set_busy(True);self.status.setText('Playing quick friendly…');self.timer.start()
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def poll_match(self):
        try:
            if self.jobs.poll():
                self.timer.stop();self.set_busy(False);self.show_halftime();self.refresh('Friendly complete; confirm management before the next match')
            elif self.jobs.halftime is not self.half_preview:self.show_halftime()
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self.timer.stop();self.set_busy(False);self.show_halftime();self.status.setText(str(exc))

    def cancel_match(self):
        self.timer.stop();self.jobs.cancel();self.set_busy(False);self.show_halftime();self.refresh('Friendly cancelled; game unchanged')

    def closeEvent(self,event):
        self.timer.stop();self.jobs.cancel();super().closeEvent(event)

    def refresh_pool(self):
        if self._refreshing:return
        try:
            view=self.display_model.pool_view(query=self.search.text(),position=self.position.currentData())
            self.reserves.setRowCount(0)
            if view is None:
                self.pool_summary.setText('National pool requires a campaign');self.exchange.setEnabled(False);return
            self.pool_summary.setText(f"Squad 20 / Reserves 80 — showing {len(view['reserves'])}\n{view['window']['reason']}")
            self.exchange.setEnabled(view['window']['allowed'] and not self.jobs.busy and self.preview is None)
            self.reserves.setRowCount(len(view['reserves']))
            for row,p in enumerate(view['reserves']):
                values=(p['id'],p['name'],f"{p['position']} — {p['position_group']}",p['ability'],p['energy'],p['confidence'],', '.join(p['availability']['reasons']) or 'Available')
                for col,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
                    if col==0:item.setData(Qt.ItemDataRole.UserRole,p['id'])
                    self.reserves.setItem(row,col,item)
        except (ValueError,IndexError,KeyError) as exc:
            self.exchange.setEnabled(False);self.pool_summary.setText(str(exc))

    def exchange_selected(self):
        if not self.require_active():return
        row=self.table.currentRow();reserve=self.reserves.currentRow()
        if row<0 or reserve<0:
            self.status.setText('Select one squad player and one reserve');return
        outgoing=self.table.item(row,0).data(Qt.ItemDataRole.UserRole)
        incoming=self.reserves.item(reserve,0).data(Qt.ItemDataRole.UserRole)
        self.action(lambda:self.model.exchange(outgoing,incoming),'Players exchanged; confirmed XI and captain repaired')

    def show_halftime(self):
        # [designed: T47] Widgets show private worker state; committed game stays unchanged.
        self.half_preview=self.jobs.halftime;preview=self.half_preview
        for widget in (self.half_out,self.half_in,self.substitute,self.continue_match):widget.setEnabled(preview is not None)
        self.half_out.clear();self.half_in.clear()
        if preview is None:return
        for word in preview['eleven']:self.half_out.addItem(self.model.goaldat.player_names[word],word)
        for word in preview['bench']:
            if word in preview['available'] and word not in preview['removed']:
                self.half_in.addItem(self.model.goaldat.player_names[word],word)
        a,b=preview['teams'];x,y=preview['score']
        self.result.setText(f"Halftime: {self.model.goaldat.country_names[a]} {x} — {y} {self.model.goaldat.country_names[b]}")
        self.status.setText(f"Halftime: {len(preview['changes'])} substitutions selected. No re-entry. Saving is unavailable until full time; cancel preserves the previous game.")

    def substitute_halftime(self):
        try:self.jobs.substitute(self.half_out.currentData(),self.half_in.currentData());self.show_halftime()
        except ValueError as exc:self.status.setText(str(exc))

    def continue_halftime(self):
        try:self.jobs.continue_match();self.show_halftime();self.status.setText('Playing second half…')
        except ValueError as exc:
            if not self.jobs.busy:
                self.timer.stop();self.set_busy(False);self.show_halftime();self.refresh(str(exc))
            else:self.status.setText(str(exc))
