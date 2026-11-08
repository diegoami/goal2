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

def actual_owned_route(raw):
    """[designed: T170c1] Two accepted held Matches; no host XI/fixture edits."""
    import builtins,hashlib,json,sys
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11)
    previous=builtins.__import__
    def denied(name,*args,**kwargs):
        if name=='unicorn' or name.startswith('unicorn.'):raise ImportError('Unicorn denied')
        return previous(name,*args,**kwargs)
    builtins.__import__=denied
    try:__import__('unicorn')
    except ImportError:pass
    else:raise AssertionError('Unicorn guard inactive')
    from goal2.engine.original_match import route,Image,Match
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.engine.original_match.match import RUN_MATCH_RETURN
    from goal2.game import engine_tables
    assert Uc is None
    image=Image.from_bytes(raw);tables=engine_tables.load();state=image.state(tables)
    digest=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=lambda x:x.__dict__).encode()).hexdigest()
    sha=lambda value:hashlib.sha256(value).hexdigest()
    keys=[route.Keys(route.DEFAULT_KEYS),route.Keys(route.DEFAULT_KEYS)]
    steps=[route.play_round(state,tables,key) for key in keys]
    assert all(v.status=='match' and type(v.match) is Match and not v.match.opts['tail'] for v in steps)
    assert steps[0].match.m.read(0,MEM_SIZE)==steps[1].match.m.read(0,MEM_SIZE)
    outputs=[];returned=[];input_matches=[]
    for index,step in enumerate(steps):
        match=step.match;parent=step.continuation
        parent_before=parent.m.read(0,MEM_SIZE);parent_regs={n:parent.m.reg(n) for n in REGS}
        record_before=copy.deepcopy(parent.record)
        input_matches.append(sha(match.m.read(0,MEM_SIZE)))
        if index==0:
            events=W.consume_match(match)
        else:
            observed=[]
            for ev in match.events():
                observed.append(copy.deepcopy(ev))
                if ev.kind=='decision':match.answer()
            events=tuple(observed)
        assert match.over and parent.pending is match and not parent.finished
        assert parent.m.read(0,MEM_SIZE)==parent_before and parent.record==record_before
        assert {n:parent.m.reg(n) for n in REGS}==parent_regs
        regs={n:match.m.reg(n) for n in REGS};returned.append(regs)
        assert match.m.pc()==match.m.lin(RUN_MATCH_RETURN) and match.m.reg('sp')==0x3EC8
        outputs.append((match.result(),events,match.m.read(0,MEM_SIZE),tuple(match.m.rd(off) for off in route.SEEDS.values())))
    assert outputs[0]==outputs[1] and returned[0]==returned[1]
    resumed=[];transferred=[]
    for step in steps:
        seen=[];parent=step.continuation
        parent.m.at('000E:6F1D',lambda replay,parent=parent,seen=seen:None if replay else seen.append({n:parent.m.reg(n) for n in REGS}))
        resumed.append(route.resume_round(parent,step.match));transferred.append(seen)
    assert transferred==[[returned[0]],[returned[1]]]
    assert resumed[0].state==resumed[1].state and resumed[0].played_fixtures==resumed[1].played_fixtures
    assert resumed[0].news_pages==resumed[1].news_pages and resumed[0].record==resumed[1].record
    assert keys[0].waiting==keys[1].waiting
    return {'input_sha256':sha(raw),'input_match_memory_sha256':input_matches,'fixture_edits':[],
            'host_xi_edits':[],'answers':'original default empty answer at every actual decision',
            'result_equal':True,'result_sha256':digest(outputs[0][0]),'events_equal':True,
            'event_count':len(outputs[0][1]),'events_sha256':digest(outputs[0][1]),
            'full_memory_equal':True,'full_memory_sha256':sha(outputs[0][2]),
            'both_pre_tail_seeds_equal':True,'pre_tail_seeds':outputs[0][3],
            'all16_return_equal':True,'returned_registers':returned[0],
            'actual6F1D_all16_transfer_equal':True,'parent_unchanged_before_explicit_resume':True,
            'post_resume_state_equal':True,'post_resume_state_sha256':digest(resumed[0].state),
            'post_resume_status':resumed[0].status,'unicorn_denied':True}


from goal2.tests import requires,pypy_engine
from goal2.engine.original_match.assets import REFERENCE
@requires.need(slow=True,files=(REFERENCE['asset'],))
class ActualOwnedRoute(unittest.TestCase):
    def test_actual_owned_route_match_equals_direct_accepted_events_and_return(self):
        import json
        from pathlib import Path
        from goal2.engine.original_match.assets import reference_image
        raw=reference_image(Path(__file__).resolve().parents[2]/'.cache')
        receipt=pypy_engine.call(__name__+':actual_owned_route',raw)
        self.assertTrue(receipt['result_equal'] and receipt['events_equal'] and receipt['full_memory_equal'])
        self.assertTrue(receipt['both_pre_tail_seeds_equal'] and receipt['all16_return_equal'])
        self.assertTrue(receipt['actual6F1D_all16_transfer_equal'])
        self.assertTrue(receipt['parent_unchanged_before_explicit_resume'])
        print('T170C1_OWNED '+json.dumps(receipt,sort_keys=True),flush=True)


if __name__=='__main__':unittest.main()
