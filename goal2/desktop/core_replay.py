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
        box.addWidget(self.watch);box.addWidget(self.skip);box.addStretch(1)
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
        self.round.show(self.index)
        # [designed: T140] The main window owns this explicit decision, as at half-time.
        w=self.window;w.setWindowState(w.windowState() & ~Qt.WindowState.WindowMinimized)
        w.raise_();w.activateWindow()

    def choose(self,watch):
        if self.window.core_jobs.busy:return
        if not self.round.state or self.round.state['stop'] not in ('replay','replay-save'):return
        self.window.run_core('replay',watch)
