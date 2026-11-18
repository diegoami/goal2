"""[designed: T170aa/#783] Shared native ownership; no original bytes embedded."""
import copy
from dataclasses import asdict
import queue
import sys
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from goal2.engine.original_match.image import Image,GAME_PTR,FIXTURES_PTR
from goal2.game import engine_tables
from goal2.game.native_season import NativeSeasonOwner,NativeFixture
from goal2.game.season import canonical_hash
from goal2.game.watched_jobs import MatchEngine
from goal2.tests.test_prematch_view_t170x import synthetic
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_prematch_marking_t170w import initial_state
from goal2.tests import pypy_engine,requires


def seed():
    """Declared data-only native-layout fixture; no original mechanism simulated."""
    p,d=synthetic();image=Image.from_state(p['state'],engine_tables.load())
    def word(at,n):image.memory[at:at+2]=n.to_bytes(2,'little')
    ds=image.DS*16;word(ds+FIXTURES_PTR,0);word(ds+FIXTURES_PTR+2,0x6900)
    game=image.far(GAME_PTR)
    for off,value in ((0x26,1),(0x28,2),(0x38,93)):word(game+off,value)
    image.memory[game+0x3C]=2
    image.memory[0x69000:0x69008]=bytes((254,0,1,0,7,0,8,0))
    p['state']=image.state(engine_tables.load());p['preview']['state_hash']=canonical_hash(p['state'])
    return p,d


class FakeEngine:
    """Typed transport scheduling control; it computes no match or season."""
    def __init__(self,callback):
        self.callback=callback;self.calls=[];self.busy=False;self.season_active=False
        self.closed=False;self.generation=0;self.process=None;self.cancel_deadline=.2
        self.pid=None;self.fail_start=False;self._number=0

    def season_open(self,state):
        if self.fail_start:raise FileNotFoundError('controlled missing worker')
        self.generation+=1;self.pid=123
        def kill():
            self.process=None;self.busy=self.season_active=False
            self.callback('death',{'code':-9})
        self.process=SimpleNamespace(kill=kill)
        self.calls.append(('open',copy.deepcopy(state)));self.busy=True

    def season_request(self,action,**values):
        if self.busy:raise ValueError('busy control')
        self.calls.append((action,copy.deepcopy(values)));self.busy=True

    def emit(self,action,deliver=True,**values):
        self._number+=1;self.busy=False
        if action=='open':self.season_active=True
        if action=='discard':self.season_active=False
        packet=('season',dict(request=self._number,action=action,**values))
        if deliver:self.callback(*packet)
        return packet

    def close(self):self.closed=True;self.process=None


def boundary(state,call=0,status='ready',fixtures=(),pages=()):
    from goal2.engine.original_match import route
    image=Image.from_state(state,engine_tables.load())
    return dict(state=copy.deepcopy(state),observation=dict(call_number=call,status=status,
        input_hash=canonical_hash(state),output_hash=canonical_hash(state),
        played_fixtures=fixtures,news_pages=pages,rng_words=[image.rd(off) for off in route.SEEDS.values()]))


