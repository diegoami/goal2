"""[designed: T170ab/#808] Lossless bounded native completed-tick feed.

Synthetic controls contain no original data. Actual port driving runs in PyPy;
only counts/digests are printed, never frames, records or original memory.
"""
import copy
import hashlib
import io
import json
import queue
import sys
import time
import unittest
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch

from goal2.game.season_pitch import validate_batch
from goal2.game.season_worker import SeasonWorker,SeasonRequestError
from goal2.game.prematch_seam import PrematchSeam
from goal2.game.season import canonical_hash
from goal2.tests.test_season_session_t170b import state,step
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest
from goal2.tests import pypy_engine,requires


def frame(sequence=0,watermark=0):
    return dict(version=2,sequence=sequence,watermark=watermark,minute=3,score=[0,0],
        subtick=0,threshold=255,remaining=1,selector=1,attack=[-127,127],sentinel=0x7F7F,
        ball=[-12,108,False],officials=dict(referee=[-128,127,False],linesmen=[[-1,120],[127,-128]],holder=22),
        players=[[i,int(i<=11),i if i<=11 else i-11,i,-i,70-i,255,False] for i in range(1,23)])


def batch(events=None,frames=None,decision=None,total=None):
    events=[] if events is None else events;frames=[] if frames is None else frames
    return dict(request=2,action='next',events=events,frames=frames,
                event_count=len(events) if total is None else total,decision=decision,over=False,exhausted=False)


class Packets(unittest.TestCase):
    def parent(self,enabled=True,count=32):
        from goal2.game.engine_process import EngineProcess
        engine=EngineProcess(lambda *a:None);engine._life=object();engine._season_active=True
        with patch.object(engine,'_send'):
            engine.season_request('configure',**({'frames':True} if enabled else {}))
            engine._decode(engine._life,dict(kind='season',value=dict(request=1,action='configure')),b'')
            engine.season_request('next',count=count)
        return engine

    def test_signed_frames_interleave_and_parent_server_roundtrip(self):
        from goal2.game.engine_server import Server,read_packet
        value=batch([dict(kind='minute',data={})],[frame(0,0),frame(1,1)])
        before=copy.deepcopy(value);self.assertEqual(validate_batch(value,0,0,0,3),(2,1,1))
        output=io.BytesIO();server=Server(io.BytesIO(),output)
        with patch.object(server.season,'dispatch',return_value=copy.deepcopy(value)):
            server._season(dict(op='season',request=2,action='next',count=3),b'')
        output.seek(0);header,payload=read_packet(output);engine=self.parent(count=3)
        kind,decoded=engine._decode(engine._life,header,payload)
        self.assertEqual(kind,'season');self.assertEqual(decoded,before);self.assertEqual(value,before)
        self.assertEqual(engine._season_pitch_sequence,2);self.assertEqual(engine._season_pitch_events,1)
        decoded['frames'][0]['players'][0][4]=99;self.assertEqual(value['frames'][0]['players'][0][4],-1)

    def test_corrupt_schema_order_watermark_counter_and_pose_never_deliver(self):
        from goal2.game.engine_server import ProtocolError
        good=batch([dict(kind='minute',data={})],[frame(0,1)])
        mutations=[lambda p:p.update(event_count=True),lambda p:p.update(event_count=2),
            lambda p:p.update(over=0),lambda p:p.update(exhausted=None),lambda p:p.update(extra=1),
            lambda p:p['frames'][0].update(sequence=1),lambda p:p['frames'][0].update(sequence=True),
            lambda p:p['frames'][0].update(watermark=2),lambda p:p['frames'][0].update(version=99),
            lambda p:p['frames'][0]['ball'].__setitem__(0,-129),
            lambda p:p['frames'][0]['players'][0].__setitem__(3,0),
            lambda p:p['frames'][0]['players'][0].__setitem__(0,True),
            lambda p:p['frames'][0]['officials'].update(holder=256),
            lambda p:p['frames'][0].update(selector=0),lambda p:p.update(decision=True),
            lambda p:p['events'].append(dict(kind='tick',data={}))]
        for mutate in mutations:
            engine=self.parent();value=copy.deepcopy(good);mutate(value)
            with self.subTest(value=mutations.index(mutate)):
                with self.assertRaises(ProtocolError):engine._decode(engine._life,dict(kind='season',value=value),b'')
                self.assertEqual(engine._season_pitch_sequence,0);self.assertEqual(engine._season_pitch_events,0)
        with self.assertRaises(ValueError):validate_batch(batch(frames=[frame(0,0)]),0,0,1,1)
        with self.assertRaises(ValueError):validate_batch(batch(frames=[frame(),frame(1)]),0,0,0,1)

    def test_decision_stop_empty_batch_and_lifecycle_resets(self):
        value=batch([dict(kind='decision',data={'context':'half_time'})],decision=5)
        self.assertEqual(validate_batch(value,0,0,0,1),(0,0,1))
        self.assertEqual(validate_batch(batch(total=1),0,0,1,1),(0,0,1))
        bad=copy.deepcopy(value);bad['events'].append(dict(kind='minute'))
        with self.assertRaises(ValueError):validate_batch(bad,0,0,0,2)
        engine=self.parent();engine._decode(engine._life,dict(kind='season',value=batch(frames=[frame()])),b'')
        with patch.object(engine,'_send'):engine.season_request('discard')
        engine._decode(engine._life,dict(kind='season',value=dict(request=3,action='discard')),b'')
        self.assertFalse(engine._season_pitch);self.assertEqual(engine._season_pitch_sequence,0)
        from goal2.game.engine_server import ProtocolError
        engine=self.parent(enabled=False)
        with self.assertRaises(ProtocolError):engine._decode(engine._life,dict(kind='season',value=batch()),b'')
        engine=self.parent();engine._life=SimpleNamespace(process=SimpleNamespace(stdin=io.BytesIO()))
        self.assertTrue(engine._ended(engine._life));self.assertFalse(engine._season_pitch)
        self.assertEqual(engine._season_pitch_sequence,0)


