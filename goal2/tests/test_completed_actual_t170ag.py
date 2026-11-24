"""[designed: T170ag/#828] Actual completed reads, not a new menu/save phase."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

from goal2.game.completed_view import CompletedMatchView,completed_result_hash
from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine,requires
from goal2.tests import test_native_driver_actual_t170ac as old
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest
from goal2.tests.test_stopped_view_actual_t170af import decoder_hashes,native_oracle

ROOT=Path(__file__).resolve().parents[2]


class Policy:
    def __init__(self,quick):self.quick=quick;self.old=old.Answers()
    def __call__(self,data):
        if self.quick and data['context']=='pause':return {'quick':True}
        return self.old(data)


def half_time_pair(data):
    positions = dict(data['positions'])
    records = {word: bytes.fromhex(record) for word, record in data['player_records']}
    return next([off, on] for off in data['eleven'][1:] for on in data['bench']
                if off and on and positions[off] == positions[on]
                and 0 < records[on][14] < 128 and not records[on][16] & 0xA4)


def direct(raw,quick,half_time=False):
    import sys
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    from goal2.game.prematch_seam import PrematchSeam
    from goal2.game.watched_pitch import snapshot
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    session=SeasonSession(Image.from_bytes(raw).state(engine_tables.load()));session.advance()
    m=session.pending_match;boundary=canonical_hash(session.state);PrematchSeam(m,frames=True)
    events=[];frames=[];policy=Policy(quick)
    edits = 0
    for ev in m.events():
        if ev.kind=='tick':
            frames.append(snapshot(m,ev,len(frames),len(events)))
            if len(frames)==1:m.pause()
        else:events.append(asdict(ev))
        if ev.kind=='decision':
            if half_time and ev.data['context'] == 'half_time' and edits < 2:
                change = ({'substitutions': [half_time_pair(ev.data)]} if edits == 0
                          else {'tactics': {1: not bool(ev.data['tactics'] & 1)}})
                m.answer(edit_only=True, **change)
                edits += 1
            else:
                m.answer(**policy(ev.data))
    result=dict(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),
        memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS],
        boundary_hash=boundary,result_hash=completed_result_hash(m.result()),board_hash=digest(m.result()['board']))
    observation=session.resume(m)
    result.update(state_hash=canonical_hash(session.state),observation_hash=digest(asdict(observation)),status=observation.status)
    return result


def actual_worker(raw):
    import sys
    from goal2.data.goaldat import load
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game import engine_tables
    from goal2.game.season_worker import SeasonWorker,SeasonRequestError
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    w=SeasonWorker();number=0
    def ask(action,**kw):
        nonlocal number
        number+=1;return w.dispatch(dict(op='season',request=number,action=action,**kw))
    try:ask('completed_preview')
    except SeasonRequestError:pass
    else:raise AssertionError('read before open')
    ask('open',state=Image.from_bytes(raw).state(engine_tables.load()));ask('advance')
    m=w.session.pending_match;identity=id(m);boundary=canonical_hash(w.session.state)
    def freeze():
        return (m.m.read(0,MEM_SIZE),tuple(m.m.reg(r) for r in REGS),copy.deepcopy(m.st),
            copy.deepcopy(m.opts),copy.deepcopy(m.inputs),copy.deepcopy(m._result),
            copy.deepcopy(getattr(m,'_replay_actions',None)),getattr(m,'_replay_events',None),
            copy.deepcopy(m._frame_state()),w.session.state,copy.deepcopy(vars(w.session._keys)),
            w.session.observe(),id(w.stream),id(w.seam),id(w.session.pending_match),
            w.decision,w.exhausted,w._decision_number,w.event_count,w.frame_sequence,w.frame_watermark)
    refused=[]
    def refusal(label):
        before=freeze()
        try:ask('completed_preview')
        except SeasonRequestError:pass
        else:raise AssertionError('read accepted at '+label)
        assert freeze()==before;refused.append(label)
    refusal('unconfigured');ask('configure',frames=True);refusal('before-events')
    events=[];frames=[];policy=Policy(True)
    while True:
        p=ask('next',count=1);events.extend(p['events']);frames.extend(p['frames'])
        if p['frames'] and len(frames)==1:assert ask('pause')['paused']
        if p['decision'] is not None:
            refusal('decision');ask('answer',decision=p['decision'],answer=policy(p['events'][-1]['data']))
        if any(e['kind']=='full_time' for e in p['events']):refusal('whistle')
        if p['over'] and not p['exhausted']:refusal('unread-end')
        if p['exhausted']:break
    assert 'unread-end' in refused and 'whistle' in refused and w.decision is None and m.waiting is None
    before=freeze();p=ask('completed_preview')
    view=CompletedMatchView.from_packet(p,request=number,managed_country=m.opts['managed'],
        event_count=w.event_count,frame_sequence=w.frame_sequence,
        fixture=(m.opts['first'],m.opts['second'],m.opts['index'],m.opts['kind']),
        score=events[-1]['score'],board=next(e['data'] for e in reversed(events) if e['kind']=='full_time'))
    assert view.result==m.result() and view.snapshot.state==m.records_after() and freeze()==before
    data=load((ROOT/'.cache/GOAL.DAT').read_bytes())
    assert decoder_hashes(view.display_state(),data,view.team_context,view.sides)==native_oracle(m,data)
    p['result']['score'][0]=99;p['state']['header']='caller mutation'
    again=ask('completed_preview');assert again['result']==view.result and freeze()==before
    assert id(w.session.pending_match)==identity and canonical_hash(w.session.state)==boundary
    actual=dict(events_hash=digest(events),frames_hash=digest(frames),events=len(events),frames=len(frames),
        memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS],
        boundary_hash=boundary,result_hash=completed_result_hash(view.result),board_hash=digest(view.board))
    done=ask('resume');actual.update(state_hash=canonical_hash(done['state']),
        observation_hash=digest(done['observation']),status=done['observation']['status'])
    try:ask('completed_preview')
    except SeasonRequestError:pass
    else:raise AssertionError('read after resume')
    observed=ask('observe');assert not observed['observation']['played_fixtures'] and not observed['observation']['news_pages']
    ask('discard')
    return dict(proof=actual,refusals=sorted(set(refused)),context=view.team_context)


@requires.need(files=('GOAL.DAT',))
class Worker(unittest.TestCase):
    def test_actual_quick_completed_reads_are_pure_and_resume_equals_sdk(self):
        raw=reference_raw();result=pypy_engine.call(__name__+':actual_worker',raw)
        self.assertEqual(result['proof'],pypy_engine.call(__name__+':direct',raw,True))
        print('T170AG_QUICK_WORKER '+json.dumps(result,sort_keys=True),flush=True)


@requires.need(files=('GOAL.DAT',))
class Driver(unittest.TestCase):
    def exercise(self,quick,review=False):
        from goal2.data.goaldat import load
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.engine_python import engine_python
        from goal2.game.watched_jobs import MatchEngine
        raw=reference_raw();data=load((ROOT/'.cache/GOAL.DAT').read_bytes())
        tmp=tempfile.TemporaryDirectory(prefix='goal2-completed-read-');self.addCleanup(tmp.cleanup)
        proof=Path(tmp.name)/'cpu.json';owner=SimpleNamespace(state='unchanged');keeper=object()
        shared=MatchEngine.join(owner,keeper);self.addCleanup(shared.leave,owner,keeper)
        script='''import hashlib,json,sys,os
from pathlib import Path
from goal2.game.engine_server import Server,main
from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
os.environ['GOAL2_ENGINE_CHILD']='1'
from goal2.data.goaldat import load
from goal2.tests.test_stopped_view_actual_t170af import native_oracle
data=load(Path(sys.argv[2]).read_bytes());real=Server.send
def send(self,kind,value=None,payload=b''):
    if kind=='season' and isinstance(value,dict) and value.get('action')=='completed_preview':
        m=self.season.session.pending_match;item=native_oracle(m,data)
        item.update(memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])
        Path(sys.argv[1]).write_text(json.dumps(item))
    return real(self,kind,value,payload)
Server.send=send
raise SystemExit(main())
'''
        shared.engine.command=[engine_python(),'-u','-c',script,str(proof),str(ROOT/'.cache/GOAL.DAT')]
        helper=old.Actual('test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk');self.addCleanup(helper.doCleanups)
        native,d,prefix,boundary=helper.prepare(owner,Image.from_bytes(raw).state(engine_tables.load()),
            **({'post_match_review': True} if review else {}))
        policy=Policy(quick);pid=native.pid;now=0.;paused=False;last_stopped=None;end=time.monotonic()+900
        reviews=[]
        while time.monotonic()<end:
            now+=1;frame=d.tick(now)
            if frame is not None:
                d.painted(frame['sequence'])
                if not paused:self.assertTrue(d.request_pause());paused=True
            if d.status=='decision':
                waiting=d.waiting;d.request_view();helper.until(lambda:d.status in ('decision','lost'),lambda:d.tick(now))
                self.assertEqual(d.status,'decision',d.error);last_stopped=d.stopped_view.snapshot.state_hash
                if waiting['event']['data']['context']=='post_match':
                    self.assertTrue(review)
                    self.assertIsNone(d.completed_view)
                    with self.assertRaises(ValueError):d.resume()
                    board=next(e['data'] for e in d.events if e['kind']=='full_time')
                    self.assertEqual(d.stopped_view.snapshot.data['board'],board)
                    self.assertNotEqual(d.stopped_view.team_context['match_set_up'],0)
                    reviews.append(waiting['decision'])
                    d.answer({'post_match_exit':1})
                    helper.until(lambda:d.status in ('decision','lost'),lambda:d.tick(now))
                    self.assertEqual(d.waiting,waiting,d.error)
                    self.assertTrue(d.message)
                    d.answer({'post_match_exit':True})
                else:
                    d.answer(policy(waiting['event']['data']))
                if quick:d.quick_result()
            if d.status=='complete':break
            self.assertNotIn(d.status,('lost','closed'),d.error);time.sleep(.0005)
        self.assertEqual(d.status,'complete',d.error);self.assertIsNone(d.completed_view);self.assertIsNone(d.stopped_view)
        before=(digest(d.events),digest(d.frames),d.shown_count,d.painted_sequence)
        views=[];d.set_held(True)
        for _ in range(2):
            d.request_completed_view();helper.until(lambda:d.status in ('complete','lost'),lambda:d.tick(now))
            self.assertEqual(d.status,'complete',d.error);view=d.completed_view;self.assertIsNotNone(view)
            self.assertEqual((digest(d.events),digest(d.frames),d.shown_count,d.painted_sequence),before)
            self.assertNotEqual(view.snapshot.state_hash,last_stopped)
            oracle=json.loads(proof.read_text());actual=decoder_hashes(view.display_state(),data,view.team_context,view.sides)
            self.assertEqual(actual,{k:v for k,v in oracle.items() if k not in ('memory_hash','all16')})
            self.assertEqual(canonical_hash(native.boundary_state),canonical_hash(boundary['state']))
            views.append((view.snapshot.state_hash,view.snapshot.result_hash))
        self.assertEqual(views[0],views[1]);self.assertEqual(native.pid,pid);self.assertEqual(shared.engine.generation,1)
        actual={k:oracle[k] for k in ('memory_hash','all16')}
        canonical=[e for e in prefix+d.events if not (
            e['kind']=='decision' and e['data']['context']=='post_match')]
        self.assertEqual(len(reviews),int(review))
        actual.update(events_hash=digest(canonical),frames_hash=digest(d.frames),events=len(canonical),
            frames=len(d.frames),boundary_hash=canonical_hash(boundary['state']),
            result_hash=completed_result_hash(view.result),board_hash=digest(view.board))
        d.resume();self.assertIsNone(d.completed_view)
        helper.until(lambda:d.status in ('resumed','lost'),lambda:d.tick(now+100))
        self.assertEqual(d.status,'resumed',d.error);packets=native.take_observations();self.assertEqual(len(packets),1)
        self.assertEqual(native.take_observations(),[]);self.assertEqual(owner.state,'unchanged')
        actual.update(state_hash=canonical_hash(native.boundary_state),observation_hash=digest(packets[0]['observation']),
            status=packets[0]['observation']['status'])
        self.assertEqual(actual,pypy_engine.call(__name__+':direct',raw,quick))
        d.close();print('T170AG_'+('QUICK_DRIVER ' if quick else 'FULL ')+json.dumps(actual,sort_keys=True),flush=True)

    def test_actual_quick_pipe_repeated_covered_reads_then_explicit_resume(self):self.exercise(True)

    def test_review_accepts_only_explicit_exit_then_resumes_the_same_match(self):self.exercise(True,review=True)

    @requires.need(slow=True)
    def test_watched_review_keeps_full_match_and_resume_equal_to_sdk(self):
        self.exercise(False, review=True)

    @requires.need(slow=True)
    def test_full_retained_driver_completion_reads_equal_sdk(self):self.exercise(False)


@requires.need(modules=('PySide6',),files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_real_pitch_completion_read_under_cover_renders_original_board_then_resumes(self):
        self.exercise()

    def test_real_post_match_review_handles_help_refusal_and_explicit_exit(self):
        self.exercise(review=True)

    def test_worker_loss_under_review_help_disables_exit_and_releases_owner(self):
        self.exercise(review=True, lose_worker=True)

    def test_real_half_time_substitution_and_tactic_refresh_before_explicit_play(self):
        self.exercise(half_time=True)

    def exercise(self, *, review=False, lose_worker=False, half_time=False):
        from PySide6.QtCore import QTimer,Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from unittest.mock import patch
        from goal2.data.goaldat import load
        from goal2.desktop import data_setup
        from goal2.desktop.model import DesktopModel
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.ui import theme
        from goal2.ui.native_pitch import NativePitchScreen
        from goal2.ui.screen import Screen
        from goal2.ui.window import Window as AppWindow
        from goal2.ui.s20_board import BoardScreen,board
        from goal2.tests.ui_assertions import assert_fits
        app=QApplication.instance() or QApplication([]);theme.install(app)
        tmp=tempfile.TemporaryDirectory(prefix='goal2-completed-window-');self.addCleanup(tmp.cleanup)
        raw=reference_raw();model=DesktopModel(load((ROOT/'.cache/GOAL.DAT').read_bytes()),raw,Path(tmp.name)/'unused')
        before=copy.deepcopy(model.state);helper=old.Actual('test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk')
        self.addCleanup(helper.doCleanups)
        native,d,prefix,_=helper.prepare(model,Image.from_bytes(raw).state(engine_tables.load()),
            **({'post_match_review': True} if review else {}));pid=native.pid
        win=AppWindow(data_setup.paths(Path(tmp.name)/'data'));win.resize(1440,1080);win.push(Screen(win));win.show()
        def close():win.leaving=True;win.close();win.deleteLater();app.processEvents()
        self.addCleanup(close);failures=[];completed=[];paused=[];held=[];policy=Policy(True)
        def decision(s,waiting):
            self.assertNotEqual(waiting['event']['data']['context'], 'post_match')
            if half_time:
                self.assertNotEqual(waiting['event']['data']['context'], 'half_time')
            s.answer_native(waiting['decision'],policy(waiting['event']['data']))
            if waiting['event']['data']['context']=='pause':d.quick_result()
        def complete(s):
            completed.append(True);held.append((digest(d.events),digest(d.frames),d.painted_sequence,d.shown_count))
            d.request_completed_view();win.push(Screen(win))
        with patch('goal2.ui.native_pitch.NativeMatchDriver',return_value=d):
            screen=NativePitchScreen(win,model,native,connection=d.connection,on_decision=decision,
                on_goal=lambda s,e:s.release_goal(),on_complete=complete,on_failure=lambda s,e:failures.append(e),
                **({'half_time_controls': True} if half_time else {}))
        win.push(screen);screen.timer.stop();self.addCleanup(screen.closing)
        def painted(seq):
            screen.painted(seq)
            if not paused:self.assertTrue(screen.controller.request_bench());paused.append(True)
        screen.pitch.on_drawn=painted
        beats=[];timer=QTimer();timer.setInterval(2);timer.timeout.connect(lambda:beats.append(True));timer.start()
        self.addCleanup(timer.stop);now=0.;end=time.monotonic()+120
        worker_killed = False
        with patch('goal2.ui.native_pitch.time',SimpleNamespace(monotonic=lambda:now)):
            def tick():
                nonlocal now
                now += 1
                screen.tick()
                app.processEvents()
                if screen.stop_box.open:
                    screen.answer_stop_box(Qt.Key.Key_Return)
                if not worker_killed:
                    self.assertEqual(failures, [])
            if half_time:
                helper.until(lambda: screen.review is not None and screen.review.phase == 'ready', tick)
                page = screen.review
                assert_fits(self, win)
                self.assertEqual(page.enter_hint_text(), 'Play second half')
                self.assertEqual(page.statistics_phase, 'half')
                start = page.snapshot
                outgoing, incoming = half_time_pair(start.snapshot.data)
                if start.sides[0] != start.managed_country:
                    self.assertFalse(page.substitute.isEnabled())
                    QTest.mouseClick(page.team_button, Qt.MouseButton.LeftButton)
                self.assertEqual(page.players, start.squad)
                frames = len(d.frames)
                QTest.mouseClick(page.roster.rows[page.players.index(outgoing)], Qt.MouseButton.LeftButton)
                QTest.keyClick(win, Qt.Key.Key_X)
                self.assertEqual(page.outgoing, outgoing)
                QTest.mouseClick(page.roster.rows[page.players.index(incoming)], Qt.MouseButton.LeftButton)
                QTest.mouseClick(page.substitute, Qt.MouseButton.LeftButton)
                QTest.keyClick(win, Qt.Key.Key_X)
                QTest.keyClick(win, Qt.Key.Key_F1)
                from goal2.ui.s22_help import HelpScreen
                helper.until(lambda: page.phase == 'ready', tick)
                self.assertIsInstance(win.current(), HelpScreen)
                self.assertEqual(len(d.frames), frames)
                self.assertIn(incoming, page.snapshot.eleven)
                self.assertIn(outgoing, page.snapshot.bench)
                latest = page.snapshot
                self.assertGreater(latest.snapshot.decision, start.snapshot.decision)
                self.assertEqual(latest.snapshot.data['substitutions_left'], start.snapshot.data['substitutions_left'] - 1)
                QTest.keyClick(win, Qt.Key.Key_Escape)
                QTest.keyClick(win, Qt.Key.Key_G)
                helper.until(lambda: page.phase == 'ready', tick)
                self.assertGreater(page.snapshot.snapshot.decision, latest.snapshot.decision)
                self.assertEqual(page.snapshot.snapshot.data['tactics'], latest.snapshot.data['tactics'] ^ 1)
                self.assertEqual(len(d.frames), frames)
                self.assertEqual(completed, [])
                QTest.mouseClick(page.enter_hint, Qt.MouseButton.LeftButton)
                QTest.keyClick(win, Qt.Key.Key_Return)
                helper.until(lambda: screen.review is None, tick)
                answers = [value for context, value in d.choices if context == 'half_time']
                self.assertEqual(len(answers), 3)
                self.assertEqual(answers[-1], {})
            if review:
                helper.until(lambda: getattr(screen, 'review', None) is not None, tick)
                page = screen.review
                self.assertEqual(page.phase, 'loading')
                self.assertEqual(page.enter_hint_text(), '')
                QTest.keyClick(win, Qt.Key.Key_Return)
                QTest.keyClick(win, Qt.Key.Key_F1)
                from goal2.ui.s22_help import HelpScreen
                self.assertIsInstance(win.current(), HelpScreen)
                if lose_worker:
                    worker_killed = True
                    native.shared.engine.process.kill()
                    helper.until(lambda: page.phase == 'failed', tick)
                    self.assertIsInstance(win.current(), HelpScreen)
                    self.assertEqual(len(failures), 1)
                    self.assertEqual(completed, [])
                    QTest.keyClick(win, Qt.Key.Key_Escape)
                    self.assertIs(win.current(), page)
                    self.assertFalse(page.available())
                    page.exit_review()
                    self.assertFalse(any(context == 'post_match' for context, _ in d.choices))
                    helper.until(lambda: native.disposed)
                    return
                helper.until(lambda: page.phase == 'ready', tick)
                self.assertIsInstance(win.current(), HelpScreen)
                self.assertFalse(page.available())
                self.assertEqual(completed, [])
                QTest.keyClick(win, Qt.Key.Key_Escape)
                self.assertIs(win.current(), page)
                assert_fits(self, win)
                self.assertTrue(page.available())
                self.assertNotEqual(page.snapshot.team_context['match_set_up'], 0)
                left, right = page.snapshot.snapshot.data['board']['final_score']
                self.assertEqual(page.score.text(), f'{page.names[0]} {left}–{right} {page.names[1]}')
                self.assertEqual(page.players, page.snapshot.squad if page.snapshot.managed_country ==
                                 page.snapshot.sides[0] else page.snapshot.opponents)
                QTest.mouseClick(page.team_button, Qt.MouseButton.LeftButton)
                self.assertEqual(page.side, 1)
                self.assertEqual(page.players, page.snapshot.squad if page.snapshot.managed_country ==
                                 page.snapshot.sides[1] else page.snapshot.opponents)
                QTest.keyClick(win, Qt.Key.Key_Down)
                self.assertEqual(page.row, 1)
                QTest.mouseClick(page.roster.rows[2], Qt.MouseButton.LeftButton)
                self.assertEqual(page.row, 2)
                QTest.mouseClick(page.stats_button, Qt.MouseButton.LeftButton)
                self.assertIsInstance(win.current(), BoardScreen)
                self.assertEqual(win.current().data['score'], [left, right])
                QTest.keyClick(win, Qt.Key.Key_Escape)
                self.assertIs(win.current(), page)
                QTest.keyClick(win, Qt.Key.Key_Escape)
                self.assertIs(win.current(), page)
                answer = screen.answer_native
                with patch.object(screen, 'answer_native', side_effect=lambda number, _: answer(number, {})):
                    QTest.keyClick(win, Qt.Key.Key_Return)
                    helper.until(lambda: page.phase == 'retry', tick)
                self.assertEqual(d.waiting['decision'], page.decision)
                QTest.keyClick(win, Qt.Key.Key_Return)
                helper.until(lambda: page.phase == 'ready', tick)
                QTest.mouseClick(page.enter_hint, Qt.MouseButton.LeftButton)
                QTest.keyClick(win, Qt.Key.Key_Return)
                QTest.keyClick(win, Qt.Key.Key_F1)
                helper.until(lambda: page.phase == 'finished', tick)
                self.assertIsInstance(win.current(), HelpScreen)
                self.assertEqual(completed, [])
                self.assertEqual(d.choices.count(('post_match', {'post_match_exit': True})), 1)
                QTest.keyClick(win, Qt.Key.Key_Escape)
                helper.until(lambda: screen.review is None, tick)
            while time.monotonic()<end and d.completed_view is None:
                tick()
                time.sleep(.001)
            view=d.completed_view;self.assertIsNotNone(view,d.error);self.assertEqual(completed,[True])
            self.assertTrue(screen.controller.covered);self.assertGreater(len(beats),2)
            self.assertEqual((digest(d.events),digest(d.frames),d.painted_sequence,d.shown_count),held[0])
            decoder_hashes(view.display_state(model.state),model.goaldat,view.team_context,view.sides)
            data=board(d.shown(),'full',d.quick)
            self.assertEqual(data['counters'],{k:view.board['statistics'][k] for k in data['counters']})
            facade=SimpleNamespace(state=view.display_state(model.state),goaldat=model.goaldat)
            names=[model.goaldat.country_names[c] for c in view.sides]
            from goal2.desktop.model import kind_word
            stats=BoardScreen(win,facade,names,kind_word(native.fixture.kind,native.fixture.stage),
                'full',data,lambda:None,screen.controller.kits)
            win.pop();win.push(stats);app.processEvents();assert_fits(self,win);win.grab()
            self.assertEqual(stats.data['score'],view.board['final_score'])
            screen.resume_native();self.assertIsNone(d.completed_view)
            helper.until(lambda:d.status in ('resumed','lost'),lambda:(screen.tick(),app.processEvents()))
        self.assertEqual(d.status,'resumed',d.error);self.assertEqual(native.pid,pid)
        self.assertEqual(native.shared.engine.generation,1);self.assertEqual(model.state,before)
        packets = native.take_observations()
        self.assertEqual(len(packets),1);self.assertEqual(native.take_observations(),[])
        if review or half_time:
            expected = pypy_engine.call(__name__+':direct', raw, True, half_time)
            canonical = [event for event in prefix + d.events if not (
                event['kind'] == 'decision' and event['data']['context'] == 'post_match')]
            self.assertEqual(digest(canonical), expected['events_hash'])
            self.assertEqual(digest(d.frames), expected['frames_hash'])
            self.assertEqual(digest(view.board), expected['board_hash'])
            self.assertEqual(completed_result_hash(view.result), expected['result_hash'])
            self.assertEqual(canonical_hash(native.boundary_state), expected['state_hash'])
            self.assertEqual(digest(packets[0]['observation']), expected['observation_hash'])


if __name__=='__main__':unittest.main()
