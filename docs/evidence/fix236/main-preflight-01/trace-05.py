import os,sys,unittest,json
os.environ['PYTHONPATH']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\tools\\desktop-ui;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\python-libs-T78;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\python-libs-T79'
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\tmp'
sys.path[:0]=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\tools\\desktop-ui', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\python-libs-T78', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-original-baseline-1792350834010012560\\.cache\\python-libs-T79']
import pygame,unicorn
assert pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"

import dataclasses,traceback
from goal2.desktop.watched import WatchedController
from goal2.desktop.model import DesktopModel
from pathlib import Path
_original_poll=WatchedController.poll
def _audit_poll(self):
 try:return _original_poll(self)
 except BaseException as exc:
  print("DIAGNOSTIC controller exception",repr(exc),flush=True)
  traceback.print_exc()
  raise
WatchedController.poll=_audit_poll

_original_cancel=WatchedController.cancel
_audit_dir=Path('.cache/viewer-diagnostic-05');_audit_dir.mkdir(exist_ok=False)
_counter=[0]
def _audit_cancel(self,*args,**kwargs):
 _counter[0]+=1
 print('DIAGNOSTIC cancel viewer code',None if self.process is None else self.process.poll(),flush=True)
 for name,handle in [('viewer',self.errors),('engine',getattr(self.engine,'_errors',None))]:
  if handle is not None:
   try:
    raw=Path(handle.name).read_bytes();(_audit_dir/(str(_counter[0])+'-'+name+'.log')).write_bytes(raw)
    print('DIAGNOSTIC '+name+' stderr',raw.decode(errors='replace'),flush=True)
   except OSError as exc:print('DIAGNOSTIC stderr read',repr(exc),flush=True)
 if self.directory is not None:
  status=self.directory/'status'
  if status.is_file():
   print('DIAGNOSTIC status',status.read_text(),flush=True)
 return _original_cancel(self,*args,**kwargs)
WatchedController.cancel=_audit_cancel
_m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT',Path('.cache/diagnostic-unused.g2save'),country=4)
_cls=type(_m.state);_old_eq=_cls.__eq__
def _audit_equal(self,other):
 result=_old_eq(self,other)
 if result is False and type(other)is _cls:
  print("DIAGNOSTIC differing state fields",[f.name for f in dataclasses.fields(self)if getattr(self,f.name)!=getattr(other,f.name)],flush=True)
  print("DIAGNOSTIC match counts",self.match_count,other.match_count,flush=True)
 return result
_cls.__eq__=_audit_equal

_original_init=WatchedController.__init__
def _mock_viewer_init(self,*args,**kwargs):
 if kwargs.get('viewer_command')is None:kwargs['viewer_command']=[sys.executable,str(Path(__file__).with_name('viewer-retry-mock.py'))]
 _original_init(self,*args,**kwargs)
WatchedController.__init__=_mock_viewer_init

def _trace(frame,event,arg):
 if frame.f_code.co_filename.endswith(('desktop\\watched.py','game\\watched_jobs.py')):
  if event=='exception':print('DIAGNOSTIC original exception',frame.f_code.co_filename,frame.f_code.co_name,frame.f_lineno,repr(arg[1]),flush=True)
  return _trace
 return None
sys.settrace(_trace)
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from goal2.desktop.window import ManagementWindow
app=QApplication([]);m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT',Path('.cache/diagnostic-unused.g2save'),country=4)
m.confirm(list(m.state.starting_eleven),m.state.starting_eleven[0],m.state.country_tactics)
w=ManagementWindow(m);w.show();QTest.qWait(100)
_original_start=w.watched.start
w.watched.start=lambda **kw:_original_start(frames=False,**kw)
w.start_watched()
print('DIAGNOSTIC started',w.watched.busy,w.status.text(),flush=True)
import time
_deadline=time.monotonic()+120
try:
 while w.watched.busy and time.monotonic()<_deadline:QTest.qWait(10)
 print('DIAGNOSTIC finished',w.watched.busy,w.status.text(),'match_count',m.state.match_count,flush=True)
finally:
 w.close();app.processEvents();sys.settrace(None)
