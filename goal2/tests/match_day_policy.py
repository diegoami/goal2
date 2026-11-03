"""[designed: T167, #541] A scripted watching player for `goal2.tests.pypy_engine.drive`: the same answers the new
window's match day gives, given by decision number, played in the engine child (so this module imports no Qt).

`Scripted(answers)` answers decision n (counted over every decision the policy is asked, bench and prompts alike) with
`answers[n]`, else with the default: no substitution at a bench decision, no key at a set-piece prompt
({'taker': None}), the original's Enter for the shoot-out order ({'shootout_order': []}) and play on before extra time.
It records what it was asked (`asked`: (context, minute) per decision) and comes back to the parent with it.
"""
from __future__ import annotations


class Scripted:
    def __init__(self, answers=None):
        self.answers = dict(answers or {})
        self.asked = []

    def decide(self, event):
        number = len(self.asked)
        context = event.data.get("context")
        self.asked.append((context, event.minute))
        if number in self.answers:
            return self.answers[number]
        if context == "set_piece":
            return {"taker": None}
        if context == "shootout_order":
            return {"shootout_order": []}
        return []

    def pause_now(self, sequence):
        return False

    def pause_dropped(self, sequence):
        pass

    def answered(self, report):
        pass
