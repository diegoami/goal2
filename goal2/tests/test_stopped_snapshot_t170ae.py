"""[designed: T170ae/#818] Current native reads do not play or publish."""
import copy
import json
import unittest
from dataclasses import FrozenInstanceError

from goal2.game.season import canonical_hash
from goal2.game.stopped_snapshot import StoppedMatchSnapshot
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_prematch_view_t170x import synthetic


def sample():
    packet,data=synthetic();data.pop('pool');data.update(context='pause',substitutions_left=0,
        substitutions_now=False,request_substitution=False)
    packet=dict(request=9,action='stopped_preview',state=packet['state'],data=data)
    packet['preview']=dict(schema='goal2/stopped-preview/1',decision=3,managed_country=7,
        state_hash=canonical_hash(packet['state']),data_hash=canonical_hash(data))
    return packet,data


def build(packet,expected,**kw):
    args=dict(request=9,decision=3,managed_country=7,data=expected);args.update(kw)
    return StoppedMatchSnapshot.from_packet(packet,**args)


class Pure(unittest.TestCase):
    def test_parent_rejects_corrupt_wire_and_serializes_requests(self):
        from unittest.mock import patch
        from goal2.game.engine_process import EngineProcess
        from goal2.game.engine_server import ProtocolError
        for corrupt in (None,'decision','country','state_hash','data_hash','data','observation','json'):
            engine=EngineProcess(lambda *args:None);engine._life=object();engine._season_active=True
            with patch.object(engine,'_send'):
                for bad in (None,True,0,'3'):
                    with self.assertRaises(ValueError):engine.season_request('stopped_preview',decision=bad)
                    self.assertFalse(engine.busy)
                engine.season_request('stopped_preview',decision=3)
                with self.assertRaises(ValueError):engine.season_request('answer',decision=3,answer={})
                with self.assertRaises(ValueError):engine.season_request('stopped_preview',decision=3)
            packet,data=sample();packet['request']=1;state=packet.pop('state')
            if corrupt in ('decision','country','state_hash','data_hash'):
                key='managed_country' if corrupt=='country' else corrupt
                packet['preview'][key]=False if corrupt in ('decision','country') else 'wrong'
            elif corrupt=='data':packet['data']['positions'][0][1]=9
            elif corrupt=='observation':packet['observation']={}
            reply=dict(kind='season',value=packet)
            payload=b'not-json' if corrupt=='json' else json.dumps(state).encode()
            if corrupt is None:
                kind,got=engine._decode(engine._life,reply,payload)
                self.assertEqual(kind,'season');self.assertEqual(got['state'],state);self.assertFalse(engine.busy)
            else:
                with self.assertRaises(ProtocolError):engine._decode(engine._life,reply,payload)

    def test_exact_identity_hashes_context_and_native_records(self):
        packet,data=sample();self.assertEqual(build(packet,data).context,'pause')
        mutations=[lambda p:p.update(request=True),lambda p:p.update(action='preview'),
            lambda p:p['preview'].update(decision=True),lambda p:p['preview'].update(managed_country=8),
            lambda p:p['preview'].update(schema='wrong'),lambda p:p['preview'].update(state_hash='bad'),
            lambda p:p['preview'].update(data_hash='bad'),lambda p:p['data']['eleven'].reverse(),
            lambda p:p['preview'].update(extra=1),lambda p:p.update(extra=1)]
        for mutate in mutations:
            p=copy.deepcopy(packet);mutate(p)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):build(p,data)
        for kw in ({'request':True},{'decision':0},{'managed_country':False},{'data':dict(data,context='pre_match')}):
            with self.assertRaises(ValueError):build(packet,data,**kw)
        # Rehashing a corrupt but internally consistent declaration cannot bypass
        # verification against the native memory/records.
        for field,value in (('tactics',0),('substitutions_left',1),('substitutions_left',False),
                            ('substitutions_now',True),('request_substitution',True),
                            ('positions',[[1,9]]),('player_records',[[1,'00'*20]]),
                            ('context','unknown')):
            p=copy.deepcopy(packet);p['data'][field]=value
            p['preview']['data_hash']=canonical_hash(p['data'])
            with self.subTest(field=field),self.assertRaises(ValueError):build(p,p['data'])

    def test_immutable_detached_state_and_exact_prompt_domains(self):
        packet,data=sample();view=build(packet,data)
        self.assertEqual(view.state,packet['state']);self.assertEqual(view.data,data)
        state=view.state;state['header']='changed';got=view.data;got['eleven'].reverse()
        packet['state']['header']='changed';data['bench'].reverse()
        self.assertNotEqual(view.state['header'],'changed');self.assertEqual(view.data['eleven'][0],1)
        with self.assertRaises(FrozenInstanceError):view.decision=4
        for context,extra in (('set_piece',dict(role=2,current=2,available=list(range(1,12)))),
                              ('shootout_order',dict(takers=11,available=list(range(1,12))))):
            p,d=sample();d.update(context=context,**extra);d.pop('substitutions_now')
            p['preview']['data_hash']=canonical_hash(d)
            self.assertEqual(build(p,d).data['available'],list(range(1,12)))
            d['available']=[1,1];p['preview']['data_hash']=canonical_hash(d)
            with self.assertRaises(ValueError):build(p,d)