class Worker(unittest.TestCase):
    def make(self):
        from goal2.engine.original_match.match import Event
        class Match:
            over=False
            def configure_route_entry(self,**values):self.options=values
            def events(self):
                yield Event('minute',0,(0,0))
                for _ in range(4):yield Event('tick',0,(0,0))
                yield Event('decision',1,(0,0),{'context':'half_time'})
                yield Event('tick',1,(0,0));self.over=True
        value=state();match=Match();worker=SeasonWorker();number=0
        def ask(action,**values):
            nonlocal number
            number+=1;return worker.dispatch(dict(op='season',request=number,action=action,**values))
        ask('open',state=value)
        with patch('goal2.game.season.route.play_round',return_value=step('match',value,match=match)):ask('advance')
        return worker,match,ask

    def test_bounded_frames_decisions_detach_and_no_implicit_answer(self):
        worker,match,ask=self.make();ask('configure',frames=True);self.assertIs(match.options['ticks'],True)
        with patch('goal2.game.watched_pitch.snapshot',side_effect=lambda m,e,s,w:frame(s,w)):
            first=ask('next',count=3)
            self.assertEqual([e['kind'] for e in first['events']],['minute'])
            self.assertEqual([f['sequence'] for f in first['frames']],[0,1]);self.assertEqual(first['event_count'],1)
            first['frames'][0]['players'][0][3]=3000
            second=ask('next',count=3)
            self.assertEqual([f['sequence'] for f in second['frames']],[2,3]);self.assertEqual(second['event_count'],2)
            self.assertIsNotNone(second['decision']);self.assertEqual(second['frames'][0]['players'][0][3],1)
            with self.assertRaises(SeasonRequestError):ask('next')
        self.assertIs(worker.session.pending_match,match)

    def test_default_kwargs_and_wire_unchanged_and_invalid_flags_are_pure(self):
        worker,match,ask=self.make()
        for bad in (None,0,1,'yes',[]):
            with self.assertRaises(SeasonRequestError):ask('configure',frames=bad)
            self.assertIsNone(worker.seam);self.assertIsNone(worker.stream)
        ask('configure');self.assertNotIn('ticks',match.options)
        packet=ask('next',count=3)
        self.assertEqual(set(packet),{'request','action','events','decision','over','exhausted'})
        self.assertEqual([e['kind'] for e in packet['events']],['minute','tick','tick'])
        other,other_match,other_ask=self.make();other_ask('configure',frames=False)
        false_packet=other_ask('next',count=3)
        # Invalid guard attempts above changed request IDs only, not the old ABI.
        self.assertEqual({k:v for k,v in packet.items() if k!='request'},
                         {k:v for k,v in false_packet.items() if k!='request'})
        self.assertEqual(match.options,other_match.options)
        with self.assertRaises(SeasonRequestError):ask('configure',frames=True)
        from goal2.game.native_season import NativeSeasonOwner
        for bad in (None,0,1,'yes'):
            owner=SimpleNamespace()
            with self.assertRaisesRegex(ValueError,'frames'):NativeSeasonOwner(owner,{},frames=bad)
            self.assertFalse(hasattr(owner,'_match_engine'))

    def test_optin_owner_declares_ticks_before_entry_and_refuses_early_samples(self):
        from goal2.tests.test_native_season_t170aa import seed,FakeEngine,boundary,Pure
        from goal2.game.watched_jobs import MatchEngine
        from goal2.game.native_season import NativeSeasonOwner
        p,data=seed();owner=SimpleNamespace();keeper=object()
        with patch('goal2.game.engine_process.EngineProcess',FakeEngine):shared=MatchEngine.join(owner,keeper)
        native=NativeSeasonOwner(owner,p['state'],frames=True);self.addCleanup(Pure.dispose,self,native)
        engine=shared.engine;engine.emit('open',**boundary(p['state']));native.poll();native.advance()
        engine.emit('advance',**boundary(p['state'],1,'match'));native.poll()
        self.assertEqual(engine.calls[-1],('configure',{'frames':True}))
        engine.emit('configure');native.poll()
        engine.emit('next',**{k:v for k,v in batch(frames=[frame()]).items() if k not in ('action','request')})
        self.assertEqual(native.poll(),'lost');self.assertIn('before pre-match',native.message)
        self.assertIsNone(native.controller)