class Pure(unittest.TestCase):
    def make(self,fail=False):
        p,d=seed();owner=SimpleNamespace(state='untouched');keeper=object()
        with patch('goal2.game.engine_process.EngineProcess',FakeEngine):shared=MatchEngine.join(owner,keeper)
        shared.engine.fail_start=fail
        native=NativeSeasonOwner(owner,p['state'])
        self.addCleanup(self.dispose,native)
        return native,shared.engine,p,d,keeper

    def dispose(self,native):
        native.close();end=time.monotonic()+2
        while not native.disposed and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(native.disposed)
        for bridge in list(native.shared.bridges):native.shared.leave(native.owner,bridge)

    def opened(self,n,e,p):
        e.callback('ready',dict(implementation='PyPy',version=[3,11],pid=123))
        e.emit('open',**boundary(p['state']));self.assertEqual(n.poll(),'boundary')

    def prematch(self,n,e,p,d):
        self.opened(n,e,p);n.advance();e.emit('advance',**boundary(p['state'],1,'match'));n.poll()
        self.assertEqual(e.calls[-1],('configure',{}))
        e.emit('configure');n.poll();self.assertEqual(e.calls[-1],('next',{'count':32}))
        e.emit('next',events=[dict(kind='decision',data=d)],decision=3,over=False,exhausted=False);n.poll()
        e.emit('preview',**{k:v for k,v in p.items() if k!='action'});self.assertEqual(n.poll(),'prematch')

    def test_input_and_fixture_are_detached_and_manager_bound(self):
        p,_=seed();before=copy.deepcopy(p['state']);n,e,p,d,_=self.make()
        p['state']['schema']='changed';self.assertEqual(n.initial_state,before)
        r=n.initial_state;r['schema']='caller';self.assertEqual(n.initial_state,before)
        fixture=NativeFixture.from_boundary(before,7)
        self.assertEqual(asdict(fixture),dict(index=1,side_a=7,side_b=8,kind=1,stage=2,year=93,state_hash=canonical_hash(before)))
        with self.assertRaises(ValueError):NativeFixture.from_boundary(before,8)
        for value in (None,{},SimpleNamespace(mem=b''),{'schema':'legacy'}):
            owner=SimpleNamespace()
            with self.assertRaises(ValueError):NativeSeasonOwner(owner,value)
            self.assertFalse(hasattr(owner,'_match_engine'))

    def test_entry_configures_once_and_delivers_boundaries_and_events_once(self):
        n,e,p,d,_=self.make();self.prematch(n,e,p,d)
        self.assertEqual([a for a,_ in e.calls],['open','advance','configure','next','preview'])
        packets=n.take_observations();self.assertEqual(len(packets),2);self.assertEqual(n.take_observations(),[])
        packets[0]['state']['schema']='caller';self.assertEqual(n.boundary_state,p['state'])
        events=n.take_entry_events();self.assertEqual(events[0]['data'],d);self.assertEqual(n.take_entry_events(),[])
        self.assertIs(n.shared.match,n)
        with self.assertRaises(ValueError):n.shared.claim(object())
        with self.assertRaises(ValueError):n.advance()
        self.assertEqual(n.owner.state,'untouched')

    def test_complete_terminal_and_pure_advance_refusal(self):
        n,e,p,d,_=self.make();self.opened(n,e,p)
        for call,status in enumerate(('complete','deferred-rollover'),1):
            n.advance();e.emit('advance',**boundary(p['state'],call,status,fixtures=[{'fixture':1}],pages=[{'text':['same']},{'text':['same']}]))
            self.assertEqual(n.poll(),'terminal' if status=='deferred-rollover' else 'boundary')
        values=n.take_observations();self.assertEqual(len(values),3)
        self.assertEqual(len(values[1]['observation']['news_pages']),2)
        with self.assertRaises(ValueError):n.advance()
        n,e,p,d,_=self.make();self.opened(n,e,p);n.advance()
        e.busy=False;e._number+=1;e.callback('season_error',dict(request=e._number,error='pure refusal',lost=False))
        self.assertEqual(n.poll(),'boundary');self.assertEqual(n.message,'pure refusal')
        n.advance();self.assertEqual(e.calls[-1][0],'advance')

    def test_handoff_is_once_and_keeps_the_session_lease(self):
        n,e,p,d,_=self.make();self.prematch(n,e,p,d);c=n.controller;c.play(captain=None)
        e.emit('answer');c.receive(*n.replies.get_nowait())
        packet=e.emit('next',events=[dict(kind='minute',data={'minute':0})],decision=None,over=False,exhausted=False)
        c.receive(*n.replies.get_nowait());h=n.handoff()
        self.assertEqual(h.packet,packet[1]);self.assertIs(h.replies,n.replies);self.assertIs(n.shared.match,n)
        with self.assertRaises(ValueError):n.handoff()
        with self.assertRaises(ValueError):h.send('advance')
        h.send('observe');self.assertEqual(e.calls[-1],('observe',{}))

    def test_discard_requires_its_delivered_ack_not_parser_flags(self):
        n,e,p,d,_=self.make();self.opened(n,e,p);e.cancel_deadline=5;n.close()
        end=time.monotonic()+1
        while not any(a=='discard' for a,_ in e.calls) and time.monotonic()<end:time.sleep(.005)
        packet=e.emit('discard',deliver=False)
        self.assertFalse(e.season_active);self.assertFalse(e.busy)
        # Observe the cleanup loop making progress after flags were cleared,
        # without delivering the terminal packet or relying on a short sleep.
        progress=threading.Event();get=n.replies.get
        def observed_get(*a,**kw):progress.set();return get(*a,**kw)
        n.replies.get=observed_get
        end=time.monotonic()+1
        while not progress.is_set() and not n.disposed and time.monotonic()<end:time.sleep(.002)
        self.assertTrue(progress.is_set() or n.disposed)
        self.assertIs(n.shared.match,n);self.assertFalse(n.disposed)
        e.callback(*packet)
        end=time.monotonic()+1
        while not n.disposed and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(n.disposed);self.assertIsNone(n.shared.match);self.assertFalse(e.closed)

    def test_pending_close_deadline_kills_only_its_process_and_releases_after_death(self):
        n,e,p,d,_=self.make();e.cancel_deadline=.03;n.close()
        end=time.monotonic()+1
        while not n.disposed and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(n.disposed);self.assertEqual(n.status,'closed')
        self.assertFalse(e.closed);self.assertIsNone(n.shared.match)

    def test_failed_start_and_wrong_thread_and_malformed_reply(self):
        n,e,p,d,_=self.make(fail=True);self.assertEqual(n.status,'lost');self.assertEqual(e.generation,0)
        n.close();end=time.monotonic()+1
        while not n.disposed and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(n.disposed)
        n,e,p,d,_=self.make();errors=[]
        def other():
            for call in (n.poll,n.advance,n.close,n.take_observations):
                try:call()
                except RuntimeError:errors.append(True)
        thread=threading.Thread(target=other);thread.start();thread.join(1);self.assertEqual(len(errors),4)
        e.callback('season',dict(request=True,action='open'));self.assertEqual(n.poll(),'lost')
        before=list(e.calls);n.poll();self.assertEqual(e.calls,before)

    def test_last_bridge_retirement_serializes_with_a_new_join(self):
        owner=SimpleNamespace();first=object();second=object()
        with patch('goal2.game.engine_process.EngineProcess',FakeEngine):
            shared=MatchEngine.join(owner,first);entered=threading.Event();release=threading.Event();joined=[]
            def closing():entered.set();release.wait(1);shared.engine.closed=True
            shared.engine.close=closing
            leave=threading.Thread(target=shared.leave,args=(owner,first));leave.start();self.assertTrue(entered.wait(1))
            join=threading.Thread(target=lambda:joined.append(MatchEngine.join(owner,second)));join.start()
            time.sleep(.02);self.assertEqual(joined,[]);release.set();leave.join(1);join.join(1)
            self.assertEqual(len(joined),1);self.assertIsNot(joined[0],shared);self.assertFalse(joined[0].engine.closed)
            joined[0].leave(owner,second)

    def test_foreign_hash_seeds_counter_fixture_and_played_prefix_never_attach(self):
        for field in ('output_hash','input_hash','rng_words','call_number'):
            n,e,p,d,_=self.make();self.opened(n,e,p);n.take_observations();n.advance()
            packet=boundary(p['state'],1,'match')
            packet['observation'][field]=[123,456] if field=='rng_words' else 7 if field=='call_number' else '0'*64
            e.emit('advance',**packet);self.assertEqual(n.poll(),'lost')
            self.assertIsNone(n.controller);self.assertEqual(n.take_observations(),[])
        n,e,p,d,_=self.make();self.opened(n,e,p);n.advance()
        e.emit('advance',**boundary(p['state'],1,'match'));n.poll();e.emit('configure');n.poll()
        e.emit('next',events=[dict(kind='minute',data={})],decision=None,over=False,exhausted=False)
        self.assertEqual(n.poll(),'lost');self.assertIsNone(n.controller)


