#!/usr/bin/env python3
"""[designed: T79] Actual product handoff oracle; main owns native Windows execution.
Observers record real render/flip results without replacing widgets or painting.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tools/desktop-ui'))

VIEWER=r'''
import collections, hashlib, inspect, json, os, pathlib, platform, sys, time
import pygame
from goal2.desktop import pygame_viewer as v
from goal2.desktop.style import COLORS
out=pathlib.Path(sys.argv.pop(1));mode=sys.argv.pop(1);out.mkdir(parents=True,exist_ok=False)
def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,default=lambda o:list(o) if isinstance(o,collections.deque) else repr(o)).encode()).hexdigest()
state={'tag':'[designed: T79] Production render/flip observer','mode':mode,'rendered':0,'last_frame':-1,'read_only':True,'captures':[]}
original=v.render_pitch;flip=pygame.display.flip;current=None;display=None
paint=original
def receipt():
 p=out/'metrics.new';p.write_text(json.dumps(state));deadline=time.monotonic()+.25
 while True:
  try:p.replace(out/'metrics.json');break
  except PermissionError as exc:
   if sys.platform!='win32' or getattr(exc,'winerror',None)!=5 or time.monotonic()>=deadline:raise
   time.sleep(min(.01,max(0,deadline-time.monotonic())))
def render(screen,font,d,scroll=0):
 global current,display
 before=digest(d.__dict__)
 texts=[]
 class ReadingTrace:
  def render(self,text,*args,**kwargs):
   texts.append(text);return font.render(text,*args,**kwargs)
  def __getattr__(self,name):return getattr(font,name)
 result=paint(screen,ReadingTrace(),d,scroll)
 state['reading_scroll']=result;state['painted_texts']=texts
 after=digest(d.__dict__);state['read_only']=state['read_only'] and before==after
 state.update(before=before,after=after,canonical_project=[list(v.project(-3,-21)),list(v.project(5,25))],font_height=font.get_height(),font_linesize=font.get_linesize())
 if not state['read_only']:
  state['failure']='renderer changed Display state';receipt();raise AssertionError(state['failure'])
 current=d.frame;display=d
 if current is not None:
  state['visible_slot_count']=sum(not row[7] for row in current['players']);state['ball_hidden']=current['ball'][2]
  state['pitch_rect']=list(v.FIELD);state['marker_radius']=11;state['ball_radius']=4
 return result
def postflip():
 flip()
 surface=pygame.display.get_surface()
 state.update(actual_sdl_driver=pygame.display.get_driver(),pygame=pygame.version.ver,sdl=list(pygame.get_sdl_version()),window_size=list(pygame.display.get_window_size()),surface_size=list(surface.get_size()),surface_flags=surface.get_flags(),platform=platform.platform(),wm_info={str(k):val if isinstance(val,(int,str,bool,float,type(None))) else repr(val) for k,val in pygame.display.get_wm_info().items()})
 if sys.platform=='win32' and state.get('native_geometry_size')!=list(surface.get_size()):
  import ctypes
  from ctypes import wintypes
  u=ctypes.WinDLL('user32',use_last_error=True);h=pygame.display.get_wm_info()['window'];r=wintypes.RECT();a=wintypes.RECT()
  u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.GetDpiForWindow.argtypes=[wintypes.HWND];u.GetDpiForWindow.restype=wintypes.UINT
  assert u.GetWindowRect(h,ctypes.byref(r));assert u.SystemParametersInfoW(0x0030,0,ctypes.byref(a),0)
  state['native_geometry_size']=list(surface.get_size())
  state['windows_native']={'hwnd':h,'dpi_for_window':u.GetDpiForWindow(h),'window_rect':[r.left,r.top,r.right,r.bottom],'available_desktop':[a.left,a.top,a.right,a.bottom]}
 size=surface.get_size()
 seen=state.setdefault('paint_sizes',[])
 if list(size) not in [entry['pixels'] for entry in seen]:
  factor=min(size[0]/1000,size[1]/720)
  p=out/('surface-%sx%s.png'%size);pygame.image.save(surface,str(p))
  seen.append({'pixels':list(size),'paint_factor':factor,'painted_body_font_height':state.get('font_height',0)*factor,'windows_native':state.get('windows_native'),'canonical_field':list(v.FIELD),'canonical_project':[list(v.project(-3,-21)),list(v.project(5,25))],'capture':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 if current is not None and current['sequence']!=state['last_frame']:
  assert current['sequence']==state['last_frame']+1,'renderer skipped discrete frame'
  state['last_frame']=current['sequence'];state['rendered']+=1
  if current['sequence'] in (100,200,300):
   from pygame._sdl2 import Window
   native=Window.from_display_module();native.size={100:(900,640),200:(1440,900),300:(1000,720)}[current['sequence']];native.position=(24,40)

  if len(state['captures'])<2:
   p=out/('frame-%s.png'%current['sequence']);pygame.image.save(surface,str(p));state['captures'].append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 if display is not None and display.result is not None and not state.get('complete'):
  state['complete']=True;state['display_lines_sha256']=digest(display.lines());state['display_result_sha256']=digest(display.result)
  p=out/'complete.png';pygame.image.save(surface,str(p));state['captures'].append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_END))
 elif display is not None and display.result is not None and state.get('complete'):
  if not state.get('rating_tail') and state['painted_texts'][-1]==display.lines()[-1]:
   p=out/'rating-tail.png';pygame.image.save(surface,str(p))
   state['rating_tail']={'scroll':state['reading_scroll'],'last_painted':state['painted_texts'][-1],'expected_last_line':display.lines()[-1],'capture':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'event':'End','observed_after_flip':True}
   pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_UP))
  elif state.get('rating_tail') and not state.get('scrolled_up') and state['reading_scroll']<state['rating_tail']['scroll']:
   p=out/'scrolled-up.png';pygame.image.save(surface,str(p))
   state['scrolled_up']={'scroll':state['reading_scroll'],'capture':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'event':'Up','observed_after_flip':True}
 receipt()
v.render_pitch=render;pygame.display.flip=postflip
sys.exit(v.main())
'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def geometry(window,app,out,report,stage):
 """[designed: T79] Recompute real text/ancestor bounds after every actual resize."""
 from PySide6.QtCore import Qt,QPoint,QRect
 from PySide6.QtGui import QFontMetrics
 from PySide6.QtTest import QTest
 from navigation import reveal
 ratio=window.devicePixelRatioF()
 sizes=((900,640),) if ratio>1.5 else ((1440,900),(1050,780),(900,700))
 entries=report.setdefault('geometry',[])
 for width,height in sizes:
  window.showNormal();window.activateWindow();QTest.qWait(120)
  attempts=[];deadline=time.monotonic()+3
  while True:
   window.resize(width,height);QTest.qWait(100)
   actual=(window.width(),window.height());attempts.append(list(actual))
   if actual==(width,height):
    QTest.qWait(50)
    if (window.width(),window.height())==(width,height):break
   assert time.monotonic()<deadline,'requested Qt logical size was not realized'
  window.navigate(3);app.processEvents()
  report.setdefault('resize_requests',[]).append({'stage':stage,'requested':[width,height],'observed_attempts':attempts,'normalized_window_state':window.windowState().value})
  assert (window.width(),window.height())==(width,height),'requested Qt logical size was not realized'
  page=window.pages[3]
  for label in (window.match_provenance,window.match_score,window.match_progress,window.fixture_routes):
   page.ensureWidgetVisible(label,0,0);app.processEvents()
   pos=label.mapTo(page.viewport(),QPoint(0,0));rect=label.contentsRect()
   text=QFontMetrics(label.font()).boundingRect(QRect(0,0,rect.width(),10000),int(Qt.TextFlag.TextWordWrap),label.text())
   assert text.width()<=rect.width() and text.height()<=rect.height(),f'{label.objectName()} text does not fit current styled bounds'
   assert label.isVisible() and pos.x()>=0 and pos.x()+label.width()<=page.viewport().width(),f'{label.objectName()} clipped horizontally'
   assert pos.y()>=0 and pos.y()+label.height()<=page.viewport().height(),f'{label.objectName()} not reachable at current size'
   entries.append({'stage':stage,'requested':[width,height],'actual':[window.width(),window.height()],
      'object':label.objectName(),'font_pixel_height':QFontMetrics(label.font()).height(),'text_bounds':[text.width(),text.height()],
      'content_bounds':[rect.width(),rect.height()],'viewport':[page.viewport().width(),page.viewport().height()],
      'origin':[pos.x(),pos.y()],'text':label.text()})
  reveal(window.play);QTest.keyClick(window,Qt.Key.Key_Tab);app.processEvents()
  focus=window.focusWidget();assert focus is not None and focus.isVisible() and focus.isEnabled(),'native Tab did not reach an enabled visible match control'
  report.setdefault('focus',[]).append({'stage':stage,'size':[width,height],'object':focus.objectName(),'accessible_name':focus.accessibleName()})
  capture=out/f'{stage}-{width}x{height}.png';assert window.grab().save(str(capture))
  report['captures'].append({'path':capture.name,'sha256':sha(capture)})


def quick_decisions(window,app,out,report):
 """[designed: T79] Actual private halftime controls and owned two-window shutdown."""
 from PySide6.QtCore import Qt,QPoint
 from PySide6.QtTest import QTest
 from PySide6.QtGui import QFontMetrics
 from goal2.tests.test_pygame_match_view import pump
 from navigation import reveal
 def click(button):reveal(button);QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
 model=window.model;prior=Path(model.save_path).read_bytes()
 window.country.setCurrentIndex(window.country.findData(4));click(window.new);click(window.confirm)
 before=copy.deepcopy(model.state)
 click(window.play);assert window.jobs.busy and window.match_provenance.text()=='Quick simulation (rebuild setup)'
 pump(lambda:window.jobs.halftime is not None,app=app,timeout=120)
 assert model.state==before and Path(model.save_path).read_bytes()==prior,'private halftime changed committed game/save'
 assert window.half_panel.isVisible() and not window.save.isEnabled() and window.stop.isEnabled()
 geometry(window,app,out,report,'quick-halftime')
 controls=[]
 for widget in (window.half_out,window.half_in,window.substitute,window.continue_match):
  reveal(widget);app.processEvents();page=window.pages[3];pos=widget.mapTo(page.viewport(),QPoint(0,0))
  assert widget.isVisible() and widget.isEnabled() and pos.x()>=0 and pos.y()>=0 and pos.x()+widget.width()<=page.viewport().width() and pos.y()+widget.height()<=page.viewport().height(),'halftime action not reachable'
  text=widget.currentText() if hasattr(widget,'currentText') else widget.text()
  assert QFontMetrics(widget.font()).horizontalAdvance(text)+24<=widget.width(),'halftime action text clipped'
  capture=out/('quick-half-'+widget.accessibleName().replace(' ','-')+'.png');assert window.grab().save(str(capture))
  report['captures'].append({'path':capture.name,'sha256':sha(capture)})
  controls.append({'name':widget.accessibleName(),'text':text,'size':[widget.width(),widget.height()]})
 click(window.substitute);assert len(window.jobs.halftime['changes'])==1,'actual substitution control did not update private decision'
 click(window.continue_match);pump(lambda:not window.jobs.busy,app=app,timeout=120)
 assert model.state.match_count==before.match_count+1 and Path(model.save_path).read_bytes()==prior
 assert window.match_provenance.text()=='Quick simulation (rebuild setup)' and not window.half_panel.isVisible(),'quick completion retained original/halftime context'
 report['quick_halftime']={'actual_private_substitution':True,'continue_completed':True,'prior_save_retained':True,'controls':controls}
 # [designed] A blocked engine keeps both real windows alive for authoritative close/reap.
 click(window.new);click(window.confirm);snapshot=copy.deepcopy(model.state)
 window.watched.engine.command=[sys.executable,'-c','import time;time.sleep(60)'];window.watched.viewer_command=None
 click(window.watch);assert window.watched.busy
 engine=window.watched.engine.process;viewer=window.watched.process
 started=time.monotonic();window.close();app.processEvents()
 assert time.monotonic()-started<3 and engine.poll() is not None and viewer.poll() is not None,'two-window close did not reap owned children'
 assert model.state==snapshot and Path(model.save_path).read_bytes()==prior and not model.match_pending
 report['both_window_shutdown']={'engine_reaped':True,'viewer_reaped':True,'state_and_save_retained':True,'seconds':time.monotonic()-started}


def lifecycle(report):
 """[designed: T79] Run retained real child/refusal/save guards without rewriting their oracles."""
 import unittest
 names=[
 'goal2.tests.test_pygame_match_view.PresentationTests.test_qt_heartbeat_blocked_tail_and_actual_viewer_quit',
 'goal2.tests.test_pygame_match_view.PresentationTests.test_real_viewer_cancel_duplicate_and_failed_start_preserve_save',
 'goal2.tests.test_pygame_match_view.PresentationTests.test_malformed_stale_ack_and_engine_failure_preserve_state',
 'goal2.tests.test_pygame_match_view.PresentationTests.test_optional_dependency_and_qualifier_boundary',
 'goal2.tests.test_desktop_quick_jobs.QuickJobTests.test_cancel_reaps_blocked_and_sigterm_ignoring_process_with_bounded_wait']
 # [designed] Discover the retained class rather than assuming its historical class name.
 from goal2.tests import test_desktop_quick_jobs as quick
 cls=next(value for value in vars(quick).values() if isinstance(value,type) and issubclass(value,unittest.TestCase) and hasattr(value,'test_cancel_reaps_blocked_and_sigterm_ignoring_process_with_bounded_wait'))
 names[-1]=cls.__module__+'.'+cls.__name__+'.test_cancel_reaps_blocked_and_sigterm_ignoring_process_with_bounded_wait'
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
 assert result.wasSuccessful() and not result.skipped,'retained handoff lifecycle failed or skipped'
 report['lifecycle']={'tests':result.testsRun,'skips':len(result.skipped),'result':'PASS','entries':names}


def scenario(options):
 """[designed: T79] Real widgets/rendering, independent original continuation and retained lifecycle."""
 from types import SimpleNamespace
 args=SimpleNamespace(mode='actual',template=options.template,data=options.data,
                      output=Path(options.evidence_dir),repeat_rate=240)
 args.output.mkdir(parents=True,exist_ok=False)
 report={'tag':'[designed: T79] Actual Qt/SDL original handoff','mode':args.mode,'platform':platform.platform(),'python':sys.version,'scenario_sha256':sha(__file__),'observer_sha256':hashlib.sha256(VIEWER.encode()).hexdigest(),'resources':{'template':sha(args.template),'data':sha(args.data)},'sources':{str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'goal2/desktop').glob('*.py'))},'repeat_policy':'resume-owned-pre-match-checkpoint','rounds':[],'captures':[],'limits':['Real product widgets and renderer; observer does not substitute painting','Qt scale does not establish SDL OS/paint scaling','Separate retained lifecycle suites remain mandatory']}
 from PySide6.QtCore import Qt,QTimer,qVersion
 from PySide6.QtWidgets import QApplication,QWidget,QFrame,QVBoxLayout,QLabel
 from PySide6.QtTest import QTest
 from goal2.desktop.model import DesktopModel
 from goal2.desktop.window import ManagementWindow
 from goal2.desktop.match_view import completion
 from goal2.desktop.style import COLORS
 from goal2.tests.test_pygame_match_view import pump
 from navigation import reveal
 from watched import expected
 app=QApplication.instance() or QApplication([])
 report['uncaught_qt_callbacks']=[];previous_hook=sys.excepthook
 def callback_exception(kind,value,trace):
  report['uncaught_qt_callbacks'].append({'type':kind.__name__,'message':str(value)});previous_hook(kind,value,trace)
 sys.excepthook=callback_exception
 report.update(qt=qVersion(),qpa=app.platformName(),requested_qt_scale=os.environ.get('QT_SCALE_FACTOR'))
 with tempfile.TemporaryDirectory(prefix='T79-planning-') as folder:
  save=Path(folder)/'owned.g2save';m=DesktopModel.open(args.template,args.data,save,country=4);w=ManagementWindow(m);w.show();assert QTest.qWaitForWindowExposed(w,2000);w.activateWindow();QTest.qWait(150)
  beats=[];heartbeat=QTimer();heartbeat.setInterval(5);heartbeat.timeout.connect(lambda:beats.append(time.monotonic()));heartbeat.start()
  presentation=QTimer();presentation.setInterval(30)
  def click(button):reveal(button);QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
  try:
   report['qt_ratio']=w.devicePixelRatioF();report['qt_available']=[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()]
   assert w.findChild(QWidget,'matchSurface') is not None,'named match surface is absent on prestyle baseline'
   assert all(w.findChild(QLabel,name) is not None for name in ('matchProvenance','matchScore','matchProgress')),'named match reading surfaces are absent'
   w.country.setCurrentIndex(w.country.findData(18));click(w.new)
   assert m.state.managed_country==18 and m.goaldat.country_names[18]=='Malta'
   fixture=m.state.campaign.next_fixture
   assert (fixture.fixture_id,fixture.side_a,fixture.side_b,fixture.kind)==('original:1376',32,18,1)
   w.captain.setCurrentIndex(w.captain.findData(m.state.starting_eleven[0]))
   w.tactics[0][1].setChecked(not w.tactics[0][1].isChecked());click(w.confirm)
   assert w.draft()==(m.state.starting_eleven,m.state.captain,m.state.country_tactics)
   assert m.state.captain==341
   control=type(m)(m.goaldat,m.template_bytes,Path(folder)/'direct');control.state=copy.deepcopy(m.state)
   # [designed: T79] Save both checkpoints through the actual Qt path/actions.
   opening=Path(folder)/'opening.g2save';working=save;repeat=Path(folder)/'repeat.g2save'
   w.path.setText(str(opening));click(w.save)
   assert opening.is_file() and m.save_path==opening,'opening checkpoint Save failed'
   opening_state=copy.deepcopy(m.state);opening_bytes=opening.read_bytes();opening_template=m.template_bytes
   w.path.setText(str(working));click(w.save)
   assert working.is_file() and m.save_path==working and m.state==opening_state
   assert working.read_bytes()==opening_bytes,'initial owned working save differs from opening checkpoint'
   first_completed_bytes=None
   report['opening_save_sha256']=sha(opening)
   geometry(w,app,args.output,report,'idle')
   original_start=w.watched.start
   for round_index in range(2):
    assert m.state.campaign.next_fixture.kind==1,'resumed checkpoint is not a supported scheduled friendly'
    outcome,events=expected(control);before=copy.deepcopy(m.state);prior_save=save.read_bytes() if save.exists() else None
    child_output=args.output/('round-%s-sdl'%round_index)
    w.watched.viewer_command=[sys.executable,'-c',VIEWER,str(child_output),args.mode]
    rate=60 if round_index==0 else args.repeat_rate
    w.watched.start=original_start if round_index==0 else lambda **kw:original_start(playback_rate=rate,**kw)
    beats.clear();click(w.watch);assert w.watched.busy,w.status.text()
    engine=w.watched.engine.process;viewer=w.watched.process
    duplicate_checked=False
    if w.watched.busy:
     w.start_watched();w.start_match();assert w.watched.engine.process is engine and not w.jobs.busy,'duplicate handoff launched another job'
     duplicate_checked=True
    geometry(w,app,args.output,report,'starting-'+str(round_index))
    # [designed: T79] Read only the product status while its observer writes diagnostics.
    live_seen=[]
    def live_check():
     if w.watched.busy and getattr(w.watched,'frame_ack',-1)>=0:
      pose=w._match_poses.get(w.watched.frame_ack)
      if pose:
       a,b=w.watched.display.countries
       assert w.match_score.text()==f'{a} {pose["score"][0]} — {pose["score"][1]} {b}','Qt live score differs from actual consumed pose'
       if not live_seen:geometry(w,app,args.output,report,'live-'+str(round_index))
       live_seen.append(w.watched.frame_ack)
     return not w.watched.busy
    pump(live_check,app=app,timeout=360)

    # Parent publication sends complete; wait for the existing child packet ACK before reaping.
    # A final pitch-frame ACK alone does not prove the later complete-board flip.
    if w.watched.process is not None:
     pump(lambda:w.watched.last_status is not None and
          w.watched.last_status['sequence']==w.watched.display.sequence and
          w.watched.last_status['digest']==w.watched.display.digest(),app=app,timeout=30)
     QTest.qWait(250)
    w.watched.close_viewer();w.poll_watched();assert viewer.poll() is not None
    metrics=json.loads((child_output/'metrics.json').read_text())
    if metrics.get('read_only') is False:
     assert metrics.get('failure')=='renderer changed Display state','renderer failure was outside read-only oracle'
     assert m.state==before and (save.read_bytes() if save.exists() else None)==prior_save,'renderer mutant altered committed state/save'
     assert opening.read_bytes()==opening_bytes and working.read_bytes()==prior_save and not m.match_pending and engine.poll() is not None,'renderer mutant lost save/ownership retention'
     report['negative_control']={'intended_read_only_failure':True,'state_and_saves_preserved':True,'engine_and_viewer_reaped':True,'pending_cleared':True,'metrics_read_after_reaping':True}
     raise AssertionError('renderer changed Display state')
    assert duplicate_checked,'duplicate exclusion was not visited while the original job was busy'
    assert live_seen,'no consumed live Qt score observed'
    assert m.state==control.state,'complete state/Memory/RNG/history differs from direct original'
    assert m.state.match_count==before.match_count+1 and len(beats)>5
    assert max((b-a for a,b in zip(beats,beats[1:])),default=0)<1,'Qt heartbeat blocked for a second'
    assert w.watched.display.events==json.loads(json.dumps(events)),'ordered original events differ'
    assert w.watched.display.result==completion(outcome,m.goaldat.player_names),'board/raw rating words/MOTM differ'
    assert w.watched.engine.outcome==outcome,'complete original outcome differs'
    assert metrics['display_lines_sha256']==hashlib.sha256(json.dumps(w.watched.display.lines(),sort_keys=True).encode()).hexdigest(),'SDL ordered reading projection differs from original result'
    from goal2.engine.original_match import Image
    players=Image.from_memory_component(outcome.memory).players()
    for side in w.watched.display.result['ratings']:
     for row in side:
      word=int.from_bytes(players[row['player']][18:20],'little');value=word if word<32768 else word-65536
      raw=None if word==0x7fff else (value-10000 if value>5000 else value)
      assert row['word']==word and row['raw']==raw and row['name']==m.goaldat.player_names[row['player']],'displayed rating differs from independent original word'
    report.setdefault('sdl',[]).append({'round':round_index,'metrics':metrics})

    assert w.watched.frames_enabled and w.watched.frame_ack==outcome.result['ticks']-1,'final rendered frame acknowledgement missing'
    assert metrics['rendered']==outcome.result['ticks'] and metrics['read_only'] and metrics.get('complete') is True
    assert metrics['last_frame']==outcome.result['ticks']-1
    assert metrics.get('rating_tail',{}).get('observed_after_flip') and metrics.get('scrolled_up',{}).get('observed_after_flip'),'actual End/Up board interaction was not observed after flip'
    assert metrics['rating_tail']['last_painted']==w.watched.display.lines()[-1] and metrics['scrolled_up']['scroll']<metrics['rating_tail']['scroll'],'actual scroll did not reach the final original rating and retreat'
    for interaction in ('rating_tail','scrolled_up'):
     assert sha(child_output/metrics[interaction]['capture'])==metrics[interaction]['sha256'],'actual board interaction capture hash differs'

    assert all(list(size) in [item['pixels'] for item in metrics['paint_sizes']] for size in ((900,640),(1000,720),(1440,900))),'actual compact/larger SDL surfaces not observed'
    for item in metrics['paint_sizes']:
     assert sha(child_output/item['capture'])==item['sha256'],'actual SDL size capture hash differs'
    assert metrics['actual_sdl_driver'] and metrics['window_size'] and metrics['surface_size'] and metrics['font_height']>0
    assert any(item['path']=='complete.png' for item in metrics['captures']),'actual SDL complete-board capture missing'
    for item in metrics['captures']:
     assert sha(child_output/item['path'])==item['sha256'],'post-flip SDL capture hash differs'
    assert (save.read_bytes() if save.exists() else None)==prior_save,'playing altered existing save bytes'
    after=copy.deepcopy(m.state)
    for _ in range(4):w.poll_watched();w.refresh();app.processEvents()
    assert m.state==after,'presentation refresh republished completed result'
    click(w.save);saved=save.read_bytes();click(w.resume)
    assert m.state==control.state and save.read_bytes()==saved,'Save/Resume lost complete original continuation'
    w.navigate(3);app.processEvents();capture=args.output/('round-%s-qt.png'%round_index);assert w.grab().save(str(capture))
    report['captures'].append({'path':capture.name,'sha256':sha(capture)})
    report['rounds'].append({'round':round_index,'rate':rate,'default_rate_first':round_index==0,'duplicate_exclusion_visited':duplicate_checked,'fixture':outcome.result['index'],'countries':w.watched.display.countries,'ticks':outcome.result['ticks'],'final_ack':w.watched.frame_ack,'heartbeats':len(beats),'live_observations':len(live_seen),'maximum_heartbeat_gap':max((b-a for a,b in zip(beats,beats[1:])),default=0),'original_image_sha256':outcome.result['image_sha256'],'source_captain':before.captain,'source_tactics':before.country_tactics,'source_xi':before.starting_eleven,'source_seeds':[before.rng_seed_7b62,before.rng_seed_8336],'final_seeds':list(outcome.seeds),'full_exact_parity':True,'sdl_metrics_sha256':sha(child_output/'metrics.json'),'diagnostics_read_after_writer_reaped':True,'complete_packet_acknowledged':True})
    if round_index==0:
     first_completed_bytes=working.read_bytes();first_completed_state=copy.deepcopy(m.state)
     pending=m.state.campaign.next_fixture
     assert pending is not None and pending.kind!=1,'Malta post-friendly qualifier boundary not visited'
     assert not w.watch.isEnabled(),'Watch enabled for next qualifier'
     assert w.fixture_routes.text().splitlines()[-1]=='Watch unavailable: scheduled friendlies only','qualifier route explanation differs'
     assert w.watched.process is None and not w.watched.busy
     w.start_watched();app.processEvents()
     assert w.status.text()=='Watch supports scheduled friendlies only; pending qualifiers are unsupported','defensive Watch refusal differs'
     assert w.watched.process is None and not w.watched.busy and not m.match_pending,'qualifier refusal launched a watched job'
     assert m.state==first_completed_state and working.read_bytes()==first_completed_bytes and opening.read_bytes()==opening_bytes,'qualifier refusal changed state/save'
     geometry(w,app,args.output,report,'qualifier-refusal')
     report['blocked_next_fixture']={'kind':pending.kind,'id':pending.fixture_id,'watch_disabled':True,'exact_route_explanation':w.fixture_routes.text().splitlines()[-1],'defensive_callback_refused':True}
     report['first_completed_save_sha256']=sha(working)
     assert first_completed_bytes!=opening_bytes,'completed and opening checkpoints unexpectedly identical'
     w.path.setText(str(opening));click(w.resume)
     assert m.save_path==opening and m.state==opening_state and m.template_bytes==opening_template,'Resume did not restore complete opening state/template'
     assert opening.read_bytes()==opening_bytes and working.read_bytes()==first_completed_bytes,'Resume altered either retained checkpoint'
     w.path.setText(str(repeat));click(w.save)
     assert m.save_path==repeat and repeat.read_bytes()==opening_bytes and m.state==opening_state,'repeat owned save differs from resumed checkpoint'
     save=repeat
     control.template_bytes=m.template_bytes;control.state=copy.deepcopy(m.state)
   assert opening.read_bytes()==opening_bytes and working.read_bytes()==first_completed_bytes,'opening or first completed save was not retained'
   report['retained_saves']={'opening_sha256':sha(opening),'first_completed_sha256':sha(working),'repeat_completed_sha256':sha(repeat),'opening_retained':True,'first_completed_retained':True,'separate_owned_files':True}
   assert len(list(args.output.glob('round-*-sdl/complete.png')))==2,'both actual original complete-board captures are required'
   assert len(report['rounds'])==2 and all(row['fixture']==1376 for row in report['rounds']),'replay source counts/fixture differ'
   geometry(w,app,args.output,report,'completed')
   quick_decisions(w,app,args.output,report)
   assert opening.read_bytes()==opening_bytes and working.read_bytes()==first_completed_bytes,'later UI actions altered retained original checkpoints'
   lifecycle(report)
   report['result']='PASS';print('PASS match-handoff: actual product Qt/SDL; full original Malta18 state/events/board/ratings; frame+complete ACK; checkpoint replay; native layout/focus and lifecycle')
  except Exception as exc:
   report.update(result='FAIL',exception=type(exc).__name__,failure=str(exc));raise
  finally:
   presentation.stop();heartbeat.stop();w.close();w.deleteLater();app.processEvents()
   report['cleanup']={'window_closed':not w.isVisible(),'pending':bool(getattr(m,'match_pending',False)),
     'owned_processes_reaped':all(controller.process is None or controller.process.poll() is not None for controller in (w.jobs,w.watched,w.competitive))}
   sys.excepthook=previous_hook
   if report['uncaught_qt_callbacks']:report.update(result='FAIL',failure='uncaught Qt callback exceptions')
   (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
   assert not report['uncaught_qt_callbacks'],'uncaught Qt callback exceptions'
   assert report['cleanup']['window_closed'] and report['cleanup']['owned_processes_reaped'] and not report['cleanup']['pending'],'owned Qt/process cleanup incomplete'




def negative_controls(options):
 """[designed: T79] Serial saved-byte controls; no other source reader may run concurrently."""
 import subprocess
 out=Path(options.evidence_dir);out.mkdir(parents=True,exist_ok=False)
 cases=[
  ('render-mutation','goal2/desktop/pygame_viewer.py',"screen.fill(color('background'));lines=display.lines()","display.sequence+=1;screen.fill(color('background'));lines=display.lines()",'test_real_framebuffer_matches_original_text_projection','rendering mutated display state'),
  ('wrapped-board','goal2/desktop/pygame_viewer.py',"rows=wrapped(font,display.lines()[3:3+count],width) if font is not None else range(count)","rows=range(count)",'test_wrapped_commentary_lands_at_board_and_scroll_retains_tail','not greater than 1'),
  ('rating-tail','goal2/desktop/pygame_viewer.py',"for n,line in enumerate(rows[scroll:scroll+count]):","for n,line in enumerate(rows[scroll:scroll+count-1]):",'test_wrapped_commentary_lands_at_board_and_scroll_retains_tail','manual scroll lost the final rating row'),
  ('future-score','goal2/desktop/match_page.py',"pose=getattr(window,'_match_poses',{}).get(getattr(window.watched,'frame_ack',-1))","pose=(d.events[-1] if d.events and getattr(window.watched,'frame_ack',-1)>=0 else None)",'test_qt_score_uses_consumed_pose_not_future_ingress','First 1 — 0 Second')]
 receipt=[]
 for name,file,before,after,test,expected in cases:
  path=ROOT/file;saved=path.read_bytes();source=saved.decode();assert source.count(before)==1,(name,'mutation anchor differs')
  try:
   path.write_text(source.replace(before,after))
   command=[sys.executable,'-B','-m','unittest','goal2.tests.test_pygame_match_view.PresentationTests.'+test,'-v']
   run=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=120)
   log=run.stdout+run.stderr;(out/(name+'.log')).write_text(log)
   assert run.returncode!=0 and 'FAIL:' in log and '\nERROR:' not in log and expected in log,(name,'did not fail intended assertion',log)
   receipt.append({'name':name,'command':command,'returncode':run.returncode,'intended_assertion':expected,'mutant_sha256':sha(path),'restored_sha256':hashlib.sha256(saved).hexdigest()})
  finally:
   path.write_bytes(saved);assert path.read_bytes()==saved
 # [designed: T79] The real scenario must reject an actual source render mutation too.
 path=ROOT/'goal2/desktop/pygame_viewer.py';saved=path.read_bytes();source=saved.decode()
 before="    screen.fill(color('background'))\n    visible = display.visible()"
 assert source.count(before)==1
 try:
  path.write_text(source.replace(before,"    display.sequence += 1\n"+before))
  command=[sys.executable,'-B',str(ROOT/'tools/desktop-ui/redesign.py'),'--scenario','match-handoff','--template',str(options.template),'--data',str(options.data),'--evidence-dir',str(out/'real-scenario-render-mutation'),'--single-scale']
  run=subprocess.run(command,cwd=ROOT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,text=True,timeout=240)
  log=run.stdout+run.stderr;(out/'real-scenario-render-mutation.log').write_text(log)
  assert run.returncode!=0 and 'AssertionError: renderer changed Display state' in log,('real scenario missed render mutation',log)
  failed=json.loads((out/'real-scenario-render-mutation/report.json').read_text())
  assert failed['negative_control']['state_and_saves_preserved'] and failed['negative_control']['engine_and_viewer_reaped']
  receipt.append({'name':'real-scenario-render-mutation','command':command,'returncode':run.returncode,'intended_assertion':'renderer changed Display state','restored_sha256':hashlib.sha256(saved).hexdigest()})
 finally:
  path.write_bytes(saved);assert path.read_bytes()==saved
 (out/'controls.json').write_text(json.dumps({'result':'PASS','controls':receipt,'exact_saved_bytes_restored':True},indent=2)+'\n')
 print('PASS5 T79 intended rendering/read-only/board/future-score controls; exact source restored')
