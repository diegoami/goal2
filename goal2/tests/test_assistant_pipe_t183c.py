"""[designed: T183c/#762] Actual PyPy assistant pipe plus labelled host controls.

The fake children below play no engine; they control protocol races/failures.
Original/native fidelity is exercised separately on actual state/2 requests.
"""
import copy
import json
import os
import queue
import sys
import tempfile
import time
import unittest
from pathlib import Path

from goal2.game.engine_process import EngineProcess
from goal2.game.engine_server import read_packet,write_packet
from goal2.tests import requires
from goal2.tests.pypy_engine import call

ROOT=Path(__file__).resolve().parents[2]
_BASE={}


def model():
    from goal2.desktop.model import DesktopModel
    if 'model' not in _BASE:
        _BASE['folder']=tempfile.TemporaryDirectory()
        _BASE['model']=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(_BASE['folder'].name)/'game.g2save',country=4)
    return copy.deepcopy(_BASE['model'])


def state():
    from goal2.game.best_twenty_state import prepare
    return prepare(model().state).native


def fake(mode):
    """Host protocol control only; no match/assistant computation under CPython."""
    incoming,out=sys.stdin.buffer,sys.stdout.buffer
    write_packet(out,{'kind':'ready','value':{'implementation':'host control','version':[3,11],'pid':os.getpid()}})
    while True:
        packet=read_packet(incoming)
        if packet is None:return
        h,p=packet
        if h['op']=='quit':return
        if h['op']=='assistant':
            n=h['request']
            if mode=='stale':write_packet(out,{'kind':'assistant_cancelled','value':{'request':n-1}})
            elif mode=='hash':write_packet(out,{'kind':'assistant','value':{'request':n,'input_hash':'wrong','output_hash':'wrong','result':{}}},b'{}')
            elif mode=='error':write_packet(out,{'kind':'assistant_error','value':{'request':n,'error':'controlled failure'}})
            elif mode=='generic':write_packet(out,{'kind':'error','value':'unbound control failure'})
            elif mode=='large':
                from goal2.game.engine_server import MAX_PAYLOAD
                write_packet(out,{'kind':'assistant','value':{},'size':MAX_PAYLOAD+1})
            elif mode in ('output_hash','payload','result'):
                from goal2.game.season import canonical_hash
                value=json.loads(p.decode('utf8'))
                result={'allowed':True,'refusal':None,'country':4,'manager':1,'squad':list(range(61,81)),
                        'pool':list(range(2561,2641)),'changed':False,'recruited':[],'calls':{'0791:DC7E':1}}
                if mode=='result':result['country']=True
                data=b'{' if mode=='payload' else p
                write_packet(out,{'kind':'assistant','value':{'request':n,'input_hash':h['input_hash'],
                    'output_hash':'wrong' if mode=='output_hash' else canonical_hash(value),'result':result}},data)
        elif h['op']=='assistant_cancel' and mode=='cancel':
            write_packet(out,{'kind':'assistant_cancelled','value':{'request':h['request']}})


class PipeCase(unittest.TestCase):
    def engine(self,mode=None,denied=False,**kwargs):
        replies=queue.Queue()
        command=None if mode is None else [sys.executable,'-u','-m',__name__,'--fake',mode]
        if denied:
            from goal2.game.engine_python import engine_python
            import textwrap
            guard=textwrap.dedent('''\
                import builtins,io,sys
                from pathlib import Path
                assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11)
                real_import,real_open=builtins.__import__,io.open
                def imports(name,*a,**k):
                    if name=='unicorn' or name.startswith('unicorn.'):
                        raise ImportError('positive T183c server Unicorn denial')
                    return real_import(name,*a,**k)
                def files(path,*a,**k):
                    if str(path).lower().endswith('.exe'):
                        raise AssertionError('positive T183c server EXE denial')
                    return real_open(path,*a,**k)
                builtins.__import__=imports
                builtins.open=io.open=files
                try:__import__('unicorn')
                except ImportError:pass
                else:raise AssertionError('Unicorn denial inactive')
                try:Path('GOAL.EXE').read_bytes()
                except AssertionError:pass
                else:raise AssertionError('EXE denial inactive')
                from goal2.game.engine_server import main
                from goal2.engine.original_match.machine import Uc
                assert Uc is None
                raise SystemExit(main())
            ''')
            command=[engine_python(),'-u','-c',guard]
        e=EngineProcess(lambda k,v:replies.put((k,v)),command=command,**kwargs)
        self.addCleanup(e.close)
        return e,replies

    def wait(self,q,kind,timeout=30):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:k,v=q.get(timeout=min(.2,max(.001,deadline-time.monotonic())))
            except queue.Empty:continue
            if k==kind:return v
            if k=='death':self.fail('engine died: '+str(v))
        self.fail('no '+kind+' reply')


