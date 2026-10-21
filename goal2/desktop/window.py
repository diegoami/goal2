"""[designed: T69] Native Qt management widgets; drafts never mutate the game.
[confirmed: F010] Tactics labels for elements1..4,6,7.
"""
from PySide6.QtCore import Qt,QTimer
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.competitive import CompetitiveJobs
from PySide6.QtWidgets import QMainWindow,QTableWidgetItem

# [confirmed: F010] Display order5,6,7,1,2,3,4,8. [designed] Labels5,8.
TACTICS=((5,'Half pitch / full pitch'),(6,'Sag back to box / stand ground'),(7,'Play safe / offside trap'),
         (1,'Stay back / push forward'),(2,'Keep ball / quick pass'),(3,'Short passes / long passes'),
         (4,'Avoid injury / go in hard'),(8,'Zone / man to man'))


# [confirmed: m244-squad screenshot; F028 DS:0D5C] The original colours a role code by line:
# green goalkeeper, red defence, cyan midfield, yellow attack. [designed: #286] Darker shades
# keep them readable on the current light table until #261 brings the black original style.
LINE_COLOURS={'goalkeeper':'#1a7f37','defence':'#b60205','midfield':'#0b6e8f','attack':'#8a6d00','unknown':'#000000'}


def role_colour(item,line):
    from PySide6.QtGui import QColor,QFont
    item.setForeground(QColor(LINE_COLOURS[line]));font=QFont(item.font());font.setBold(True);item.setFont(font)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)


