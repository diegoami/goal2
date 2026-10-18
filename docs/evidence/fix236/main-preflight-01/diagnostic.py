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
_m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT',Path('.cache/diagnostic-unused.g2save'),country=4)
_cls=type(_m.state);_old_eq=_cls.__eq__
def _audit_equal(self,other):
 result=_old_eq(self,other)
 if result is False and type(other)is _cls:
  print("DIAGNOSTIC differing state fields",[f.name for f in dataclasses.fields(self)if getattr(self,f.name)!=getattr(other,f.name)],flush=True)
  print("DIAGNOSTIC match counts",self.match_count,other.match_count,flush=True)
 return result
_cls.__eq__=_audit_equal
suite=unittest.defaultTestLoader.loadTestsFromName("goal2.tests.test_pygame_match_view.OriginalQtAcceptance")
r=unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if r.wasSuccessful()else 1)
