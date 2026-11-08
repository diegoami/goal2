"""[designed: T170c1/#655] Consume the already owned ordinary Match only."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from goal2.engine.original_match.match import Event,MatchError
from goal2.game import watched_match as W


def event(kind='decision',context='half_time',**data):
    return Event(kind,45,(0,0),dict(context=context,**data))


class Owned:
    def __init__(self,events):
        self.stream=events;self.answers=[];self.side=0
        self.m=SimpleNamespace(rd=lambda *args:2)
    def events(self):yield from self.stream
    def answer(self,**value):self.answers.append(copy.deepcopy(value))
    def pause(self):raise MatchError('no available poll')
    def result(self):raise AssertionError('consumer must not project result')
    def memory_component(self):raise AssertionError('consumer must not assemble outcome')
    @property
    def opts(self):raise AssertionError('consumer must not inspect or mutate private options')


class Policy:
    def __init__(self,values=()):self.values=iter(values);self.reports=[];self.pauses=[];self.dropped=[]
    def decide(self,ev):return next(self.values)
    def answered(self,value):self.reports.append(value)
    def pause_now(self,n):self.pauses.append(n);return True
    def pause_dropped(self,n):self.dropped.append(n)


class OwnedConsumer(unittest.TestCase):
    def consume(self,match,**options):
        def forbidden(*args,**kwargs):raise AssertionError('factory/setup/tail/publication forbidden')
        with patch.object(W,'Match',forbidden),patch.object(W,'sealed',forbidden),patch.object(W,'prepare_watched',forbidden),patch.object(W,'_complete_memory',forbidden),patch.object(W,'WatchedOutcome',forbidden):
            return W.consume_match(match,**options)

    def test_same_object_detached_order_and_single_edit_report(self):
        source=[event(),event('substitution',off=1,on=12,team=0),event('tactics',changes=[1]),event('commentary',text=['go'])]
        original=copy.deepcopy(source);match=Owned(source);policy=Policy([[(1,12)]])
        seen=[]
        def observer(ev):seen.append(copy.deepcopy(ev));ev.data['observer']='private'
        result=self.consume(match,policy=policy,_observe=observer)
        self.assertEqual(result,tuple(original));self.assertEqual(source,original);self.assertEqual(seen,original)
        self.assertEqual(match.answers,[{'substitutions':[[1,12]]}]);self.assertEqual(len(policy.reports),1)
        self.assertEqual(policy.reports[0]['made'],[[1,12]])
        result[-1].data['text'].append('caller');self.assertEqual(source,original)

    def test_false_cancellation_opportunity_and_prompt_answers(self):
        source=[event(context='pause'),event(context='substitution_opportunity'),event(context='set_piece'),event(context='shootout_order'),event(context='extra_time')]
        match=Owned(source);policy=Policy([{'request_substitution':False,'edit_only':True},{'opportunity':'accept'},{'taker':7},{'shootout_order':[7,8]},{}])
        self.consume(match,policy=policy,substitution_control=True,prompts=True,_observe_pitch=lambda x:None)
        self.assertEqual(match.answers,[{'substitutions':[],'request_substitution':False,'edit_only':True},{'opportunity':'accept'},{'taker':7},{'shootout_order':[7,8]},{}])

    def test_tick_sequence_pause_drop_and_event_watermarks(self):
        source=[event('commentary'),event('tick'),event('tick'),event('commentary')]
        match=Owned(source);policy=Policy();frames=[]
        with patch('goal2.game.watched_pitch.snapshot',side_effect=lambda m,ev,seq,watermark: {'sequence':seq,'watermark':watermark,'same':m is match}):
            result=self.consume(match,policy=policy,_observe_pitch=frames.append)
        self.assertEqual([v['sequence'] for v in frames],[0,1]);self.assertEqual([v['watermark'] for v in frames],[1,1])
        self.assertTrue(all(v['same'] for v in frames));self.assertEqual(policy.pauses,[0,1]);self.assertEqual(policy.dropped,[0,1])
        self.assertEqual([v.kind for v in result],['commentary','commentary'])

    def test_refusal_unknown_context_and_invalid_answers_remain_errors(self):
        for source in ([event(context='unknown')],[event(refused='illegal')],[event(),event()]):
            self.assertRaises(RuntimeError,self.consume,Owned(source))
        for answer in ({'opportunity':'wrong'},{'opportunity':'accept','substitutions':[]}):
            self.assertRaises(ValueError,self.consume,Owned([event(context='substitution_opportunity')]),policy=Policy([answer]),substitution_control=True,_observe_pitch=lambda x:None)
        self.assertRaises(ValueError,self.consume,Owned([event(context='pause')]),policy=Policy([[(1,12)]]),substitution_control=True,_observe_pitch=lambda x:None)
        self.assertRaises(ValueError,self.consume,Owned([]),prompts=True)
        self.assertRaises(ValueError,self.consume,Owned([]),substitution_control=True)

    def test_legacy_wrapper_configures_ticks_in_constructor_and_assembles_after_tail(self):
        # The wrapper alone owns construction/projection; the consumer sees exactly its object.
        match=Owned([]);match.result=lambda:{'score':[1,0]};match.memory_component=lambda:b'physical'
        state=SimpleNamespace(managed_country=7,captain=0);image=SimpleNamespace(year=lambda:3)
        after=SimpleNamespace(rd=lambda off: 12 if off==0x7B62 else 34)
        with patch.object(W,'Match',return_value=match) as factory,patch.object(W,'sealed',return_value='sealed'),patch.object(W,'consume_match',return_value=()) as consumer,patch.object(W,'_complete_memory',return_value=b'complete'),patch.object(W,'Image',return_value=after):
            result=W._drive_match(state,image,'fixture',_observe_pitch=lambda x:None)
        self.assertIs(consumer.call_args.args[0],match);self.assertIs(factory.call_args.kwargs['ticks'],True)
        self.assertEqual((result.memory,result.seeds,result.engine_year),(b'complete',(12,34),3))

if __name__=='__main__':unittest.main()
