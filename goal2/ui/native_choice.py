"""[designed: T170ak/#844] Present verified native choices through Goal2's chooser."""

from types import SimpleNamespace

from PySide6.QtCore import Qt

from goal2.ui.s16_choose import ChooseScreen
from goal2.ui.s22_help import HelpScreen


class NativeChooseScreen(ChooseScreen):
    GRID = True

    def handle_key(self, key):
        if self.done and key != Qt.Key.Key_F1:
            return True
        return super().handle_key(key)


class NativeChoiceFlow:
    """The pitch remains the only queue consumer and holds while the chooser is open."""

    def __init__(self, pitch, waiting):
        self.pitch = pitch
        self.window = pitch.window_
        self.driver = pitch.controller.driver
        self.decision = waiting['decision']
        self.context = waiting['event']['data']['context']
        self.widget = None
        self.submitted = False
        self.refusal = ''
        self.driver.request_view()

    def update(self):
        if self.driver.pending:
            return False
        if self.submitted:
            if self.driver.waiting is None:
                return self.dismiss()
            self.refusal = self.driver.message
            self.submitted = False
            self.driver.request_view()
            return False
        view = self.driver.stopped_view
        if view is None or view.snapshot.decision != self.decision:
            raise ValueError(self.driver.message or 'Current native choice could not be verified.')
        if self.widget is not None:
            if not self.widget.done or self.window.current() is not self.widget:
                return False
            self.dismiss()
        if self.window.current() is not self.pitch or self.pitch.controller.commentary_paused:
            return False
        self.open(view)
        return False

    def open(self, view):
        data = view.snapshot.data
        model = self.pitch.model
        facade = SimpleNamespace(state=view.display_state(model.state), goaldat=model.goaldat)
        self.widget = NativeChooseScreen(
            self.window, facade, 'taker' if self.context == 'set_piece' else 'order',
            view.eleven, data.get('current'), self.submit, available=data['available'],
            role=data.get('role', 1), takers=data.get('takers', 0),
            match=self.pitch.controller.display.kind,
        )
        if self.refusal:
            self.widget.wait_detail.setText(self.refusal)
        self.window.push(self.widget)

    def submit(self, value):
        if self.submitted:
            return
        key = 'taker' if self.context == 'set_piece' else 'shootout_order'
        self.driver.answer_choice(self.decision, {key: value})
        self.submitted = True
        self.widget.wait_detail.setText('Confirming the choice…')
        self.widget.set_enter('', lambda: None)
        self.widget.strip.setEnabled(False)

    def dismiss(self):
        if self.widget is None:
            return True
        current = self.window.current()
        if isinstance(current, HelpScreen) and current.under is self.widget:
            # [designed: #796] A taker timeout closes its own Help after the reply.
            self.window.pop()
        if self.window.current() is not self.widget:
            return False
        self.close()
        self.window.pop()
        self.widget = None
        return True

    def close(self):
        if self.widget is not None:
            self.widget.done = True
            self.widget.closing()
