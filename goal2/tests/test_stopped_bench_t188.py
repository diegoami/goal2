"""[designed: owner #599] Stopped edits are explicit, consumed once and never queued at a pause."""
import unittest
from types import SimpleNamespace
from goal2.tests import requires

class EditProtocol(unittest.TestCase):
    def bridge(self,context='half_time',allowed=True):
        from goal2.game.watched_jobs import WatchedJobs
        jobs=object.__new__(WatchedJobs)
        jobs.token='test';jobs.closed=False;jobs._active=True;jobs._decisions=3
        jobs.waiting=SimpleNamespace(data=dict(context=context,substitutions_now=allowed))
        jobs.sent=[]
        engine=SimpleNamespace(answer=lambda *args,**kwargs:jobs.sent.append((args,kwargs)))
        jobs._command=lambda token,send:send(engine)
        return jobs

    def test_edit_flag_round_trips_and_rejects_ambiguous_values(self):
        from goal2.game.watched_jobs import _changes
        self.assertEqual(_changes({'edit_only':True}),{'edit_only':True})
        self.assertEqual(_changes({'edit_only':False}),{})
        for value in (1,0,'true',{},[]):
            with self.assertRaises(ValueError):_changes({'edit_only':value})

    def test_one_stopped_edit_is_one_answer_and_the_consumed_decision_cannot_repeat_it(self):
        jobs=self.bridge()
        jobs.edit('test',[(105,112)])
        self.assertEqual(jobs.sent,[((3,[[105,112]]),{'changes':{'edit_only':True}})])
        self.assertEqual(jobs._decisions,4)
        self.assertIsNone(jobs.waiting)
        with self.assertRaises(ValueError): jobs.edit('test',[(105,112)])
        self.assertEqual(len(jobs.sent),1)

    def test_pause_or_disallowed_operation_keeps_decision_and_sends_nothing(self):
        for context,allowed in [('pause',False),('extra_time',True),('half_time',False)]:
            jobs=self.bridge(context,allowed)
            waiting=jobs.waiting
            with self.assertRaises(ValueError):jobs.edit('test',[(105,112)])
            self.assertIs(jobs.waiting,waiting)
            self.assertEqual(jobs.sent,[])
            self.assertEqual(jobs._decisions,3)

    def test_lower_level_answer_cannot_bypass_stop_requirement(self):
        jobs=self.bridge('pause',False)
        with self.assertRaises(ValueError):jobs.answer('test',[(105,112)],{'edit_only':True})
        self.assertEqual(jobs.sent,[])
        self.assertIsNotNone(jobs.waiting)

if __name__=='__main__':unittest.main()
