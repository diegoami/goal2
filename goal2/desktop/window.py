"""[designed: T69] Native Qt management widgets; drafts never mutate the game.
[derived: F010] Tactics elements1..4; remaining labels retain rebuild policy.
"""
from PySide6.QtCore import Qt,QTimer
from goal2.desktop.jobs import QuickJobs
from PySide6.QtWidgets import (QCheckBox,QComboBox,QHeaderView,QHBoxLayout,QLabel,
 QLineEdit,QMainWindow,QPushButton,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)

# [confirmed: F010] Display order5,6,7,1,2,3,4,8. [designed] Labels5..8.
TACTICS=((5,'Half pitch / full pitch'),(6,'Short kicks / long kicks'),(7,'Stay back / push forward'),
         (1,'Stay back / push forward'),(2,'Keep ball / quick pass'),(3,'Short passes / long passes'),
         (4,'Avoid injury / go in hard'),(8,'Zone / man to man'))


class ManagementWindow(QMainWindow):
    """[designed] All widget access and active-state publication stay on the Qt thread."""
    def __init__(self,model):
        super().__init__();self.model=model;self._refreshing=False
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
        self.table=QTableWidget(20,7);self.table.setObjectName('squad')
        self.table.setHorizontalHeaderLabels(['XI','Player','Position','Ability','Energy','Confidence','Availability'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table,1)
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
        self.result=QLabel();self.result.setWordWrap(True);self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.result)
        self.status=QLabel('Confirm management, then play a quick friendly or save.');self.status.setWordWrap(True);self.status.setObjectName('status');layout.addWidget(self.status)
        self.new.clicked.connect(lambda:self.action(lambda:model.new_campaign(self.country.currentData()),'New campaign created'))
        self.friendly.clicked.connect(lambda:self.action(lambda:model.new_friendly(self.country.currentData()),'New standalone friendly created'))
        self.play.clicked.connect(self.start_match);self.stop.clicked.connect(self.cancel_match)
        self.confirm.clicked.connect(self.confirm_draft);self.cancel.clicked.connect(lambda:self.refresh('Draft discarded'))
        self.save.clicked.connect(lambda:self.action(lambda:model.save(self.path.text()),'Game saved; unconfirmed edits are excluded'))
        self.resume.clicked.connect(lambda:self.action(lambda:model.resume(self.path.text()),'Game resumed'))
        self.table.itemChanged.connect(self.selection_changed)
        self.refresh()

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
        view=self.model.view();state=self.model.state;self._refreshing=True
        self.title.setText(view['country_name']);self.country.setCurrentIndex(self.country.findData(view['country']))
        self.result.setText('Quick simulation (rebuild setup)\n'+self.model.result_text())
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
        if message:self.status.setText(message)

    def action(self,operation,message):
        try:operation();self.refresh(message)
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def confirm_draft(self):
        bits=sum(1<<(element-1) for element,box in self.tactics if box.isChecked())
        self.action(lambda:self.model.confirm(self.selected_ids(),self.captain.currentData(),bits),'Management confirmed')

    def set_busy(self,busy):
        # [designed: T70] Prevent conflicting edits while keeping the UI responsive.
        for widget in (self.country,self.new,self.friendly,self.table,self.captain,self.confirm,self.cancel,self.save,self.resume,self.path):widget.setEnabled(not busy)
        for _,box in self.tactics:box.setEnabled(not busy)
        self.play.setEnabled(not busy);self.stop.setEnabled(busy)

    def start_match(self):
        try:
            bits=sum(1<<(element-1) for element,box in self.tactics if box.isChecked())
            state=self.model.state
            if (self.selected_ids()!=state.starting_eleven or self.captain.currentData()!=state.captain or bits!=state.country_tactics):
                raise ValueError('Confirm or discard management edits before playing')
            self.jobs.start();self.set_busy(True);self.status.setText('Playing quick friendly…');self.timer.start()
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def poll_match(self):
        try:
            if self.jobs.poll():
                self.timer.stop();self.set_busy(False);self.refresh('Friendly complete; confirm management before the next match')
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self.timer.stop();self.set_busy(False);self.status.setText(str(exc))

    def cancel_match(self):
        self.timer.stop();self.jobs.cancel();self.set_busy(False);self.refresh('Friendly cancelled; game unchanged')

    def closeEvent(self,event):
        self.timer.stop();self.jobs.cancel();super().closeEvent(event)
