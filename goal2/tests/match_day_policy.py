"""[designed: T167, #541] A scripted watching player for `goal2.tests.pypy_engine.drive`: the same answers the new
window's match day gives, given by decision number, played in the engine child (so this module imports no Qt).

`Scripted(answers)` answers decision n (counted over every decision the policy is asked, bench and prompts alike) with
`answers[n]`, else with the default: no substitution at a bench decision, no key at a set-piece prompt
({'taker': None}), the original's Enter for the shoot-out order ({'shootout_order': []}) and play on before extra time.
It records what it was asked (`asked`: (context, minute) per decision) and comes back to the parent with it.

`play_through_bridge(model, choices, ...)` plays the same match through the bridge, headless, with the answers the
window's MatchController recorded (`choices`): the reference of the match day's tests.
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


def play_through_bridge(model, choices, *, competitive=False, fixture=None, wait=900):
    """The same match through the bridge, headless, with the same answers: `model`'s next fixture on its own
    WatchedJobs (or CompetitiveJobs), with the pitch samples, the bench and the player prompts, every sample
    acknowledged as it arrives, and each decision the bridge waits on answered with the next of `choices` ((context,
    value) as the window's MatchController records them: [] plays on, a dict answers a prompt). Returns the outcome;
    the bridge is closed, so `model.state` is the published career."""
    import time
    if competitive:
        from goal2.desktop.competitive import CompetitiveJobs
        jobs = CompetitiveJobs(model)
    else:
        from goal2.game.watched_jobs import WatchedJobs
        jobs = WatchedJobs(model)
    options = dict(delay_byte=0, record_draws=True, frames=True, bench=True, prompts=True)
    answers = list(choices)
    try:
        token = jobs.start(**options) if competitive else jobs.start(fixture, **options)
        ack = -1
        deadline = time.monotonic() + wait
        while True:
            if time.monotonic() > deadline:
                raise AssertionError("the reference match did not finish")
            jobs.poll(token)
            if not jobs.busy:
                break
            jobs.poll_frames(token)
            if not jobs.busy:
                break
            received = jobs._frame_sequence - 1
            if received > ack:
                jobs.ack_frames(token, received)
                ack = received
            if jobs.waiting is not None and jobs.frames_drained():
                context, value = answers.pop(0)
                if context != jobs.waiting.data.get("context"):
                    raise AssertionError(f"the reference waits on {jobs.waiting.data.get('context')}, not {context}")
                if isinstance(value, dict):
                    jobs.choose(token, value)
                else:
                    jobs.answer(token, value)
            time.sleep(.002)
        if answers:
            raise AssertionError(f"answers left over: {answers}")
        return jobs.outcome
    finally:
        jobs.close()
