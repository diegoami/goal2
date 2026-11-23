"""[designed: T170af/#822] Real retained driver and current decoder oracle.

Engine computation stays in PyPy; original data stay private. Logs hold digests.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine,requires
from goal2.tests import test_native_driver_actual_t170ac as old
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_news_wire_t170t import digest

ROOT=Path(__file__).resolve().parents[2]


def decoder_hashes(state,goaldat,context,sides):
    from goal2.game.player_card import card
    from goal2.game.country_card import card as team_card
    words=[]
    for c in sides:
        raw=state.countries[c]
        words.extend(int.from_bytes(raw[i:i+2],'little') for i in range(0,40,2))
    return dict(records_hash=hashlib.sha256(b''.join(state.players+state.countries)).hexdigest(),
        cards_hash=digest([card(state,w,goaldat) for w in words if w]),
        teams_hash=digest([team_card(state,c,goaldat,performance_context=context) for c in sides]))


def native_oracle(m,goaldat):
    """Independent byte reads of the actual stopped machine, not state/2 decode."""
    from goal2.engine.original_match.image import PLAYERS_PTR,COUNTRIES_PTR
    from goal2.game.state import GameState
    players=[m.m.read(m.m.far(PLAYERS_PTR)+20*w,20) for w in range(3061)]
    countries=[m.m.read(m.m.far(COUNTRIES_PTR)+191*c,191) for c in range(129)]
    country=m.opts['managed'];squad=[int.from_bytes(countries[country][i:i+2],'little') for i in range(0,40,2)]
    state=GameState(players,countries,country,squad,m.m.rd(0x7B62),m.m.rd(0x8336),{},b'',m.memory_component(),
        starting_eleven=squad[:11],country_tactics=countries[country][0x2D])
    sides=[m.m.rd(0x9B34),m.m.rd(0x9B36)]
    context=dict(match_set_up=m.m.rd(0xC1E,1),in_match_menu_used=m.m.rd(0xC1F,1),sides=sides)
    return decoder_hashes(state,goaldat,context,sides)


@requires.need(files=('GOAL.DAT',))
class Actual(unittest.TestCase):
    def exercise(self,complete=False):
        from goal2.engine.original_match.image import Image
        from goal2.game import engine_tables
        from goal2.game.engine_python import engine_python
        from goal2.game.watched_jobs import MatchEngine
        from goal2.data.goaldat import load
        raw=reference_raw();goaldat=load((ROOT/'.cache/GOAL.DAT').read_bytes())
        tmp=tempfile.TemporaryDirectory(prefix='goal2-stopped-view-');self.addCleanup(tmp.cleanup)
        proof=Path(tmp.name)/'native.json';owner=SimpleNamespace(state='unchanged');keeper=object()
        shared=MatchEngine.join(owner,keeper);self.addCleanup(shared.leave,owner,keeper)
        script='''import hashlib,json,sys
from pathlib import Path
from goal2.data.goaldat import load
from goal2.game.engine_server import Server,main
from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
import os
os.environ['GOAL2_ENGINE_CHILD']='1'
from goal2.tests.test_stopped_view_actual_t170af import native_oracle
goaldat=load(Path(sys.argv[2]).read_bytes());proof={'views':[]};real=Server.send
def send(self,kind,value=None,payload=b''):
    if kind=='season' and isinstance(value,dict):
        if value.get('action')=='stopped_preview':
            item=native_oracle(self.season.session.pending_match,goaldat)
            item['decision']=value['preview']['decision'];proof['views'].append(item)
            Path(sys.argv[1]).write_text(json.dumps(proof))
        if value.get('action')=='next' and value.get('exhausted'):
            m=self.season.session.pending_match
            proof['cpu']=dict(memory_hash=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])
            Path(sys.argv[1]).write_text(json.dumps(proof))
    return real(self,kind,value,payload)
Server.send=send
raise SystemExit(main())
'''
        shared.engine.command=[engine_python(),'-u','-c',script,str(proof),str(ROOT/'.cache/GOAL.DAT')]
        helper=old.Actual('test_complete_pause_edit_paced_driver_and_resume_equal_direct_sdk')
        self.addCleanup(helper.doCleanups)
        native,d,prefix,boundary=helper.prepare(owner,Image.from_bytes(raw).state(engine_tables.load()))
        pid=native.pid;answers=old.Answers();now=0.;requested=False;views=[];end=time.monotonic()+900
        while time.monotonic()<end:
            now+=1;frame=d.tick(now)
            if frame is not None:
                d.painted(frame['sequence'])
                if not requested:self.assertTrue(d.request_pause());requested=True
            if d.status=='decision':
                decision=d.waiting;before=(d.events,d.frames,d.shown_count,d.painted_sequence)
                d.set_held(True);d.request_view()
                helper.until(lambda:d.status in ('decision','lost'),lambda:d.tick(now))
                self.assertEqual(d.status,'decision',d.error);view=d.stopped_view
                self.assertIsNotNone(view);self.assertEqual(view.snapshot.decision,decision['decision'])
                self.assertEqual((d.events,d.frames,d.shown_count,d.painted_sequence),before)
                self.assertEqual(view.snapshot.state_hash,canonical_hash(view.snapshot.state))
                actual=decoder_hashes(view.display_state(),goaldat,view.team_context,view.sides)
                expected=json.loads(proof.read_text())['views'][-1]
                self.assertEqual(actual,{k:v for k,v in expected.items() if k!='decision'})
                self.assertEqual(expected['decision'],decision['decision'])
                views.append(view.snapshot.state_hash)
                count=shared.engine._season_requests
                for _ in range(3):d.tick(now+100)
                self.assertEqual(shared.engine._season_requests,count)
                self.assertEqual(canonical_hash(native.boundary_state),canonical_hash(boundary['state']))
                d.set_held(False);d.answer(answers(decision['event']['data']))
                self.assertIsNone(d.stopped_view)
                if len(views)==2 and not complete:break
            self.assertEqual(native.pid,pid);self.assertNotIn(d.status,('lost','closed'),d.error)
            if d.status=='complete':break
            time.sleep(.0005)
        self.assertEqual(native.pid,pid);self.assertEqual(shared.engine.generation,1)
        self.assertEqual(owner.state,'unchanged');self.assertEqual(len(set(views)),len(views))
        if not complete:
            self.assertEqual(len(views),2);d.close();return
        self.assertEqual(d.status,'complete');self.assertTrue(answers.edited)
        d.resume();helper.until(lambda:d.status in ('resumed','lost'),lambda:d.tick(now+100))
        self.assertEqual(d.status,'resumed',d.error);self.assertIsNone(d.stopped_view)
        packets=native.take_observations();self.assertEqual(len(packets),1);self.assertEqual(native.take_observations(),[])
        result=json.loads(proof.read_text())['cpu']
        result.update(events_hash=digest(prefix+d.events),frames_hash=digest(d.frames),events=len(prefix+d.events),
            frames=len(d.frames),boundary_hash=canonical_hash(boundary['state']),state_hash=canonical_hash(native.boundary_state),
            observation_hash=digest(packets[0]['observation']),status=packets[0]['observation']['status'],
            pauses=d.pause_requests,edited=answers.edited)
        self.assertEqual(result,pypy_engine.call('goal2.tests.test_native_driver_actual_t170ac:direct',raw))
        self.assertEqual(native.pid,pid);self.assertIs(shared.match,native);self.assertEqual(owner.state,'unchanged')
        d.close();print('T170AF_FULL '+json.dumps(dict(views=len(views),result=result),sort_keys=True),flush=True)

    def test_actual_pipe_held_reads_refresh_and_both_sides_decode_from_native_records(self):self.exercise()

    @requires.need(slow=True)
    def test_full_retained_driver_reads_equal_direct_sdk(self):self.exercise(complete=True)


@requires.need(modules=('PySide6',),files=('GOAL.DAT',))
class Window(unittest.TestCase):
    def test_existing_pitch_delivers_covered_reads_and_confirms_edit_before_play(self):
        from PySide6.QtCore import QTimer
        from goal2.ui.native_pitch import NativePitchScreen
        from goal2.ui.screen import Screen
        from goal2.tests.test_native_pitch_actual_t170ad import NativeWindow
        NativeWindow.setUpClass()
        case=NativeWindow('test_held_widgets_to_native_pitch_pause_reading_and_covered_close')
        self.addCleanup(case.doCleanups);views=[];failures=[];edited=[]
        class ReadingPitch(NativePitchScreen):
            def __init__(s,window,model,native,**kwargs):
                original=kwargs['on_decision']
                def decision(screen,waiting):
                    d=screen.controller.driver
                    before=(d.events,d.frames,d.painted_sequence,d.shown_count)
                    d.request_view();cover=Screen(window);window.push(cover)
                    timer=QTimer(screen);timer.setInterval(2)
                    def poll():
                        if screen._closed:timer.stop();return
                        view=d.stopped_view
                        if view is None:return
                        timer.stop()
                        try:
                            self.assertTrue(screen.controller.covered)
                            self.assertEqual((d.events,d.frames,d.painted_sequence,d.shown_count),before)
                            decoder_hashes(view.display_state(model.state),model.goaldat,view.team_context,view.sides)
                            if waiting['event']['data']['context']=='pause':
                                views.append((view.snapshot.state_hash,view.countries[view.managed_country][0x2D]))
                            self.assertIs(window.current(),cover);window.pop()
                            if waiting['event']['data']['context']=='pause' and not edited:
                                edited.append(True)
                                screen.answer_native(waiting['decision'],dict(edit_only=True,
                                    tactics={1:not bool(waiting['event']['data']['tactics']&1)}))
                            else:original(screen,waiting)
                            self.assertIsNone(d.stopped_view)
                        except Exception as exc:
                            failures.append(str(exc));screen._failure(str(exc))
                    timer.timeout.connect(poll);timer.start()
                kwargs['on_decision']=decision
                super().__init__(window,model,native,**kwargs)
        with patch('goal2.tests.test_native_pitch_actual_t170ad.NativePitchScreen',ReadingPitch):
            case.test_held_widgets_to_native_pitch_pause_reading_and_covered_close()
        self.assertEqual(failures,[]);self.assertEqual(len(views),2)
        self.assertNotEqual(views[0][0],views[1][0]);self.assertEqual(views[0][1]^views[1][1],1)


if __name__=='__main__':unittest.main()