class ManagementWindow(QMainWindow):
    """[designed] All widget access and active-state publication stay on the Qt thread."""
    def __init__(self,model):
        super().__init__();self.model=model;self._refreshing=False;self.preview=None;self.active_draft=None
        from goal2.desktop.watched import WatchedController
        self.watched=WatchedController(model)
        self.competitive=CompetitiveJobs(model)
        self.competitive_timer=QTimer(self);self.competitive_timer.setInterval(30);self.competitive_timer.timeout.connect(self.poll_competitive)
        self.watch_timer=QTimer(self);self.watch_timer.setInterval(30);self.watch_timer.timeout.connect(self.poll_watched)
        self.jobs=QuickJobs(model);self.timer=QTimer(self);self.timer.setInterval(30);self.timer.timeout.connect(self.poll_match)
        from goal2.desktop.pages import compose
        compose(self,model,TACTICS)
        self.standings.clicked.connect(self.show_standings)
        self.watch.clicked.connect(self.start_watched)
        self.substitute.clicked.connect(self.substitute_halftime);self.continue_match.clicked.connect(self.continue_halftime)
        # [designed: T87] Replacing the game asks first when progress or a draft would be lost.
        self.new.clicked.connect(lambda:self.decide('Start a new campaign') and self.action(lambda:model.new_campaign(self.country.currentData(),self.start_year.currentData()),'New campaign created',replace=True))
        self.friendly.clicked.connect(lambda:self.decide('Start a standalone friendly') and self.action(lambda:model.new_friendly(self.country.currentData()),'New standalone friendly created',replace=True))
        self.play.clicked.connect(self.start_match);self.stop.clicked.connect(self.cancel_match)
        self.confirm.clicked.connect(self.confirm_draft);self.cancel.clicked.connect(lambda:self.refresh('Draft discarded'))
        self.save.clicked.connect(lambda:self.save_to(self.path.text()))
        self.save_as.clicked.connect(self.save_as_dialog)
        self.resume.clicked.connect(lambda:self.decide('Resume another save') and self.action(lambda:model.resume(self.path.text()),'Game resumed',replace=True))
        self._closing=False
        from goal2.desktop.save_page import game_menu
        game_menu(self)
        self.search.textChanged.connect(self.refresh_pool);self.position.currentIndexChanged.connect(self.refresh_pool)
        self.exchange.clicked.connect(self.exchange_selected)
        self.table.itemChanged.connect(self.selection_changed)
        from goal2.desktop.squad_page import refresh as refresh_squad
        self.table.currentCellChanged.connect(lambda *args:refresh_squad(self))
        self.captain.currentIndexChanged.connect(lambda *args:refresh_squad(self))
        for _,box in self.tactics:box.toggled.connect(lambda *args:refresh_squad(self))
        self.refresh()
        self.country.currentIndexChanged.connect(self.country_changed)

    def navigate(self,index):
        """[designed: T74] Presentation only; preserve draft and job ownership."""
        self.page_stack.setCurrentIndex(index)
        for number,button in enumerate(self.navigation):button.setChecked(number==index)
        self.pages[index].verticalScrollBar().setValue(0)
        self.pages[index].heading.setFocus(Qt.FocusReason.ShortcutFocusReason)

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
        self.refresh_squad()

    def refresh_squad(self):
        from goal2.desktop.squad_page import refresh
        refresh(self)

    def country_changed(self):
        if self._refreshing:return
        country=self.country.currentData()
        if getattr(self.model,'match_pending',False):
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
                candidate.new_campaign(country,self.start_year.currentData())
                if self.preview is None:self.active_draft=self.draft()
                self.preview=candidate;self.refresh()
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self._refreshing=True;self.country.setCurrentIndex(self.country.findData(self.display_model.state.managed_country));self._refreshing=False
            self.status.setText(str(exc))

    def require_active(self):
        if getattr(self.model,'match_pending',False):
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
        self.refresh_squad()

    def update_captain(self):
        previous=self.captain.currentData();selected=self.selected_ids()
        self.captain.clear()
        # [designed: T80] Preserve supplied competitive input; fresh friendly drafts keep their named default.
        state=self.display_model.state
        pending=state.campaign.next_fixture if state.campaign else None
        from goal2.game.watched_schema import COMPETITIVE_SCHEMA,watched
        from goal2.engine.original_match.match import KINDS
        original=(pending is not None and pending.kind!=1 and pending.kind in KINDS) or (watched(state.last_match) and state.last_match['schema']==COMPETITIVE_SCHEMA)
        if state.captain==0 and original:
            self.captain.addItem('Original captain selection',0)
            self.captain.model().item(0).setEnabled(False)
        for word in selected:self.captain.addItem(self.model.goaldat.player_names[word],word)
        self.captain.setCurrentIndex(max(0,self.captain.findData(previous)))

    def refresh(self,message=None):
        if self.standings_dialog is not None:
            self.standings_dialog.close();self.standings_dialog=None
        display=self.display_model;view=display.view();state=display.state;self._refreshing=True
        self.context.setText(('Preview · active game: '+self.model.goaldat.country_names[self.model.state.managed_country]) if self.preview is not None else 'Active game')
        self.title.setText(view['country_name']);self.country.setCurrentIndex(self.country.findData(view['country']))
        from goal2.desktop.overview_page import refresh as refresh_overview
        refresh_overview(self,display,view)
        from goal2.desktop.fixtures_page import refresh as refresh_fixtures
        refresh_fixtures(self,display,view)
        self.play.setText(view['play_label'])
        self.summary.setText(f"Team morale: {view['morale']}     Next fixture: {view['fixture'] or ('Standalone friendly' if state.campaign is None else 'No supported fixture')}")
        for row,p in enumerate(view['players']):
            available=p['availability']['available'];selected=p['id'] in state.starting_eleven
            item=QTableWidgetItem();item.setData(Qt.ItemDataRole.UserRole,p['id']);item.setData(Qt.ItemDataRole.UserRole+1,available)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable| (Qt.ItemFlag.ItemIsUserCheckable if self.preview is None and (available or selected) else Qt.ItemFlag.NoItemFlags))
            item.setCheckState(Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked);self.table.setItem(row,0,item)
            reason=', '.join(p['availability']['reasons']) or 'Available'
            if p['availability']['carried_bookings']:reason+='; carried booking'
            for col,value in enumerate((p['name'],p['role'],p['position_name'],p['energy'],p['confidence'],reason),1):
                cell=QTableWidgetItem(str(value));cell.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable);self.table.setItem(row,col,cell)
                if col==2:role_colour(cell,p['line'])
        self.update_captain();self.captain.setCurrentIndex(max(0,self.captain.findData(state.captain)))
        for element,box in self.tactics:box.setChecked(bool(state.country_tactics & (1<<(element-1))))
        self.path.setText(str(self.model.save_path));self._refreshing=False
        # [designed: T87] What the window shows for the confirmed team; a draft is a change from it.
        if self.preview is None:self.shown_draft=self.draft()
        self.refresh_squad()
        self.refresh_pool()
        self.set_busy(getattr(self.model,'match_pending',False))
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
        if getattr(self.model,'match_pending',False) or (not replace and not self.require_active()):return
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
        busy=bool(busy or getattr(self.model,'match_pending',False))
        # [designed: T70] Prevent conflicting edits while keeping the UI responsive.
        for widget in (self.country,self.start_year,self.new,self.friendly,self.resume,self.path):widget.setEnabled(not busy)
        self.overview_return.setEnabled(not busy and self.preview is not None)
        active=not busy and self.preview is None
        # [designed: #241] Idle previews browse rows/details; management stays active-only.
        for widget in (self.table,self.pool_panel):widget.setEnabled(not busy)
        for widget in (self.captain,self.confirm,self.cancel,self.save,self.save_as,self.play,self.watch,self.standings):widget.setEnabled(active)
        for _,box in self.tactics:box.setEnabled(active)
        from goal2.desktop.pool_page import context as pool_context
        pool_context(self,busy)
        self.stop.setEnabled(busy)
        from goal2.desktop.fixtures_page import enabled as fixtures_enabled
        fixtures_enabled(self,active)

    def start_match(self):
        if not self.require_active():return
        try:
            bits=sum(1<<(element-1) for element,box in self.tactics if box.isChecked())
            state=self.model.state
            if (self.selected_ids()!=state.starting_eleven or self.captain.currentData()!=state.captain or bits!=state.country_tactics):
                raise ValueError('Confirm or discard management edits before playing')
            pending=state.campaign.next_fixture if state.campaign else None
            if pending is not None and pending.kind!=1:
                self.competitive.start(record_draws=True);self.set_busy(True)
                self.status.setText('Starting original competitive engine…');self.competitive_timer.start()
            else:
                self.jobs.start(halftime=state.campaign is not None);self.set_busy(True);self.status.setText('Playing quick friendly…');self.timer.start()
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def start_watched(self):
        if not self.require_active():return
        try:
            self.watched.fixture()
            state=self.model.state
            if self.draft()!=(state.starting_eleven,state.captain,state.country_tactics):
                raise ValueError('Confirm or discard management edits before watching')
            self.watched.start();self.set_busy(True);self.status.setText('Starting original friendly in Pygame…');self.watch_timer.start()
        except (OSError,ValueError,IndexError,KeyError) as exc:self.status.setText(str(exc))

    def poll_watched(self):
        try:
            if self.watched.poll():
                self.set_busy(False);self.refresh('Original friendly complete; result can be saved. Scroll the Pygame window for board and Raw rating.')
            elif self.watched.busy and self.watched.display.events:
                event=self.watched.display.events[-1]
                self.status.setText(f"Original engine: {event['minute']}′ {event['score'][0]} — {event['score'][1]}")
            if self.watched.process is None:
                self.watch_timer.stop();self.set_busy(False)
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self.watch_timer.stop();self.set_busy(False);self.status.setText(str(exc))

    def poll_competitive(self):
        """[designed: T80] Poll bounded IPC on Qt; publish only the validated full continuation."""
        try:
            events=self.competitive.poll(self.competitive.token)
            if not self.competitive.busy:
                self.competitive_timer.stop();self.set_busy(False)
                self.refresh('Original competitive match complete; result can be saved')
            elif events:
                event=events[-1]
                self.status.setText(f"Original competitive engine: {event.minute}′ {event.score[0]} — {event.score[1]}")
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self.competitive_timer.stop();self.set_busy(False);self.status.setText(str(exc))

    def poll_match(self):
        try:
            if self.jobs.poll():
                self.timer.stop();self.set_busy(False);self.show_halftime();self.refresh('Friendly complete; confirm management before the next match')
            elif self.jobs.halftime is not self.half_preview:self.show_halftime()
        except (OSError,ValueError,IndexError,KeyError) as exc:
            self.timer.stop();self.set_busy(False);self.show_halftime();self.status.setText(str(exc))

    def cancel_match(self):
        self.timer.stop();self.watched.cancel();self.watch_timer.stop();self.jobs.cancel()
        self.competitive_timer.stop()
        if self.competitive.busy:self.competitive.cancel(self.competitive.token)
        self.set_busy(False);self.show_halftime();self.refresh('Match cancelled; game unchanged')

    # [designed: T87] Save, Save as, and the decisions before replacing or quitting -----------------
    def losses(self):
        """What replacing or quitting now would lose, in words."""
        lost=[]
        if self.model.unsaved:lost.append('progress confirmed since the last save')
        draft=self.active_draft if self.preview is not None else self.draft()
        shown=getattr(self,'shown_draft',None)
        # Compared as a set: the engine's squad reorder (#280) is not a manager's edit.
        if draft is not None and shown is not None and (set(draft[0]),draft[1],draft[2])!=(set(shown[0]),shown[1],shown[2]):
            lost.append('an unconfirmed squad, captain or tactics draft')
        return lost

    def ask(self,title,text,choices):
        """A modal question; choices are (key, label) with the safest last. Returns the key."""
        from PySide6.QtWidgets import QMessageBox
        box=QMessageBox(self);box.setWindowTitle(title);box.setText(text);box.setObjectName('decision')
        buttons={box.addButton(label,QMessageBox.ButtonRole.AcceptRole if key!='cancel' else QMessageBox.ButtonRole.RejectRole):key
                 for key,label in choices}
        cancel=[b for b,k in buttons.items() if k=='cancel']
        if cancel:box.setEscapeButton(cancel[0]);box.setDefaultButton(cancel[0])
        box.exec()
        return buttons.get(box.clickedButton(),'cancel')

    def decide(self,verb):
        """True when the caller may go on: nothing would be lost, or the player chose."""
        lost=self.losses();running=bool(getattr(self.model,'match_pending',False))
        if not lost and not running:return True
        text=verb+'?\n'+('\n'.join('This loses '+item+'.' for item in lost))
        choices=[]
        if running:
            text+='\nThe running match will be cancelled; saving waits until it has finished.'
        elif self.model.unsaved:
            choices.append(('save','Save and continue'))
        choices+=[('discard','Continue without saving'),('cancel','Cancel')]
        choice=self.ask(verb,text.strip(),choices)
        if choice=='cancel':
            self.status.setText(verb+' cancelled; nothing changed');return False
        if choice=='save':return self.save_to(str(self.model.save_path))
        return True

    def save_to(self,path):
        """Save the confirmed state; a different existing file is overwritten only after asking."""
        from pathlib import Path
        if getattr(self.model,'match_pending',False):
            self.status.setText('Saving during a match is unavailable; cancel or finish first');return False
        target=Path(path).expanduser()
        if target.exists() and target.resolve()!=self.model.save_path.resolve():
            if self.ask('Overwrite save',f'{target} already exists. Replace it with this game?',
                        (('overwrite','Overwrite'),('cancel','Cancel')))!='overwrite':
                self.status.setText('Save cancelled; '+str(target)+' was not changed');return False
        try:self.model.save(target)
        except (OSError,ValueError) as exc:
            self.status.setText(str(exc));return False
        self.path.setText(str(self.model.save_path))
        self.status.setText('Game saved to '+str(self.model.save_path)+('; the unconfirmed draft is not included' if self.losses() else ''))
        return True

    def save_as_dialog(self):
        from PySide6.QtWidgets import QInputDialog
        path,ok=QInputDialog.getText(self,'Save as','Save file',text=str(self.model.save_path))
        if ok and path.strip():self.save_to(path.strip())

    def quit_game(self):
        if self.decide('Quit'):
            self._closing=True;self.close()

    def closeEvent(self,event):
        # [designed: T87] Only a user's close asks; programmatic close() (tests, scripts) never blocks.
        if event.spontaneous() and not self._closing and not self.decide('Quit'):
            event.ignore();return
        self.timer.stop();self.watch_timer.stop();self.competitive_timer.stop();self.watched.close();self.jobs.cancel();self.competitive.close();super().closeEvent(event)

    def refresh_pool(self):
        if self._refreshing:return
        try:
            view=self.display_model.pool_view(query=self.search.text(),position=self.position.currentData())
            self.reserves.setRowCount(0)
            if view is None:
                self.pool_summary.setText('National pool requires a campaign');self.exchange.setEnabled(False)
                from goal2.desktop.pool_page import refresh as refresh_pool_page
                refresh_pool_page(self);return
            self.pool_summary.setText(f"Squad 20 / Reserves 80 — showing {len(view['reserves'])}\n{view['window']['reason']}")
            self.exchange.setEnabled(view['window']['allowed'] and not self.jobs.busy and self.preview is None)
            self.reserves.setRowCount(len(view['reserves']))
            for row,p in enumerate(view['reserves']):
                values=(p['id'],p['name'],p['role'],p['position_name'],p['energy'],p['confidence'],', '.join(p['availability']['reasons']) or 'Available')
                for col,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
                    if col==2:role_colour(item,p['line'])
                    if col==0:item.setData(Qt.ItemDataRole.UserRole,p['id'])
                    self.reserves.setItem(row,col,item)
            from goal2.desktop.pool_page import refresh as refresh_pool_page
            refresh_pool_page(self)
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
