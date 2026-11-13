"""[designed: owner#429/T140] Explicit choices at the original replay questions."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence,QShortcut
from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton


class ReplayPage:
    def __init__(self, round_view):
        self.round=round_view;self.window=round_view.window;self.partial=False
        self.view=QWidget();self.view.setObjectName('coreReplayChoices')
        box=QVBoxLayout(self.view);box.setSpacing(12)
        self.title=QLabel('ACTION REPLAY?');self.title.setObjectName('prepTitle');box.addWidget(self.title)
        self.note=QLabel();self.note.setObjectName('prepNote');self.note.setWordWrap(True);box.addWidget(self.note)
        self.watch=QPushButton('Watch replay without saving (Y)');self.watch.setObjectName('watchGoalReplay')
        self.skip=QPushButton('Continue match (N)');self.skip.setObjectName('skipGoalReplay')
        self.watch.clicked.connect(lambda:self.choose(True));self.skip.clicked.connect(lambda:self.choose(False))
        # [designed: T223; confirmed: F030, code/seg_0791_02.asm 0BD0-0C02] The original's question ends by itself
        # (N) after wait_or_key's 600 polls of 10 ms: the countdown shows that wait at its own pace, and at its end
        # the original's remaining polls run with no key (Driver.replay_timeout). A choice before then is pressed
        # at the question's current poll, as before (T140).
        self.countdown=QLabel();self.countdown.setObjectName('replayCountdown');box.addWidget(self.countdown)
        box.addWidget(self.watch);box.addWidget(self.skip);box.addStretch(1)
        from PySide6.QtCore import QTimer
        self.deadline=None
        self.timer=QTimer(self.view);self.timer.setInterval(100);self.timer.timeout.connect(self.tick)
        self.index=round_view.views.addWidget(self.view)
        self.yes=QShortcut(QKeySequence('Y'),self.view,activated=lambda:self.choose(True))
        self.no=QShortcut(QKeySequence('N'),self.view,activated=lambda:self.choose(self.partial))
        for shortcut in (self.yes,self.no):shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.controls=[self.watch,self.skip]

    def offer(self,state):
        self.partial=state['stop']=='replay-save'
        names=state['board']['names'];score=state['board']['score']
        self.note.setText(f'{names[0]} {score[0]} — {score[1]} {names[1]}\n'
                          'Watch the original action again, then return to live play. No highlight file is saved.')
        self.watch.setText('Continue replay without saving (N)' if self.partial else 'Watch replay without saving (Y)')
        self.watch.setAccessibleName(self.watch.text());self.skip.setVisible(not self.partial)
        self.yes.setEnabled(not self.partial)
        import time
        self.deadline=time.monotonic()+state.get('countdown_ms',0)/1000
        self.tick();self.timer.start()
        self.round.show(self.index)
        # [designed: T140] The main window owns this explicit decision, as at half-time.
        w=self.window;w.setWindowState(w.windowState() & ~Qt.WindowState.WindowMinimized)
        w.raise_();w.activateWindow()

    def left(self):
        """The seconds the original's question still waits, by the wall clock since it was offered."""
        import time
        return None if self.deadline is None else max(0.0,self.deadline-time.monotonic())

    def tick(self):
        """[designed: T223] The countdown; at its end the original goes on with no key (its own N)."""
        if not self.round.state or self.round.state['stop'] not in ('replay','replay-save') or self.deadline is None:
            self.timer.stop();self.deadline=None;self.countdown.setText('');return
        left=self.left()
        what='the replay plays without saving' if self.partial else 'the match goes on without a replay'
        self.countdown.setText(f'The original asks for {left:.1f} s more; then {what}.')
        if left<=0 and not self.window.core_jobs.busy:
            self.timer.stop();self.deadline=None
            self.window.run_core('replay_timeout')

    def choose(self,watch):
        if self.window.core_jobs.busy:return
        if not self.round.state or self.round.state['stop'] not in ('replay','replay-save'):return
        self.timer.stop();self.deadline=None
        self.window.run_core('replay',watch)
