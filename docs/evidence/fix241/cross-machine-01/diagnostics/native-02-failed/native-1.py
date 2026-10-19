import os,sys,runpy
os.environ['PYTHONPATH']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T78;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T79'
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\tmp'
sys.path[:0]=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\tools\\desktop-ui', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T78', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\python-libs-T79']
assert sys.platform=="win32"
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\tools\\desktop-ui\\player-browsing.py', '--source-head', '7560fbc336fa0efd6ea188c3739eb66e6460df63', '--template', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\e010-r0008-halftime.sav', '--data', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\.cache\\GOAL.DAT', '--evidence-dir', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\observations\\scale-1']
try:
 runpy.run_path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\fix241-production-7560fbc336fa-1792394491870788399\\tools\\desktop-ui\\player-browsing.py',run_name="__main__")
finally:
 app=QApplication.instance()
 if app is not None:
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
  assert not app.topLevelWidgets(),"owned Qt widgets remain"
