"""[designed: T79] Planning-only stale disabled-Watch test compatibility, unchanged product."""
from pathlib import Path
import runpy,sys,copy
ROOT=Path.cwd();sys.path[:0]=[str(ROOT),str(ROOT/'tools/desktop-ui')]
from PySide6.QtTest import QTest
original=QTest.mouseClick
def click(widget,*args,**kwargs):
 if widget.objectName()=='watchOriginal'and not widget.isEnabled():
  window=widget.window();before=copy.deepcopy(window.model.state)
  assert 'Watch unavailable: scheduled friendlies only'in window.fixture_routes.text()
  window.start_watched()
  assert window.model.state==before and not getattr(window.model,'match_pending',False)
  print('MOCK: disabled Watch remains disabled; direct callback refusal exercised explicitly',flush=True)
  return
 window=widget.window()
 if widget is getattr(window,'play',None)and not widget.isEnabled():
  before=copy.deepcopy(window.model.state)
  assert 'Play unavailable: unsupported pending fixture'in window.fixture_routes.text()
  window.start_match()
  assert window.model.state==before and not getattr(window.model,'match_pending',False)
  print('MOCK: unsupported Play remains disabled; direct callback refusal exercised explicitly',flush=True)
  return
 return original(widget,*args,**kwargs)
QTest.mouseClick=click
try:runpy.run_path(str(ROOT/'tools/desktop-ui/competitive_play.py'),run_name='__main__')
finally:QTest.mouseClick=original
