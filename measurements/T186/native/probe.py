"""T186 supporting probe: packaged Windows Qt, isolated profile, never activated.
All post-import card/match packets are declared UI fixtures, not engine outcomes.
"""
import argparse,ctypes,hashlib,json,os,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--cache',type=Path,required=True)
p.add_argument('--out',type=Path,required=True);p.add_argument('--hashes',type=Path,required=True);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=True);report={'cases':[],'passed':False,'kind':'native packaged rendering; declared UI packets','requested_factor':os.environ.get('QT_SCALE_FACTOR')}
window=None;app=None;stage='startup'
try:
 import goal2
 from PySide6.QtWidgets import QApplication
 from PySide6.QtCore import Qt
 from goal2.ui import theme
 from goal2.ui.window import Window
 from goal2.desktop import fixed_page,data_setup
 root=a.root.resolve();where=Path(goal2.__file__).resolve()
 assert root/'python' in where.parents,where
 report.update(goal2=str(where),python=sys.executable,profile_isolated=True)
 package=where.parent
 for name,value in json.loads(a.hashes.read_text()).items():
  assert hashlib.sha256((package/name).read_bytes()).hexdigest()==value,('wrong packaged source',name)
 app=QApplication([]);theme.install(app)
 assert app.platformName()=='windows',app.platformName()
 report['qpa']=app.platformName();report['font_family']=app.font().family();report['font_baseline']=theme.TEXT
 target=data_setup.paths(a.out/'private-profile')
 window=Window(target,choose=lambda:str(a.cache))
 window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating,True)
 window.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus,True)
 # Enforce NOACTIVATE on this probe's own HWND before it is shown; no other window is touched.
 user32=ctypes.WinDLL('user32',use_last_error=True)
 getstyle=user32.GetWindowLongPtrW;getstyle.argtypes=[ctypes.c_void_p,ctypes.c_int];getstyle.restype=ctypes.c_ssize_t
 setstyle=user32.SetWindowLongPtrW;setstyle.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_ssize_t];setstyle.restype=ctypes.c_ssize_t
 foreground=user32.GetForegroundWindow;foreground.restype=ctypes.c_void_p
 hwnd=int(window.winId());setstyle(hwnd,-20,getstyle(hwnd,-20)|0x08000000)
 assert getstyle(hwnd,-20)&0x08000000
 area=app.primaryScreen().availableGeometry()
 window.resize(min(1440,area.width()-40),min(900,area.height()-70));window.move(area.x()+20,area.y()+20)
 window.show();window.lower();window.start()
 def pump():
  until=time.monotonic()+.15
  while time.monotonic()<until:app.processEvents();time.sleep(.005)
  current=int(window.winId())
  assert getstyle(current,-20)&0x08000000,'NOACTIVATE was not retained'
  assert int(foreground() or 0)!=current,'probe became the foreground window'
 def capture(name):
  pump();issues=fixed_page.problems(window)
  path=a.out/(name+'.png');assert window.grab().save(str(path))
  report['cases'].append(dict(name=name,window=[window.width(),window.height()],page_scale=window.frame.scale,
   device_pixel_ratio=window.devicePixelRatioF(),foreground=False,problems=issues,screenshot=path.name,
   sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  return issues
 stage='font_baseline';first=capture('first-start')
 measured=window.current().name_label.font().pixelSize()
 report['rendered_label_px']=measured
 assert abs(measured-round(theme.TEXT*window.frame.scale))<=1,(measured,theme.TEXT,window.frame.scale)
 assert theme.TEXT>=24,('font baseline',theme.TEXT,'expected at least24')
 assert not first,first
 stage='native_packets'
 assert window.current().choose_and_import()
 assert not capture('start')
 from goal2.ui.s04_country import new_career
 owner=new_career(target,2,2028,'K Ees');window.open_career(owner)
 assert not capture('desk')
 from goal2.ui.match_day import for_window
 from goal2.ui.s15_match_menu import MenuScreen
 day=for_window(window,owner);day.fixture=owner.state.campaign.next_fixture;day.watch=True
 window.push(MenuScreen(window,day,'before'))
 assert not capture('match-menu')
 from goal2.ui.s17_pitch import MatchController,PitchScreen
 class Bridge:
  busy=True;token='native-packet';reports=[];waiting=None
  def start(self,*args,**kw):return self.token
  def poll(self,*args):return []
  def poll_frames(self,*args):return []
  def frames_drained(self):return True
  def ack_frames(self,*args):pass
  def close(self):self.busy=False
  def cancel_and_reap(self,*args):self.busy=False
 controller=MatchController(owner,day.fixture,Bridge());controller.start()
 pitch=window.push(PitchScreen(window,owner,controller));pitch.timer.stop()
 for minute in (12,13):
  event=dict(kind='commentary',minute=minute,score=[0,0],data={'text':'A player with a long surname scored after an assist from another named player.'})
  controller._send('event',event);controller.events.append(event)
 controller.released=len(controller.events);pitch.refresh()
 assert not capture('packet-pitch')
 pitch.toggle_commentary();assert not capture('packet-paused-reading');pitch.toggle_commentary()
 window.pop()
 from types import SimpleNamespace
 from goal2.ui.s19_bench import BenchAnswer,BenchScreen
 words=owner.state.managed_squad;off,on=words[1],words[12]
 decision=SimpleNamespace(minute=45,score=[0,0],data=dict(context='half_time',eleven=words[:11],bench=words[11:],
  substitutions_now=True,substitutions_left=5,injured=[off],positions=[[w,owner.state.players[w][6]] for w in words]))
 answer=BenchAnswer(owner,decision)
 names=(owner.goaldat.country_names[day.fixture.side_a],owner.goaldat.country_names[day.fixture.side_b])
 bench=window.push(BenchScreen(window,owner,answer,names=names));bench.row=1;bench.refresh()
 assert not capture('packet-injured-bench')
 answer.enter(off);answer.enter(on);bench.refresh();assert not capture('packet-chosen-pair')
 window.pop()
 refusal=dict(context='half_time',asked=[[off,on]],made=[],requested=[],substitutions_left=0,
  refused=[[off,on,'no more substitutes']])
 window.push(BenchScreen(window,owner,answer,names=names,report=refusal))
 assert not capture('packet-refusal-no-more')
 report['no_activation']=True;report['passed']=True
except BaseException as error:
 report.update(stage=stage,error=type(error).__name__+': '+str(error))
finally:
 if window is not None:
  window.leave()
  if app:app.processEvents()
 (a.out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report.get(k) for k in ('passed','qpa','font_baseline','rendered_label_px','stage','error')}))
raise SystemExit(0 if report['passed'] else 1)
