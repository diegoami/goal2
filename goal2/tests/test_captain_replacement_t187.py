"""[derived: #659/goal2#593] Kickoff overrides are not later captain choices.

These are declared synthetic coordinator-control states, not original-match evidence.
The live report has the withdrawn captain at squad slot14 and the guest highlight at3.
"""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from goal2.engine.original_match.match import Match
from goal2.engine.original_match import screens as S


class CaptainReentryT187(unittest.TestCase):
    def match(self, kickoff=None):
        match = object.__new__(Match)
        machine = SimpleNamespace(DS=0x1000, cursor=5, seed=0)
        machine.stack_word = lambda offset: {0: 0xCED9, 2: 1, 4: 0}[offset]
        machine.reg = lambda register: 0x100
        machine.frame_word = lambda bp, offset: machine.cursor
        machine.far = lambda pointer: 0x30000
        machine.rd = lambda address: machine.seed
        match.m = machine
        match.side = 0
        match.opts = dict(managed=7, captain=105, seed=0, delay_byte=0, set_piece=True)
        match.st = dict(prompt=None, kickoff_seed=kickoff, recording=kickoff is not None, answer=None)
        match.squad = list(range(101, 121))
        match._squad = lambda country: match.squad
        match.declarations = []
        match._declare = lambda *args: match.declarations.append(args)
        return match

    def test_initial_explicit_captain_is_still_selected(self):
        match = self.match()
        match.m.cursor = 3
        match._on_prompt(False)
        self.assertEqual(match._captain_key(), S.DOWN)
        match.m.cursor = 5
        self.assertEqual(match._captain_key(), S.ENTER)
        self.assertIsNone(match.st['prompt'])

    def test_withdrawn_captain_is_not_forced_from_bench_slot_fourteen(self):
        match = self.match(kickoff=0)
        match.squad[4], match.squad[13] = match.squad[13], match.squad[4]
        match.m.cursor = 3
        match._on_prompt(False)
        self.assertEqual(match._captain_key(), S.ENTER)
        self.assertIsNone(match.st['prompt'])

    def test_later_captain_choice_uses_the_guests_eligible_default(self):
        match = self.match(kickoff=123)
        match.m.cursor = 3
        match._on_prompt(False)
        self.assertEqual(match._captain_key(), S.ENTER)

    def test_zero_kickoff_seed_and_delay_are_not_reapplied_later(self):
        match = self.match()
        match._on_prompt(False)
        match._on_wait(False)
        self.assertEqual(len(match.declarations), 2)
        self.assertEqual(match.st['kickoff_seed'], 0)
        self.assertTrue(match.st['recording'])
        self.assertEqual(match._captain_key(), S.ENTER)
        match.declarations.clear()
        match.m.seed = 999
        match._on_prompt(False)
        match._on_wait(False)
        self.assertEqual(match.declarations, [])
        self.assertEqual(match.st['kickoff_seed'], 0)
        self.assertTrue(match.st['recording'])

    def test_set_piece_target_selection_is_preserved(self):
        match = self.match(kickoff=0)
        match.st['prompt'] = dict(role=2, target=106, waited=True)
        match.m.cursor = 3
        self.assertEqual(match._captain_key(), S.DOWN)
        match.m.cursor = 6
        self.assertEqual(match._captain_key(), S.ENTER)


from goal2.tests import requires


def original_withdrawal(state, fixture, pair):
    """Unicorn reference; the sealed port is played only by the real worker."""
    from dataclasses import asdict
    from goal2.tests.test_watched_adapter import direct_image
    from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS
    from goal2.tests.test_watched_bench_t102 import _memory_digest
    match=Match(direct_image(state),fixture,managed=state.managed_country,captain=state.captain,
                delay_byte=0,record_draws=True,substitutions=FRIENDLY_SUBSTITUTIONS)
    events=[];sent=False
    for event in match.events():
        events.append(asdict(event))
        if event.kind=='decision':
            if event.data['context']=='half_time' and not sent:
                match.answer(substitutions=[pair]);sent=True
            else: match.answer()
    assert sent
    return match.result(),_memory_digest(match.memory_component()),events


@requires.need(modules=('unicorn',), slow=True, **requires.HALFTIME)
class ActualCaptainWithdrawalT187(unittest.TestCase):
    def test_withdrawn_explicit_captain_finishes_and_publishes_exactly_once(self):
        import copy
        import tempfile
        import time
        from dataclasses import asdict
        from goal2.tests.test_watched_bench_t102 import model,fixture_of,_memory_digest
        from goal2.tests import port_parity
        from goal2.game import campaign_rounds
        from goal2.game.watched_jobs import WatchedJobs
        with tempfile.TemporaryDirectory() as folder:
            owner=model(Path(folder)/'captain.g2save')
            owner.state.captain=owner.state.starting_eleven[3]
            captain=owner.state.captain
            before=copy.deepcopy(owner.state)
            fixture=fixture_of(before)
            jobs=WatchedJobs(owner)
            pair=None
            try:
                token=jobs.start(fixture,delay_byte=0,record_draws=True,frames=True,bench=True)
                deadline=time.monotonic()+900
                while jobs.busy:
                    self.assertLess(time.monotonic(),deadline,'captain withdrawal did not finish')
                    jobs.poll(token)
                    if not jobs.busy: break
                    jobs.poll_frames(token)
                    if not jobs.busy: break
                    if jobs._frame_sequence:
                        jobs.ack_frames(token,jobs._frame_sequence-1)
                    if jobs.waiting is not None and jobs.frames_drained():
                        decision=jobs.waiting
                        if decision.data['context']=='half_time' and pair is None:
                            self.assertIn(captain,decision.data['eleven'])
                            positions=dict(decision.data['positions'])
                            on=next(w for w in decision.data['bench'] if positions[w]!=0)
                            pair=[captain,on]
                            jobs.answer(token,[pair])
                        else: jobs.answer(token,[])
                    time.sleep(.002)
                self.assertIsNotNone(pair)
                self.assertIsNotNone(jobs.outcome)
                made=[e for e in jobs.outcome.result['substitutions'] if [e['off'],e['on']]==pair]
                self.assertEqual(len(made),1)
                self.assertEqual(owner.state.match_count,before.match_count+1)
                published=copy.deepcopy(owner.state)
                jobs.poll(token)
                self.assertEqual(owner.state,published)
                prepared=campaign_rounds.prepare(before,owner.template_bytes)
                result,memory,events=original_withdrawal(prepared,fixture,pair)
                self.assertEqual(port_parity.comparable_result(jobs.outcome.result),
                                 port_parity.comparable_result(result))
                self.assertEqual(_memory_digest(jobs.outcome.memory),memory)
                self.assertEqual(port_parity.comparable_events(jobs.outcome.events),
                                 port_parity.comparable_events(events))
            finally: jobs.close()


if __name__ == '__main__':
    unittest.main()