@requires.need(**requires.HALFTIME)
class NativePipe(PipeCase):
    def test_actual_pypy_pipe_equals_direct_native_and_reuses_process(self):
        value=state();value['note']='Αθήνα · café'
        before=copy.deepcopy(value)
        expected=call('goal2.tests.test_best_twenty_t183a:native',value)
        e,q=self.engine(denied=True)
        n=e.assistant(value);answer=self.wait(q,'assistant')
        self.assertEqual(answer['request'],n)
        self.assertEqual(answer['result'],expected)
        self.assertEqual(e.ready['implementation'],'PyPy')
        self.assertEqual(e.ready['version'],[3,11])
        pid=e.pid
        self.assertFalse(e.busy)
        n2=e.assistant(value);again=self.wait(q,'assistant')
        self.assertGreater(n2,n);self.assertEqual(e.pid,pid)
        self.assertEqual(again['result'],expected)
        self.assertEqual(value,before)

    def test_invalid_native_context_is_repairable_in_same_child(self):
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        good=state();im=Image.from_state(good,engine_tables.load())
        im.memory[im.DS*16+0xC1E]=1
        e,q=self.engine();n=e.assistant(im.state(engine_tables.load()))
        error=self.wait(q,'assistant_error');pid=e.pid
        self.assertEqual(error['request'],n);self.assertIn('outside a match',error['error'])
        self.assertFalse(e.busy)
        e.assistant(good);self.wait(q,'assistant');self.assertEqual(e.pid,pid)

    def test_open_game_and_assistant_reuse_one_process_and_cache(self):
        m=model();e,q=self.engine();e.open(m.state,m.template_bytes)
        self.wait(q,'opened');pid=e.pid;opens=e.opens
        n=e.assistant(state());self.wait(q,'assistant')
        self.assertEqual(e.pid,pid);self.assertEqual(e.opens,opens)
        self.assertIsNotNone(e._game)
        self.assertFalse(e.cancel_assistant(n))
        e.open(m.state,m.template_bytes);self.wait(q,'opened')
        self.assertEqual(e.pid,pid)

    @requires.need(slow=True)
    def test_helper_and_actual_match_share_process_and_reply_channels(self):
        from goal2.engine.original_match import Fixture
        m=model();e,q=self.engine();e.assistant(state());first=self.wait(q,'assistant')['result']
        pid=e.pid;e.open(m.state,m.template_bytes);self.wait(q,'opened')
        f=m.state.campaign.next_fixture
        fixture=Fixture(first=f.side_a,second=f.side_b,index=int(f.fixture_id.split(':')[1]),kind=f.kind)
        # Main-owned T183c clarification: this short conversation proves live
        # transport ownership/cancellation. T159/T160 retain full completion,
        # exact events/memory/RNG and their original reference case budgets.
        e.match('watched',fixture,frames=True,bench=True)
        frame=self.wait(q,'frame',timeout=120)
        self.assertGreaterEqual(frame['sequence'],0)
        self.assertTrue(e.cancel())
        self.wait(q,'cancelled',timeout=120)
        self.assertFalse(e.busy)
        self.assertEqual(e.pid,pid)
        e.assistant(state());again=self.wait(q,'assistant')['result']
        self.assertEqual(again,first,'a cancelled match must not leak into the next assistant request')
        self.assertEqual(e.pid,pid)

    @requires.need(modules=('unicorn',),slow=True,files=('g16-proof-279904b6-private.zip',))
    def test_actual_tour_refusal_crosses_pipe_unchanged(self):
        import hashlib
        from zipfile import ZipFile
        from goal2.core import Core
        from goal2.core.driver import Driver
        from goal2.core.screens import INSERT
        from goal2.tests.eleven_repair import fix_eleven
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        bundle=ROOT/'.cache/g16-proof-279904b6-private.zip'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(),'2332459f7bf64be1afd2e92fc61d81f3b9489bf9d01208a3e6ad8edb469d4cd9')
        with ZipFile(bundle) as z:raw=z.read('.cache/T123-proof-r2/annual-3.g2core')
        d=Driver(Core.load(raw,goal_dat=ROOT/'.cache/GOAL.DAT'))
        d.goto('select-squad');d.press(INSERT,expect=('select-squad',));d.to_menu()
        d.play_round(fix_eleven=fix_eleven,on_taker=lambda *_:13,on_replay=lambda *_:False)
        value=Image.from_memory_component(d.wait.state.memory_component()).state(engine_tables.load())
        expected=call('goal2.tests.test_best_twenty_t183a:native',value)
        e,q=self.engine();e.assistant(value);answer=self.wait(q,'assistant')['result']
        self.assertEqual(answer,expected);self.assertFalse(answer['allowed']);self.assertEqual(answer['refusal'],'tour')


