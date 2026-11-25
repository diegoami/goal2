"""[designed: T170ar/T170as] S09 backed by one verified retained bench."""

from types import SimpleNamespace

from PySide6.QtCore import Qt

from goal2.ui.s09_player_tactics import LINES, MARK, PlayerTacticsScreen
from goal2.ui.s19_bench import BenchAnswer
from goal2.ui.squad_card import full_name


class NativePlayerTacticsScreen(PlayerTacticsScreen):
    GRID = True

    def __init__(self, parent, word):
        self.parent_bench = parent
        self.pending = False
        self.message = ''
        self.goal = None
        self.current_mark = parent.snapshot.marking_word(word)
        country_name = parent.data.country_names[parent.snapshot.managed_country]
        model = SimpleNamespace(state=parent.state, goaldat=parent.data,
                                view=lambda: {'country_name': country_name})
        super().__init__(parent.window_, model, word, self.bench_answer(model),
                         allow_marking=bool(parent.snapshot.marking_targets(word)))

    def bench_answer(self, model):
        parent = self.parent_bench
        decision = parent.driver.waiting['event']
        return BenchAnswer(model, SimpleNamespace(**decision))

    def refresh(self):
        super().refresh()
        if self.marks:
            current = (full_name(self.model, self.current_mark) if 0 < self.current_mark < len(self.model.state.players)
                       else self.card()['mark'])
            self.rows[len(LINES)].set((MARK, current or 'Team default'))
        self.explain.setText(self.message or 'One tactic is confirmed at a time. Play stays on the bench.')

    def alter(self):
        parent = self.parent_bench
        if (self.pending or parent.phase != 'ready' or parent.driver.stopped_view is not parent.snapshot
                or self.window_.current() is not self):
            return
        element = self.line + 1
        if element > len(LINES):
            targets = parent.snapshot.marking_targets(self.word)
            if not targets:
                return
            index = targets.index(self.current_mark) if self.current_mark in targets else -1
            value = targets[(index + 1) % len(targets)]
            if self.current_mark != value:
                self.submit(element, value, {'marking': {self.word: value}})
            return
        byte = parent.snapshot.record(self.word)[15]
        personal = bool(byte & (1 << (element + 3)))
        value = (None if byte & (1 << (element - 1)) else True) if personal else False
        self.submit(element, value, {'own_tactics': {self.word: {element: value}}})

    def submit(self, element, value, edit):
        parent = self.parent_bench
        if parent.apply_edit(edit):
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
        self.current_mark = self.parent_bench.snapshot.marking_word(self.word)
        element, wanted = self.goal
        if element > len(LINES):
            actual = self.current_mark
        else:
            byte = self.bench.record(self.word)[15]
            actual = bool(byte & (1 << (element - 1))) if byte & (1 << (element + 3)) else None
        if not message and actual != wanted:
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
