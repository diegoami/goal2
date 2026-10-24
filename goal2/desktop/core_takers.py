"""[designed:T120; confirmed:T88/T89] Original role2/5 choice controls over immutable wait data."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton
from goal2.desktop.roster import RosterView
from goal2.desktop.player_card import PlayerCardView,core_card
from goal2.core.screens import UP,DOWN,RETURN,ESCAPE,SPACE


class TakerRoster(RosterView):
    original_key=Signal(int)
    def keyPressEvent(self,event):
        # [confirmed:CC7B] Up/Down wrap in the guest; the general roster's clamp is not this prompt's rule.
        codes={Qt.Key.Key_Up:UP,Qt.Key.Key_Down:DOWN,Qt.Key.Key_Return:RETURN,Qt.Key.Key_Enter:RETURN,
               Qt.Key.Key_Escape:ESCAPE,Qt.Key.Key_Space:SPACE,Qt.Key.Key_C:ord('c')}
        if event.key() in codes:
            self.original_key.emit(codes[event.key()]);event.accept()
        else:super().keyPressEvent(event)


class TakerPages:
    def __init__(self,round_view):
        self.round=round_view;self.window=round_view.window;self.data=None
        self.choice=QWidget();box=QVBoxLayout(self.choice);box.setSpacing(8)
        self.title=QLabel();self.title.setObjectName('prepTitle');self.title.setWordWrap(True);box.addWidget(self.title)
        self.hint=QLabel('Up/Down select  Enter choose  C original choice  Esc keep  Space view pitch')
        self.hint.setObjectName('prepNote');self.hint.setWordWrap(True);box.addWidget(self.hint)
        columns=QHBoxLayout();columns.setSpacing(8);box.addLayout(columns)
        left=QVBoxLayout();columns.addLayout(left)
        self.roster=TakerRoster('FIRST ELEVEN',toggles=False,grouped=False,marks=False,capacity=11)
        self.roster.setFixedWidth(300);left.addWidget(self.roster)
        actions=QGridLayout();left.addLayout(actions)
        self.select=QPushButton('Select (Enter)');self.computer=QPushButton('Computer (C)')
        self.keep=QPushButton('Keep (Esc)');self.space=QPushButton('Pitch (Space)')
        for button,row,col,key in ((self.select,0,0,RETURN),(self.computer,0,1,ord('c')),
                                  (self.keep,1,0,ESCAPE),(self.space,1,1,SPACE)):
            actions.addWidget(button,row,col);button.clicked.connect(lambda checked=False,k=key:self.key(k))
        left.addStretch(1);self.card=PlayerCardView(compact=True);columns.addWidget(self.card)
        box.addStretch(1)
        self.roster.original_key.connect(self.key);self.roster.current_changed.connect(self.highlight)
        self.roster.activated.connect(lambda row:self.key(RETURN))
        self.preview=QWidget();pbox=QVBoxLayout(self.preview)
        title=QLabel('VIEW THE PITCH');title.setObjectName('prepTitle');pbox.addWidget(title)
        self.preview_note=QLabel('The original waits while the pitch is shown. Enter returns to the same selector.')
        self.preview_note.setObjectName('prepNote');self.preview_note.setWordWrap(True);pbox.addWidget(self.preview_note)
        self.back=QPushButton('Return to choices (Enter)');pbox.addWidget(self.back)
        self.reopen=QPushButton('Show pitch again');pbox.addWidget(self.reopen);pbox.addStretch(1)
        self.back.clicked.connect(lambda:self.key(RETURN))
        self.reopen.clicked.connect(lambda:self.round.show_taker_pitch(self.round.state))
        self.choice_index=round_view.views.addWidget(self.choice)
        self.preview_index=round_view.views.addWidget(self.preview)
        self.controls=[self.roster,self.select,self.computer,self.keep,self.space,self.back,self.reopen]

    def offer(self,state):
        self.data=state
        if state['stop']=='taker':
            choice=state['taker'];label={2:'CORNER TAKER',5:'GOAL KICK TAKER'}[choice['role']]
            self.title.setText(f"{label} / {choice['name'].upper()}")
            self.roster.marked={choice['stored']}
            self.roster.set_rows([(p['player'],p['name'],p['code'],p['line'],True,False) for p in choice['players']],
                                 choice['slot']-1,unavailable={p['player'] for p in choice['players'] if not p['available']})
            self.card.set_card(core_card(choice['card']))
            self.round.show(self.choice_index);self.roster.setFocus()
        else:
            self.round.show(self.preview_index)
            self.round.show_taker_pitch(state)
        self.refresh_controls()

    def key(self,key):
        if self.window.core_jobs.busy or self.data is None:return
        if self.round.state is None or self.round.state['stop'] not in ('taker','taker-pitch'):return
        if self.data['stop']=='taker-pitch' and not self.back.isEnabled():return
        self.window.run_core('taker_key',key)

    def highlight(self,row):
        if self.window.core_jobs.busy or self.data is None or self.data['stop']!='taker':return
        if self.round.state is None or self.round.state['stop']!='taker':return
        players=self.data['taker']['players']
        if 0<=row<len(players) and row!=self.data['taker']['slot']-1:
            self.window.run_core('taker_highlight',players[row]['player'])

    def refresh_controls(self):
        state=self.round.state;busy=self.window.core_jobs.busy
        choice=not busy and state is not None and state['stop']=='taker'
        preview=not busy and state is not None and state['stop']=='taker-pitch'
        for w in (self.roster,self.select,self.computer,self.keep,self.space):w.setEnabled(choice)
        viewer=self.round.viewer
        self.back.setEnabled(preview and (viewer is None or viewer.drained))
        self.reopen.setEnabled(preview and viewer is None)
