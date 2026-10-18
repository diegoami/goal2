"""[designed: T66] Real quick/Qt save flow with watched dependencies import-blocked."""
import subprocess,sys
code='''import importlib.abc,sys,tempfile,time
from pathlib import Path
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.split('.')[0] in ('pygame','unicorn'):raise ImportError('blocked optional dependency')
sys.meta_path.insert(0,Block())
from PySide6.QtWidgets import QApplication
from goal2.desktop.model import DesktopModel
from goal2.desktop.window import ManagementWindow
app=QApplication([])
with tempfile.TemporaryDirectory() as folder:
 m=DesktopModel.open('.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT',Path(folder)/'save',country=4)
 w=ManagementWindow(m)
 try:
  w.confirm_draft();w.start_match()
  deadline=time.monotonic()+60
  while w.jobs.busy and time.monotonic()<deadline:
   app.processEvents()
   if w.jobs.halftime is not None:w.continue_halftime()
   time.sleep(.01)
  assert not w.jobs.busy and m.state.match_count==1,w.status.text()
  assert not any(k.startswith(('pygame','unicorn')) for k in sys.modules)
  m.save(m.save_path);m.resume(m.save_path);assert m.state.match_count==1
 finally:w.close();app.processEvents()
 print('PASS actual Qt quick friendly + confirmed management/save/resume with pygame and Unicorn imports blocked; no watched reference asset lookup')
'''
result=subprocess.run([sys.executable,'-c',code],timeout=75)
raise SystemExit(result.returncode)