@requires.need(**requires.HALFTIME)
class ProtocolControls(PipeCase):
    def test_busy_and_request_specific_cancellation(self):
        e,q=self.engine('cancel');n=e.assistant(state())
        self.assertTrue(e.busy)
        with self.assertRaisesRegex(ValueError,'pending'):e.assistant(state())
        with self.assertRaises(ValueError):e.season_open(state())
        with self.assertRaises(ValueError):e.open_encoded(b'not sent')
        self.assertFalse(e.cancel_assistant(True));self.assertFalse(e.cancel_assistant(n+1))
        self.assertFalse(e.cancel(),'match cancellation must not target the assistant')
        self.assertTrue(e.cancel_assistant(n))
        self.assertEqual(self.wait(q,'assistant_cancelled'),{'request':n});self.assertFalse(e.busy)

    def test_stale_or_hash_mismatched_reply_kills_child(self):
        for mode in ('stale','hash','output_hash','payload','result','large','generic'):
            with self.subTest(mode=mode):
                e,q=self.engine(mode);e.assistant(state())
                death=self.wait(q,'death')
                self.assertIn('ProtocolError',death['error'])
                self.assertFalse(e.busy)
                self.assertNotIn('assistant',[k for k,v in list(q.queue)])

    def test_cancel_deadline_then_new_actual_child_is_not_killed_by_old_timer(self):
        e,q=self.engine('ignore',cancel_deadline=.1);n=e.assistant(state());self.wait(q,'ready')
        oldlife=e._life;oldpid=e.pid
        self.assertTrue(e.cancel_assistant(n));self.wait(q,'death')
        self.assertFalse(e.busy)
        e.command=None
        e.assistant(state());e._assistant_overdue(oldlife,n)
        self.wait(q,'assistant')
        self.assertNotEqual(e.pid,oldpid);self.assertEqual(e.ready['implementation'],'PyPy')

    def test_typed_error_and_close_reset_pending_request(self):
        e,q=self.engine('error');n=e.assistant(state())
        self.assertEqual(self.wait(q,'assistant_error'),{'request':n,'error':'controlled failure'})
        self.assertFalse(e.busy)
        n2=e.assistant(state());self.wait(q,'assistant_error');self.assertGreater(n2,n)
        e.close();self.assertFalse(e.busy)
        with self.assertRaisesRegex(ValueError,'closed'):e.assistant(state())

    def test_invalid_schema_rejected_before_process_start(self):
        e,q=self.engine()
        with self.assertRaisesRegex(ValueError,'state/2'):e.assistant({})
        self.assertIsNone(e.process)




@requires.need(**requires.HALFTIME)
class PublicationControls(unittest.TestCase):
    def jobs(self):
        from goal2.game.best_twenty_jobs import for_model
        m=model();j=for_model(m);self.addCleanup(j.close)
        return m,j

    def ready(self,j,timeout=30):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            if not j._results.empty():return
            time.sleep(.01)
        self.fail('private candidate did not arrive')

    def test_cancel_after_private_candidate_before_poll_never_publishes(self):
        m,j=self.jobs();before=copy.deepcopy(m.state)
        token=j.start();self.ready(j)
        self.assertEqual(m.state,before)
        self.assertTrue(j.cancel(token))
        self.assertEqual(j.poll(token),{'status':'cancelled'})
        self.assertEqual(m.state,before)

    def test_cancellation_during_owner_validation_never_publishes(self):
        m,j=self.jobs();before=copy.deepcopy(m.state)
        token=j.start();self.ready(j);view=m.view
        def cancel(value=None):
            if value is not None:j.cancel(token)
            return view(value)
        m.view=cancel
        self.assertEqual(j.poll(token),{'status':'cancelled'})
        self.assertEqual(m.state,before)

    def test_owner_replacement_during_validation_is_not_overwritten(self):
        from goal2.game.best_twenty_jobs import AssistantStale
        m,j=self.jobs();before=copy.deepcopy(m.state)
        token=j.start();self.ready(j);view=m.view;replacement=[]
        def replace(value=None):
            m.state=copy.deepcopy(m.state);replacement.append(m.state)
            return view(value)
        m.view=replace
        with self.assertRaises(AssistantStale):j.poll(token)
        self.assertIs(m.state,replacement[0]);self.assertEqual(m.state,before)

    def test_poll_requires_owner_thread_and_publishes_once(self):
        import threading
        m,j=self.jobs();before=copy.deepcopy(m.state)
        token=j.start();self.ready(j);errors=[]
        def wrong():
            try:j.poll(token)
            except RuntimeError as exc:errors.append(str(exc))
        thread=threading.Thread(target=wrong);thread.start();thread.join(5)
        self.assertTrue(errors,'a background poll must not publish owner state')
        self.assertEqual(m.state,before)
        result=j.poll(token);self.assertEqual(result['status'],'complete')
        published=m.state;self.assertIsNone(j.poll(token));self.assertIs(m.state,published)

    def test_watched_bridge_keeps_same_process_when_assistant_bridge_closes(self):
        from goal2.game.watched_jobs import WatchedJobs
        m,j=self.jobs();token=j.start();self.ready(j);j.poll(token)
        watched=WatchedJobs(m);self.addCleanup(watched.close)
        self.assertIs(watched.shared,j.shared)
        pid=j.shared.engine.pid;j.close()
        self.assertEqual(watched.shared.engine.pid,pid)
        self.assertIsNone(watched.shared.engine.process.poll())


if __name__=='__main__':
    if '--fake' in sys.argv:fake(sys.argv[-1])
    else:unittest.main()