def actual(raw,complete=False,watched=False):
    import hashlib
    import sys
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game import engine_tables
    from goal2.game.season_worker import SeasonWorker,SeasonRequestError
    from goal2.tests.test_native_driver_actual_t170ac import Answers
    from goal2.tests.test_season_news_wire_t170t import digest
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    initial=Image.from_bytes(raw).state(engine_tables.load());w=SeasonWorker();n=0
    def ask(action,**kw):
        nonlocal n
        n+=1;return w.dispatch(dict(op='season',request=n,action=action,**kw))
    def refused(**kw):
        before=freeze()
        try:ask('stopped_preview',**kw)
        except SeasonRequestError:pass
        else:raise AssertionError('expected pure stopped read refusal')
        assert freeze()==before
    try:ask('stopped_preview',decision=1)
    except SeasonRequestError:pass
    else:raise AssertionError('read without season')
    from goal2.engine.original_match import route
    # [confirmed: route.READ/default policy, original0791:E80D/E869] Explicit
    # native watch answer; no started-Match options are changed.
    keys=dict(route.DEFAULT_KEYS)
    if watched:keys[route.MENU_SITE+'<0791:E86E']=ord('Y')
    ask('open',state=initial,keys=keys);ask('advance');m=w.session.pending_match;identity=id(m)
    def freeze():
        return (m.m.read(0,MEM_SIZE),tuple(m.m.reg(r) for r in REGS),copy.deepcopy(m.st),
            copy.deepcopy(m.opts),copy.deepcopy(m.inputs),copy.deepcopy(getattr(m,'_replay_actions',None)),
            getattr(m,'_replay_events',None),copy.deepcopy(m._frame_state()),w.session.state,
            copy.deepcopy(vars(w.session._keys)),w.session.observe(),id(w.stream),id(w.seam),
            id(w.session.pending_match),w.decision,w.exhausted,w._decision_number,w.event_count,
            w.frame_sequence,w.frame_watermark)
    refused(decision=1);ask('configure',frames=True);refused(decision=1)
    boundary=canonical_hash(w.session.state);events=[];frames=[];policy=Answers();samples=[];contexts=set();reads=0
    while True:
        p=ask('next',count=1);events.extend(p['events']);frames.extend(p['frames'])
        if not watched and p['frames'] and len(frames)==1:assert ask('pause')['paused']
        if p['decision'] is not None:
            d=p['events'][-1]['data'];number=p['decision']
            if d['context']=='pre_match':refused(decision=number)
            else:
                before=freeze();got=ask('stopped_preview',decision=number)
                assert freeze()==before
                view=StoppedMatchSnapshot.from_packet(got,request=n,decision=number,
                    managed_country=m.opts['managed'],data=d)
                assert view.state==m.records_after() and view.data==m.waiting
                assert canonical_hash(w.session.state)==boundary and id(w.session.pending_match)==identity
                contexts.add(view.context);reads+=1
                if len(samples)<2:samples.append(copy.deepcopy(got))
                got['data']['eleven'].reverse();got['state']['header']='caller mutation'
                again=ask('stopped_preview',decision=number)
                assert again['data']==view.data and again['state']==view.state and freeze()==before
                for bad in (None,True,'1',number+1):refused(decision=bad)
                if watched and d['context']=='set_piece':
                    return dict(initial=initial,samples=[copy.deepcopy(again)])
            answer=policy(d);ask('answer',decision=number,answer=answer);refused(decision=number)
            if not watched and policy.edited and len(samples)==2 and not complete:
                return dict(initial=initial,samples=samples)
        if p['exhausted']:break
    if watched:raise AssertionError('explicit watched fixture did not reach a taker prompt')
    final=dict(memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])
    refused(decision=1);done=ask('resume');refused(decision=1)
    observed=ask('observe');assert not observed['observation']['played_fixtures'] and not observed['observation']['news_pages']
    final.update(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),
        boundary_hash=boundary,state_hash=canonical_hash(done['state']),observation_hash=digest(done['observation']),
        status=done['observation']['status'],pauses=1,edited=policy.edited)
    ask('discard')
    try:ask('stopped_preview',decision=1)
    except SeasonRequestError:pass
    else:raise AssertionError('read after discard')
    return dict(result=final,reads=reads,contexts=sorted(contexts))


