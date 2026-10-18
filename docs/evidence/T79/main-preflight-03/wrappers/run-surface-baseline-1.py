import os,sys,runpy,json,traceback
from pathlib import Path
os.environ['PYTHONPATH']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\python-libs-T78;C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\python-libs-T79'
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']='1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR']='0'
os.environ['SDL_VIDEODRIVER']='windows'
os.environ['SDL_AUDIODRIVER']='dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.environ['TMPDIR']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\tmp'
os.environ['TMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\tmp'
os.environ['TEMP']='C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\tmp'
sys.path[:0]=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\python-libs-T78', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\python-libs-T79']
import pygame,unicorn
assert sys.platform=="win32" and pygame.version.ver=="2.5.8" and unicorn.__version__=="2.1.4"
from PySide6.QtCore import QCoreApplication,QEvent
from PySide6.QtWidgets import QApplication
callbacks=[]
def callback_error(kind,error,tb):
 callbacks.append("".join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)
sys.excepthook=callback_error
sys.argv=['C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\T79-main-planning-probe.py', '--mode', 'baseline', '--output', 'C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\observations\\surface-baseline-1', '--render-scale', '1']
try:
 runpy.run_path('C:\\Users\\diego\\projects\\goal2-exe\\.goal2-validation\\T79-planning-ccc659fc804a-1792357903286503972\\.cache\\T79-main-planning-probe.py',run_name="__main__")
finally:
 app=QApplication.instance()
 if app is not None:
  QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
  assert not app.topLevelWidgets(),"owned planning Qt widgets remain"
 assert not callbacks,callbacks
