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


@requires.need(modules=('unicorn',),slow=True,**requires.HALFTIME)
class ActualStoppedEdits(unittest.TestCase):
    def test_two_edits_and_one_refusal_stay_stopped_then_publish_once(self):
        import copy
        import tempfile
        import time
        from pathlib import Path
        from goal2.tests.test_watched_bench_t102 import model,fixture_of
        from goal2.game.watched_jobs import WatchedJobs
        with tempfile.TemporaryDirectory() as folder:
            owner=model(Path(folder)/'edits.g2save')
            before=copy.deepcopy(owner.state)
            fixture=fixture_of(before)
            team=0 if fixture.first==before.managed_country else 1
            jobs=WatchedJobs(owner)
            phase=0; pairs=[]; frozen=None; original_left=None; stopped_minute=None
            try:
                token=jobs.start(fixture,delay_byte=0,record_draws=True,frames=True,bench=True)
                deadline=time.monotonic()+900
                while jobs.busy:
                    self.assertLess(time.monotonic(),deadline,'stopped edits did not finish')
                    jobs.poll(token)
                    if not jobs.busy:break
                    jobs.poll_frames(token)
                    if not jobs.busy:break
                    if jobs._frame_sequence-1>jobs._frame_ack:
                        jobs.ack_frames(token,jobs._frame_sequence-1)
                    if jobs.waiting is None or not jobs.frames_drained():
                        time.sleep(.002);continue
                    decision=jobs.waiting;data=decision.data
                    if data['context']!='half_time':
                        jobs.answer(token,[]);continue
                    self.assertLess(phase,4,'Play returned to an unexpected duplicate edit')
                    self.assertEqual(owner.state,before,'a stopped edit published the unfinished career')
                    if phase==0:
                        positions=dict(data['positions'])
                        off=[w for w in data['eleven'] if positions[w]!=0 and w!=before.captain]
                        on=[w for w in data['bench'] if positions[w]!=0]
                        pairs=[[off[i],on[i]] for i in range(2)]
                        original_left=data['substitutions_left']
                        frozen=jobs._frame_sequence
                        stopped_minute=decision.minute
                        jobs.edit(token,[pairs[0]]);phase=1;continue
                    self.assertTrue(data.get('edited'))
                    self.assertEqual(decision.minute,stopped_minute)
                    self.assertEqual(jobs._frame_sequence,frozen,'the pitch advanced before Play')
                    self.assertEqual(data['substitutions_left'],original_left-min(phase,2))
                    self.assertFalse(data.get('requested'))
                    for off,on in pairs[:min(phase,2)]:
                        self.assertIn(off,data['bench']);self.assertIn(on,data['eleven'])
                    if phase in (1,2):
                        self.assertEqual(jobs.reports[-1]['asked'],[pairs[phase-1]])
                        self.assertEqual(jobs.reports[-1]['made'],[pairs[phase-1]])
                        self.assertEqual(jobs.reports[-1]['requested'],[])
                    if phase==1:jobs.edit(token,[pairs[1]])
                    elif phase==2:jobs.edit(token,[[pairs[0][1],pairs[0][0]]])
                    else:
                        self.assertEqual(jobs.reports[-1]['made'],[])
                        refused=jobs.reports[-1]['refused']
                        self.assertEqual(len(refused),1)
                        self.assertEqual(refused[0][:2],[pairs[0][1],pairs[0][0]])
                        self.assertTrue(refused[0][2])
                        jobs.answer(token,[])
                    phase+=1
                self.assertEqual(phase,4)
                self.assertIsNotNone(jobs.outcome)
                made=[e for e in jobs.outcome.result['substitutions'] if e['team']==team]
                self.assertEqual([[e['off'],e['on']] for e in made],pairs)
                self.assertEqual(len(jobs.reports),3)
                self.assertTrue(all(not report['requested'] for report in jobs.reports))
                self.assertEqual(owner.state.match_count,before.match_count+1)
                published=copy.deepcopy(owner.state)
                with self.assertRaises(ValueError):jobs.answer(token,pairs)
                self.assertEqual(owner.state,published)
            finally:jobs.close()

if __name__=='__main__':unittest.main()