class Actual(unittest.TestCase):
    def test_actual_watched_taker_read_preserves_exact_domain_and_machine(self):
        result=pypy_engine.call(__name__+':actual',reference_raw(),watched=True)
        self.assertEqual(result['samples'][0]['data']['context'],'set_piece')

    def test_actual_pause_edit_reads_preserve_full_machine_and_retry(self):
        samples=pypy_engine.call(__name__+':actual',reference_raw())['samples']
        self.assertEqual(len(samples),2)
        self.assertTrue(all(p['data']['context']=='pause' for p in samples))
        self.assertNotEqual(samples[0]['preview']['decision'],samples[1]['preview']['decision'])
        self.assertNotEqual(samples[0]['preview']['state_hash'],samples[1]['preview']['state_hash'])

    @requires.need(slow=True)
    def test_complete_sampled_worker_with_reads_equals_direct_sdk(self):
        from goal2.tests.test_native_driver_actual_t170ac import direct
        raw=reference_raw();expected=pypy_engine.call(direct.__module__+':direct',raw)
        got=pypy_engine.call(__name__+':actual',raw,complete=True)
        self.assertEqual(got['result'],expected)
        self.assertEqual(got['contexts'],['half_time','pause'])
        print('T170AE_FULL '+json.dumps(got,sort_keys=True),flush=True)


class Pipe(unittest.TestCase):
    from goal2.tests.test_season_worker_t170o import Pipe as _Pipe
    make_engine=_Pipe.make_engine
    receive=_Pipe.receive

    def test_actual_parent_pipe_snapshots_and_repairable_stale_read(self):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        raw=reference_raw();expected=pypy_engine.call(__name__+':actual',raw)['samples']
        engine=self.make_engine();engine.season_open(Image.from_bytes(raw).state(engine_tables.load()))
        self.receive('ready');self.receive('season');engine.season_request('advance');self.receive('season')
        engine.season_request('configure',frames=True);self.receive('season');frames=0;captured=[]
        from goal2.tests.test_native_driver_actual_t170ac import Answers
        policy=Answers()
        while len(captured)<2:
            engine.season_request('next',count=1);p=self.receive('season');frames+=len(p['frames'])
            if p['frames'] and frames==1:
                engine.season_request('pause');self.assertTrue(self.receive('season')['paused'])
            if p['decision'] is None:continue
            data=p['events'][-1]['data'];number=p['decision']
            if data['context']!='pre_match':
                engine.season_request('stopped_preview',decision=number+1)
                self.assertFalse(self.receive('season_error')['lost'])
                engine.season_request('stopped_preview',decision=number);got=self.receive('season')
                view=StoppedMatchSnapshot.from_packet(got,request=got['request'],decision=number,
                    managed_country=expected[0]['preview']['managed_country'],data=data)
                captured.append(view)
                e=expected[len(captured)-1]
                self.assertEqual(view.state,e['state']);self.assertEqual(view.data,e['data'])
                self.assertIsNone(engine._season_request);self.assertTrue(engine._season_active)
            engine.season_request('answer',decision=number,answer=policy(data));self.receive('season')
        engine.season_request('discard');self.receive('season')


if __name__=='__main__':unittest.main()
