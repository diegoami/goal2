#!/usr/bin/env python3
"""[designed: T79] Planning-only actual-original handoff oracle; main owns execution.
Runtime presentation mocks are not product implementation. No lifecycle/IPC changes.
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
ROOT=Path(__file__).resolve().parents[1]
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
state={'tag':'[designed: T79] planning-only runtime presentation instrumentation','mode':mode,'rendered':0,'last_frame':-1,'read_only':True,'captures':[]}
original=v.render_pitch;flip=pygame.display.flip;current=None;display=None
source=inspect.getsource(original).replace('screen.fill((18, 28, 37))','screen.fill(tuple(bytes.fromhex(COLORS["background"][1:])))').replace('(232, 239, 229)','tuple(bytes.fromhex(COLORS["text"][1:]))').replace('(232,239,229)','tuple(bytes.fromhex(COLORS["text"][1:]))')
namespace=dict(vars(v),COLORS=COLORS);exec(compile(source,'<T79 planning color mock>','exec'),namespace);paint=namespace['render_pitch']
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
 if mode=='mutate-render' and d.frame is not None:d.frame['score'][0]+=1
 result=paint(screen,font,d,scroll)
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
 if sys.platform=='win32' and 'windows_native' not in state:
  import ctypes
  from ctypes import wintypes
  u=ctypes.WinDLL('user32',use_last_error=True);h=pygame.display.get_wm_info()['window'];r=wintypes.RECT();a=wintypes.RECT()
  u.GetWindowRect.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.RECT)];u.GetDpiForWindow.argtypes=[wintypes.HWND];u.GetDpiForWindow.restype=wintypes.UINT
  assert u.GetWindowRect(h,ctypes.byref(r));assert u.SystemParametersInfoW(0x0030,0,ctypes.byref(a),0)
  state['windows_native']={'hwnd':h,'dpi_for_window':u.GetDpiForWindow(h),'window_rect':[r.left,r.top,r.right,r.bottom],'available_desktop':[a.left,a.top,a.right,a.bottom]}
 if current is not None and current['sequence']!=state['last_frame']:
  assert current['sequence']==state['last_frame']+1,'renderer skipped discrete frame'
  state['last_frame']=current['sequence'];state['rendered']+=1
  if len(state['captures'])<2:
   p=out/('frame-%s.png'%current['sequence']);pygame.image.save(surface,str(p));state['captures'].append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 if display is not None and display.result is not None and not state.get('complete'):
  state['complete']=True;state['display_lines_sha256']=digest(display.lines());state['display_result_sha256']=digest(display.result)
  p=out/'complete.png';pygame.image.save(surface,str(p));state['captures'].append({'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 receipt()
v.render_pitch=render;pygame.display.flip=postflip
sys.exit(v.main())
'''

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--mode',required=True,choices=('baseline','mock','mutate-render'))
 p.add_argument('--template',required=True);p.add_argument('--data',required=True)
 p.add_argument('--output',required=True,type=Path);p.add_argument('--repeat-rate',type=int,default=240)
 p.add_argument('--describe',action='store_true');args=p.parse_args()
 if args.describe:
  print(json.dumps({'planning_only':True,'modes':['baseline missing named surface','mock actual original parity','mutate-render intended read-only failure'],'qt_objects':['matchSurface','matchProvenance','matchScore','matchProgress'],'first_rate':60,'repeat_rate':args.repeat_rate,'viewer_code_sha256':hashlib.sha256(VIEWER.encode()).hexdigest()},indent=2));return
 args.output.mkdir(parents=True,exist_ok=False)
 report={'tag':'[designed: T79] PLANNING-ONLY actual original handoff','mode':args.mode,'platform':platform.platform(),'python':sys.version,'probe_sha256':sha(__file__),'resources':{'template':sha(args.template),'data':sha(args.data)},'sources':{str(f.relative_to(ROOT)):sha(f) for f in sorted((ROOT/'goal2/desktop').glob('*.py'))},'rounds':[],'captures':[],'limits':['Runtime-added Qt widgets/colors are planning mocks, not implementation','Qt scale does not establish SDL OS/paint scaling','Separate retained lifecycle suites remain mandatory']}
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
 report.update(qt=qVersion(),qpa=app.platformName(),requested_qt_scale=os.environ.get('QT_SCALE_FACTOR'))
 with tempfile.TemporaryDirectory(prefix='T79-planning-') as folder:
  save=Path(folder)/'owned.g2save';m=DesktopModel.open(args.template,args.data,save,country=4);w=ManagementWindow(m);w.show();w.activateWindow();QTest.qWait(150)
  beats=[];heartbeat=QTimer();heartbeat.setInterval(5);heartbeat.timeout.connect(lambda:beats.append(time.monotonic()));heartbeat.start()
  presentation=QTimer();presentation.setInterval(30)
  def click(button):reveal(button);QTest.mouseClick(button,Qt.MouseButton.LeftButton);app.processEvents()
  try:
   report['qt_ratio']=w.devicePixelRatioF();report['qt_available']=[w.screen().availableGeometry().width(),w.screen().availableGeometry().height()]
   if args.mode!='baseline':
    panel=QFrame();panel.setObjectName('matchSurface');layout=QVBoxLayout(panel)
    panel.setStyleSheet('QFrame#matchSurface {background:'+COLORS['panel']+';border:1px solid '+COLORS['divider']+';} QLabel {color:'+COLORS['text']+';}')
    labels=[]
    for name in ('matchProvenance','matchScore','matchProgress'):
     label=QLabel();label.setObjectName(name);label.setWordWrap(True);layout.addWidget(label);labels.append(label)
    w.pages[3].content.insertWidget(1,panel)
    def update_surface():
     d=w.watched.display
     labels[0].setText('Original engine — friendly')
     if d is not None and d.countries:
      score=d.events[-1]['score'] if d.events else [0,0]
      labels[1].setText('%s %s — %s %s'%(d.countries[0],score[0],score[1],d.countries[1]))
      labels[2].setText('Original full-time board available in SDL' if d.result else 'Original engine running; Cancel match remains available')
    presentation.timeout.connect(update_surface);presentation.start();update_surface()
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
   original_start=w.watched.start
   for round_index in range(2):
    assert m.state.campaign.next_fixture.kind==1,'repeat is not a supported scheduled friendly'
    outcome,events=expected(control);before=copy.deepcopy(m.state);prior_save=save.read_bytes() if save.exists() else None
    child_output=args.output/('round-%s-sdl'%round_index)
    w.watched.viewer_command=[sys.executable,'-c',VIEWER,str(child_output),args.mode]
    rate=60 if round_index==0 else args.repeat_rate
    w.watched.start=original_start if round_index==0 else lambda **kw:original_start(playback_rate=rate,**kw)
    beats.clear();click(w.watch);assert w.watched.busy,w.status.text()
    engine=w.watched.engine.process;viewer=w.watched.process
    w.start_watched();w.start_match();assert w.watched.engine.process is engine and not w.jobs.busy,'duplicate handoff launched another job'
    def finished():
     metrics=child_output/'metrics.json'
     if metrics.exists():
      value=json.loads(metrics.read_text())
      assert value['read_only'],'renderer changed Display state'
     return not w.watched.busy
    pump(finished,app=app,timeout=360)
    assert m.state==control.state,'complete state/Memory/RNG/history differs from direct original'
    assert m.state.match_count==before.match_count+1 and len(beats)>5
    assert w.watched.display.events==json.loads(json.dumps(events)),'ordered original events differ'
    assert w.watched.display.result==completion(outcome,m.goaldat.player_names),'board/raw rating words/MOTM differ'
    assert w.watched.engine.outcome==outcome,'complete original outcome differs'
    assert w.watched.frames_enabled and w.watched.frame_ack==outcome.result['ticks']-1,'final rendered frame acknowledgement missing'
    pump(lambda:json.loads((child_output/'metrics.json').read_text()).get('complete',False),app=app,timeout=30)
    metrics=json.loads((child_output/'metrics.json').read_text())
    assert metrics['rendered']==outcome.result['ticks'] and metrics['read_only']
    assert (save.read_bytes() if save.exists() else None)==prior_save,'playing altered existing save bytes'
    after=copy.deepcopy(m.state)
    for _ in range(4):w.poll_watched();w.refresh();app.processEvents()
    assert m.state==after,'presentation refresh republished completed result'
    click(w.save);saved=save.read_bytes();click(w.resume)
    assert m.state==control.state and save.read_bytes()==saved,'Save/Resume lost complete original continuation'
    w.navigate(3);presentation.timeout.emit();app.processEvents();capture=args.output/('round-%s-qt.png'%round_index);assert w.grab().save(str(capture))
    report['captures'].append({'path':capture.name,'sha256':sha(capture)})
    report['rounds'].append({'round':round_index,'rate':rate,'default_rate_first':round_index==0,'fixture':outcome.result['index'],'countries':w.watched.display.countries,'ticks':outcome.result['ticks'],'final_ack':w.watched.frame_ack,'heartbeats':len(beats),'original_image_sha256':outcome.result['image_sha256'],'source_captain':before.captain,'source_tactics':before.country_tactics,'source_xi':before.starting_eleven,'source_seeds':[before.rng_seed_7b62,before.rng_seed_8336],'final_seeds':list(outcome.seeds),'full_exact_parity':True,'sdl_metrics_sha256':sha(child_output/'metrics.json')})
    w.watched.close_viewer();w.poll_watched();assert viewer.poll() is not None
   report['result']='PASS';print('PASS T79 planning-only actual original Malta18 handoff; full state/events/boards/ratings; real frame ACK; Save/Resume/repeat')
  except Exception as exc:
   report.update(result='FAIL',exception=type(exc).__name__,failure=str(exc));raise
  finally:
   presentation.stop();heartbeat.stop();w.close();w.deleteLater();app.processEvents()
   (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
