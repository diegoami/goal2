"""[designed: T170am/#848] Present the verified retained substitution notice."""

from types import SimpleNamespace

from PySide6.QtCore import Qt

from goal2.ui.s18_stop import substitution_text


class NativeOpportunityFlow:
    def __init__(self, pitch, decision):
        self.pitch = pitch
        self.driver = pitch.controller.driver
        self.decision = decision
        self.enter_before = pitch.enter_action
        self.request_read()

    def request_read(self):
        controller = self.pitch.controller
        if controller.note == self.driver.message:
            controller.note = ''
        self.driver.request_view()
        self.phase = 'reading'
        self.pitch.set_enter('', lambda: None)

    def update(self):
        if self.driver.pending:
            return False
        if self.phase == 'answering':
            if self.driver.waiting is None:
                self.pitch.set_enter(*self.enter_before)
                return True
            self.retry()
        elif self.phase == 'reading':
            view = self.driver.stopped_view
            if view is None:
                self.retry()
            elif view.snapshot.decision != self.decision:
                raise ValueError('The substitution prompt lost its verified decision.')
            elif self.pitch.window_.current() is self.pitch and not self.pitch.controller.commentary_paused:
                self.show(view)
        return False

    def show(self, view):
        model = self.pitch.model
        data = view.snapshot.data
        facade = SimpleNamespace(state=view.display_state(model.state), goaldat=model.goaldat)
        detail = substitution_text(facade, SimpleNamespace(data=data))
        self.pitch.stop_box.show_opportunity(data, self.respond, detail=detail)
        self.phase = 'open'
        self.pitch.set_enter('Open the bench', lambda: self.pitch.answer_stop_box(Qt.Key.Key_Return))
        self.pitch.refresh()

    def respond(self, key):
        # [designed: #636] Esc is an accepting UI key. The deadline sends no key.
        answer = {'opportunity': 'timeout' if key is None else 'accept'}
        self.driver.answer_choice(self.decision, answer)
        self.phase = 'answering'
        self.pitch.set_enter('', lambda: None)

    def retry(self):
        self.phase = 'retry'
        self.pitch.set_enter('Retry substitution prompt', self.request_read)
