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
_audit_dir=Path('.cache/viewer-diagnostic-06');_audit_dir.mkdir(exist_ok=False)
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

import inspect
from goal2.desktop import watched as _watched_module
_poll_source=inspect.getsource(_original_poll)
_anchor="                with path.open('rb') as stream:\n                    data = stream.read(4097)\n"
_replacement="""                try:
                    with path.open('rb') as stream:
                        data = stream.read(4097)
                except PermissionError as exc:
                    if sys.platform!='win32' or getattr(exc,'winerror',None)!=5:raise
                    now=time.monotonic()
                    if getattr(self,'_mock_read_deadline',None)is None:self._mock_read_deadline=now+.25
                    if now>=self._mock_read_deadline:raise
                    print('MOCK deferred transient Windows status read',flush=True)
                    return False
                self._mock_read_deadline=None
"""
assert _poll_source.count(_anchor)==1
_namespace=dict(vars(_watched_module));exec(compile('if True:\n'+_poll_source.replace(_anchor,_replacement),'<runtime-only bounded status-read mock>','exec'),_namespace)
_original_poll=_namespace['poll']
_base_close=WatchedController.close_viewer
_base_cancel=_original_cancel
def _bounded_close(self):
 refs={name:getattr(self,name) for name in('process','folder','errors','stream','directory')}
 folder=self.folder
 if folder is None:return _base_close(self)
 cleanup=folder.cleanup
 def bounded():
  deadline=time.monotonic()+.5
  while True:
   try:return cleanup()
   except PermissionError as exc:
    remaining=deadline-time.monotonic()
    if sys.platform!='win32'or getattr(exc,'winerror',None)!=32 or remaining<=0:raise
    print('MOCK retried transient Windows owned-viewer cleanup',flush=True)
    time.sleep(min(.02,remaining))
    if time.monotonic()>=deadline:raise
 folder.cleanup=bounded
 try:return _base_close(self)
 except BaseException:
  for name,value in refs.items():setattr(self,name,value)
  raise
 finally:folder.cleanup=cleanup
def _bounded_cancel(self,*args,**kwargs):
 owned=self._pending_owned
 try:return _base_cancel(self,*args,**kwargs)
 except BaseException:
  if owned:self._pending_owned=True;self.model.match_pending=True
  raise
WatchedController.close_viewer=_bounded_close
_original_cancel=_bounded_cancel
suite=unittest.defaultTestLoader.loadTestsFromName("goal2.tests.test_pygame_match_view.OriginalQtAcceptance")
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if r.wasSuccessful()else 1)
