"""[designed: T170ar] S09 backed by one verified retained bench."""

from types import SimpleNamespace

from PySide6.QtCore import Qt

from goal2.ui.s09_player_tactics import PlayerTacticsScreen
from goal2.ui.s19_bench import BenchAnswer


class NativePlayerTacticsScreen(PlayerTacticsScreen):
    GRID = True

    def __init__(self, parent, word):
        self.parent_bench = parent
        self.pending = False
        self.message = ''
        self.goal = None
        country_name = parent.data.country_names[parent.snapshot.managed_country]
        model = SimpleNamespace(state=parent.state, goaldat=parent.data,
                                view=lambda: {'country_name': country_name})
        super().__init__(parent.window_, model, word, self.bench_answer(model), allow_marking=False)

    def bench_answer(self, model):
        parent = self.parent_bench
        decision = parent.driver.waiting['event']
        return BenchAnswer(model, SimpleNamespace(**decision))

    def refresh(self):
        super().refresh()
        self.explain.setText(self.message or 'One tactic is confirmed at a time. Play stays on the bench.')

    def alter(self):
        parent = self.parent_bench
        if (self.pending or parent.phase != 'ready' or parent.driver.stopped_view is not parent.snapshot
                or self.window_.current() is not self):
            return
        element = self.line + 1
        byte = parent.snapshot.record(self.word)[15]
        personal = bool(byte & (1 << (element + 3)))
        value = (None if byte & (1 << (element - 1)) else True) if personal else False
        if parent.apply_edit({'own_tactics': {self.word: {element: value}}}):
            parent._edited_player = self.word
            self.pending = True
            self.goal = (element, value)
            self.message = 'Confirming the player tactic…'
        else:
            self.message = parent.status.text()
        self.refresh()

    def acknowledge(self, message):
        self.model.state = self.parent_bench.state
        self.bench = self.bench_answer(self.model)
        element, wanted = self.goal
        byte = self.bench.record(self.word)[15]
        actual = bool(byte & (1 << (element - 1))) if byte & (1 << (element + 3)) else None
        if not message and actual is not wanted:
            message = 'The game kept the current tactic.'
        self.rejected(message or 'Tactic confirmed. The match is still stopped.')

    def rejected(self, message):
        self.pending = False
        self.goal = None
        self.message = message
        self.refresh()

    def choose(self, index):
        if not self.pending:
            return super().choose(index)

    def escape(self):
        if not self.pending:
            return super().escape()

    def handle_key(self, key):
        if self.pending and key != Qt.Key.Key_F1:
            return True
        return super().handle_key(key)