def policy(data):
    if data.get('context')=='substitution_opportunity':return {'opportunity':'dismiss'}
    if data.get('context')=='pre_match':return {'captain':None}
    return {}


def full_run(raw,worker_mode=True,enabled=True):
    """Complete actual Match and round; report hashes only. PyPy exclusively."""
    from goal2.game.season import SeasonSession
    from goal2.game import engine_tables
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game.watched_pitch import snapshot
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    initial=Image.from_bytes(raw).state(engine_tables.load());number=0;events=[];frames=[];guards=0
    def checked(m,e,s,w):
        nonlocal guards
        before=None
        if s%500==0:
            before=(m.m.read(0,MEM_SIZE),tuple(m.m.reg(r) for r in REGS),copy.deepcopy((m.st,m.opts,m.inputs)))
        result=snapshot(m,e,s,w)
        if before is not None:
            assert before==(m.m.read(0,MEM_SIZE),tuple(m.m.reg(r) for r in REGS),copy.deepcopy((m.st,m.opts,m.inputs))),'sampler changed backend'
            guards+=1
        return result
    if worker_mode:
        worker=SeasonWorker()
        def ask(action,**values):
            nonlocal number
            number+=1;return worker.dispatch(dict(op='season',request=number,action=action,**values))
        ask('open',state=initial);boundary=ask('advance');match=worker.session.pending_match;identity=id(match)
        ask('configure',**({'frames':True} if enabled else {}))
        with patch('goal2.game.watched_pitch.snapshot',side_effect=checked):
            while True:
                p=ask('next',count=32);events.extend(p['events']);frames.extend(p.get('frames',[]))
                assert id(worker.session.pending_match)==identity
                if p['decision'] is not None:ask('answer',decision=p['decision'],answer=policy(p['events'][-1]['data']))
                if p['exhausted']:break
        boundary_hash=canonical_hash(boundary['state'])
        result=ask('resume');state_hash=canonical_hash(result['state']);observation_hash=digest(result['observation'])
        observed=ask('observe');assert not observed['observation']['news_pages'] and not observed['observation']['played_fixtures']
    else:
        session=SeasonSession(initial);session.advance();match=session.pending_match;identity=id(match)
        boundary_hash=canonical_hash(session.state);PrematchSeam(match,frames=enabled)
        for event in match.events():
            if event.kind=='tick' and enabled:frames.append(checked(match,event,len(frames),len(events)))
            else:events.append(asdict(event))
            if event.kind=='decision':match.answer(**policy(event.data))
            assert id(session.pending_match)==identity
        obs=session.resume(match);state_hash=canonical_hash(session.state);observation_hash=digest(asdict(obs))
        observed=session.observe();assert not observed.news_pages and not observed.played_fixtures
    return dict(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),guards=guards,
        boundary_hash=boundary_hash,state_hash=state_hash,observation_hash=observation_hash,
        memory_hash=hashlib.sha256(match.m.read(0,MEM_SIZE)).hexdigest(),all16=[match.m.reg(r) for r in REGS])


class Actual(unittest.TestCase):
    @requires.need(slow=True)
    def test_complete_worker_equals_direct_sdk_and_sampling_changes_no_backend_state(self):
        raw=reference_raw();actual=pypy_engine.call(__name__+':full_run',raw,True,True)
        direct=pypy_engine.call(__name__+':full_run',raw,False,True)
        self.assertEqual(actual,direct);self.assertGreater(actual['frames'],0);self.assertGreater(actual['guards'],0)
        disabled=pypy_engine.call(__name__+':full_run',raw,False,False)
        for key in ('events_hash','events','boundary_hash','state_hash','observation_hash','memory_hash','all16'):
            self.assertEqual(actual[key],disabled[key],key)
        print('T170AB_COMPLETE '+json.dumps(actual,sort_keys=True),flush=True)


if __name__=='__main__':unittest.main()