def direct_entry(raw):
    """Actual sealed entry only in a PyPy child; compare the source's own opts."""
    from goal2.game.season import SeasonSession
    from goal2.game.prematch_seam import PrematchSeam
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11)
    native,_,_=initial_state(raw);session=SeasonSession(native);session.advance();match=session.pending_match
    image=Image.from_state(session.state,engine_tables.load())
    fixture=dict(index=match.opts['index'],side_a=match.opts['first'],side_b=match.opts['second'],kind=match.opts['kind'],
                 stage=image.memory[image.far(GAME_PTR)+0x3C],year=image.year(),state_hash=canonical_hash(session.state))
    PrematchSeam(match)
    for event in match.events():
        if event.kind=='decision':break
    return dict(fixture=fixture,preview=canonical_hash(match.records_after()))


class Actual(unittest.TestCase):
    def native(self,raw=None):
        raw=reference_raw() if raw is None else raw;state,_,_=initial_state(raw)
        owner=SimpleNamespace(state='identity owner remains unchanged');keeper=object();shared=MatchEngine.join(owner,keeper)
        n=NativeSeasonOwner(owner,state)
        def cleanup():
            n.close();self.until(lambda:n.disposed,15)
            shared.leave(owner,keeper)
        self.addCleanup(cleanup);return n,shared,state

    def until(self,condition,limit=120,step=None):
        end=time.monotonic()+limit
        while time.monotonic()<end:
            if step:step()
            if condition():return
            time.sleep(.002)
        self.fail('native owner did not settle within its existing operation budget')

    def prepared(self,n):
        self.until(lambda:n.status in ('boundary','lost'),step=n.poll);self.assertEqual(n.status,'boundary',n.message)
        n.advance();self.until(lambda:n.status in ('prematch','lost'),step=n.poll);self.assertEqual(n.status,'prematch',n.message)

    def test_actual_native_entry_equals_direct_source_and_handoff_keeps_one_pid(self):
        raw=reference_raw();expected=pypy_engine.call(__name__+':direct_entry',raw)
        n,shared,state=self.native(raw);self.prepared(n);pid=n.pid
        self.assertEqual(asdict(n.fixture),expected['fixture']);self.assertEqual(n.controller.view.state_hash,expected['preview'])
        self.assertEqual(shared.engine.ready['implementation'],'PyPy');self.assertEqual(shared.engine.generation,1)
        self.assertEqual(n.owner.state,'identity owner remains unchanged')
        with self.assertRaises(ValueError):shared.claim(object())
        c=n.controller;w=next(w for w in c.view.bench if c.view.can_mark(w));c.set_marking(w,0)
        def pump():
            try:c.receive(*n.replies.get_nowait())
            except queue.Empty:pass
        self.until(lambda:not c.pending,step=pump);self.assertEqual(c.view.marking_goal(w),0)
        c.play(captain=None);self.until(lambda:not c.pending,step=pump)
        h=n.handoff();self.assertTrue(h.packet['events']);self.assertIs(shared.match,n);self.assertEqual(n.pid,pid)
        self.assertEqual(n.boundary_state,n.take_observations()[-1]['state'])
        self.assertEqual(n.take_observations(),[]);self.assertEqual(n.pid,pid)

    def test_actual_pending_close_disposes_without_ui_poll_then_assistant_reuses_child(self):
        n,shared,state=self.native();pid=n.pid;n.close();self.until(lambda:n.disposed,15)
        self.assertIsNone(shared.match);self.assertFalse(shared.engine.season_active);self.assertEqual(shared.engine.pid,pid)
        class Reply:
            def __init__(self):self.queue=queue.Queue()
            def put(self,*value):self.queue.put(value)
        reply=Reply();shared.claim(reply)
        try:
            shared.engine.assistant(state);self.until(lambda:not reply.queue.empty())
            kind,value=reply.queue.get_nowait();self.assertEqual(kind,'assistant')
            self.assertEqual(shared.engine.pid,pid);self.assertEqual(shared.engine.generation,1)
        finally:shared.release(reply)

    def test_actual_death_releases_only_on_close_and_new_entry_is_explicit(self):
        n,shared,state=self.native();self.prepared(n);oldpid=n.pid
        shared.engine.process.kill()
        self.until(lambda:shared.engine.process is None);self.assertIs(shared.match,n)
        n.close();self.until(lambda:n.disposed,15)
        next_owner=NativeSeasonOwner(n.owner,state)
        try:
            self.until(lambda:next_owner.status in ('boundary','lost'),step=next_owner.poll)
            self.assertEqual(next_owner.status,'boundary',next_owner.message);self.assertNotEqual(next_owner.pid,oldpid)
            self.assertEqual(shared.engine.generation,2)
        finally:next_owner.close();self.until(lambda:next_owner.disposed,15)

    @requires.need(**requires.HALFTIME)
    def test_existing_legacy_cache_survives_native_entry_and_plays_again_in_same_child(self):
        from goal2.tests.test_assistant_pipe_t183c import model
        from goal2.engine.original_match import Fixture
        owner=model();before=copy.deepcopy(owner.state);keeper=object();shared=MatchEngine.join(owner,keeper)
        self.addCleanup(shared.leave,owner,keeper)
        class Reply:
            def __init__(self):self.queue=queue.Queue()
            def put(self,*value):self.queue.put(value)
        def receive(reply,wanted):
            end=time.monotonic()+120
            while time.monotonic()<end:
                kind,value=reply.queue.get(timeout=max(.01,end-time.monotonic()))
                if kind==wanted:return value
                self.assertNotIn(kind,('death','error','season','season_error'))
            self.fail('legacy reply did not arrive')
        reply=Reply();shared.claim(reply)
        shared.engine.open(owner.state,owner.template_bytes);receive(reply,'opened')
        pid=shared.engine.pid;self.assertEqual(shared.engine.opens,1);shared.release(reply)
        state,_,_=initial_state(reference_raw());native=NativeSeasonOwner(owner,state)
        try:
            self.until(lambda:native.status in ('boundary','lost'),step=native.poll)
            self.assertEqual(native.status,'boundary',native.message);self.assertEqual(native.pid,pid)
        finally:native.close();self.until(lambda:native.disposed,15)
        reply=Reply();shared.claim(reply)
        try:
            f=owner.state.campaign.next_fixture
            fixture=Fixture(first=f.side_a,second=f.side_b,index=int(f.fixture_id.split(':')[1]),kind=f.kind)
            shared.engine.match('watched',fixture,frames=True,bench=True)
            frame=receive(reply,'frame');self.assertGreaterEqual(frame['sequence'],0)
            self.assertTrue(shared.engine.cancel());receive(reply,'cancelled')
            self.assertEqual(shared.engine.pid,pid);self.assertEqual(shared.engine.generation,1)
            self.assertEqual(shared.engine.opens,1);self.assertEqual(owner.state,before)
        finally:shared.release(reply)


if __name__=='__main__':unittest.main()
